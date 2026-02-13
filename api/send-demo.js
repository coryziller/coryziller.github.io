import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import nodemailer from 'nodemailer';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

export default async function handler(req, res) {
  // CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { name, email } = req.body;

    if (!name || !email) {
      return res.status(400).json({ error: 'Name and email are required' });
    }

    // Load cached report data
    const reportPath = join(__dirname, '..', 'latest_report.json');
    const reportData = JSON.parse(readFileSync(reportPath, 'utf-8'));

    // Build personalized script
    const now = new Date().toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });

    const total = reportData.total_posts || 0;
    const sentiment = reportData.sentiment_stats?.overall_label || 'Mixed';
    const score = reportData.sentiment_stats?.average_score || 0;
    const topIssues = reportData.top_issues?.slice(0, 3) || [];

    const emailBody = `Hi ${name},

Thank you for your interest in my Social Listening project!

📊 LATEST NVIDIA GPU SENTIMENT REPORT — ${now}

Posts analyzed: ${total}
Overall sentiment: ${sentiment} (${score}/100)

🔥 TOP ISSUES DETECTED:
${topIssues.map((issue, i) => `${i + 1}. [${issue.severity.toUpperCase()}] ${issue.category}: ${issue.title}`).join('\n')}

🎧 I've attached a personalized 30-second audio briefing just for you.

This demo showcases how I built an automated social listening system that:
- Scrapes Reddit & Hacker News for NVIDIA GPU discussions
- Analyzes sentiment and prioritizes issues
- Generates personalized audio briefings using AI text-to-speech
- Delivers insights via automated email

Thanks for checking out my work!

Best regards,
Cory Ziller
https://coryziller.github.io
`;

    // Build personalized audio script
    const audioScript = `Hi ${name}, this is your 30 second round up for ${now}. Found ${total} posts discussing NVIDIA GPU issues. Sentiment: ${sentiment}. ${topIssues.length > 0 ? `Top issue: ${topIssues[0].category}. ${topIssues[0].title.substring(0, 60)}.` : ''} Check your email for full details.`;

    // Generate audio with ElevenLabs
    const elevenLabsKey = process.env.ELEVENLABS_API_KEY;
    if (!elevenLabsKey) {
      return res.status(500).json({ error: 'ElevenLabs API key not configured' });
    }

    const voiceId = "21m00Tcm4TlvDq8ikWAM"; // Rachel voice
    const ttsResponse = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${voiceId}`, {
      method: 'POST',
      headers: {
        'Accept': 'audio/mpeg',
        'Content-Type': 'application/json',
        'xi-api-key': elevenLabsKey
      },
      body: JSON.stringify({
        text: audioScript,
        model_id: "eleven_monolingual_v1",
        voice_settings: {
          stability: 0.5,
          similarity_boost: 0.75,
          style: 0.0,
          use_speaker_boost: true
        }
      })
    });

    if (!ttsResponse.ok) {
      const errorText = await ttsResponse.text();
      console.error('ElevenLabs error:', errorText);
      return res.status(500).json({ error: 'Failed to generate audio' });
    }

    const audioBuffer = Buffer.from(await ttsResponse.arrayBuffer());

    // Send email with attachment
    const transporter = nodemailer.createTransport({
      service: 'gmail',
      auth: {
        user: process.env.SENDER_EMAIL,
        pass: process.env.GMAIL_APP_PASSWORD
      }
    });

    const mailOptions = {
      from: process.env.SENDER_EMAIL,
      to: email,
      subject: `🎧 Your Personalized NVIDIA GPU Report — ${now}`,
      text: emailBody,
      attachments: [
        {
          filename: `nvidia_report_${name.replace(/\s+/g, '_')}.mp3`,
          content: audioBuffer,
          contentType: 'audio/mpeg'
        }
      ]
    };

    await transporter.sendMail(mailOptions);

    return res.status(200).json({
      success: true,
      message: 'Email sent successfully with personalized audio report!'
    });

  } catch (error) {
    console.error('Error:', error);
    return res.status(500).json({
      error: 'Failed to send demo',
      details: error.message
    });
  }
}
