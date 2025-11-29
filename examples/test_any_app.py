"""
Example: Testing ANY web application with testScout

This example shows how to use testScout to test any web application.
The framework is completely general-purpose - you just provide:
1. The URL
2. Natural language instructions for actions
3. Natural language assertions for verification

The AI handles:
- Finding the right elements (via Set-of-Marks + vision)
- Executing actions reliably
- Verifying visual state
"""

import os
import pytest
from playwright.sync_api import sync_playwright

# Import testScout
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from testscout import Scout, Context, VisualAssertions, create_scout


# Skip if no API key
pytestmark = pytest.mark.skipif(
    not os.environ.get("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY not set"
)


class TestAnyWebApp:
    """
    Example tests that work on ANY web application.
    Just change the URL and the assertions!
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up browser and scout for each test."""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)

        browser_context = self.browser.new_context()
        self.page = browser_context.new_page()

        # Create context to capture everything
        self.context = Context()
        self.context.attach_to_page(self.page)

        # Create scout with AI
        self.scout = Scout(
            self.page,
            api_key=os.environ.get("GEMINI_API_KEY"),
            context=self.context,
        )

        yield

        # Cleanup
        self.scout.cleanup()
        self.browser.close()
        self.playwright.stop()

        # Save report
        self.context.save_report("examples/last_test_report.txt")

    def test_google_search(self):
        """Test Google search - works on google.com."""
        self.page.goto("https://www.google.com")

        # AI finds and interacts with elements
        self.scout.action("Click the search input field")
        self.scout.action("Type 'testScout AI testing' into the search box")
        self.scout.action("Press Enter or click the search button")

        # AI verifies the result
        assert self.scout.verify("Search results should be displayed")

    def test_wikipedia(self):
        """Test Wikipedia - works on wikipedia.org."""
        self.page.goto("https://en.wikipedia.org")

        # AI-powered interaction
        self.scout.action("Click on the search input")
        self.scout.action("Type 'Playwright automation'")
        self.scout.action("Click search or press Enter")

        # Verify we got results
        assert self.scout.verify("An article or search results page should be visible")

    def test_github(self):
        """Test GitHub homepage."""
        self.page.goto("https://github.com")

        # Ask AI what's on the page
        description = self.scout.query("What is the main call to action on this page?")
        print(f"AI says: {description}")

        # Verify basic elements
        assert self.scout.verify("A navigation bar with GitHub logo should be visible")

    def test_element_discovery(self):
        """Demonstrate AI-powered element discovery."""
        self.page.goto("https://www.google.com")

        # AI discovers all buttons on the page
        buttons = self.scout.discover_elements("button")
        print(f"AI found {len(buttons)} buttons:")
        for btn in buttons:
            print(f"  - {btn.get('label', 'unlabeled')} ({btn.get('position', 'unknown')})")

        # Also use rule-based discovery
        elements = self.scout.discovery.discover()
        print(f"\nDOM discovery found {len(elements.elements)} interactive elements")

    def test_no_errors_generic(self):
        """Test that any page loads without critical errors."""
        self.page.goto("https://example.com")

        # Use assertion helpers
        assertions = VisualAssertions(self.scout)
        assertions.no_errors()
        assertions.page_shows("A simple webpage with content")


class TestJobsCoachApp:
    """
    Example: Testing the JobsCoach app specifically.

    This shows how to create app-specific tests by just changing
    the URL and the natural language instructions.
    """

    BASE_URL = "http://localhost:8888"

    @pytest.fixture(autouse=True)
    def setup(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)

        browser_context = self.browser.new_context()
        self.page = browser_context.new_page()

        self.context = Context()
        self.context.attach_to_page(self.page)

        self.scout = Scout(
            self.page,
            api_key=os.environ.get("GEMINI_API_KEY"),
            context=self.context,
        )

        yield

        self.scout.cleanup()
        self.browser.close()
        self.playwright.stop()
        self.context.save_report("examples/jobscoach_report.txt")

    @pytest.mark.skip(reason="Requires local server running")
    def test_login_flow(self):
        """Test the login flow."""
        self.page.goto(self.BASE_URL)

        # AI handles the login
        self.scout.action("Click the Sign In or Login button")
        self.scout.action("Enter 'test@example.com' in the email field")
        self.scout.action("Enter 'TestPassword123!' in the password field")
        self.scout.action("Click the submit or sign in button")

        # Verify login result
        assert self.scout.verify(
            "Either a dashboard/home page is shown, or an error message about invalid credentials"
        )

    @pytest.mark.skip(reason="Requires local server running")
    def test_navigation(self):
        """Test navigation between sections."""
        self.page.goto(self.BASE_URL)

        sections = ["Pipeline", "Search", "Analytics", "Resume", "Settings"]

        for section in sections:
            self.scout.action(f"Click on the {section} tab or navigation item")
            assert self.scout.verify(
                f"The {section} section should be displayed without errors"
            ), f"Failed to navigate to {section}"

    @pytest.mark.skip(reason="Requires local server running")
    def test_job_search(self):
        """Test the job search feature."""
        self.page.goto(self.BASE_URL)

        # Navigate to search
        self.scout.action("Click on Search in the navigation")

        # Perform a search
        self.scout.action("Enter 'Software Engineer' in the job title field")
        self.scout.action("Enter 'Remote' in the location field")
        self.scout.action("Click the Search button")

        # Verify results (or loading state)
        assert self.scout.verify(
            "Search results, a loading indicator, or a message about jobs should be visible"
        )


if __name__ == "__main__":
    # Run with: python examples/test_any_app.py
    # Or: pytest examples/test_any_app.py -v -s
    pytest.main([__file__, "-v", "-s"])
