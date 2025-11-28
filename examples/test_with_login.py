#!/usr/bin/env python3
"""
testScout Example: Comprehensive E2E Test with Login

This example demonstrates how to:
1. Login using DOM-based approach (saves AI calls for rate limiting)
2. Verify UI state with AI vision
3. Navigate through the application
4. Check for errors (console, network, visual)

Configure via environment variables:
  TEST_URL - The application URL (default: http://localhost:8888)
  TEST_EMAIL - Login email
  TEST_PASSWORD - Login password
  GEMINI_API_KEY - Required for AI features

Rate Limit Strategy:
  - DOM-based login (no AI calls)
  - 5-second delay between AI calls (to stay under 15 req/min free tier)
  - ~9 AI calls total
"""

import os
import sys
import time

from playwright.sync_api import sync_playwright

# Add package to path if running directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_e2e import Scout, Context, VisualAssertions

# Configuration via environment variables
BASE_URL = os.environ.get("TEST_URL", "http://localhost:8888")
TEST_EMAIL = os.environ.get("TEST_EMAIL", "")
TEST_PASSWORD = os.environ.get("TEST_PASSWORD", "")
AI_DELAY = int(os.environ.get("AI_DELAY_SECONDS", "5"))


class TestResults:
    """Track test results."""

    def __init__(self):
        self.tests = []
        self.passed = 0
        self.failed = 0

    def add(self, name: str, passed: bool, reason: str = ""):
        self.tests.append({"name": name, "passed": passed, "reason": reason})
        if passed:
            self.passed += 1
        else:
            self.failed += 1

    def summary(self):
        return f"{self.passed}/{self.passed + self.failed} passed"

    def pass_rate(self):
        total = self.passed + self.failed
        return (self.passed / total * 100) if total > 0 else 0


def ai_call(func, *args, **kwargs):
    """AI call with rate limiting delay."""
    time.sleep(AI_DELAY)
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if "429" in str(e) or "quota" in str(e).lower():
            print("    [Rate limit hit, waiting 30s...]")
            time.sleep(30)
            return func(*args, **kwargs)
        raise


def main():
    print("=" * 60)
    print("testScout: Comprehensive E2E Test with Login")
    print("=" * 60)

    # Check configuration
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: Set GEMINI_API_KEY environment variable")
        return 1

    if not TEST_EMAIL or not TEST_PASSWORD:
        print("WARNING: TEST_EMAIL and TEST_PASSWORD not set")
        print("Set them to test login flow, or test will skip login")

    print(f"URL: {BASE_URL}")
    print(f"AI Delay: {AI_DELAY}s between calls")
    print()

    results = TestResults()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        context = Context()
        context.attach_to_page(page)

        scout = Scout(page, api_key=api_key, context=context)

        try:
            # ========================================
            # PHASE 1: DOM-Based Login
            # ========================================
            print("PHASE 1: Page Load & Login")
            print("-" * 40)

            print("Loading page...")
            page.goto(BASE_URL)
            page.wait_for_load_state("networkidle")
            time.sleep(1)

            # Check for login page
            password_input = page.query_selector('input[type="password"]')
            if password_input and TEST_EMAIL and TEST_PASSWORD:
                print("Login page detected, filling credentials...")

                # Fill email
                email_input = page.query_selector(
                    'input[type="email"], input[name="email"], '
                    'input[placeholder*="email" i], input[placeholder*="Email"]'
                )
                if email_input:
                    email_input.fill(TEST_EMAIL)
                    results.add("Fill Email", True, "DOM-based")
                else:
                    results.add("Fill Email", False, "Email input not found")

                # Fill password
                password_input.fill(TEST_PASSWORD)
                results.add("Fill Password", True, "DOM-based")

                # Click submit
                submit_btn = page.query_selector(
                    'button[type="submit"], '
                    'button:has-text("Sign In"), '
                    'button:has-text("Login")'
                )
                if submit_btn:
                    submit_btn.click()
                    results.add("Click Login", True, "DOM-based")
                else:
                    results.add("Click Login", False, "Submit button not found")

                page.wait_for_timeout(3000)
                page.wait_for_load_state("networkidle")
            else:
                print("No login page detected (or no credentials set)")
                results.add("Page Load", True, "No login needed")

            print()

            # ========================================
            # PHASE 2: AI Verification
            # ========================================
            print("PHASE 2: AI Verification")
            print("-" * 40)

            # Verify main content is visible
            print("Verifying main content...")
            main_visible = ai_call(
                scout.verify,
                "The main application content should be visible (not an error page or login screen)",
                timeout=15
            )
            results.add("Main Content Visible", main_visible, "AI verified")

            # Element discovery (no AI)
            print("Discovering elements...")
            elements = scout.discovery.discover()
            elem_count = len(elements.elements)
            results.add("Element Discovery", elem_count > 0, f"Found {elem_count}")
            print(f"  Found {elem_count} interactive elements")

            # AI page analysis
            print("Analyzing page...")
            analysis = ai_call(
                scout.query,
                "What are the main sections or features visible on this page?"
            )
            results.add("Page Analysis", len(analysis) > 20, "Got analysis")
            print(f"  {analysis[:100]}...")

            print()

            # ========================================
            # PHASE 3: Navigation Test
            # ========================================
            print("PHASE 3: Navigation Test")
            print("-" * 40)

            # Try to click on any navigation element
            print("Testing navigation...")
            nav_clicked = ai_call(
                scout.action,
                "Click on any navigation tab, menu item, or sidebar link",
                retry=1
            )

            if nav_clicked:
                page.wait_for_timeout(1500)
                nav_worked = ai_call(
                    scout.verify,
                    "A different view or content should now be visible",
                    timeout=10
                )
                results.add("Navigation Works", nav_worked, "AI verified")

                # Try to go back
                ai_call(scout.action, "Click back, close, or home button", retry=0)
                page.wait_for_timeout(1000)
            else:
                results.add("Navigation Works", False, "No nav found")

            print()

            # ========================================
            # PHASE 4: Error Checking
            # ========================================
            print("PHASE 4: Error Checking")
            print("-" * 40)

            # Visual error check
            print("Checking for visual errors...")
            no_visual_errors = ai_call(
                scout.verify,
                "The page should not show any error messages, broken layouts, or crash screens",
                timeout=10
            )
            results.add("No Visual Errors", no_visual_errors, "AI verified")

            # Console errors
            print("Checking console errors...")
            summary = context.summary()
            has_critical = context.has_critical_errors()
            results.add("No Critical Errors", not has_critical, f"{summary['errors']} errors")

            # Network errors
            print("Checking network errors...")
            net_errors = summary["network_errors"]
            results.add("Network OK", net_errors <= 3, f"{net_errors} errors")

            print()

            # ========================================
            # FINAL REPORT
            # ========================================
            print("=" * 60)
            print("FINAL REPORT")
            print("=" * 60)

            print(f"\nResults: {results.summary()}")
            for test in results.tests:
                status = "PASS" if test["passed"] else "FAIL"
                print(f"  [{status}] {test['name']}: {test['reason']}")

            print(f"\nContext Summary:")
            print(f"  Console: {summary['console_logs']} logs, {summary['errors']} errors")
            print(f"  Network: {summary['network_errors']} errors")
            print(f"  AI: {summary['ai_verifications']} calls ({summary['ai_passes']} pass)")

            pass_rate = results.pass_rate()
            print(f"\nPass Rate: {pass_rate:.1f}%")
            print("TEST SUITE:", "PASSED" if pass_rate >= 80 else "FAILED")

            return 0 if pass_rate >= 80 else 1

        except Exception as e:
            print(f"\nTEST CRASHED: {e}")
            import traceback
            traceback.print_exc()
            return 1

        finally:
            scout.cleanup()
            browser.close()


if __name__ == "__main__":
    exit(main())
