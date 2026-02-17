#!/usr/bin/env python3
"""
Spotify Data Updater for GitHub Action
========================================
Runs daily via GitHub Action. Fetches current Spotify data
and updates the SPOTIFY_DATA in index.html.

Only updates the CURRENT YEAR data - historical data from
the privacy export stays untouched.
"""

import os
import sys
import json
import re
import requests
import base64
from datetime import datetime

# Get credentials from environment (GitHub Secrets)
CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("SPOTIFY_REFRESH_TOKEN")

def get_access_token():
    """Use refresh token to get a fresh access token."""
    auth_header = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()

    response = requests.post(
        "https://accounts.spotify.com/api/token",
        headers={
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded"
        },
        data={
            "grant_type": "refresh_token",
            "refresh_token": REFRESH_TOKEN
        }
    )

    if response.status_code != 200:
        print(f"Error refreshing token: {response.status_code}")
        print(response.text)
        sys.exit(1)

    return response.json()["access_token"]

def spotify_get(endpoint, token, params=None):
    """Make an authenticated GET request to Spotify API."""
    response = requests.get(
        f"https://api.spotify.com/v1/{endpoint}",
        headers={"Authorization": f"Bearer {token}"},
        params=params
    )

    if response.status_code != 200:
        print(f"Error fetching {endpoint}: {response.status_code}")
        print(response.text)
        return None

    return response.json()

def fetch_spotify_data(token):
    """Fetch all relevant data from Spotify API."""
    current_year = str(datetime.now().year)

    # Top Artists - short term (last 4 weeks) for current trends
    top_artists_short = spotify_get("me/top/artists", token, {
        "time_range": "short_term",
        "limit": 10
    })

    # Top Artists - medium term (last 6 months)
    top_artists_medium = spotify_get("me/top/artists", token, {
        "time_range": "medium_term",
        "limit": 10
    })

    # Top Tracks - short term
    top_tracks_short = spotify_get("me/top/tracks", token, {
        "time_range": "short_term",
        "limit": 10
    })

    # Top Tracks - medium term
    top_tracks_medium = spotify_get("me/top/tracks", token, {
        "time_range": "medium_term",
        "limit": 10
    })

    # Recently played
    recent = spotify_get("me/player/recently-played", token, {
        "limit": 50
    })

    # Build the current year artist evolution data
    current_artists = []
    if top_artists_short and "items" in top_artists_short:
        for i, artist in enumerate(top_artists_short["items"][:10]):
            current_artists.append({
                "name": artist["name"],
                "genres": artist.get("genres", [])[:3],
                "popularity": artist.get("popularity", 0)
            })

    # Build current year top tracks
    current_tracks = []
    if top_tracks_short and "items" in top_tracks_short:
        for track in top_tracks_short["items"][:10]:
            current_tracks.append({
                "name": track["name"],
                "artist": track["artists"][0]["name"] if track["artists"] else "Unknown"
            })

    # Extract genre distribution from top artists (medium term for stability)
    genre_counts = {}
    if top_artists_medium and "items" in top_artists_medium:
        for artist in top_artists_medium["items"]:
            for genre in artist.get("genres", []):
                # Map to broader categories
                broad_genre = map_to_broad_genre(genre)
                genre_counts[broad_genre] = genre_counts.get(broad_genre, 0) + 1

    # Normalize genre percentages
    total_genres = sum(genre_counts.values()) or 1
    genre_percentages = {}
    for genre, count in sorted(genre_counts.items(), key=lambda x: -x[1]):
        genre_percentages[genre] = round((count / total_genres) * 100, 1)

    # Build word cloud data from current artists and tracks
    word_cloud_words = []
    if top_artists_short and "items" in top_artists_short:
        for artist in top_artists_short["items"][:10]:
            words = artist["name"].lower().split()
            for word in words:
                clean = re.sub(r'[^a-zA-Z]', '', word)
                if clean and len(clean) > 1:
                    word_cloud_words.append(clean)

    if top_tracks_short and "items" in top_tracks_short:
        for track in top_tracks_short["items"][:10]:
            words = track["name"].lower().split()
            for word in words:
                clean = re.sub(r'[^a-zA-Z]', '', word)
                if clean and len(clean) > 2:
                    word_cloud_words.append(clean)

    return {
        "year": current_year,
        "artists": current_artists,
        "tracks": current_tracks,
        "genres": genre_percentages,
        "word_cloud": word_cloud_words,
        "updated_at": datetime.now().strftime("%B %d, %Y")
    }

def map_to_broad_genre(genre):
    """Map Spotify's detailed genres to broader categories."""
    genre_lower = genre.lower()

    genre_map = {
        "pop": ["pop", "dance pop", "electropop", "indie pop", "art pop", "synth-pop"],
        "R&B / Soul": ["r&b", "soul", "neo soul", "contemporary r&b", "urban contemporary"],
        "Indie / Singer-Songwriter": ["indie", "singer-songwriter", "folk", "acoustic"],
        "Electronic": ["electronic", "edm", "house", "techno", "dubstep", "ambient"],
        "Hip-Hop": ["hip hop", "rap", "trap"],
        "Rock": ["rock", "alternative", "punk", "grunge", "metal"],
        "Jazz Pop": ["jazz", "smooth jazz", "jazz pop"],
        "Broadway": ["broadway", "show tunes", "musical theatre", "musical theater"],
        "A Cappella": ["a cappella", "acappella", "vocal"],
        "Gospel": ["gospel", "christian", "worship", "ccm"],
        "Latin": ["latin", "reggaeton", "salsa", "bachata"],
        "Country": ["country", "americana"],
        "Classical": ["classical", "orchestra", "piano"],
    }

    for broad, keywords in genre_map.items():
        for keyword in keywords:
            if keyword in genre_lower:
                return broad

    return "Other"

def update_index_html(data):
    """Update the SPOTIFY_DATA in index.html with fresh API data."""
    with open("index.html", "r", encoding="utf-8") as f:
        content = f.read()

    current_year = data["year"]

    # 1. Update artistEvolution for current year
    # Find the artistEvolution object and update the current year's data
    artist_names = [a["name"] for a in data["artists"]]
    if artist_names:
        # Build the JS array string for current year artists
        artist_js = json.dumps(artist_names[:10])

        # Use regex to find and replace the current year in artistEvolution
        # Pattern: "2026": ["name1", "name2", ...]
        pattern = rf'"{current_year}":\s*\[([^\]]*)\]'

        # Check if pattern exists in artistEvolution section
        ae_start = content.find("artistEvolution:")
        if ae_start == -1:
            ae_start = content.find("artistEvolution :")

        if ae_start != -1:
            # Find the closing brace of artistEvolution
            ae_section_end = content.find("},", ae_start)
            if ae_section_end != -1:
                ae_section = content[ae_start:ae_section_end]

                # Replace current year data
                new_ae_section = re.sub(
                    pattern,
                    f'"{current_year}": {artist_js}',
                    ae_section
                )

                if new_ae_section != ae_section:
                    content = content[:ae_start] + new_ae_section + content[ae_section_end:]
                    print(f"Updated artistEvolution for {current_year}")
                else:
                    print(f"No change needed for artistEvolution {current_year}")

    # 2. Update genreEvolution for current year
    if data["genres"]:
        genre_data = data["genres"]

        ge_start = content.find("genreEvolution:")
        if ge_start == -1:
            ge_start = content.find("genreEvolution :")

        if ge_start != -1:
            ge_section_end = content.find("},", ge_start + 100)
            if ge_section_end != -1:
                ge_section = content[ge_start:ge_section_end]

                # Build genre object for current year
                genre_entries = []
                for genre_name, pct in genre_data.items():
                    safe_name = genre_name.replace('"', '\\"')
                    genre_entries.append(f'"{safe_name}": {pct}')
                genre_obj = "{" + ", ".join(genre_entries) + "}"

                pattern = rf'"{current_year}":\s*\{{[^}}]*\}}'
                new_ge_section = re.sub(
                    pattern,
                    f'"{current_year}": {genre_obj}',
                    ge_section
                )

                if new_ge_section != ge_section:
                    content = content[:ge_start] + new_ge_section + content[ge_section_end:]
                    print(f"Updated genreEvolution for {current_year}")

    # 3. Update word cloud data for current year
    if data["word_cloud"]:
        wc_start = content.find("wordCloudData:")
        if wc_start == -1:
            wc_start = content.find("wordCloudData :")

        if wc_start != -1:
            wc_section_end = content.find("},", wc_start + 100)
            if wc_section_end != -1:
                wc_section = content[wc_start:wc_section_end]

                words_js = json.dumps(data["word_cloud"])
                pattern = rf'"{current_year}":\s*\[[^\]]*\]'
                new_wc_section = re.sub(
                    pattern,
                    f'"{current_year}": {words_js}',
                    wc_section
                )

                if new_wc_section != wc_section:
                    content = content[:wc_start] + new_wc_section + content[wc_section_end:]
                    print(f"Updated wordCloudData for {current_year}")

    # 4. Update the "DATA THROUGH" date in the header
    old_date_pattern = r'DATA THROUGH [A-Z]+ \d+, \d+'
    new_date = f'DATA THROUGH {datetime.now().strftime("%B %d, %Y").upper()}'
    content = re.sub(old_date_pattern, new_date, content)
    print(f"Updated date to: {new_date}")

    # Write updated file
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(content)

    print("index.html updated successfully!")

def main():
    # Validate credentials
    if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]):
        print("Error: Missing environment variables!")
        print("Make sure SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, and SPOTIFY_REFRESH_TOKEN are set")
        sys.exit(1)

    print("Fetching fresh access token...")
    token = get_access_token()

    print("Fetching Spotify data...")
    data = fetch_spotify_data(token)

    print(f"\nFetched data for {data['year']}:")
    print(f"  Top Artists: {', '.join(a['name'] for a in data['artists'][:5])}")
    print(f"  Top Tracks: {', '.join(t['name'] for t in data['tracks'][:3])}")
    print(f"  Genres: {', '.join(list(data['genres'].keys())[:5])}")
    print(f"  Word Cloud words: {len(data['word_cloud'])}")

    print("\nUpdating index.html...")
    update_index_html(data)

if __name__ == "__main__":
    main()
