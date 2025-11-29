#!/usr/bin/env python3
"""
Simple test to verify JavaScript execution in headless browsers.
This helps diagnose whether the issue is with the browser configuration
or with the target application.
"""
from playwright.sync_api import sync_playwright
import json


def test_js_execution():
    """Test basic JavaScript execution in headless browser."""
    print("Testing JavaScript execution in headless browsers...")
    print("=" * 60)

    # Simple HTML with JavaScript
    test_html = """
    <!DOCTYPE html>
    <html>
    <head><title>JS Test</title></head>
    <body>
        <div id="root">Initial content</div>
        <script>
            // Basic JS test
            document.getElementById('root').innerHTML = 'JavaScript works!';
            window.jsTest = {
                executed: true,
                timestamp: Date.now(),
                navigator: navigator.userAgent
            };
        </script>
    </body>
    </html>
    """

    results = {}

    with sync_playwright() as p:
        for browser_name, browser_type in [("Chromium", p.chromium), ("Firefox", p.firefox)]:
            print(f"\n--- Testing {browser_name} ---")
            try:
                # Launch browser
                browser = browser_type.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox'] if browser_name == "Chromium" else []
                )
                page = browser.new_page()

                # Set content directly (no server needed)
                page.set_content(test_html)

                # Check if JS executed
                root_content = page.locator('#root').inner_text()
                js_test = page.evaluate('window.jsTest')

                results[browser_name] = {
                    "launched": True,
                    "js_executed": root_content == "JavaScript works!",
                    "root_content": root_content,
                    "window_jsTest": js_test,
                    "error": None
                }

                if root_content == "JavaScript works!":
                    print(f"  [OK] JavaScript executed successfully")
                    print(f"  User-Agent: {js_test.get('navigator', 'N/A')[:50]}...")
                else:
                    print(f"  [FAIL] JavaScript did NOT execute")
                    print(f"  Root content: {root_content}")

                browser.close()

            except Exception as e:
                results[browser_name] = {
                    "launched": False,
                    "js_executed": False,
                    "error": str(e)
                }
                print(f"  [ERROR] {e}")

    # Test with a real website
    print(f"\n--- Testing with example.com ---")
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
            page = browser.new_page()
            page.goto("https://example.com", timeout=30000)
            title = page.title()
            has_h1 = page.locator('h1').count() > 0
            results["example.com"] = {
                "loaded": True,
                "title": title,
                "has_h1": has_h1
            }
            print(f"  [OK] Loaded example.com: {title}")
            browser.close()
        except Exception as e:
            results["example.com"] = {"loaded": False, "error": str(e)}
            print(f"  [ERROR] {e}")

    print("\n" + "=" * 60)
    print("Summary:")
    for browser, result in results.items():
        if result.get("js_executed") or result.get("loaded"):
            print(f"  {browser}: OK")
        else:
            print(f"  {browser}: FAIL - {result.get('error', result.get('root_content', 'Unknown'))}")

    # Return True if at least one browser works
    return any(r.get("js_executed") or r.get("loaded") for r in results.values())


if __name__ == "__main__":
    success = test_js_execution()
    exit(0 if success else 1)
