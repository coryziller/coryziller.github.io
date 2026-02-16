# Spotify Trends Dashboard

## Setup Instructions

### 1. File Structure
Copy these files to your github_website folder:
- `index.html` (updated with Spotify Trends card)
- `spotify-trends/` folder with all JSON files

### 2. Auto-Update System

The dashboard can automatically refresh with new Spotify data!

**How it works:**
1. `update_spotify_data.py` runs on a schedule (cron/Task Scheduler)
2. Fetches new Spotify streaming history (requires Spotify API setup)
3. Re-runs analysis
4. Updates JSON files
5. Dashboard automatically shows new data on next page load

**Setup Auto-Updates:**

**On Mac/Linux (using cron):**
```bash
# Edit crontab
crontab -e

# Add this line to run weekly on Sundays at 2am:
0 2 * * 0 cd /path/to/github_website && python3 update_spotify_data.py

# Or run daily at midnight:
0 0 * * * cd /path/to/github_website && python3 update_spotify_data.py
```

**On Windows (using Task Scheduler):**
1. Open Task Scheduler
2. Create Basic Task
3. Set trigger (daily/weekly)
4. Action: Start a program
5. Program: `python`
6. Arguments: `update_spotify_data.py`
7. Start in: `C:\path\to\github_website`

### 3. Spotify API Setup (for auto-updates)

To fetch new data automatically, you need Spotify API credentials:

1. Go to https://developer.spotify.com/dashboard
2. Create an app
3. Get your Client ID and Client Secret
4. Add them to the update script

**Or** manually export new data from Spotify:
- Go to https://www.spotify.com/account/privacy/
- Request your data
- Download new JSON files
- Replace files in spotify-trends/ folder

## Current Data
- **Date Range:** October 2012 - February 2026
- **Total Plays:** 132,916
- **Total Hours:** 6,529
- **Unique Tracks:** 9,458
- **Unique Artists:** 3,819

## Files
- `basic_stats.json` - Overall statistics
- `artist_evolution.json` - Top artists by year
- `monthly_trends.json` - Month-by-month breakdown
- `top_songs_by_period.json` - Top songs per time period
- `last_updated.json` - Timestamp of last data refresh

---

Built with Python, Chart.js, and lots of music 🎵
