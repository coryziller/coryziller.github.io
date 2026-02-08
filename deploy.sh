#!/bin/bash

# 🚀 Quick Deploy Script for GitHub Pages
# This script helps you deploy your portfolio to GitHub

echo "=================================="
echo "🚀 GitHub Portfolio Deployment"
echo "=================================="
echo ""

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo "❌ Git is not installed. Please install Git first:"
    echo "   https://git-scm.com/downloads"
    exit 1
fi

echo "✅ Git is installed"
echo ""

# Check if already a git repository
if [ -d .git ]; then
    echo "📁 Git repository already exists"
    echo ""
else
    echo "📁 Initializing Git repository..."
    git init
    echo "✅ Git repository initialized"
    echo ""
fi

# Check if remote exists
if git remote | grep -q "origin"; then
    echo "🔗 Remote 'origin' already configured:"
    git remote get-url origin
    echo ""
    read -p "Do you want to change it? (y/n): " change_remote
    if [ "$change_remote" = "y" ]; then
        read -p "Enter new GitHub repository URL: " repo_url
        git remote set-url origin "$repo_url"
        echo "✅ Remote updated"
    fi
else
    echo "🔗 Setting up GitHub remote..."
    echo ""
    echo "First, create a repository on GitHub:"
    echo "   https://github.com/new"
    echo ""
    echo "Recommended name: coryziller.github.io"
    echo "Make it PUBLIC and DON'T initialize with README"
    echo ""
    read -p "Enter your GitHub repository URL: " repo_url

    if [ -z "$repo_url" ]; then
        echo "❌ No URL provided. Exiting."
        exit 1
    fi

    git remote add origin "$repo_url"
    echo "✅ Remote configured"
fi

echo ""
echo "📝 Staging files..."
git add .

echo ""
echo "💾 Creating commit..."
read -p "Enter commit message (or press Enter for default): " commit_msg
if [ -z "$commit_msg" ]; then
    commit_msg="Initial commit: Interactive portfolio website"
fi

git commit -m "$commit_msg"

echo ""
echo "🌿 Checking branch name..."
current_branch=$(git branch --show-current)
if [ "$current_branch" != "main" ]; then
    echo "Renaming branch to 'main'..."
    git branch -M main
fi

echo ""
echo "📤 Pushing to GitHub..."
echo ""
echo "⚠️  You'll need to authenticate:"
echo "   Username: coryziller"
echo "   Password: Use a Personal Access Token (NOT your GitHub password)"
echo ""
echo "   Get a token here: https://github.com/settings/tokens"
echo "   Required scopes: 'repo'"
echo ""

read -p "Ready to push? (y/n): " ready
if [ "$ready" != "y" ]; then
    echo "Cancelled. Run this script again when ready."
    exit 0
fi

git push -u origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "=================================="
    echo "🎉 SUCCESS!"
    echo "=================================="
    echo ""
    echo "Your website has been pushed to GitHub!"
    echo ""
    echo "Next steps:"
    echo "1. Go to your repository settings"
    echo "2. Navigate to 'Pages' in the left sidebar"
    echo "3. Under 'Source', select 'main' branch"
    echo "4. Click 'Save'"
    echo "5. Wait 1-2 minutes"
    echo ""
    echo "Your site will be live at:"
    if [[ "$repo_url" == *"coryziller.github.io"* ]]; then
        echo "   🌐 https://coryziller.github.io"
    else
        repo_name=$(basename "$repo_url" .git)
        echo "   🌐 https://coryziller.github.io/$repo_name"
    fi
    echo ""
else
    echo ""
    echo "=================================="
    echo "❌ Push Failed"
    echo "=================================="
    echo ""
    echo "Common issues:"
    echo "1. Authentication failed - Make sure you're using a Personal Access Token"
    echo "2. Repository doesn't exist - Create it on GitHub first"
    echo "3. Permission denied - Check repository access"
    echo ""
    echo "Need help? Check DEPLOYMENT_GUIDE.md"
fi
