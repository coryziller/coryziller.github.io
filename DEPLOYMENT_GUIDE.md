# 🚀 GitHub Website Deployment Guide

Complete guide to connect your local files with GitHub and deploy your portfolio website.

---

## 📋 Prerequisites

- GitHub account (you have: coryziller)
- Git installed on your computer
- Your website files in a folder (you have: github_website)

---

## 🎯 Step 1: Initialize Git Repository

Open Terminal/Command Prompt and navigate to your website folder:

```bash
cd /path/to/github_website
```

Initialize a new Git repository:

```bash
git init
git add .
git commit -m "Initial commit: Interactive portfolio with social listening project"
```

---

## 🌐 Step 2: Create GitHub Repository

### Option A: Using GitHub Website

1. Go to **[https://github.com/new](https://github.com/new)**
2. **Repository name:** Choose one:
   - `coryziller.github.io` (makes your site available at `https://coryziller.github.io`)
   - OR `portfolio` or any name (site will be at `https://coryziller.github.io/portfolio`)
3. **Description:** "Interactive portfolio showcasing social listening automation workflow"
4. **Public** (required for free GitHub Pages)
5. **DO NOT** initialize with README, .gitignore, or license
6. Click **"Create repository"**

### Option B: Using Command Line (if you have GitHub CLI)

```bash
gh repo create coryziller.github.io --public --source=. --remote=origin
```

---

## 🔗 Step 3: Connect Local Folder to GitHub

Copy the commands from GitHub (they'll show up after creating the repo), or use these:

```bash
# Add the GitHub repository as remote
git remote add origin https://github.com/coryziller/coryziller.github.io.git

# Rename branch to main (if needed)
git branch -M main

# Push your code to GitHub
git push -u origin main
```

**Note:** You might need to authenticate:
- Enter your GitHub username
- For password, use a **Personal Access Token** (not your GitHub password)

### Create Personal Access Token:
1. Go to **GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)**
2. Click **"Generate new token (classic)"**
3. Give it a name: "Website Deployment"
4. Select scopes: `repo` (full control)
5. Click **"Generate token"**
6. **Copy the token** (you won't see it again!)
7. Use this as your password when pushing

---

## 🌍 Step 4: Enable GitHub Pages

1. Go to your repository: `https://github.com/coryziller/coryziller.github.io`
2. Click **Settings** (top menu)
3. Scroll down to **"Pages"** in the left sidebar
4. Under **"Source"**, select:
   - Branch: `main`
   - Folder: `/ (root)`
5. Click **"Save"**
6. Wait 1-2 minutes for deployment
7. Your site will be live at: `https://coryziller.github.io`

---

## 🔄 Step 5: Workflow for Updates

### Every Time You Make Changes:

```bash
# 1. Check what files changed
git status

# 2. Stage your changes
git add .
# Or add specific files: git add index.html

# 3. Commit with a descriptive message
git commit -m "Updated social listening project details"

# 4. Push to GitHub
git push

# 5. Wait 30-60 seconds for GitHub Pages to rebuild
# Your site will automatically update!
```

---

## 🤖 Step 6: Automatic Deployment (Optional but Recommended)

GitHub Pages already deploys automatically, but you can add a GitHub Action for more control:

Create this file: `.github/workflows/deploy.yml`

```yaml
name: Deploy Website

on:
  push:
    branches: [ main ]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Pages
        uses: actions/configure-pages@v4

      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: '.'

      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

This ensures your site deploys every time you push changes.

---

## 📸 Step 7: Add Your Profile Photo

1. Save your profile photo as `profile.jpg` in the `github_website` folder
2. Commit and push:

```bash
git add profile.jpg
git commit -m "Added profile photo"
git push
```

Your photo will now appear on the website!

---

## 📂 Step 8: Project File Structure

Your final repository should look like:

```
github_website/
├── index.html                  # Main website
├── profile.jpg                 # Your photo
├── README.md                   # Project description
├── EMAIL_SETUP_GUIDE.md       # EmailJS setup
├── DEPLOYMENT_GUIDE.md        # This file
└── .github/
    └── workflows/
        └── deploy.yml         # Auto-deployment (optional)
```

---

## 🔧 Common Commands Reference

### Check Status
```bash
git status                     # See what files changed
git log --oneline             # View commit history
```

### Update Website
```bash
git add .                     # Stage all changes
git commit -m "Your message"  # Commit changes
git push                      # Deploy to GitHub
```

### Undo Changes (Before Commit)
```bash
git restore index.html        # Undo changes to a file
git restore .                 # Undo all changes
```

### View Remote Info
```bash
git remote -v                 # Show GitHub connection
```

### Pull Latest Changes
```bash
git pull                      # Get latest from GitHub
```

---

## 🌟 Advanced: Custom Domain (Optional)

Want your site at `www.coryziller.com` instead of `coryziller.github.io`?

### Step 1: Buy a Domain
- Namecheap, Google Domains, etc.

### Step 2: Add CNAME File
Create a file named `CNAME` (no extension) with your domain:

```
www.coryziller.com
```

### Step 3: Configure DNS
In your domain provider's DNS settings, add:

**For apex domain (coryziller.com):**
```
A Record:
@ → 185.199.108.153
@ → 185.199.109.153
@ → 185.199.110.153
@ → 185.199.111.153
```

**For www subdomain:**
```
CNAME Record:
www → coryziller.github.io
```

### Step 4: Enable in GitHub
1. GitHub Settings → Pages
2. Custom domain: `www.coryziller.com`
3. Check "Enforce HTTPS"
4. Wait 24-48 hours for DNS propagation

---

## 🆘 Troubleshooting

### "Permission denied (publickey)"
**Solution:** Use HTTPS instead of SSH:
```bash
git remote set-url origin https://github.com/coryziller/coryziller.github.io.git
```

### "Updates were rejected"
**Solution:** Pull first, then push:
```bash
git pull origin main --rebase
git push
```

### Website not updating
**Solution:**
1. Check GitHub Actions tab for deployment status
2. Hard refresh browser: `Ctrl+Shift+R` (Windows) or `Cmd+Shift+R` (Mac)
3. Clear browser cache

### 404 Error on GitHub Pages
**Solution:**
1. Make sure `index.html` is in the root folder
2. Check GitHub Pages is enabled in Settings
3. Wait a few minutes after first push

---

## 📱 Step 9: Test Your Website

After deployment, test on multiple devices:

- **Desktop:** Chrome, Firefox, Safari
- **Mobile:** iPhone, Android
- **Navigation:** Try all 5 panes
- **Form:** Test the email demo (after setting up EmailJS)
- **Links:** Click LinkedIn button

---

## 🎨 Step 10: Update Social Listening Project Details

Once you figure out your social listening project details, update:

1. **Pane 2 (The Challenge)** - What problem does it solve?
2. **Pane 3 (The Solution)** - What does your project do?
3. **Pane 4 (How It Works)** - Update the workflow steps
4. **Pane 5 (Try It)** - Configure email template

Then commit and push:
```bash
git add index.html
git commit -m "Updated with real social listening project details"
git push
```

---

## 📊 Step 11: Track Your Website

### Add Google Analytics (Optional)

1. Go to [analytics.google.com](https://analytics.google.com)
2. Create a property for your website
3. Get your Measurement ID (looks like `G-XXXXXXXXXX`)
4. Add to `index.html` before `</head>`:

```html
<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-XXXXXXXXXX');
</script>
```

---

## ✅ Deployment Checklist

- [ ] Git repository initialized
- [ ] GitHub repository created
- [ ] Code pushed to GitHub
- [ ] GitHub Pages enabled
- [ ] Website accessible at URL
- [ ] Profile photo added
- [ ] EmailJS configured (for demo form)
- [ ] Social listening project details updated
- [ ] Tested on desktop and mobile
- [ ] LinkedIn link works
- [ ] All 5 panes navigate correctly
- [ ] Custom domain configured (optional)
- [ ] Google Analytics added (optional)

---

## 🎯 Quick Start Commands

```bash
# One-time setup
cd /path/to/github_website
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/coryziller/coryziller.github.io.git
git branch -M main
git push -u origin main

# Future updates
git add .
git commit -m "Updated content"
git push
```

---

## 📞 Need Help?

- **GitHub Pages Docs:** [docs.github.com/pages](https://docs.github.com/pages)
- **Git Tutorial:** [git-scm.com/doc](https://git-scm.com/doc)
- **Contact:** coryziller@gmail.com

---

Your portfolio will be live at: **https://coryziller.github.io** 🎉

Once deployed, share it on:
- LinkedIn
- Resume
- Email signature
- Business cards
