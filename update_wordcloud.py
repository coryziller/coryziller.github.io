#!/usr/bin/env python3
"""
Word Cloud Precomputer (multi-source).

For each year in spotify-trends/top_songs_by_period.json:
  1. Aggregate top songs of that year.
  2. Fetch lyrics from LyricsOVH, LyricFind, Genius, AZLyrics, Lyrics.com,
     SongLyrics, STLyrics (musicals), AllMusicals (musicals), and a generic
     DDG HTML search fallback. First hit wins.
  3. Count words (stopword-filtered) weighted by play count.
  4. Write spotify-trends/wordclouds/<year>.json plus an index.json.

Output never includes raw lyrics; only aggregated word counts and per-song
metadata (artist/track/plays/found/word_count/source).
"""
from __future__ import annotations

import html
import json
import logging
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('wordcloud-updater')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'spotify-trends')
OUT_DIR = os.path.join(DATA_DIR, 'wordclouds')
TOP_SONGS_PATH = os.path.join(DATA_DIR, 'top_songs_by_period.json')

USER_AGENT = (
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 '
    '(KHTML, like Gecko) Version/17.0 Safari/605.1.15 coryziller-portfolio/2.0'
)

TOP_N_PER_YEAR = 30
MAX_WORKERS = 6
REQUEST_TIMEOUT = 12
TOP_WORDS_OUT = 80


# ---------------------------------------------------------------------------
# HTTP + slug helpers
# ---------------------------------------------------------------------------

def _http_get(url: str, timeout: int = REQUEST_TIMEOUT) -> Optional[str]:
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/json;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode('utf-8', errors='replace')
    except Exception as e:
        log.debug('GET %s failed: %s', url, e)
        return None


def _slug(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", '-', s).strip('-')
    return s.lower()


def _azlyrics_slug(s: str) -> str:
    s = s.lower()
    s = re.sub(r"^the\s+", '', s)
    return re.sub(r"[^a-z0-9]+", '', s)


def _strip_html(text: str) -> str:
    text = re.sub(r'(?is)<script.*?</script>', ' ', text)
    text = re.sub(r'(?is)<style.*?</style>', ' ', text)
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.I)
    text = re.sub(r'</(p|div|li)>', '\n', text, flags=re.I)
    text = re.sub(r'<[^>]+>', ' ', text)
    return html.unescape(text)


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------

def source_lyricsovh(artist: str, title: str) -> Optional[str]:
    url = ('https://api.lyrics.ovh/v1/'
           + urllib.parse.quote(artist, safe='')
           + '/' + urllib.parse.quote(title, safe=''))
    body = _http_get(url)
    if not body:
        return None
    try:
        data = json.loads(body)
    except Exception:
        return None
    text = (data.get('lyrics') or '').strip()
    return text or None


def source_lyricfind(artist: str, title: str) -> Optional[str]:
    slug = f'{_slug(artist)}-{_slug(title)}'
    body = _http_get(f'https://lyrics.lyricfind.com/lyrics/{slug}')
    if not body:
        return None
    m = re.search(r'"lyrics"\s*:\s*"((?:\\.|[^"\\])+)"', body)
    if m:
        raw = m.group(1).encode('utf-8').decode('unicode_escape', errors='replace')
        raw = raw.replace('\\n', '\n').replace('\\r', '')
        if len(raw) > 50:
            return raw
    m = re.search(r'(?is)<div[^>]+class="[^"]*lyrics-body[^"]*"[^>]*>(.*?)</div>\s*</div>', body)
    if m:
        text = _strip_html(m.group(1)).strip()
        if len(text) > 50:
            return text
    return None


def _genius_find_url(artist: str, title: str) -> Optional[str]:
    q = urllib.parse.quote_plus(f'{title} {artist}')
    body = _http_get(f'https://genius.com/api/search/multi?q={q}')
    if not body:
        return None
    try:
        data = json.loads(body)
    except Exception:
        return None
    sections = (data.get('response') or {}).get('sections') or []
    for sec in sections:
        for hit in (sec.get('hits') or []):
            res = hit.get('result') or {}
            url = res.get('url')
            if url and 'genius.com' in url:
                return url
    return None


def source_genius(artist: str, title: str) -> Optional[str]:
    url = _genius_find_url(artist, title)
    if not url:
        return None
    body = _http_get(url)
    if not body:
        return None
    matches = re.findall(r'(?is)<div[^>]+data-lyrics-container="true"[^>]*>(.*?)</div>', body)
    if matches:
        joined = '\n'.join(_strip_html(m) for m in matches).strip()
        if len(joined) > 50:
            return joined
    m = re.search(r'(?is)<div[^>]+class="lyrics"[^>]*>(.*?)</div>', body)
    if m:
        text = _strip_html(m.group(1)).strip()
        if len(text) > 50:
            return text
    return None


def source_azlyrics(artist: str, title: str) -> Optional[str]:
    url = f'https://www.azlyrics.com/lyrics/{_azlyrics_slug(artist)}/{_azlyrics_slug(title)}.html'
    body = _http_get(url)
    if not body:
        return None
    m = re.search(r'(?is)<!--\s*Usage of azlyrics\.com.*?-->\s*<div>(.*?)</div>', body)
    if m:
        text = _strip_html(m.group(1)).strip()
        if len(text) > 50:
            return text
    return None


def source_lyricscom(artist: str, title: str) -> Optional[str]:
    q = urllib.parse.quote_plus(f'{title} {artist}')
    search = _http_get(f'https://www.lyrics.com/lyrics/{q}')
    if not search:
        return None
    m = re.search(r'href="(/lyric/\d+/[^"]+)"', search)
    if not m:
        return None
    page = _http_get('https://www.lyrics.com' + m.group(1))
    if not page:
        return None
    m2 = re.search(r'(?is)<pre[^>]+id="lyric-body-text"[^>]*>(.*?)</pre>', page)
    if not m2:
        return None
    text = _strip_html(m2.group(1)).strip()
    return text if len(text) > 50 else None


def source_songlyrics(artist: str, title: str) -> Optional[str]:
    url = f'https://www.songlyrics.com/{_slug(artist)}/{_slug(title)}-lyrics/'
    page = _http_get(url)
    if not page:
        return None
    m = re.search(r'(?is)<p[^>]+id="songLyricsDiv"[^>]*>(.*?)</p>', page)
    if not m:
        return None
    text = _strip_html(m.group(1)).strip()
    if len(text) < 50 or 'We do not have' in text:
        return None
    return text


def _musical_name_from_artist(artist: str) -> Optional[str]:
    a = re.sub(r'\s*[\[(].*?[\])]\s*', ' ', artist).strip()
    a = re.sub(r'\s+(cast recording|original cast|broadway cast|musical|soundtrack|cast).*$', '', a, flags=re.I).strip()
    return a or None


def source_stlyrics(artist: str, title: str) -> Optional[str]:
    musical = _musical_name_from_artist(artist) or artist
    direct = f'https://www.stlyrics.com/lyrics/{_slug(musical)}/{_slug(title)}.htm'
    page = _http_get(direct)
    if not page:
        q = urllib.parse.quote_plus(f'{title} {musical}')
        search = _http_get(f'https://www.stlyrics.com/cgi-bin/search.cgi?search={q}&cat=ml')
        if not search:
            return None
        m = re.search(r'href="(/lyrics/[^"]+\.htm)"', search)
        if not m:
            return None
        page = _http_get('https://www.stlyrics.com' + m.group(1))
        if not page:
            return None
    m2 = re.search(r'(?is)<div[^>]+id="lyrics"[^>]*>(.*?)</div>', page)
    if m2:
        text = _strip_html(m2.group(1)).strip()
        if len(text) > 50:
            return text
    return None


def source_allmusicals(artist: str, title: str) -> Optional[str]:
    musical = _musical_name_from_artist(artist) or artist
    if not musical:
        return None
    url = f'https://www.allmusicals.com/lyrics/{_slug(musical)}/{_slug(title)}.htm'
    page = _http_get(url)
    if not page:
        return None
    m = re.search(r'(?is)<div[^>]+class="[^"]*entry-content[^"]*"[^>]*>(.*?)</div>', page)
    if not m:
        m = re.search(r'(?is)<pre[^>]*>(.*?)</pre>', page)
    if m:
        text = _strip_html(m.group(1)).strip()
        if len(text) > 50:
            return text
    return None


_KNOWN_LYRIC_HOSTS = ['genius.com', 'www.azlyrics.com', 'www.lyrics.com',
                      'www.songlyrics.com', 'lyrics.lyricfind.com',
                      'www.stlyrics.com', 'www.allmusicals.com']


def source_ddg(artist: str, title: str) -> Optional[str]:
    q = urllib.parse.quote_plus(f'{artist} {title} lyrics')
    body = _http_get(f'https://duckduckgo.com/html/?q={q}')
    if not body:
        return None
    hits = re.findall(r'href="(https?://[^"]+)"', body)
    for h in hits:
        for host in _KNOWN_LYRIC_HOSTS:
            if host not in h:
                continue
            try:
                if host == 'genius.com':
                    text = source_genius(artist, title)
                elif host == 'www.azlyrics.com':
                    text = source_azlyrics(artist, title)
                elif host == 'www.lyrics.com':
                    text = source_lyricscom(artist, title)
                elif host == 'www.songlyrics.com':
                    text = source_songlyrics(artist, title)
                elif host == 'lyrics.lyricfind.com':
                    text = source_lyricfind(artist, title)
                elif host == 'www.stlyrics.com':
                    text = source_stlyrics(artist, title)
                elif host == 'www.allmusicals.com':
                    text = source_allmusicals(artist, title)
                else:
                    text = None
                if text and len(text) > 50:
                    return text
            except Exception:
                pass
    return None


SOURCES = [
    ('lyricsovh', source_lyricsovh),
    ('lyricfind', source_lyricfind),
    ('genius', source_genius),
    ('azlyrics', source_azlyrics),
    ('lyricscom', source_lyricscom),
    ('songlyrics', source_songlyrics),
    ('stlyrics', source_stlyrics),
    ('allmusicals', source_allmusicals),
    ('ddg', source_ddg),
]


# ---------------------------------------------------------------------------
# Artist / title variants + musical composer map
# ---------------------------------------------------------------------------

MUSICAL_COMPOSER_MAP = {
    'in the heights': 'Lin-Manuel Miranda',
    'hamilton': 'Lin-Manuel Miranda',
    'dear evan hansen': 'Pasek and Paul',
    'rent': 'Jonathan Larson',
    'wicked': 'Stephen Schwartz',
    'the greatest showman': 'Pasek and Paul',
    'les miserables': 'Claude-Michel Schoenberg',
    'waitress': 'Sara Bareilles',
    'the book of mormon': 'Trey Parker',
    'book of mormon': 'Trey Parker',
    'come from away': 'Irene Sankoff',
    'hadestown': 'Anais Mitchell',
    'tick tick boom': 'Jonathan Larson',
    'into the woods': 'Stephen Sondheim',
    'sweeney todd': 'Stephen Sondheim',
    'company': 'Stephen Sondheim',
    'spring awakening': 'Duncan Sheik',
    'next to normal': 'Tom Kitt',
    'the last five years': 'Jason Robert Brown',
    'phantom of the opera': 'Andrew Lloyd Webber',
    'cats': 'Andrew Lloyd Webber',
    'jesus christ superstar': 'Andrew Lloyd Webber',
    'evita': 'Andrew Lloyd Webber',
    'chicago': 'John Kander',
    'cabaret': 'John Kander',
    'kinky boots': 'Cyndi Lauper',
    'aladdin': 'Alan Menken',
    'beauty and the beast': 'Alan Menken',
    'the little mermaid': 'Alan Menken',
    'newsies': 'Alan Menken',
    'little shop of horrors': 'Alan Menken',
    'avenue q': 'Robert Lopez',
    'frozen': 'Kristen Anderson-Lopez',
    'falsettos': 'William Finn',
    'annie': 'Charles Strouse',
    'a chorus line': 'Marvin Hamlisch',
    'moulin rouge': 'Moulin Rouge Cast',
    'putnam': 'William Finn',
    'mean girls': 'Jeff Richmond',
    'parade': 'Jason Robert Brown',
    'songs for a new world': 'Jason Robert Brown',
}


def _title_variants(title: str) -> list[str]:
    out = [title]
    t = re.sub(r'\s*[\[(].*?[\])]\s*', ' ', title).strip()
    t = re.sub(r'\s*[-\u2013\u2014]\s*(feat\.|featuring|remaster|remix|version|edit|live|acoustic|reprise|bonus).*$', '', t, flags=re.I).strip()
    if t and t.lower() != title.lower():
        out.append(t)
    t2 = re.sub(r'\s*/\s*.+$', '', title).strip()
    if t2 and t2.lower() != title.lower() and t2 not in out:
        out.append(t2)
    return out


def _artist_variants(artist: str) -> list[str]:
    out = [artist]
    a = re.sub(r'\s*[\[(].*?[\])]\s*', ' ', artist).strip()
    if a and a.lower() != artist.lower():
        out.append(a)
    a2 = re.sub(r'\s*(feat\.|featuring|ft\.?|with|&|vs\.?|and)\s+.*$', '', a, flags=re.I).strip()
    if a2 and a2.lower() not in [x.lower() for x in out]:
        out.append(a2)
    if re.search(r'(cast recording|original cast|broadway cast|musical|soundtrack|cast)', artist, re.I):
        lower = artist.lower()
        for key, comp in MUSICAL_COMPOSER_MAP.items():
            if key in lower and comp not in out:
                out.append(comp)
                break
    return out


def fetch_lyrics(artist: str, title: str) -> tuple[Optional[str], Optional[str]]:
    seen = set()
    is_musical = bool(re.search(r'(cast recording|original cast|broadway cast|musical|soundtrack)', artist, re.I))
    ordered = list(SOURCES)
    if is_musical:
        musical_prefs = [s for s in ordered if s[0] in ('stlyrics', 'allmusicals')]
        others = [s for s in ordered if s[0] not in ('stlyrics', 'allmusicals')]
        ordered = musical_prefs + others

    for art in _artist_variants(artist):
        for tit in _title_variants(title):
            key = (art.lower(), tit.lower())
            if key in seen:
                continue
            seen.add(key)
            for name, fn in ordered:
                try:
                    text = fn(art, tit)
                except Exception as e:
                    log.debug('%s error for %r/%r: %s', name, art, tit, e)
                    text = None
                if text and len(text.strip()) > 50:
                    return text, name
    return None, None


# ---------------------------------------------------------------------------
# Tokenization
# ---------------------------------------------------------------------------

_LYRIC_STOPWORDS = set("""
a about after ah all also am an and any are aren at be because been before
being below both but by can could cause cuz did didn do does don down during
each else even ever every for from get got gonna gotta had has have having he
her here hers him his how i if in into is isn it its just know let like ll
look ma made make makes making many may me might more most must my na nah no
not now o of off oh on once only or other our ours ourselves out over own re
said say says see should shouldn so some such than that the their theirs them
then there these they this those though through thus to too uh uhh um up upon
us use used very wanna was way we well were what whatever when where which
while who why will with would wow yeah yep yes yet you your yours yourself
yourselves ya ll ve re
""".split())
_LYRIC_STOPWORDS.update({
    'll','ve','re','em','ol','mm','hmm','huh','ooh','ohh','oo','ay','ayy','yah',
    'yo','im','ima','aint','ya','y','bout','cause','got','gonna','gotta','wanna',
    'tryna','lil','bro','one','two','three','baby',
})
_WORD_RE = re.compile(r"[a-z']+")


def clean_lyrics_words(text: str) -> list[str]:
    text = re.sub(r'\[[^\]]{0,40}\]', ' ', text)
    text = re.sub(r'\([^)]{0,60}\)', ' ', text)
    words = _WORD_RE.findall(text.lower())
    return [w.strip("'") for w in words
            if len(w) >= 3 and w not in _LYRIC_STOPWORDS and not w.isdigit()]


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def collect_top_songs(top_songs_by_period, year, limit=TOP_N_PER_YEAR):
    bag = {}
    for period, items in top_songs_by_period.items():
        if not period.startswith(year):
            continue
        for it in items or []:
            artist = (it.get('artist') or '').strip()
            track = (it.get('track') or '').strip()
            if not artist or not track:
                continue
            key = (artist.lower(), track.lower())
            rec = bag.get(key) or {'artist': artist, 'track': track, 'play_count': 0}
            rec['play_count'] += int(it.get('play_count') or 1)
            bag[key] = rec
    return sorted(bag.values(), key=lambda x: x['play_count'], reverse=True)[:limit]


def build_year_cloud(year, songs):
    counts = Counter()
    per_song = []

    def do_one(s):
        text, src = fetch_lyrics(s['artist'], s['track'])
        if not text:
            return {'artist': s['artist'], 'track': s['track'],
                    'plays': s['play_count'], 'found': False}, []
        words = clean_lyrics_words(text)
        return {'artist': s['artist'], 'track': s['track'],
                'plays': s['play_count'], 'found': True,
                'word_count': len(words), 'source': src}, words

    source_hits = Counter()
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = [pool.submit(do_one, s) for s in songs]
        for fut in as_completed(futures):
            try:
                info, words = fut.result()
            except Exception as e:
                log.warning('  fetch worker error: %s', e)
                continue
            per_song.append(info)
            if words:
                plays = max(info.get('plays', 1), 1)
                for w, c in Counter(words).items():
                    counts[w] += c * plays
                if info.get('source'):
                    source_hits[info['source']] += 1

    per_song.sort(key=lambda p: p['plays'], reverse=True)
    found = [p for p in per_song if p.get('found')]
    total_plays = sum(p['plays'] for p in per_song)
    found_plays = sum(p['plays'] for p in found)

    return {
        'ok': True, 'year': year,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'words': counts.most_common(TOP_WORDS_OUT),
        'stats': {
            'songs_considered': len(per_song),
            'lyrics_found': len(found),
            'coverage_by_plays': round(100 * found_plays / total_plays, 1) if total_plays else 0.0,
            'total_words_counted': sum(counts.values()),
            'unique_words': len(counts),
            'source_hits': dict(source_hits),
        },
        'songs': per_song,
    }


def main():
    if not os.path.exists(TOP_SONGS_PATH):
        log.error('top_songs_by_period.json not found at %s', TOP_SONGS_PATH)
        sys.exit(1)
    os.makedirs(OUT_DIR, exist_ok=True)

    with open(TOP_SONGS_PATH, 'r', encoding='utf-8') as f:
        top_songs = json.load(f)

    years = sorted({p[:4] for p in top_songs.keys() if len(p) >= 4 and p[:4].isdigit()})
    log.info('Building word clouds for years: %s', years)
    only = os.environ.get('ONLY_YEAR', '').strip()
    if only:
        years = [y for y in years if y == only]

    index = []
    grand = Counter()
    for year in years:
        songs = collect_top_songs(top_songs, year, TOP_N_PER_YEAR)
        if not songs:
            continue
        t0 = time.time()
        log.info('  %s: fetching lyrics for %d songs...', year, len(songs))
        result = build_year_cloud(year, songs)
        dt = time.time() - t0
        stats = result['stats']
        log.info('  %s done in %.1fs: %d/%d songs (%.1f%% by plays), sources=%s',
                 year, dt, stats['lyrics_found'], stats['songs_considered'],
                 stats['coverage_by_plays'], stats['source_hits'])
        grand.update(stats['source_hits'])

        out_path = os.path.join(OUT_DIR, f'{year}.json')
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, separators=(',', ':'))
        index.append({
            'year': year, 'file': f'wordclouds/{year}.json',
            'songs_considered': stats['songs_considered'],
            'lyrics_found': stats['lyrics_found'],
            'coverage_by_plays': stats['coverage_by_plays'],
            'unique_words': stats['unique_words'],
        })

    with open(os.path.join(OUT_DIR, 'index.json'), 'w', encoding='utf-8') as f:
        json.dump({
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'years': index,
            'source_hits_total': dict(grand),
        }, f, ensure_ascii=False, indent=2)

    log.info('Done. Source totals: %s', dict(grand))


if __name__ == '__main__':
    main()
