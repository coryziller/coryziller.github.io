# 🚀 Deploy to GitHub Pages

## Quick Start

1. **Copy these files to your `github_website` folder:**
   - `index.html` (your updated portfolio with Spotify Trends)
   - `spotify-trends/` (folder with all JSON data)
   - `update_spotify_data.py` (optional - for auto-updates)
   - `README.md` (optional - documentation)

2. **Push to GitHub:**
   ```bash
   cd /path/to/github_website
   git add .
   git commit -m "Add Spotify Trends dashboard with Wrapped aesthetic"
   git push origin main
   ```

3. **Visit your site:**
   - Go to https://coryziller.github.io
   - Click the orange Spotify Trends card
   - Enjoy your 13-year music journey! 🎵

## What's Included

✅ **index.html** - Your complete portfolio with:
   - Social Listening card (purple)
   - Spotify Trends card (orange) - NEW!
   - 2x "More to Come" cards
   - All Spotify data embedded (works offline!)
   - Wrapped-style aesthetic with gradients & animations

✅ **spotify-trends/** - JSON data files:
   - basic_stats.json
   - artist_evolution.json  
   - monthly_trends.json
   - top_songs_by_period.json
   - last_updated.json

✅ **update_spotify_data.py** - Auto-update script (optional)

## Testing Before Deploy

1. Open `index.html` in your browser
2. Click the Spotify Trends card
3. Verify it expands and shows your data
4. Check that charts and stats look good

## Need Help?

- Card won't expand? Hard refresh (Ctrl+Shift+R)
- Data not showing? Check browser console (F12)
- Styling issues? Clear browser cache

---

Built with Python, Chart.js, and 6,500+ hours of music 🎵
