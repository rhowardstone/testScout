"""
Example: Autonomous Bug Hunting with testScout Explorer

The Explorer is an AI-powered autonomous QA agent that:
1. Navigates your app without scripts
2. Clicks buttons, fills forms, explores menus
3. Detects JS errors, network failures, broken UI
4. Reports bugs with reproduction steps

Usage:
    # Set your API key
    export GEMINI_API_KEY=your-key

    # Run the explorer
    python examples/explore_app.py http://localhost:8888

    # Check the generated report
    open exploration_report.html
"""

import sys
import os
from playwright.sync_api import sync_playwright

# Add parent to path for local development
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from testscout import Explorer, create_explorer, BugSeverity


def main():
    # Get URL from command line or use default
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8888"

    print(f"Starting autonomous exploration of: {url}")
    print("=" * 60)

    with sync_playwright() as p:
        # Launch browser (headless=False to watch it explore)
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # Create explorer
        explorer = create_explorer(page)

        # Run exploration
        print("Exploring... (watch the browser!)")
        print("The AI will autonomously click around and look for bugs.")
        print()

        report = explorer.explore(
            start_url=url,
            max_actions=50,      # Stop after 50 actions
            max_time=300,        # Or after 5 minutes
            max_depth=5,         # Don't go too deep
        )

        browser.close()

    # Print summary
    print()
    print(report.summary())

    # Print bugs by severity
    for severity in [BugSeverity.CRITICAL, BugSeverity.HIGH, BugSeverity.MEDIUM, BugSeverity.LOW]:
        bugs = [b for b in report.bugs if b.severity == severity]
        if bugs:
            print(f"\n{severity.value.upper()} BUGS ({len(bugs)}):")
            for bug in bugs:
                print(f"  - {bug.title}")
                print(f"    {bug.description}")
                if bug.console_errors:
                    print(f"    Errors: {bug.console_errors[0][:80]}...")

    # Print AI observations
    if report.ai_observations:
        print("\nAI OBSERVATIONS:")
        for obs in report.ai_observations[:10]:
            print(f"  - {obs}")

    # Save reports
    report.save("exploration_report.html")
    report.save("exploration_report.json")
    print(f"\nReports saved:")
    print("  - exploration_report.html")
    print("  - exploration_report.json")


if __name__ == "__main__":
    main()
