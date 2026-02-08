#!/bin/bash

# 🔄 Quick Update Script
# Use this to push changes to your website after initial deployment

echo "=================================="
echo "🔄 Updating Your Website"
echo "=================================="
echo ""

# Check if git repository exists
if [ ! -d .git ]; then
    echo "❌ Not a git repository. Run deploy.sh first!"
    exit 1
fi

# Show what changed
echo "📝 Files changed:"
git status --short
echo ""

# Ask for confirmation
read -p "Do you want to push these changes? (y/n): " confirm
if [ "$confirm" != "y" ]; then
    echo "Cancelled."
    exit 0
fi

# Get commit message
echo ""
read -p "Enter commit message: " commit_msg
if [ -z "$commit_msg" ]; then
    commit_msg="Updated website content"
fi

echo ""
echo "📦 Staging changes..."
git add .

echo "💾 Committing..."
git commit -m "$commit_msg"

echo "📤 Pushing to GitHub..."
git push

if [ $? -eq 0 ]; then
    echo ""
    echo "=================================="
    echo "✅ Update Successful!"
    echo "=================================="
    echo ""
    echo "Your website will update in 30-60 seconds."
    echo "View it at: https://coryziller.github.io"
    echo ""
else
    echo ""
    echo "❌ Push failed. Check your internet connection and GitHub access."
fi
