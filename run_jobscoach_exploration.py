"""
Run autonomous exploration on JobsCoach to find bugs.
Runs headless for CI/CLI environments.

Usage:
    # Make sure JobsCoach dev server is running: npm run dev (port 8888)
    # And backend: python -m uvicorn main:app --port 8001

    GEMINI_API_KEY=your-key python run_jobscoach_exploration.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from playwright.sync_api import sync_playwright
from ai_e2e import Explorer, BugSeverity


def main():
    url = "http://localhost:8888"
    print(f"Starting autonomous exploration of JobsCoach: {url}")
    print("=" * 60)

    with sync_playwright() as p:
        # Try multiple browser configurations for WSL/CI compatibility
        browser = None
        browser_type = "unknown"

        # Configuration 1: Try Firefox FIRST (better JS support in WSL headless)
        try:
            browser = p.firefox.launch(headless=True)
            browser_type = "firefox"
            print("Using Firefox (best WSL headless support)")
        except Exception as e:
            print(f"Firefox failed: {e}")

        # Configuration 2: Try Chromium with enhanced args as fallback
        if browser is None:
            try:
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                        '--enable-features=NetworkService,NetworkServiceInProcess',
                        '--disable-features=VizDisplayCompositor',
                        '--force-color-profile=srgb',
                        '--disable-web-security',
                        '--allow-running-insecure-content',
                    ]
                )
                browser_type = "chromium"
                print("Falling back to Chromium")
            except Exception as e:
                print(f"Chromium also failed: {e}")

        if browser is None:
            print("ERROR: Could not launch any browser")
            return

        page = browser.new_page(viewport={"width": 1280, "height": 800})

        # Enable JavaScript explicitly
        page.set_extra_http_headers({"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"})

        print(f"Browser: {browser_type}")

        # Create explorer with Gemini
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print("ERROR: GEMINI_API_KEY not set")
            return

        explorer = Explorer(page, api_key=api_key, backend_type="gemini")

        print("Exploring... (headless mode)")
        print("AI will autonomously click and look for bugs.")
        print("Explorer will wait for React app to hydrate before starting.")
        print()

        # Save debug screenshot before exploration starts
        page.goto(url, wait_until='domcontentloaded', timeout=30000)
        page.screenshot(path="/mnt/c/Users/rhowa/Documents/jobsCoach/debug_screenshot.png")
        print(f"Debug screenshot saved to debug_screenshot.png")

        # Use improved Explorer with SPA-aware waiting
        # The explorer now handles:
        # - networkidle wait
        # - wait_for_selector for React root
        # - app_ready_check for JS hydration
        # - blank page detection
        report = explorer.explore(
            start_url=url,
            max_actions=30,      # Fewer actions for faster test
            max_time=180,        # 3 minutes max
            max_depth=3,
            wait_for_selector="#root",  # Wait for React root element
            wait_timeout=20.0,          # Give more time for SPA apps
            app_ready_check='document.querySelector("#root")?.innerHTML?.length > 100',
        )

        browser.close()

    # Print summary
    print()
    print(report.summary())

    # Print bugs by severity
    for severity in [BugSeverity.CRITICAL, BugSeverity.HIGH, BugSeverity.MEDIUM, BugSeverity.LOW, BugSeverity.INFO]:
        bugs = [b for b in report.bugs if b.severity == severity]
        if bugs:
            print(f"\n{severity.value.upper()} BUGS ({len(bugs)}):")
            for bug in bugs:
                print(f"  [{bug.severity.value}] {bug.title}")
                print(f"      {bug.description[:100]}")
                if bug.reproduction_steps:
                    print(f"      Steps: {' -> '.join(bug.reproduction_steps[:3])}")

    # Print AI observations
    if report.ai_observations:
        print("\nAI OBSERVATIONS:")
        for obs in report.ai_observations[:10]:
            print(f"  - {obs}")

    # Save reports
    report.save("/mnt/c/Users/rhowa/Documents/jobsCoach/exploration_report.html")
    report.save("/mnt/c/Users/rhowa/Documents/jobsCoach/exploration_report.json")
    print(f"\nReports saved to jobsCoach/exploration_report.html and .json")


if __name__ == "__main__":
    main()
