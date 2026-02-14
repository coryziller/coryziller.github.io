# Deployment Guide - Social Listening (Simplified!)

## What You Need

✅ **Railway account** (already have)
✅ **Brevo API key** (already have)
⚠️ **OpenAI API key** (need to get)

**NO Reddit credentials needed!** Uses public JSON endpoints.

---

## Step 1: Get OpenAI API Key (5 minutes)

1. **Go to**: https://platform.openai.com/api-keys
2. **Sign up or log in**
3. **Click**: "Create new secret key"
4. **Name it**: `Social Listening`
5. **Copy the key** (starts with `sk-proj-...`)
6. **Add credits**:
   - Go to https://platform.openai.com/settings/organization/billing
   - Click "Add payment method"
   - Add $5-10 (will last 6+ months at ~$0.30/month)

**Cost: ~$0.01 per report = $0.30/month for daily reports**

---

## Step 2: Add OpenAI Key to Railway

1. **Go to Railway dashboard**: https://railway.app/dashboard
2. **Click your project**
3. **Click "Variables" tab**
4. **Add this variable**:
   ```
   OPENAI_API_KEY=sk-proj-your_key_here
   ```

You should already have:
- `BREVO_API_KEY` ✅
- `SENDER_EMAIL` ✅
- `PORT` ✅

---

## Step 3: Set Up Daily Cron Job

The `railway.toml` file is already configured to run the scraper daily at 9 AM UTC.

It will:
- Scrape Reddit (public JSON, no auth!)
- Scrape Hacker News (public API, no auth!)
- Analyze with OpenAI
- Update `latest_report.json`

**No additional setup needed!**

---

## Step 4: Push Code to GitHub

```bash
cd "/Users/coryziller/Automation Workflows/github_website"
git add railway-api/
git commit -m "Add automated sentiment analysis with Reddit + HN scraping"
git push
```

Railway will auto-deploy.

---

## Step 5: Test the Scraper

After Railway deploys, manually run the first scrape:

1. In Railway dashboard → your service
2. Go to "Deployments" → latest deployment
3. Click "View Logs"
4. In the shell/terminal, run:
   ```bash
   python generate_report.py
   ```

**Expected output:**
```
📡 STEP 1: SCRAPING DATA
Using Reddit's public JSON endpoints - no credentials needed!
Scraping Reddit - 4 subreddits, 7 days back
  - r/nvidia: 12 posts
  - r/hardware: 8 posts
  ...

🤖 STEP 2: ANALYZING SENTIMENT
Analyzing posts 1-10 of 45
...

✅ Report generation complete!
Total posts analyzed: 45
Overall sentiment: Mixed (52.3/100)
```

---

## Step 6: Verify Everything Works

1. **Check Railway logs** - Should see successful scrape
2. **Visit your portfolio**: https://coryziller.github.io
3. **Click Social Listening project**
4. **Submit demo form** with your email
5. **Check inbox** - You'll get real data!

---

## Daily Operation

**Automatic flow (no action needed):**

- **9:00 AM UTC every day** → Railway runs `python generate_report.py`
- Scrapes Reddit + HN (last 7 days)
- Analyzes ~50-100 posts with OpenAI
- Updates `latest_report.json`
- Any visitor who clicks demo gets fresh data

---

## Costs

- **Railway**: Free tier (or $5/month if scaling)
- **OpenAI**: ~$0.30/month ($0.01/day)
- **Total**: $0.30 - $5.30/month

---

## Customization

**Change scrape schedule:**

Edit `railway.toml`:
```toml
schedule = "0 14 * * *"  # 2 PM UTC instead of 9 AM
```

**Change what to scrape:**

Edit `scraper.py` lines 18-20:
```python
subreddits=['nvidia', 'hardware', 'YOUR_SUBREDDIT']
keywords=['nvidia', 'rtx', '4090', 'YOUR_KEYWORD']
```

**Change time range:**

Edit `generate_report.py` line 38:
```python
posts = scraper.scrape_all(days_back=14)  # Or 3, 7, 30, etc.
```

---

## Troubleshooting

### "No posts found"
- Check internet connection
- Try different subreddits in `scraper.py`
- Reddit might be temporarily down

### "OpenAI API error"
- Verify API key is correct
- Check you have billing credits
- Make sure key starts with `sk-proj-`

### Cron job not running
- Check Railway logs for errors
- Verify `railway.toml` is in repo root
- Check environment variables are set

---

## That's It! 🚀

**Setup Summary:**
1. ✅ Get OpenAI key
2. ✅ Add to Railway
3. ✅ Push code
4. ✅ Test first run
5. ✅ Watch it work daily!

**No Reddit credentials needed. No complex setup. Just works.**
