"""
Example: Explore Wikipedia with Full Audit Trail

This example demonstrates the complete audit trail feature of testScout.
It explores Wikipedia autonomously and saves a full audit directory with:
- Screenshots (clean and with set-of-marks overlay)
- AI prompts and responses
- All decisions with reasoning
- Network and console logs

Usage:
    # Set your API key
    export GEMINI_API_KEY=your-key

    # Run the explorer
    python examples/explore_wikipedia.py

    # Check the audit trail
    ls -la wikipedia_audit/
"""

import sys
import os
from playwright.sync_api import sync_playwright

# Add parent to path for local development
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from testscout import Explorer, create_explorer, BugSeverity


def main():
    print("=" * 70)
    print("testScout Wikipedia Exploration with Full Audit Trail")
    print("=" * 70)
    print()

    with sync_playwright() as p:
        # Launch browser (headless for CI, set False to watch)
        headless = "--headless" in sys.argv or os.environ.get("CI") == "true"
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()

        # Create explorer (audit is enabled by default)
        explorer = create_explorer(page)

        print("Starting exploration of Wikipedia...")
        print("(The AI will autonomously click around and explore)")
        print()

        # Run a short exploration (5 actions for demo)
        report = explorer.explore(
            start_url="https://en.wikipedia.org",
            max_actions=5,  # Keep it short for demo
            max_time=120,   # 2 minute max
            max_depth=2,    # Don't go too deep
        )

        # Save the audit trail
        audit_dir = "wikipedia_audit"
        explorer.save_audit(audit_dir)
        print(f"\nAudit trail saved to: {audit_dir}/")

        browser.close()

    # Print summary
    print()
    print(report.summary())

    # Print what was captured in the audit
    print()
    print("AUDIT TRAIL CONTENTS:")
    print("-" * 40)

    if os.path.exists(audit_dir):
        # List top-level structure
        for item in sorted(os.listdir(audit_dir)):
            item_path = os.path.join(audit_dir, item)
            if os.path.isdir(item_path):
                # Count files in action directories
                files = os.listdir(item_path)
                print(f"  {item}/  ({len(files)} files)")
                for f in sorted(files)[:5]:  # Show first 5 files
                    print(f"    - {f}")
                if len(files) > 5:
                    print(f"    ... and {len(files) - 5} more")
            else:
                size = os.path.getsize(item_path)
                print(f"  {item}  ({size} bytes)")

    # Save reports too
    report.save("wikipedia_report.html")
    print(f"\nExploration report saved to: wikipedia_report.html")


if __name__ == "__main__":
    main()
