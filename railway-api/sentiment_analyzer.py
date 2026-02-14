"""
Sentiment Analyzer using OpenAI API
Analyzes user feedback to identify sentiment, pain points, and feature requests
"""
from openai import OpenAI
import json

class SentimentAnalyzer:
    def __init__(self, api_key):
        """Initialize OpenAI client"""
        self.client = OpenAI(api_key=api_key)

    def analyze_batch(self, posts, batch_size=10):
        """
        Analyze sentiment of multiple posts using OpenAI

        Args:
            posts: List of post dictionaries
            batch_size: Number of posts to analyze per API call

        Returns:
            List of posts with sentiment analysis added
        """
        analyzed_posts = []

        # Process in batches to optimize API usage
        for i in range(0, len(posts), batch_size):
            batch = posts[i:i + batch_size]
            print(f"Analyzing posts {i+1}-{min(i+batch_size, len(posts))} of {len(posts)}")

            try:
                # Prepare batch for analysis
                posts_text = []
                for idx, post in enumerate(batch):
                    post_content = f"Title: {post['title']}\nText: {post['text'][:500]}"
                    posts_text.append(f"POST {idx}: {post_content}")

                combined_text = "\n\n".join(posts_text)

                # Create prompt for GPT
                prompt = f"""Analyze these social media posts about NVIDIA products for sentiment and key issues.

{combined_text}

For each post, provide:
1. Sentiment score (0-100, where 0=very negative, 50=neutral, 100=very positive)
2. Sentiment label (Positive, Neutral, Negative)
3. Main category (e.g., "Performance Issues", "Driver Problems", "Pricing Concerns", "Feature Request", "General Praise")
4. Key pain point or praise (one sentence)
5. Severity (Low, Medium, High, Critical) - based on how urgent/impactful the issue is

Return ONLY valid JSON in this exact format:
{{
  "analyses": [
    {{
      "post_index": 0,
      "sentiment_score": 45,
      "sentiment_label": "Negative",
      "category": "Performance Issues",
      "key_point": "Users experiencing frame drops with RTX 4090 in specific games",
      "severity": "High"
    }}
  ]
}}"""

                # Call OpenAI API
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",  # Cost-effective model
                    messages=[
                        {"role": "system", "content": "You are a product analyst specializing in extracting actionable insights from user feedback. Always return valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,  # Lower temperature for more consistent analysis
                    response_format={"type": "json_object"}
                )

                # Parse response
                result = json.loads(response.choices[0].message.content)
                analyses = result.get('analyses', [])

                # Add sentiment data to posts
                for analysis in analyses:
                    post_idx = analysis.get('post_index', 0)
                    if post_idx < len(batch):
                        post = batch[post_idx]
                        post['sentiment_score'] = analysis.get('sentiment_score', 50)
                        post['sentiment_label'] = analysis.get('sentiment_label', 'Neutral')
                        post['category'] = analysis.get('category', 'Uncategorized')
                        post['key_point'] = analysis.get('key_point', '')
                        post['severity'] = analysis.get('severity', 'Medium')
                        analyzed_posts.append(post)

            except Exception as e:
                print(f"Error analyzing batch {i//batch_size + 1}: {e}")
                # Add posts without analysis if API fails
                for post in batch:
                    post['sentiment_score'] = 50
                    post['sentiment_label'] = 'Neutral'
                    post['category'] = 'Uncategorized'
                    post['key_point'] = 'Analysis unavailable'
                    post['severity'] = 'Low'
                    analyzed_posts.append(post)

        return analyzed_posts

    def generate_summary_stats(self, analyzed_posts):
        """
        Generate summary statistics from analyzed posts

        Returns:
            Dictionary with summary stats
        """
        if not analyzed_posts:
            return {
                'total_posts': 0,
                'average_score': 50,
                'overall_label': 'Neutral',
                'sentiment_distribution': {}
            }

        # Calculate average sentiment
        avg_score = sum(p['sentiment_score'] for p in analyzed_posts) / len(analyzed_posts)

        # Determine overall label
        if avg_score >= 60:
            overall_label = 'Positive'
        elif avg_score >= 40:
            overall_label = 'Mixed'
        else:
            overall_label = 'Negative'

        # Count sentiment distribution
        sentiment_counts = {}
        for post in analyzed_posts:
            label = post['sentiment_label']
            sentiment_counts[label] = sentiment_counts.get(label, 0) + 1

        return {
            'total_posts': len(analyzed_posts),
            'average_score': round(avg_score, 1),
            'overall_label': overall_label,
            'sentiment_distribution': sentiment_counts
        }

    def extract_top_issues(self, analyzed_posts, limit=5):
        """
        Extract top issues based on severity and frequency

        Returns:
            List of top issues
        """
        # Group by category
        categories = {}
        for post in analyzed_posts:
            cat = post['category']
            if cat not in categories:
                categories[cat] = {
                    'category': cat,
                    'count': 0,
                    'severity_scores': [],
                    'examples': []
                }

            categories[cat]['count'] += 1
            categories[cat]['examples'].append(post['key_point'])

            # Convert severity to numeric
            severity_map = {'Low': 1, 'Medium': 2, 'High': 3, 'Critical': 4}
            categories[cat]['severity_scores'].append(severity_map.get(post['severity'], 2))

        # Calculate priority score (frequency * avg severity)
        issues = []
        for cat_data in categories.values():
            avg_severity = sum(cat_data['severity_scores']) / len(cat_data['severity_scores'])
            priority = cat_data['count'] * avg_severity

            # Map severity back to label
            severity_labels = {1: 'Low', 2: 'Medium', 3: 'High', 4: 'Critical'}
            avg_severity_label = severity_labels[round(avg_severity)]

            issues.append({
                'category': cat_data['category'],
                'count': cat_data['count'],
                'severity': avg_severity_label,
                'priority_score': round(priority, 1),
                'title': cat_data['examples'][0] if cat_data['examples'] else 'No details'
            })

        # Sort by priority
        issues.sort(key=lambda x: x['priority_score'], reverse=True)

        return issues[:limit]
