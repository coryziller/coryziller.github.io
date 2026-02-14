"""
Social Listening Report Generator
Orchestrates scraping, analysis, and report generation
NO REDDIT CREDENTIALS NEEDED - uses public JSON endpoints!
"""
import os
import json
from datetime import datetime
from scraper import SocialScraper
from sentiment_analyzer import SentimentAnalyzer

def generate_report():
    """
    Main function to generate the social listening report
    Scrapes data, analyzes sentiment, and saves to latest_report.json
    """
    print("=" * 60)
    print("SOCIAL LISTENING REPORT GENERATOR")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Load environment variables
    openai_api_key = os.environ.get('OPENAI_API_KEY')

    # Validate API credentials
    if not openai_api_key:
        print("❌ ERROR: Missing OPENAI_API_KEY environment variable")
        print("Please set this in your .env file or Railway dashboard.")
        print("See .env.example for template.\n")
        return False

    # Step 1: Scrape data (no Reddit auth needed!)
    print("\n📡 STEP 1: SCRAPING DATA")
    print("-" * 60)
    print("Using Reddit's public JSON endpoints - no credentials needed!")
    scraper = SocialScraper()

    posts = scraper.scrape_all(days_back=7)

    if not posts:
        print("❌ No posts found. Check your internet connection.\n")
        return False

    print(f"✅ Scraped {len(posts)} total posts")

    # Step 2: Analyze sentiment
    print("\n🤖 STEP 2: ANALYZING SENTIMENT")
    print("-" * 60)
    analyzer = SentimentAnalyzer(api_key=openai_api_key)

    analyzed_posts = analyzer.analyze_batch(posts, batch_size=10)
    print(f"✅ Analyzed {len(analyzed_posts)} posts")

    # Step 3: Generate summary statistics
    print("\n📊 STEP 3: GENERATING SUMMARY")
    print("-" * 60)
    sentiment_stats = analyzer.generate_summary_stats(analyzed_posts)
    top_issues = analyzer.extract_top_issues(analyzed_posts, limit=5)

    print(f"Average sentiment: {sentiment_stats['average_score']}/100 ({sentiment_stats['overall_label']})")
    print(f"Top issues identified: {len(top_issues)}")

    # Step 4: Save report
    print("\n💾 STEP 4: SAVING REPORT")
    print("-" * 60)

    report = {
        'generated_at': datetime.now().isoformat(),
        'total_posts': len(analyzed_posts),
        'sentiment_stats': sentiment_stats,
        'top_issues': top_issues,
        'posts': analyzed_posts  # Include full post data
    }

    # Save to latest_report.json
    with open('latest_report.json', 'w') as f:
        json.dump(report, f, indent=2)

    print(f"✅ Report saved to latest_report.json")

    # Print summary
    print("\n" + "=" * 60)
    print("REPORT SUMMARY")
    print("=" * 60)
    print(f"Total posts analyzed: {report['total_posts']}")
    print(f"Overall sentiment: {sentiment_stats['overall_label']} ({sentiment_stats['average_score']}/100)")
    print(f"\nSentiment distribution:")
    for label, count in sentiment_stats['sentiment_distribution'].items():
        print(f"  - {label}: {count} posts")
    print(f"\nTop 5 Issues:")
    for i, issue in enumerate(top_issues, 1):
        print(f"  {i}. [{issue['severity']}] {issue['category']} ({issue['count']} mentions)")
        print(f"     {issue['title'][:80]}...")

    print("\n✅ Report generation complete!")
    print("=" * 60)
    return True

if __name__ == '__main__':
    success = generate_report()
    exit(0 if success else 1)
