#!/usr/bin/env python3
"""
Daily Reddit & Hacker News Sentiment Scraper
Runs via GitHub Actions at 6 AM UTC daily
"""

import os
import json
import requests
from datetime import datetime
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

def scrape_reddit(query="NVIDIA", limit=10):
    """Scrape recent posts from Reddit"""
    print(f"🔍 Scraping Reddit for '{query}'...")

    url = "https://www.reddit.com/search.json"
    headers = {'User-Agent': 'SentimentBot/1.0'}
    params = {
        'q': query,
        'sort': 'new',
        'limit': limit,
        't': 'day'  # Posts from the last day
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        posts = []
        for post in data['data']['children']:
            p = post['data']
            posts.append({
                'title': p.get('title', ''),
                'text': p.get('selftext', ''),
                'score': p.get('score', 0),
                'url': f"https://reddit.com{p.get('permalink', '')}",
                'source': 'Reddit'
            })

        print(f"✅ Found {len(posts)} Reddit posts")
        return posts
    except Exception as e:
        print(f"❌ Reddit scraping failed: {e}")
        return []

def scrape_hackernews(query="NVIDIA", limit=10):
    """Scrape recent stories from Hacker News"""
    print(f"🔍 Scraping Hacker News for '{query}'...")

    # Search Algolia HN API
    url = "https://hn.algolia.com/api/v1/search"
    params = {
        'query': query,
        'tags': 'story',
        'hitsPerPage': limit
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        posts = []
        for hit in data.get('hits', []):
            posts.append({
                'title': hit.get('title', ''),
                'text': hit.get('story_text', ''),
                'score': hit.get('points', 0),
                'url': f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
                'source': 'Hacker News'
            })

        print(f"✅ Found {len(posts)} Hacker News stories")
        return posts
    except Exception as e:
        print(f"❌ Hacker News scraping failed: {e}")
        return []

def analyze_sentiment(posts):
    """Use OpenAI to analyze sentiment of posts"""
    print(f"🤖 Analyzing sentiment with OpenAI...")

    if not posts:
        print("⚠️ No posts to analyze")
        return {
            'summary': 'No data available',
            'sentiment': 'neutral',
            'key_themes': [],
            'posts_analyzed': 0
        }

    # Prepare text for analysis
    posts_text = "\n\n".join([
        f"Source: {p['source']}\nTitle: {p['title']}\nText: {p['text'][:500]}\nScore: {p['score']}"
        for p in posts[:15]  # Limit to avoid token limits
    ])

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a sentiment analyst. Analyze the following social media posts about NVIDIA and provide: 1) Overall sentiment (positive/negative/neutral), 2) Key themes (3-5 bullet points), 3) Brief summary (2-3 sentences)."
                },
                {
                    "role": "user",
                    "content": posts_text
                }
            ],
            max_tokens=500,
            temperature=0.3
        )

        analysis = response.choices[0].message.content

        # Parse sentiment
        sentiment = 'neutral'
        if 'positive' in analysis.lower():
            sentiment = 'positive'
        elif 'negative' in analysis.lower():
            sentiment = 'negative'

        print(f"✅ Sentiment analysis complete: {sentiment}")

        return {
            'summary': analysis,
            'sentiment': sentiment,
            'posts_analyzed': len(posts),
            'timestamp': datetime.utcnow().isoformat()
        }

    except Exception as e:
        print(f"❌ OpenAI analysis failed: {e}")
        return {
            'summary': f'Analysis failed: {str(e)}',
            'sentiment': 'error',
            'posts_analyzed': len(posts),
            'timestamp': datetime.utcnow().isoformat()
        }

def main():
    """Main execution"""
    print("=" * 60)
    print("🚀 Starting Daily Sentiment Scraper")
    print(f"⏰ Timestamp: {datetime.utcnow().isoformat()}")
    print("=" * 60)

    # Scrape data
    reddit_posts = scrape_reddit("NVIDIA", limit=10)
    hn_posts = scrape_hackernews("NVIDIA", limit=10)

    all_posts = reddit_posts + hn_posts

    # Analyze sentiment
    analysis = analyze_sentiment(all_posts)

    # Prepare report
    report = {
        'timestamp': datetime.utcnow().isoformat(),
        'query': 'NVIDIA',
        'total_posts': len(all_posts),
        'reddit_posts': len(reddit_posts),
        'hackernews_posts': len(hn_posts),
        'analysis': analysis,
        'sample_posts': [
            {
                'title': p['title'],
                'source': p['source'],
                'score': p['score'],
                'url': p['url']
            }
            for p in all_posts[:5]  # Include top 5 posts
        ]
    }

    # Save to file
    output_path = 'railway-api/latest_report.json'
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)

    print("=" * 60)
    print(f"✅ Report saved to {output_path}")
    print(f"📊 Total posts analyzed: {len(all_posts)}")
    print(f"😊 Overall sentiment: {analysis.get('sentiment', 'unknown')}")
    print("=" * 60)

if __name__ == '__main__':
    main()
