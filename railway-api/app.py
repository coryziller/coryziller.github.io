"""
Reddit + Hacker News sentiment workflow — real backend.

Drop-in replacement for railway-api/app.py. This version runs the ENTIRE
workflow on demand when the form on coryziller.github.io is submitted:

    1. Live-scrape last 24h of NVIDIA GPU mentions from Reddit + HN
    2. Score sentiment with OpenAI (with a deterministic fallback if no key)
    3. Generate a ~30-second audio briefing with gTTS
    4. Email the report + MP3 attachment via Brevo

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
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from threading import Lock
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
# Scrape cache — avoids hammering Reddit/HN on every form submission.
# Results are reused for SCRAPE_CACHE_TTL seconds. On a 429 we fall back
# to cached data rather than surfacing a raw HTTP error.
# ---------------------------------------------------------------------------
SCRAPE_CACHE_TTL = 300  # 5 minutes

_scrape_cache: dict[str, Any] = {'reddit': [], 'hn': [], 'ts': 0.0}
_scrape_lock = Lock()

# ---------------------------------------------------------------------------
# Per-IP rate limiter for /send-demo (max 1 request per 60s per IP)
# ---------------------------------------------------------------------------
RATE_LIMIT_WINDOW = 60
_rate_limit: dict[str, float] = {}
_rate_lock = Lock()


def _check_rate_limit(ip: str) -> bool:
    now = time.time()
    with _rate_lock:
        last = _rate_limit.get(ip, 0.0)
        if now - last < RATE_LIMIT_WINDOW:
            return False
        _rate_limit[ip] = now
        cutoff = now - RATE_LIMIT_WINDOW * 10
        for k in [k for k, v in _rate_limit.items() if v < cutoff]:
            del _rate_limit[k]
    return True


# ---------------------------------------------------------------------------
# 1. Scraping
# ---------------------------------------------------------------------------

def _http_get_json(url: str, timeout: int = 15) -> dict:
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def fetch_reddit(limit: int = 25) -> list[dict]:
    now = time.time()
    with _scrape_lock:
        cache_age = now - _scrape_cache['ts']
        if _scrape_cache['ts'] and cache_age < SCRAPE_CACHE_TTL:
            log.info('Reddit: cache hit (age %.0fs)', cache_age)
            return list(_scrape_cache['reddit'])

    url = (
        'https://www.reddit.com/search.json'
        f'?q={urllib.parse.quote_plus(QUERY)}&sort=new&t=day&limit={limit}'
    )
    try:
        data = _http_get_json(url)
    except urllib.error.HTTPError as e:
        if e.code == 429:
            with _scrape_lock:
                cached = list(_scrape_cache['reddit'])
            if cached:
                log.warning('Reddit 429 — using cached data (%d posts)', len(cached))
                return cached
            raise RuntimeError(
                'Reddit is temporarily rate-limiting requests. '
                'Please wait 60 seconds and try again.'
            ) from e
        raise

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
    with _scrape_lock:
        _scrape_cache['reddit'] = out
        _scrape_cache['ts'] = time.time()
    return out


def fetch_hackernews(limit: int = 25) -> list[dict]:
    since = int(time.time()) - 86_400
    url = (
        'https://hn.algolia.com/api/v1/search_by_date'
        f'?query={urllib.parse.quote_plus(QUERY)}'
        f'&numericFilters=created_at_i>{since}&hitsPerPage={limit}'
    )
    try:
        data = _http_get_json(url)
    except urllib.error.HTTPError as e:
        if e.code == 429:
            with _scrape_lock:
                cached = list(_scrape_cache['hn'])
            if cached:
                log.warning('HN 429 — using cached data (%d posts)', len(cached))
                return cached
            raise RuntimeError(
                'Hacker News is temporarily rate-limiting. Please wait 60 seconds and try again.'
            ) from e
        raise

    out = [
        {
            'source': 'hn',
            'title': (h.get('title') or h.get('story_title') or '').strip(),
            'text': (h.get('comment_text') or h.get('story_text') or '')[:400],
            'score': h.get('points') or 0,
            'num_comments': h.get('num_comments') or 0,
            'url': f"https://news.ycombinator.com/item?id={h.get('objectID')}",
        }
        for h in data.get('hits', [])
    ]
    hn_results = [p for p in out if p['title']]
    with _scrape_lock:
        _scrape_cache['hn'] = hn_results
    return hn_results


# ---------------------------------------------------------------------------
# 2. Sentiment
# ---------------------------------------------------------------------------

_POS = {'love','great','amazing','awesome','fantastic','incredible','best','excellent',
        'fast','smooth','impressive','solid','reliable','worth','happy','recommend','beats','wins','upgrade'}
_NEG = {'bad','terrible','awful','worst','broken','crash','crashes','fails','disappointed',
        'slow','overpriced','scam','hate','issue','issues','problem','problems','bug','bugs',
        'driver','overheat','overheats','expensive'}


def score_one_lexicon(text: str) -> float:
    words = re.findall(r"[a-z']+", text.lower())
    pos = sum(1 for w in words if w in _POS)
    neg = sum(1 for w in words if w in _NEG)
    if pos == 0 and neg == 0:
        return 50.0
    return round(100 * pos / max(pos + neg, 1), 1)


def score_posts(posts: list[dict]) -> list[dict]:
    api_key = os.environ.get('OPENAI_API_KEY')
    if api_key and posts:
        try:
            return _score_with_openai(posts, api_key)
        except Exception as e:
            log.warning('OpenAI scoring failed, using lexicon fallback: %s', e)
    for p in posts:
        p['sentiment'] = score_one_lexicon(f"{p['title']} {p['text']}")
    return posts


def _score_with_openai(posts: list[dict], api_key: str) -> list[dict]:
    snippets = [{'i': i, 'text': f"{p['title']}. {p['text']}"[:500]} for i, p in enumerate(posts)]
    body = {
        'model': 'gpt-4o-mini',
        'messages': [{'role': 'user', 'content': (
            'Score each snippet for NVIDIA/GPU sentiment 0-100. '
            'Return ONLY JSON: {"scores":[{"i":0,"s":72},...]}\n\n' + json.dumps(snippets)
        )}],
        'response_format': {'type': 'json_object'},
        'temperature': 0.0,
    }
    req = urllib.request.Request(
        'https://api.openai.com/v1/chat/completions',
        data=json.dumps(body).encode('utf-8'),
        headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(json.loads(r.read().decode('utf-8'))['choices'][0]['message']['content'])
    by_i = {row['i']: row['s'] for row in data.get('scores', [])}
    for i, p in enumerate(posts):
        p['sentiment'] = float(by_i.get(i, score_one_lexicon(p['title'])))
    return posts


# ---------------------------------------------------------------------------
# 3. Report + audio
# ---------------------------------------------------------------------------

def build_report(posts: list[dict]) -> dict:
    if not posts:
        return {'generated_at': datetime.now(timezone.utc).isoformat(), 'total_posts': 0,
                'avg_sentiment': 50.0, 'overall_label': 'No chatter', 'by_source': {},
                'top_positive': [], 'top_negative': []}
    avg = round(sum(p['sentiment'] for p in posts) / len(posts), 1)
    label = ('Positive' if avg >= 65 else 'Mildly positive' if avg >= 55 else
             'Mixed' if avg >= 45 else 'Mildly negative' if avg >= 35 else 'Negative')
    by_source = {}
    for src in ('reddit', 'hn'):
        sp = [p for p in posts if p['source'] == src]
        if sp:
            by_source[src] = {'count': len(sp),
                              'avg_sentiment': round(sum(p['sentiment'] for p in sp) / len(sp), 1)}
    ranked = sorted(posts, key=lambda p: p['sentiment'], reverse=True)
    return {'generated_at': datetime.now(timezone.utc).isoformat(), 'total_posts': len(posts),
            'avg_sentiment': avg, 'overall_label': label, 'by_source': by_source,
            'top_positive': ranked[:3], 'top_negative': ranked[-3:][::-1]}


def audio_script(name: str, report: dict) -> str:
    total, label, avg = report['total_posts'], report['overall_label'], report['avg_sentiment']
    if total == 0:
        return f"Hi {name}, this is Cory with your NVIDIA GPU sentiment briefing. No fresh posts in the last 24 hours."
    top = (report['top_positive'] or [None])[0]
    bot = (report['top_negative'] or [None])[0]
    return (
        f"Hi {name}, this is Cory Ziller with your NVIDIA GPU sentiment briefing. "
        f"In the last 24 hours I analyzed {total} posts across Reddit and Hacker News. "
        f"Overall sentiment is {label}, averaging {avg} out of 100."
        + (f" Most positive: {top['title'][:120]}." if top else '')
        + (f" Most negative: {bot['title'][:120]}." if bot else '')
        + " The full report is attached. Thanks for checking out my work!"
    )


def synth_audio(script: str) -> bytes:
    buf = io.BytesIO()
    gTTS(text=script, lang='en', slow=False).write_to_fp(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# 4. Email
# ---------------------------------------------------------------------------

def format_email_body(name: str, report: dict, audio_filename: str) -> str:
    now = datetime.now().strftime('%b %d')
    return (
        f"Hi {name},\n\n"
        f"NVIDIA GPU sentiment, last 24h ({now}):\n"
        f"  {report['overall_label']} — {report['avg_sentiment']}/100 across {report['total_posts']} posts\n\n"
        f"LISTEN: a 30-second audio briefing is attached as {audio_filename}.\n\n"
        f"— Cory\n"
    )


def send_email(name: str, email: str, report: dict, audio: bytes) -> str:
    api_key = os.environ.get('BREVO_API_KEY')
    if not api_key:
        raise RuntimeError('BREVO_API_KEY not set')
    cfg = sib_api_v3_sdk.Configuration()
    cfg.api_key['api-key'] = api_key
    client = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(cfg))
    audio_filename = 'nvidia-gpu-audio-briefing.mp3'
    msg = sib_api_v3_sdk.SendSmtpEmail(
        to=[{'email': email, 'name': name or email}],
        sender={'email': os.environ.get('SENDER_EMAIL', 'demo@coryziller.com'), 'name': 'Cory Ziller'},
        reply_to={'email': 'coryziller@gmail.com', 'name': 'Cory Ziller'},
        subject=f"Your NVIDIA GPU sentiment report + audio briefing — {datetime.now().strftime('%b %d, %Y')}",
        text_content=format_email_body(name, report, audio_filename),
        attachment=[{'content': base64.b64encode(audio).decode('utf-8'), 'name': audio_filename}],
    )
    return getattr(client.send_transac_email(msg), 'message_id', '') or ''


# ---------------------------------------------------------------------------
# HTTP endpoints
# ---------------------------------------------------------------------------

@app.route('/health', methods=['GET'])
def health():
    with _scrape_lock:
        cache_age = time.time() - _scrape_cache['ts'] if _scrape_cache['ts'] else None
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'has_brevo_key': bool(os.environ.get('BREVO_API_KEY')),
        'has_openai_key': bool(os.environ.get('OPENAI_API_KEY')),
        'scrape_cache_age_seconds': round(cache_age, 1) if cache_age is not None else None,
        'scrape_cache_reddit_count': len(_scrape_cache['reddit']),
        'scrape_cache_hn_count': len(_scrape_cache['hn']),
    })


@app.route('/preview', methods=['GET'])
def preview():
    posts = score_posts(fetch_reddit() + fetch_hackernews())
    return jsonify(build_report(posts))


@app.route('/send-demo', methods=['POST', 'OPTIONS'])
def send_demo():
    if request.method == 'OPTIONS':
        return '', 200

    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr or 'unknown').split(',')[0].strip()
    if not _check_rate_limit(client_ip):
        return jsonify({'ok': False, 'error': 'You already submitted recently. Please wait 60 seconds and try again.'}), 429

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
        log.info('report: total=%d label=%s avg=%.1f', report['total_posts'], report['overall_label'], report['avg_sentiment'])
        audio = synth_audio(audio_script(name, report))
        log.info('audio: %d bytes', len(audio))
        message_id = send_email(name, email, report, audio)
        log.info('email sent: %s message_id=%s', email, message_id)
        return jsonify({'ok': True, 'posts_analyzed': report['total_posts'],
                       'overall_label': report['overall_label'], 'message_id': message_id})
    except ApiException as e:
        log.exception('brevo api error')
        return jsonify({'ok': False, 'error': 'Email provider error', 'details': str(e)}), 502
    except RuntimeError as e:
        log.warning('send-demo runtime error: %s', e)
        return jsonify({'ok': False, 'error': str(e)}), 503
    except Exception as e:
        log.exception('send-demo failed')
        return jsonify({'ok': False, 'error': str(e)}), 500


# ---------------------------------------------------------------------------
# Lyrics word-cloud endpoint
# ---------------------------------------------------------------------------

from concurrent.futures import ThreadPoolExecutor, as_completed

_LYRICS_CACHE: dict[str, list[str] | None] = {}
_LYRICS_LOCK = Lock()

_LYRIC_STOPWORDS = set("""
a about after ah all also am an and any are aren at be because been before
being below both but by can could cause cuz did didn do does don down during
each else even ever every for from get got gonna gotta had has have having he
her here hers him his how i if in into is isn it its just know let like ll
look ma made make makes making many may me might more most must my na nah no
not now o of off oh on once only or other our ours out over own re said say
says see should shouldn so some such than that the their them then there these
they this those though through to too uh um up upon us use used very wanna was
way we well were what when where which while who why will with would yeah yes
yet you your yours ya ll ve re
""".split())
_LYRIC_STOPWORDS.update({'ll','ve','re','em','ol','mm','hmm','huh','ooh','ohh','oo','ay','ayy',
    'yah','yo','im','ima','aint','ya','y','bout','cause','got','gonna','gotta','wanna','tryna',
    'lil','bro','one','two','three','baby'})

_WORD_RE = re.compile(r"[a-z']+")
_WORDCLOUD_CACHE: dict[str, dict] = {}
_WORDCLOUD_CACHE_LOCK = Lock()


def fetch_lyrics_ovh(artist: str, title: str, timeout: int = 12) -> str | None:
    key = f'{artist.lower().strip()}||{title.lower().strip()}'
    with _LYRICS_LOCK:
        if key in _LYRICS_CACHE:
            return _LYRICS_CACHE[key] or None
    try:
        url = f"https://api.lyrics.ovh/v1/{urllib.parse.quote(artist, safe='')}/{urllib.parse.quote(title, safe='')}"
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = json.loads(r.read().decode('utf-8', errors='replace'))
        text = (body.get('lyrics') or '').strip() or None
    except Exception as e:
        log.info('lyrics miss %r / %r: %s', artist, title, e)
        text = None
    with _LYRICS_LOCK:
        _LYRICS_CACHE[key] = text
    return text


def _clean_lyrics_words(text: str) -> list[str]:
    text = re.sub(r'\[[^\]]{0,40}\]', ' ', text)
    words = _WORD_RE.findall(text.lower())
    return [w.strip("'") for w in words if len(w) >= 3 and w not in _LYRIC_STOPWORDS and not w.isdigit()]


@app.route('/lyrics-wordcloud', methods=['POST', 'OPTIONS'])
def lyrics_wordcloud():
    if request.method == 'OPTIONS':
        return '', 200
    data: dict[str, Any] = request.get_json(silent=True) or {}
    year = str(data.get('year', '')).strip() or 'all'
    songs_in = data.get('songs') or []
    if not isinstance(songs_in, list) or not songs_in:
        return jsonify({'ok': False, 'error': 'songs[] required'}), 400

    normalized: list[dict] = []
    seen: set = set()
    for s in songs_in:
        artist = str(s.get('artist', '')).strip()
        track = str(s.get('track', '') or s.get('title', '')).strip()
        plays = int(s.get('play_count') or s.get('plays') or 1)
        key = (artist.lower(), track.lower())
        if not artist or not track or key in seen:
            continue
        seen.add(key)
        normalized.append({'artist': artist, 'track': track, 'plays': plays})
    normalized.sort(key=lambda x: x['plays'], reverse=True)
    normalized = normalized[:30]
    if not normalized:
        return jsonify({'ok': False, 'error': 'no valid songs provided'}), 400

    fp = '|'.join(f"{s['artist'].lower()}::{s['track'].lower()}" for s in normalized)
    cache_key = f"{year}:{datetime.now(timezone.utc).strftime('%Y-%m-%d')}:{hash(fp)}"
    with _WORDCLOUD_CACHE_LOCK:
        hit = _WORDCLOUD_CACHE.get(cache_key)
        if hit:
            return jsonify(hit)

    from collections import Counter
    counts: Counter = Counter()
    per_song: list[dict] = []

    def do_one(s: dict) -> tuple[dict, list[str]]:
        text = fetch_lyrics_ovh(s['artist'], s['track'])
        if not text:
            return {'artist': s['artist'], 'track': s['track'], 'plays': s['plays'], 'found': False}, []
        words = _clean_lyrics_words(text)
        return {'artist': s['artist'], 'track': s['track'], 'plays': s['plays'], 'found': True, 'word_count': len(words)}, words

    with ThreadPoolExecutor(max_workers=8) as pool:
        for info, words in [f.result() for f in as_completed([pool.submit(do_one, s) for s in normalized])]:
            per_song.append(info)
            if words:
                bag = Counter(words)
                for w, c in bag.items():
                    counts[w] += c * info.get('plays', 1)

    found = [p for p in per_song if p.get('found')]
    total_plays = sum(p['plays'] for p in per_song)
    found_plays = sum(p['plays'] for p in found)
    result = {
        'ok': True, 'year': year, 'words': counts.most_common(80),
        'stats': {
            'songs_considered': len(per_song), 'lyrics_found': len(found),
            'coverage_by_plays': round(100 * found_plays / total_plays, 1) if total_plays else 0.0,
            'total_words_counted': sum(counts.values()), 'unique_words': len(counts),
        },
        'songs': sorted(per_song, key=lambda p: p['plays'], reverse=True),
    }
    with _WORDCLOUD_CACHE_LOCK:
        _WORDCLOUD_CACHE[cache_key] = result
    return jsonify(result)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8000)), debug=False)
