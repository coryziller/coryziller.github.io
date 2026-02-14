# Social Listening Automation - Setup Guide

This guide will help you set up the automated social listening system that scrapes Reddit and Hacker News, analyzes sentiment, and sends personalized audio reports.

## Prerequisites

- Python 3.9+
- Reddit API credentials
- OpenAI API key
- Brevo (Sendinblue) API key

## Step 1: Get Reddit API Credentials

1. Go to https://www.reddit.com/prefs/apps
2. Scroll to the bottom and click **"create another app"**
3. Fill in the form:
   - **name**: Social Listening Bot (or any name)
   - **App type**: Select **"script"**
   - **description**: (optional)
   - **about url**: (optional)
   - **redirect uri**: http://localhost:8080
4. Click **"create app"**
5. You'll see your credentials:
   - **client_id**: The string under "personal use script" (14 characters)
   - **client_secret**: The "secret" field (27 characters)

## Step 2: Get OpenAI API Key

1. Go to https://platform.openai.com/api-keys
2. Sign up or log in
3. Click **"Create new secret key"**
4. Copy the key (starts with `sk-...`)
5. **Important**: Add $5-10 credit to your account at https://platform.openai.com/account/billing

**Cost estimate**: ~$0.01-0.03 per report using `gpt-4o-mini`

## Step 3: Configure Environment Variables

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your credentials:
   ```bash
   REDDIT_CLIENT_ID=your_14_char_client_id
   REDDIT_CLIENT_SECRET=your_27_char_secret
   REDDIT_USER_AGENT=SocialListeningBot/1.0
   OPENAI_API_KEY=sk-your_openai_key_here
   BREVO_API_KEY=your_brevo_key
   SENDER_EMAIL=demo@coryziller.com
   ```

## Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 5: Run the Report Generator

Generate your first report:

```bash
python generate_report.py
```

This will:
1. Scrape Reddit and Hacker News for NVIDIA-related posts (last 7 days)
2. Analyze sentiment using OpenAI
3. Save results to `latest_report.json`
4. Print a summary to the console

## Step 6: Test the Email System

Start the Flask app:

```bash
python app.py
```

Then test the demo email form on your website. It will use the `latest_report.json` you just generated.

## Automation (Optional)

To run this daily automatically:

### Option 1: Railway Cron Job

1. Deploy to Railway
2. Add environment variables in Railway dashboard
3. Add a cron job in `railway.toml`:
   ```toml
   [build]
   builder = "nixpacks"

   [[crons]]
   schedule = "0 9 * * *"  # Run at 9 AM daily
   command = "python generate_report.py"
   ```

### Option 2: Local Cron (Mac/Linux)

1. Edit crontab:
   ```bash
   crontab -e
   ```

2. Add this line (runs daily at 9 AM):
   ```bash
   0 9 * * * cd /path/to/railway-api && python generate_report.py
   ```

## Troubleshooting

### "PRAW received 401 HTTP response"
- Check your Reddit credentials are correct
- Make sure you selected "script" as the app type

### "OpenAI API error"
- Verify your API key is correct
- Check you have billing credits at https://platform.openai.com/account/billing

### "No posts found"
- Reddit may be rate-limiting you
- Try increasing `days_back` parameter
- Check the subreddits and keywords in `scraper.py`

## Customization

### Change search parameters

Edit `generate_report.py` and modify:

```python
posts = scraper.scrape_all(days_back=7)  # Change to 14, 30, etc.
```

### Change subreddits/keywords

Edit `scraper.py` in the `scrape_reddit()` function:

```python
subreddits=['nvidia', 'hardware', 'buildapc']  # Add more
keywords=['nvidia', 'rtx', '4090']  # Add more
```

### Adjust analysis batch size

Edit `generate_report.py`:

```python
analyzed_posts = analyzer.analyze_batch(posts, batch_size=10)  # Increase for faster processing
```

## Questions?

Contact: coryziller@gmail.com
