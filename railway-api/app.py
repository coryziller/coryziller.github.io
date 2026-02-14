from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from gtts import gTTS
import io

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route('/send-demo', methods=['POST', 'OPTIONS'])
def send_demo():
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return '', 200

    try:
        # Get request data
        data = request.get_json()
        name = data.get('name')
        email = data.get('email')

        if not name or not email:
            return jsonify({'error': 'Name and email are required'}), 400

        # Load cached report data
        with open('latest_report.json', 'r') as f:
            report_data = json.load(f)

        # Build personalized script
        now = datetime.now().strftime('%B %d, %Y')

        total = report_data.get('total_posts', 0)
        sentiment = report_data.get('sentiment_stats', {}).get('overall_label', 'Mixed')
        score = report_data.get('sentiment_stats', {}).get('average_score', 0)
        top_issues = report_data.get('top_issues', [])[:3]

        # Build email body
        email_body = f"""Hi {name},

Thank you for your interest in my Social Listening project!

LATEST NVIDIA GPU SENTIMENT REPORT - {now}

Posts analyzed: {total}
Overall sentiment: {sentiment} ({score}/100)

TOP ISSUES DETECTED:
"""
        for i, issue in enumerate(top_issues, 1):
            email_body += f"{i}. [{issue['severity'].upper()}] {issue['category']}: {issue['title']}\n"

        email_body += f"""
I've attached a personalized 30-second audio briefing just for you.

This demo showcases how I built an automated social listening system that:
- Scrapes Reddit & Hacker News for NVIDIA GPU discussions
- Analyzes sentiment and prioritizes issues
- Generates personalized audio briefings using AI text-to-speech
- Delivers insights via automated email

Thanks for checking out my work!

Best regards,
Cory Ziller
https://coryziller.github.io
"""

        # Build personalized audio script
        top_issue_text = ""
        if top_issues:
            top_issue_text = f"Top issue: {top_issues[0]['category']}. {top_issues[0]['title'][:60]}."

        audio_script = f"Hi {name}, this is your 30 second round up for {now}. Found {total} posts discussing NVIDIA GPU issues. Sentiment: {sentiment}. {top_issue_text} Check your email for full details."

        # Generate audio with gTTS (Google Text-to-Speech)
        print(f"Generating audio with gTTS for: {name}")

        # Create gTTS object
        tts = gTTS(text=audio_script, lang='en', slow=False)

        # Save to BytesIO buffer instead of file
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)  # Reset buffer position to beginning

        # Get audio data
        audio_data = audio_buffer.read()

        print(f"Audio generated successfully - {len(audio_data)} bytes")

        # Send email with attachment
        sender_email = os.environ.get('SENDER_EMAIL')
        gmail_password = os.environ.get('GMAIL_APP_PASSWORD')

        if not sender_email or not gmail_password:
            return jsonify({'error': 'Email credentials not configured'}), 500

        # Create email
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = email
        msg['Subject'] = f'Your Personalized NVIDIA GPU Report - {now}'

        # Add body
        msg.attach(MIMEText(email_body, 'plain'))

        # Add audio attachment
        audio_attachment = MIMEBase('audio', 'mpeg')
        audio_attachment.set_payload(audio_data)
        encoders.encode_base64(audio_attachment)
        filename = f"nvidia_report_{name.replace(' ', '_')}.mp3"
        audio_attachment.add_header('Content-Disposition', f'attachment; filename={filename}')
        msg.attach(audio_attachment)

        # Send email
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, gmail_password)
            server.send_message(msg)

        return jsonify({
            'success': True,
            'message': 'Email sent successfully with personalized audio report!'
        }), 200

    except Exception as e:
        print(f"EXCEPTION in send-demo: {type(e).__name__}")
        print(f"Exception message: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': 'Failed to send demo',
            'type': type(e).__name__,
            'details': str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
