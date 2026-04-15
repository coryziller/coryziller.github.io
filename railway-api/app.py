"""
Reddit + Hacker News sentiment workflow — real backend.

Drop-in replacement for railway-api/app.py. This version runs the ENTIRE
workflow on demand when the form on coryziller.github.io is submitted:

    1. Live-scrape last 24h of NVIDIA GPU mentions from Reddit + HN
    2. Score sentiment with OpenAI (with a deterministic fallback if no key)
    3. Generate a ~30-second audio briefing with gTTS
    4. Email the report + MP3 attachment via Brevo

Designed to deploy to Render.com (or Fly.io) with no code changes. See
render.yaml and DEPLOY.md in this folder for the 5-minute deploy steps.

Required environment variables:
    BREVO_API_KEY      — Brevo transactional API key
    SENDER_EMAIL       — verified sender in Brevo (e.g. demo@coryziller.com)
Optional:
    OPENAI_API_KEY     — if set, uses gpt-4o-mini for sentiment; otherwise
                         uses a built-in lexicon scorer so the demo still works
    ALLOWED_ORIGIN     — CORS origin (default: https://coryziller.github.io)
"""

from __future__ import annotations

import base64
import io
import json
import logging
import os
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

from flask import Flask, jsonify, request
from flask_cors import CORS
from gtts import gTTS
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('sentiment-demo')

app = Flask(__name__)
ALLOWED_ORIGIN = os.environ.get('ALLOWED_ORIGIN', 'https://coryziller.github.io')
CORS(app, resources={r'/*': {'origins': [ALLOWED_ORIGIN, 'http://localhost:*']}})

QUERY = 'nvidia gpu'
USER_AGENT = 'coryziller-portfolio/2.0 (contact: coryziller@gmail.com)'


# ---------------------------------------------------------------------------
# 1. Scraping
# ---------------------------------------------------------------------------

def _http_get_json(url: str, timeout: int = 15) -> dict:
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def fetch_reddit(limit: int = 25) -> list[dict]:
    """Last 24h of Reddit results for the query, sorted by recency."""
    url = (
        'https://www.reddit.com/search.json'
        f'?q={urllib.parse.quote_plus(QUERY)}'
        '&sort=new&t=day'
        f'&limit={limit}'
    )
    data = _http_get_json(url)
    out = []
    for c in data.get('data', {}).get('children', []):
        p = c.get('data', {})
        out.append({
            'source': 'reddit',
            'title': p.get('title', '').strip(),
            'text': (p.get('selftext') or '').strip()[:400],
            'score': p.get('score', 0),
            'num_comments': p.get('num_comments', 0),
            'subreddit': p.get('subreddit'),
            'url': f"https://www.reddit.com{p.get('permalink', '')}",
        })
    return out


def fetch_hackernews(limit: int = 25) -> list[dict]:
    """Last 24h of Hacker News stories/comments matching the query."""
    since = int(time.time()) - 86_400
    url = (
        'https://hn.algolia.com/api/v1/search_by_date'
        f'?query={urllib.parse.quote_plus(QUERY)}'
        f'&numericFilters=created_at_i>{since}'
        f'&hitsPerPage={limit}'
    )
    data = _http_get_json(url)
    out = []
    for h in data.get('hits', []):
        title = h.get('title') or h.get('story_title') or ''
        out.append({
            'source': 'hn',
            'title': title.strip(),
            'text': (h.get('comment_text') or h.get('story_text') or '')[:400],
            'score': h.get('points') or 0,
            'num_comments': h.get('num_comments') or 0,
            'url': f"https://news.ycombinator.com/item?id={h.get('objectID')}",
        })
    return [p for p in out if p['title']]


# ---------------------------------------------------------------------------
# 2. Sentiment
# ---------------------------------------------------------------------------

_POS = {
    'love', 'great', 'amazing', 'awesome', 'fantastic', 'incredible', 'best',
    'excellent', 'fast', 'smooth', 'impressive', 'solid', 'reliable', 'worth',
    'happy', 'recommend', 'beats', 'wins', 'upgrade',
}
_NEG = {
    'bad', 'terrible', 'awful', 'worst', 'broken', 'crash', 'crashes', 'fails',
    'disappointed', 'slow', 'overpriced', 'scam', 'hate', 'issue', 'issues',
    'problem', 'problems', 'bug', 'bugs', 'driver', 'overheat', 'overheats',
    'expensive',
}


def score_one_lexicon(text: str) -> float:
    words = re.findall(r"[a-z']+", text.lower())
    pos = sum(1 for w in words if w in _POS)
    neg = sum(1 for w in words if w in _NEG)
    if pos == 0 and neg == 0:
        return 50.0
    return round(100 * pos / max(pos + neg, 1), 1)


def score_posts(posts: list[dict]) -> list[dict]:
    """Attach a 0–100 sentiment score to each post."""
    api_key = os.environ.get('OPENAI_API_KEY')
    if api_key and posts:
        try:
            return _score_with_openai(posts, api_key)
        except Exception as e:  # pragma: no cover
            log.warning('OpenAI scoring failed, using lexicon fallback: %s', e)

    for p in posts:
        p['sentiment'] = score_one_lexicon(f"{p['title']} {p['text']}")
    return posts


def _score_with_openai(posts: list[dict], api_key: str) -> list[dict]:
    """Batch-score sentiment with gpt-4o-mini. One call, strict JSON."""
    snippets = [
        {'i': i, 'text': f"{p['title']}. {p['text']}"[:500]}
        for i, p in enumerate(posts)
    ]
    body = {
        'model': 'gpt-4o-mini',
        'messages': [{
            'role': 'user',
            'content': (
                'Score each snippet below for sentiment about NVIDIA/GPUs on a '
                '0 (very negative) to 100 (very positive) scale. Return ONLY '
                'JSON: {"scores":[{"i":0,"s":72}, ...]}\n\n'
                + json.dumps(snippets)
            ),
        }],
        'response_format': {'type': 'json_object'},
        'temperature': 0.0,
    }
    req = urllib.request.Request(
        'https://api.openai.com/v1/chat/completions',
        data=json.dumps(body).encode('utf-8'),
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        resp = json.loads(r.read().decode('utf-8'))
    content = resp['choices'][0]['message']['content']
    data = json.loads(content)
    by_i = {row['i']: row['s'] for row in data.get('scores', [])}
    for i, p in enumerate(posts):
        p['sentiment'] = float(by_i.get(i, score_one_lexicon(p['title'])))
    return posts


# ---------------------------------------------------------------------------
# 3. Report + audio
# ---------------------------------------------------------------------------

def build_report(posts: list[dict]) -> dict:
    if not posts:
        return {
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'total_posts': 0,
            'avg_sentiment': 50.0,
            'overall_label': 'No chatter',
            'by_source': {},
            'top_positive': [],
            'top_negative': [],
        }

    avg = round(sum(p['sentiment'] for p in posts) / len(posts), 1)
    if avg >= 65: label = 'Positive'
    elif avg >= 55: label = 'Mildly positive'
    elif avg >= 45: label = 'Mixed'
    elif avg >= 35: label = 'Mildly negative'
    else: label = 'Negative'

    by_source: dict[str, dict] = {}
    for src in ('reddit', 'hn'):
        sp = [p for p in posts if p['source'] == src]
        if sp:
            by_source[src] = {
                'count': len(sp),
                'avg_sentiment': round(sum(p['sentiment'] for p in sp) / len(sp), 1),
            }

    ranked = sorted(posts, key=lambda p: p['sentiment'], reverse=True)
    return {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'total_posts': len(posts),
        'avg_sentiment': avg,
        'overall_label': label,
        'by_source': by_source,
        'top_positive': ranked[:3],
        'top_negative': ranked[-3:][::-1],
    }


def audio_script(name: str, report: dict) -> str:
    total = report['total_posts']
    label = report['overall_label']
    avg = report['avg_sentiment']

    if total == 0:
        return (f"Hi {name}, this is Cory with your NVIDIA GPU sentiment briefing. "
                "No fresh posts in the last 24 hours. Check the attached report for context.")

    top = (report['top_positive'] or [None])[0]
    bot = (report['top_negative'] or [None])[0]
    top_line = f" Most positive chatter: {top['title'][:120]}." if top else ''
    bot_line = f" Most negative chatter: {bot['title'][:120]}." if bot else ''

    return (
        f"Hi {name}, this is Cory Ziller with your NVIDIA GPU sentiment briefing. "
        f"In the last 24 hours I analyzed {total} posts across Reddit and Hacker News. "
        f"Overall sentiment is {label}, averaging {avg} out of 100.{top_line}{bot_line} "
        "The full report is attached. Thanks for checking out my work!"
    )


def synth_audio(script: str) -> bytes:
    tts = gTTS(text=script, lang='en', slow=False)
    buf = io.BytesIO()
    tts.write_to_fp(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# 4. Email
# ---------------------------------------------------------------------------

def format_email_body(name: str, report: dict) -> str:
    now = datetime.now().strftime('%B %d, %Y')
    lines = [
        f"Hi {name},",
        '',
        "Thanks for trying the Reddit & Hacker News sentiment workflow demo.",
        '',
        f"NVIDIA GPU sentiment report — {now}",
        f"  Posts analyzed: {report['total_posts']}",
        f"  Overall sentiment: {report['overall_label']} ({report['avg_sentiment']}/100)",
    ]
    for src, stats in report.get('by_source', {}).items():
        src_name = 'Reddit' if src == 'reddit' else 'Hacker News'
        lines.append(f"    {src_name}: {stats['count']} posts, avg {stats['avg_sentiment']}/100")

    if report['top_positive']:
        lines += ['', 'Top positive chatter:']
        for p in report['top_positive']:
            lines.append(f"  • [{p['sentiment']}/100] {p['title'][:140]}")
            lines.append(f"    {p['url']}")

    if report['top_negative']:
        lines += ['', 'Top negative chatter:']
        for p in report['top_negative']:
            lines.append(f"  • [{p['sentiment']}/100] {p['title'][:140]}")
            lines.append(f"    {p['url']}")

    lines += [
        '',
        'Attached is a ~30-second audio briefing generated just for you.',
        '',
        'Best,',
        'Cory Ziller',
        'https://coryziller.github.io',
    ]
    return '\n'.join(lines)


def send_email(name: str, email: str, report: dict, audio: bytes) -> str:
    api_key = os.environ.get('BREVO_API_KEY')
    sender = os.environ.get('SENDER_EMAIL', 'demo@coryziller.com')
    if not api_key:
        raise RuntimeError('BREVO_API_KEY not set')

    cfg = sib_api_v3_sdk.Configuration()
    cfg.api_key['api-key'] = api_key
    client = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(cfg))

    attachment = [{
        'content': base64.b64encode(audio).decode('utf-8'),
        'name': f"nvidia_sentiment_{name.replace(' ', '_') or 'report'}.mp3",
    }]

    msg = sib_api_v3_sdk.SendSmtpEmail(
        to=[{'email': email, 'name': name or email}],
        sender={'email': sender, 'name': 'Cory Ziller'},
        reply_to={'email': 'coryziller@gmail.com', 'name': 'Cory Ziller'},
        subject=f"Your NVIDIA GPU sentiment report — {datetime.now().strftime('%b %d, %Y')}",
        text_content=format_email_body(name, report),
        attachment=attachment,
    )
    resp = client.send_transac_email(msg)
    return getattr(resp, 'message_id', '') or ''


# ---------------------------------------------------------------------------
# HTTP endpoints
# ---------------------------------------------------------------------------

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'has_brevo_key': bool(os.environ.get('BREVO_API_KEY')),
        'has_openai_key': bool(os.environ.get('OPENAI_API_KEY')),
    })


@app.route('/preview', methods=['GET'])
def preview():
    """Run the full pipeline end-to-end WITHOUT sending email — for smoke testing."""
    reddit_posts = fetch_reddit()
    hn_posts = fetch_hackernews()
    posts = score_posts(reddit_posts + hn_posts)
    return jsonify(build_report(posts))


@app.route('/send-demo', methods=['POST', 'OPTIONS'])
def send_demo():
    if request.method == 'OPTIONS':
        return '', 200

    data: dict[str, Any] = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()[:120]
    email = (data.get('email') or '').strip()[:200]

    if not email or not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
        return jsonify({'ok': False, 'error': 'Valid email required'}), 400
    if not name:
        name = email.split('@', 1)[0]

    try:
        log.info('send-demo start: %s', email)
        reddit_posts = fetch_reddit()
        hn_posts = fetch_hackernews()
        log.info('scraped: reddit=%d hn=%d', len(reddit_posts), len(hn_posts))

        posts = score_posts(reddit_posts + hn_posts)
        report = build_report(posts)
        log.info('report: total=%d label=%s avg=%.1f',
                 report['total_posts'], report['overall_label'], report['avg_sentiment'])

        audio = synth_audio(audio_script(name, report))
        log.info('audio: %d bytes', len(audio))

        message_id = send_email(name, email, report, audio)
        log.info('email sent: %s message_id=%s', email, message_id)

        return jsonify({
            'ok': True,
            'posts_analyzed': report['total_posts'],
            'overall_label': report['overall_label'],
            'message_id': message_id,
        })
    except ApiException as e:
        log.exception('brevo api error')
        return jsonify({'ok': False, 'error': 'Email provider error', 'details': str(e)}), 502
    except Exception as e:
        log.exception('send-demo failed')
        return jsonify({'ok': False, 'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)
