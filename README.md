# 🚀 Cory Ziller - Interactive Portfolio

[![Live Demo](https://img.shields.io/badge/demo-online-brightgreen.svg)](https://coryziller.github.io)
[![GitHub Pages](https://img.shields.io/badge/deployed-GitHub%20Pages-blue.svg)](https://pages.github.com/)

An interactive, story-driven portfolio website showcasing my social listening automation workflow and data analytics expertise.

## ✨ Features

- **🎨 Interactive Chevron Design** - Full-screen panes with smooth transitions
- **📖 Story-Driven Navigation** - 5-pane journey through the project
- **🎯 Multiple Navigation Methods** - Arrows, keyboard, mouse wheel, dots, and swipe
- **📱 Fully Responsive** - Beautiful on desktop, tablet, and mobile
- **📰 Live News Search** - Real-time company news fetching from Google News
- **⚡ Lightning Fast** - Single-file architecture, no build process needed

## 🌐 Live Demo

**Visit:** [https://coryziller.github.io](https://coryziller.github.io)

## 🚀 Quick Deploy

### Option 1: Automated Script (Recommended)
```bash
cd github_website
./deploy.sh
```

### Option 2: Manual Steps
```bash
# Initialize and push to GitHub
git init
git add .
git commit -m "Initial commit: Interactive portfolio"
git remote add origin https://github.com/coryziller/coryziller.github.io.git
git branch -M main
git push -u origin main

# Then enable GitHub Pages in repository Settings → Pages
```

## 📖 Full Documentation

- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Complete deployment instructions

## 🔄 Updating Your Website

```bash
# Make your changes, then:
./update.sh

# Or manually:
git add .
git commit -m "Updated content"
git push
```

## 📂 Project Structure

```
github_website/
├── index.html              # Main website (all-in-one file)
├── profile.jpg             # Your profile photo
├── deploy.sh              # Initial deployment script
├── update.sh              # Quick update script
├── README.md              # This file
└── DEPLOYMENT_GUIDE.md    # Detailed deployment guide
```

## 🎨 Customization

The website is built with vanilla HTML, CSS, and JavaScript - no frameworks needed!

**Update Content:**
- Edit text directly in `index.html`
- All content is clearly labeled and easy to find
- Changes take effect immediately

**Change Colors:**
Edit the `:root` CSS variables (line ~15):
```css
--primary: #2563eb;
--secondary: #1e40af;
```

**Add Your Photo:**
1. Save your photo as `profile.jpg`
2. Place in the same folder as `index.html`
3. The site will automatically use it!

## 📰 Company News Search

The interactive news search uses Google News RSS feeds (completely free, no API key needed).

**How It Works:**
1. Users enter a company name
2. Fetches latest news from Google News
3. Displays articles with titles, sources, and timestamps
4. Click any article to read the full story

**No setup required** - works out of the box!

## 🛠️ Tech Stack

- **HTML5** - Semantic markup
- **CSS3** - Modern styling with gradients, animations, and flexbox
- **JavaScript (ES6+)** - Interactive navigation, form handling, and API integration
- **Google News RSS** - Real-time news data via RSS2JSON API
- **GitHub Pages** - Free hosting and deployment

## 📱 Browser Support

- ✅ Chrome/Edge (latest)
- ✅ Firefox (latest)
- ✅ Safari (latest)
- ✅ Mobile browsers (iOS Safari, Chrome Mobile)

## 🎯 Navigation Features

- **← → Arrow Keys** - Navigate between panes
- **Mouse Wheel** - Scroll to change panes
- **Click Arrows** - Left/right buttons
- **Navigation Dots** - Jump to specific pane
- **Touch/Swipe** - Mobile-friendly gestures
- **Progress Bar** - Visual indicator at top

## 📊 What's Inside

**Pane 1:** Introduction & About Me
**Pane 2:** The Challenge (Problem Statement)
**Pane 3:** The Solution (Social Listening Automation)
**Pane 4:** How It Works (Visual Workflow)
**Pane 5:** Company News Search (Interactive Real-Time News Demo)

## 🔒 Security

- No sensitive data in repository
- EmailJS keys can be restricted by domain
- GitHub Pages uses HTTPS by default
- No backend = minimal attack surface

## 📈 Performance

- **Load Time:** <1 second
- **File Size:** ~28KB
- **No Dependencies:** Everything in one file
- **No Build Process:** Deploy instantly

## 🌟 Coming Soon

- [ ] Social listening project details from actual GitHub repo
- [ ] Real-time demo with live data
- [ ] Additional project showcases
- [ ] Blog section for technical writing
- [ ] Dark mode toggle

## 📞 Contact

**Cory Ziller**
📧 coryziller@gmail.com
🔗 [LinkedIn](https://linkedin.com/in/coryziller)
💼 STEM MBA Candidate @ Fisher College of Business '27

## 📄 License

Free to use and modify for personal portfolios.

---

**⭐ Star this repo if you find it useful!**

Built with ❤️ using Claude Code
