#!/usr/bin/env python3
"""
Spotify Data Auto-Updater
Automatically fetches new Spotify streaming data and updates the dashboard

This script should be run periodically (daily/weekly) to keep the dashboard fresh
"""

import json
import os
import sys
from datetime import datetime
import subprocess

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "spotify-trends")
ANALYZER_SCRIPT = os.path.join(os.path.dirname(SCRIPT_DIR), "spotify_trends_analyzer.py")

def log(message):
    """Print timestamped log message"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def check_for_new_data():
    """Check if there are new Spotify data files"""
    log("Checking for new Spotify data...")
    # In a real implementation, this would:
    # 1. Check the Spotify API for new streaming history
    # 2. Download any new data files
    # 3. Return True if new data was found
    return True

def run_analysis():
    """Run the Spotify trends analysis script"""
    log("Running Spotify trends analysis...")
    try:
        result = subprocess.run(
            ['python3', ANALYZER_SCRIPT],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        if result.returncode == 0:
            log("✅ Analysis completed successfully")
            return True
        else:
            log(f"❌ Analysis failed with error:\n{result.stderr}")
            return False
    except Exception as e:
        log(f"❌ Error running analysis: {e}")
        return False

def update_last_updated():
    """Update the last_updated.json file with current timestamp"""
    last_updated = {
        'timestamp': datetime.now().isoformat(),
        'date_readable': datetime.now().strftime("%B %d, %Y at %I:%M %p")
    }

    output_path = os.path.join(DATA_DIR, 'last_updated.json')
    with open(output_path, 'w') as f:
        json.dump(last_updated, f, indent=2)

    log(f"✅ Updated last_updated.json")

def main():
    """Main update process"""
    log("=" * 60)
    log("SPOTIFY DATA AUTO-UPDATER")
    log("=" * 60)

    # Step 1: Check for new data
    has_new_data = check_for_new_data()

    if not has_new_data:
        log("No new data found. Skipping update.")
        return

    # Step 2: Run analysis
    success = run_analysis()

    if not success:
        log("Update failed. Please check logs.")
        sys.exit(1)

    # Step 3: Update timestamp
    update_last_updated()

    log("=" * 60)
    log("✅ UPDATE COMPLETE!")
    log("=" * 60)
    log(f"Dashboard data has been refreshed.")
    log(f"Data files location: {DATA_DIR}")

if __name__ == "__main__":
    main()
