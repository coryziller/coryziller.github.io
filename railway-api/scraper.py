"""
Social Listening Scraper
Scrapes Reddit and Hacker News for discussions about NVIDIA GPUs
Uses public JSON endpoints - NO API CREDENTIALS NEEDED
"""
import requests
from datetime import datetime, timedelta
import time

class SocialScraper:
    def __init__(self):
        """Initialize scraper - no credentials needed!"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

    def scrape_reddit(self, subreddits=['nvidia', 'hardware', 'buildapc', 'pcmasterrace'],
                      keywords=['nvidia', 'rtx', '4090', '4080', '3090', 'gpu'],
                      days_back=7,
                      limit=25):
        """
        Scrape Reddit using public JSON endpoints (no auth required!)

        Args:
            subreddits: List of subreddits to search
            keywords: Keywords to search for
            days_back: How many days back to search
            limit: Max posts per subreddit

        Returns:
            List of post dictionaries
        """
        posts = []
        cutoff_date = datetime.now() - timedelta(days=days_back)

        print(f"Scraping Reddit - {len(subreddits)} subreddits, {days_back} days back")

        for subreddit_name in subreddits:
            try:
                # Use Reddit's public JSON endpoint
                url = f"https://www.reddit.com/r/{subreddit_name}/new.json?limit={limit}"

                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                data = response.json()

                subreddit_posts = 0
                for post_data in data.get('data', {}).get('children', []):
                    post = post_data.get('data', {})

                    # Get post date
                    post_date = datetime.fromtimestamp(post.get('created_utc', 0))

                    # Only include recent posts
                    if post_date < cutoff_date:
                        continue

                    # Check if post mentions any keywords
                    title = post.get('title', '').lower()
                    text = post.get('selftext', '').lower()

                    if any(keyword.lower() in title or keyword.lower() in text for keyword in keywords):
                        posts.append({
                            'source': 'reddit',
                            'subreddit': subreddit_name,
                            'title': post.get('title', ''),
                            'text': post.get('selftext', ''),
                            'url': f"https://reddit.com{post.get('permalink', '')}",
                            'score': post.get('score', 0),
                            'num_comments': post.get('num_comments', 0),
                            'created_at': post_date.isoformat(),
                            'author': post.get('author', '[deleted]')
                        })
                        subreddit_posts += 1

                print(f"  - r/{subreddit_name}: {subreddit_posts} posts")
                time.sleep(2)  # Be nice to Reddit's servers

            except Exception as e:
                print(f"Error scraping r/{subreddit_name}: {e}")
                continue

        # Also search across Reddit
        print(f"Searching Reddit for keywords: {keywords}")
        for keyword in keywords[:3]:  # Limit to top 3 keywords
            try:
                search_url = f"https://www.reddit.com/search.json?q={keyword}&sort=new&limit={limit}&t=week"

                response = self.session.get(search_url, timeout=10)
                response.raise_for_status()
                data = response.json()

                keyword_posts = 0
                for post_data in data.get('data', {}).get('children', []):
                    post = post_data.get('data', {})

                    post_date = datetime.fromtimestamp(post.get('created_utc', 0))

                    if post_date < cutoff_date:
                        continue

                    # Avoid duplicates
                    post_url = f"https://reddit.com{post.get('permalink', '')}"
                    if any(p['url'] == post_url for p in posts):
                        continue

                    posts.append({
                        'source': 'reddit',
                        'subreddit': post.get('subreddit', 'unknown'),
                        'title': post.get('title', ''),
                        'text': post.get('selftext', ''),
                        'url': post_url,
                        'score': post.get('score', 0),
                        'num_comments': post.get('num_comments', 0),
                        'created_at': post_date.isoformat(),
                        'author': post.get('author', '[deleted]')
                    })
                    keyword_posts += 1

                print(f"  - Search '{keyword}': {keyword_posts} posts")
                time.sleep(2)

            except Exception as e:
                print(f"Error searching Reddit for '{keyword}': {e}")
                continue

        return posts

    def scrape_hackernews(self, keywords=['nvidia', 'rtx', 'gpu'], days_back=7):
        """
        Scrape Hacker News for posts about NVIDIA
        Uses Algolia HN Search API (no auth required)

        Args:
            keywords: Keywords to search for
            days_back: How many days back to search

        Returns:
            List of post dictionaries
        """
        posts = []
        cutoff_timestamp = int((datetime.now() - timedelta(days=days_back)).timestamp())

        print(f"Scraping Hacker News - keywords: {keywords}")

        for keyword in keywords:
            try:
                # Algolia HN Search API
                url = f"http://hn.algolia.com/api/v1/search?query={keyword}&tags=story&numericFilters=created_at_i>{cutoff_timestamp}"
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                data = response.json()

                for hit in data.get('hits', []):
                    posts.append({
                        'source': 'hackernews',
                        'title': hit.get('title', ''),
                        'text': hit.get('story_text', ''),
                        'url': hit.get('url', f"https://news.ycombinator.com/item?id={hit.get('objectID')}"),
                        'score': hit.get('points', 0),
                        'num_comments': hit.get('num_comments', 0),
                        'created_at': datetime.fromtimestamp(hit.get('created_at_i', 0)).isoformat(),
                        'author': hit.get('author', 'unknown')
                    })

                time.sleep(0.5)

            except Exception as e:
                print(f"Error scraping HN for '{keyword}': {e}")
                continue

        print(f"  - Found {len(posts)} Hacker News posts")
        return posts

    def scrape_all(self, days_back=7):
        """
        Scrape both Reddit and Hacker News

        Returns:
            Combined list of all posts
        """
        all_posts = []

        # Scrape Reddit (no auth needed!)
        reddit_posts = self.scrape_reddit(days_back=days_back)
        all_posts.extend(reddit_posts)

        # Scrape Hacker News
        hn_posts = self.scrape_hackernews(days_back=days_back)
        all_posts.extend(hn_posts)

        # Remove duplicates based on URL
        seen_urls = set()
        unique_posts = []
        for post in all_posts:
            if post['url'] not in seen_urls:
                seen_urls.add(post['url'])
                unique_posts.append(post)

        print(f"\nTotal unique posts scraped: {len(unique_posts)}")
        print(f"  - Reddit: {len([p for p in unique_posts if p['source'] == 'reddit'])}")
        print(f"  - Hacker News: {len([p for p in unique_posts if p['source'] == 'hackernews'])}")

        return unique_posts
