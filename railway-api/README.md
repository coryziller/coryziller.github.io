# Social Listening API - Railway Backend

Python Flask API for the social listening demo on https://coryziller.github.io

## Endpoints

- `POST /send-demo` - Sends personalized email with MP3 audio briefing
- `GET /health` - Health check endpoint

## Environment Variables Required

Set these in Railway:

```
ELEVENLABS_API_KEY=your_key_here
SENDER_EMAIL=your_gmail@gmail.com
GMAIL_APP_PASSWORD=your_app_password_here
```

## Deployment

Railway auto-deploys from GitHub. Push to main branch to deploy.

## Local Development

```bash
pip install -r requirements.txt
export ELEVENLABS_API_KEY=your_key
export SENDER_EMAIL=your_email
export GMAIL_APP_PASSWORD=your_password
python app.py
```

API will run on http://localhost:8000
