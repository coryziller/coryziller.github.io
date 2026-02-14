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

# Simple CORS - allow everything
CORS(app)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()}), 200

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

        # Load report data
        try:
            with open('latest_report.json', 'r') as f:
                report_data = json.load(f)
        except Exception as e:
            print(f"Error loading report: {e}")
            return jsonify({'error': 'Report data not available'}), 500

        # Build email content
        now = datetime.now().strftime('%B %d, %Y')
        total = report_data.get('total_posts', 0)
        sentiment = report_data.get('sentiment_stats', {}).get('overall_label', 'Mixed')
        score = report_data.get('sentiment_stats', {}).get('average_score', 0)
        top_issues = report_data.get('top_issues', [])[:3]

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
I've attached a personalized 30-second audio briefing with key insights.

Best regards,
Cory Ziller
https://coryziller.github.io
"""

        # Generate audio
        top_issue_text = ""
        if top_issues:
            top_issue_text = f"Top issue: {top_issues[0]['category']}."

        audio_script = f"Hi {name}, this is Cory Ziller with your social listening briefing. I've analyzed {total} posts discussing NVIDIA GPUs. Overall sentiment is {sentiment}. {top_issue_text} Check your email for the complete report. Thanks for checking out my work!"

        print(f"Generating audio for {name}")
        tts = gTTS(text=audio_script, lang='en', slow=False)
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        audio_data = audio_buffer.read()
        print(f"Audio generated: {len(audio_data)} bytes")

        # Send email with Brevo
        brevo_api_key = os.environ.get('BREVO_API_KEY')
        sender_email = os.environ.get('SENDER_EMAIL', 'demo@coryziller.com')

        if not brevo_api_key:
            return jsonify({'error': 'Email service not configured'}), 500

        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = brevo_api_key
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        filename = f"nvidia_report_{name.replace(' ', '_')}.mp3"

        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": email, "name": name}],
            sender={"email": sender_email, "name": "Cory Ziller"},
            subject=f"Your NVIDIA GPU Report - {now}",
            text_content=email_body,
            attachment=[{
                "content": audio_base64,
                "name": filename
            }]
        )

        print(f"Sending email to {email}")
        api_response = api_instance.send_transac_email(send_smtp_email)
        print(f"Email sent! Message ID: {api_response.message_id}")

        return jsonify({
            'success': True,
            'message': 'Email sent successfully!'
        }), 200

    except Exception as e:
        print(f"Error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': 'Failed to send demo',
            'details': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
