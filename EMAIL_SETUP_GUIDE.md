# EmailJS Setup Guide

## 🚀 Quick Setup (5 minutes)

Follow these steps to enable real email sending on your portfolio website.

---

## Step 1: Create EmailJS Account

1. Go to **[https://www.emailjs.com/](https://www.emailjs.com/)**
2. Click **"Sign Up"** (top right)
3. Create a free account using your email
4. Verify your email address

**Free Plan Includes:**
- 200 emails/month
- No credit card required
- Perfect for portfolio demos

---

## Step 2: Add Email Service

1. After logging in, go to **"Email Services"** in the left menu
2. Click **"Add New Service"**
3. Choose your email provider:
   - **Gmail** (Recommended for personal use)
   - **Outlook/Office365**
   - **Yahoo**
   - Or any other supported service
4. Click **"Connect Account"** and authorize EmailJS
5. **Copy your Service ID** (looks like `service_xxxxxxx`)

---

## Step 3: Create Email Template

1. Go to **"Email Templates"** in the left menu
2. Click **"Create New Template"**
3. Set up your template:

### Template Settings:
- **Template Name:** `portfolio_demo_email`

### Email Content (Subject):
```
🚀 Automation Demo from Cory Ziller's Portfolio
```

### Email Content (Body):
```html
Hello!

Thank you for trying out my email automation workflow demo!

---

YOUR MESSAGE:
{{user_message}}

---

HOW THIS WORKS:

📧 Step 1: Email Received
Your request was captured by the automated system

🔍 Step 2: Data Extracted
Key information was parsed and structured:
• Recipient: {{to_email}}
• Timestamp: {{current_time}}
• Message Content: Analyzed and categorized

🧠 Step 3: AI Processing
The system analyzed your message and generated this response

✉️ Step 4: Automated Delivery
This formatted email was sent automatically!

---

WHAT THIS DEMONSTRATES:

✓ 24/7 Monitoring - System runs continuously
✓ Instant Processing - Response generated in seconds
✓ Smart Formatting - Professional email layout
✓ Reliable Delivery - Guaranteed message arrival

This same workflow can be applied to:
• Customer inquiry responses
• Data report generation
• Meeting summaries
• Content notifications
• And much more!

---

Want to learn more about this automation workflow?
Visit: https://linkedin.com/in/coryziller

Best regards,
Cory Ziller
STEM MBA Candidate | Sr. Data Analyst
```

### Template Variables to Use:
- `{{to_email}}` - Recipient's email
- `{{user_message}}` - The message they entered
- `{{from_name}}` - Your name (automatically filled)

4. Click **"Save"**
5. **Copy your Template ID** (looks like `template_xxxxxxx`)

---

## Step 4: Get Your Public Key

1. Go to **"Account"** in the left menu
2. Scroll down to **"API Keys"** section
3. **Copy your Public Key** (looks like a long string)

---

## Step 5: Add Keys to Your Website

1. Open `index.html` in a text editor
2. Find this section (around line 660):

```javascript
// EmailJS Configuration
const EMAILJS_PUBLIC_KEY = 'YOUR_PUBLIC_KEY_HERE';
const EMAILJS_SERVICE_ID = 'YOUR_SERVICE_ID_HERE';
const EMAILJS_TEMPLATE_ID = 'YOUR_TEMPLATE_ID_HERE';
```

3. Replace with your actual values:

```javascript
// EmailJS Configuration
const EMAILJS_PUBLIC_KEY = 'paste_your_public_key_here';
const EMAILJS_SERVICE_ID = 'service_xxxxxxx';
const EMAILJS_TEMPLATE_ID = 'template_xxxxxxx';
```

4. Save the file

---

## Step 6: Test It Out!

1. Open `index.html` in your browser
2. Navigate to Page 5 (the demo form)
3. Enter your email address
4. Click "Send Me a Demo Report"
5. Check your inbox!

---

## 🎨 Customize the Email Template

Want to make the email look even better? You can use HTML in the EmailJS template:

### Example HTML Template:
```html
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #f9fafb; padding: 40px 20px;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 10px; color: white; text-align: center;">
        <h1 style="margin: 0;">🚀 Automation Demo</h1>
        <p style="margin: 10px 0 0; opacity: 0.9;">From Cory Ziller's Portfolio</p>
    </div>

    <div style="background: white; padding: 30px; margin-top: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
        <h2 style="color: #2563eb;">Thank You for Testing!</h2>
        <p>Your message was successfully processed by the automation workflow.</p>

        <div style="background: #f3f4f6; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <strong>Your Message:</strong><br>
            {{user_message}}
        </div>

        <h3 style="color: #2563eb;">🔄 How It Worked:</h3>
        <ol style="line-height: 1.8;">
            <li><strong>Received:</strong> Your request was captured</li>
            <li><strong>Extracted:</strong> Key data was parsed</li>
            <li><strong>Analyzed:</strong> AI processed the content</li>
            <li><strong>Delivered:</strong> This email was sent automatically</li>
        </ol>

        <div style="text-align: center; margin-top: 30px;">
            <a href="https://linkedin.com/in/coryziller" style="display: inline-block; padding: 15px 30px; background: #2563eb; color: white; text-decoration: none; border-radius: 50px; font-weight: bold;">Connect on LinkedIn</a>
        </div>
    </div>

    <div style="text-align: center; margin-top: 20px; color: #6b7280; font-size: 14px;">
        <p>Sent by Cory Ziller's Automated Portfolio System</p>
    </div>
</div>
```

---

## 📊 Monitor Email Sends

1. Go to EmailJS Dashboard
2. Click **"Email History"**
3. See all sent emails, delivery status, and errors

---

## 🔒 Security Best Practices

### For Production (GitHub Pages):

**Option 1: Use EmailJS Domain Restrictions**
1. Go to EmailJS Account Settings
2. Add your GitHub Pages domain (e.g., `username.github.io`)
3. This prevents unauthorized use of your keys

**Option 2: Environment Variables (Advanced)**
If deploying to Netlify/Vercel:
1. Store keys as environment variables
2. Use build-time substitution
3. Never commit keys to GitHub

### For Now (Demo):
- The free tier (200 emails/month) is safe for portfolio demos
- Keys in the code are fine for low-traffic personal sites
- Monitor your EmailJS dashboard for unusual activity

---

## 🆘 Troubleshooting

### "Failed to send email" error
- **Check:** Are your keys correct?
- **Check:** Is your email service connected in EmailJS?
- **Check:** Did you authorize EmailJS to access your email?

### Email not arriving
- **Check:** Spam folder
- **Check:** EmailJS email history - was it sent?
- **Check:** Template variables match ({{to_email}} vs {{email}})

### "EmailJS Not Configured" message
- **Check:** Did you replace ALL THREE placeholders?
- **Check:** No quotes around the keys (use single quotes)
- **Check:** Saved the file after editing

### Rate limit exceeded
- **Free tier:** 200 emails/month
- **Solution:** Upgrade to paid plan or wait for monthly reset

---

## 💰 Pricing (If You Need More)

| Plan | Emails/Month | Price |
|------|--------------|-------|
| Free | 200 | $0 |
| Basic | 1,000 | $7/mo |
| Pro | 10,000 | $15/mo |

For a portfolio demo, **Free is perfect!**

---

## 🎯 Alternative: Custom Backend (Advanced)

If you want more control, you can build your own backend:

### Quick Options:
1. **Vercel Serverless Function** (Free)
2. **AWS Lambda + SES** (Very cheap)
3. **Netlify Functions** (Free tier)

I can help you set this up if needed!

---

## ✅ Checklist

- [ ] Created EmailJS account
- [ ] Added email service (Gmail/Outlook)
- [ ] Created email template
- [ ] Copied Service ID
- [ ] Copied Template ID
- [ ] Copied Public Key
- [ ] Updated index.html with all three keys
- [ ] Tested the form
- [ ] Received demo email

---

**Need Help?** Feel free to reach out or check the [EmailJS Documentation](https://www.emailjs.com/docs/)

---

Built with ❤️ for automated portfolios
