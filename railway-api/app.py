from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from datetime import datetime
from gtts import gTTS
import io
import base64
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

app = Flask(__name__)
# Enable CORS with explicit configuration
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# Add CORS headers to all responses (belt and suspenders approach)
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    return response

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
        print(f"[DEBUG] Attempting to load latest_report.json")
        print(f"[DEBUG] Current working directory: {os.getcwd()}")
        print(f"[DEBUG] Files in current directory: {os.listdir('.')}")

        try:
            with open('latest_report.json', 'r') as f:
                report_data = json.load(f)
            print(f"[DEBUG] Successfully loaded report data!")
        except FileNotFoundError:
            print(f"[ERROR] File not found: latest_report.json")
            return jsonify({'error': 'Report data not available. Please try again later.'}), 500
        except Exception as e:
            print(f"[ERROR] Error loading report: {e}")
            return jsonify({'error': f'Failed to load report data: {str(e)}'}), 500

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
I've attached a personalized 30-second audio briefing with key insights from the analysis.

ABOUT THIS PROJECT:
I built this end-to-end automated social listening pipeline to monitor brand sentiment and surface critical issues in real-time. The system continuously scrapes Reddit and Hacker News discussions, performs AI-powered sentiment analysis, and delivers personalized audio briefings via automated email—all running on a serverless architecture.

Key capabilities:
• Multi-source data aggregation (Reddit API, Hacker News API)
• Real-time sentiment analysis with severity classification
• AI-generated audio summaries using Google Text-to-Speech
• Automated email delivery with dynamic attachments
• Scalable deployment on Railway with scheduled cron jobs

This demonstrates my ability to build production-ready automation systems that combine web scraping, NLP, and AI to deliver actionable insights.

I'd love to discuss how I can bring similar solutions to your team!

Best regards,
Cory Ziller
https://coryziller.github.io
"""

        # Build personalized audio script
        top_issue_text = ""
        if top_issues:
            top_issue_text = f"Top issue: {top_issues[0]['category']}. {top_issues[0]['title'][:60]}."

        audio_script = f"Hi {name}, this is Cory Ziller with your personalized social listening briefing. I've analyzed {total} posts discussing NVIDIA GPU issues across Reddit and Hacker News. Overall sentiment is {sentiment}. {top_issue_text} This automated system scrapes forums, analyzes sentiment using AI, and generates these personalized briefings. Check your email for the complete report with detailed insights. Thanks for checking out my work!"

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

        # Send email with Brevo (Sendinblue)
        brevo_api_key = os.environ.get('BREVO_API_KEY')
        sender_email = os.environ.get('SENDER_EMAIL', 'demo@coryziller.com')

        if not brevo_api_key:
            return jsonify({'error': 'Brevo API key not configured'}), 500

        # Configure Brevo API
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = brevo_api_key
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

        # Encode audio as base64 for attachment
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        filename = f"nvidia_report_{name.replace(' ', '_')}.mp3"

        # Create email
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": email, "name": name}],
            sender={"email": sender_email, "name": "Cory Ziller"},
            subject=f"Your Personalized NVIDIA GPU Report - {now}",
            text_content=email_body,
            attachment=[{
                "content": audio_base64,
                "name": filename
            }]
        )

        # Send email using Brevo
        print(f"Sending email to {email} via Brevo...")

        try:
            api_response = api_instance.send_transac_email(send_smtp_email)
            print(f"Brevo: Email sent successfully! Message ID: {api_response.message_id}")
        except ApiException as e:
            print(f"Brevo API Error: {e}")
            return jsonify({'error': f'Failed to send email: {str(e)}'}), 500

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
