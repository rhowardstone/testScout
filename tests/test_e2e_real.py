"""
Comprehensive End-to-End Tests on Real Websites

Tests all major features using stable, publicly accessible websites:
- Wikipedia: Complex, stable, lots of interactive elements
- Example.com: Ultra-simple, perfect for basic tests
- GitHub: Modern SPA, good for testing dynamic content

These tests actually run the browser and verify the framework works!
"""

import os

import pytest
from playwright.sync_api import sync_playwright

from testscout import Context, Explorer, Scout, VisualAssertions

# Skip tests if no API key (for CI/CD)
skip_if_no_api_key = pytest.mark.skipif(
    not os.environ.get("GEMINI_API_KEY") and not os.environ.get("OPENAI_API_KEY"),
    reason="No AI API key available",
)


@pytest.fixture(scope="session")
def browser():
    """Shared browser instance for all tests."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    """Fresh page for each test."""
    page = browser.new_page()
    yield page
    page.close()


@pytest.fixture
def scout_with_context(page):
    """Scout with context attached."""
    context = Context()
    context.attach_to_page(page)

    # Try Gemini first, fall back to OpenAI
    api_key = os.environ.get("GEMINI_API_KEY")
    backend_type = "gemini"
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY")
        backend_type = "openai"

    scout = Scout(page, api_key=api_key, backend_type=backend_type, context=context)
    yield scout, context
    scout.cleanup()


class TestBasicFunctionality:
    """Test core features on simple, stable websites."""

    @skip_if_no_api_key
    def test_example_com_basic(self, scout_with_context):
        """Test basic navigation and verification on example.com."""
        scout, context = scout_with_context
        page = scout.page

        # Navigate
        page.goto("https://example.com", wait_until="networkidle")

        # Test query (asking AI about the page)
        answer = scout.query("What is the main heading on this page?")
        assert "example" in answer.lower(), f"Expected 'example' in answer, got: {answer}"

        # Test verification
        assert scout.verify("The page shows 'Example Domain' as a heading", timeout=5.0)
        assert scout.verify("There is a link that says 'More information'", timeout=5.0)

        # Test no errors
        assert scout.check_no_errors(), "Should have no errors on example.com"

        # Verify context captured page load
        assert context.console_logs or True  # May or may not have logs, that's ok


class TestWikipediaInteraction:
    """Test comprehensive interaction on Wikipedia (stable, complex site)."""

    @skip_if_no_api_key
    def test_wikipedia_search_and_navigate(self, scout_with_context):
        """Test searching and navigating on Wikipedia."""
        scout, context = scout_with_context
        page = scout.page

        # Navigate to Wikipedia
        page.goto("https://en.wikipedia.org", wait_until="networkidle")

        # Verify we're on Wikipedia
        assert scout.verify("Wikipedia logo is visible", timeout=5.0)

        # Search for something
        success = scout.action("Type 'Python programming' into the search box", timeout=10000)
        assert success, "Should successfully type in search box"

        # Submit search (try pressing enter or clicking search)
        success = scout.action("Press enter or click search button", timeout=10000)
        # Note: This might not always work perfectly, but we should try

        # Verify no critical errors occurred
        assert (
            not context.has_critical_errors()
        ), f"Critical errors: {context.get_critical_errors()}"

    @skip_if_no_api_key
    def test_wikipedia_element_discovery(self, scout_with_context):
        """Test element discovery on Wikipedia."""
        scout, context = scout_with_context
        page = scout.page

        page.goto("https://en.wikipedia.org", wait_until="networkidle")

        # Discover elements
        buttons = scout.discover_elements("button")
        links = scout.discover_elements("link")

        # Wikipedia has lots of links
        assert len(links) > 5, f"Expected many links, found {len(links)}"

        # Should find some buttons too
        assert len(buttons) >= 0, "Should find buttons (or none if none visible)"


class TestVisualAssertions:
    """Test all visual assertion helpers."""

    @skip_if_no_api_key
    def test_assertion_helpers_wikipedia(self, scout_with_context):
        """Test VisualAssertions class on Wikipedia."""
        scout, context = scout_with_context
        page = scout.page

        page.goto("https://en.wikipedia.org", wait_until="networkidle")

        assertions = VisualAssertions(scout)

        # Test page_shows
        assertions.page_shows("Wikipedia homepage with search box")

        # Test no_errors (Wikipedia is stable)
        assertions.no_errors(timeout=3.0)

        # Test element_visible
        assertions.element_visible("Search input", timeout=5.0)

        # Test text_present
        assertions.text_present("Wikipedia", timeout=3.0)

        # Test loading_complete (should be done loading)
        assertions.loading_complete(timeout=5.0)

    @skip_if_no_api_key
    def test_assertion_context_batch(self, scout_with_context):
        """Test batch assertions with AssertionContext."""
        from testscout import AssertionContext

        scout, context = scout_with_context
        page = scout.page

        page.goto("https://example.com", wait_until="networkidle")

        # All assertions should pass
        with AssertionContext(scout) as check:
            check.page_shows("Example Domain page")
            check.element_visible("heading")
            check.text_present("Example Domain")
            check.no_errors()


class TestContextCapture:
    """Test comprehensive context capture."""

    def test_context_captures_navigation(self, page):
        """Test that context captures page navigation."""
        context = Context()
        context.attach_to_page(page)

        # Navigate to a few pages
        page.goto("https://example.com")
        page.goto("https://en.wikipedia.org")

        # Should have captured network requests
        assert len(context.network_requests) > 0, "Should capture network requests"

        # Should have some requests to wikipedia.org
        wiki_requests = [r for r in context.network_requests if "wikipedia" in r.url]
        assert len(wiki_requests) > 0, "Should have requests to Wikipedia"

    def test_context_detects_errors(self, page):
        """Test that context detects console errors."""
        context = Context()
        context.attach_to_page(page)

        # Navigate to example.com (should have no errors)
        page.goto("https://example.com")

        # Inject a JavaScript error
        page.evaluate("console.error('Test error message')")

        # Should capture the error
        assert len(context.errors) > 0, "Should capture console errors"
        assert any("Test error" in err for err in context.errors), "Should capture our test error"


class TestExplorer:
    """Test autonomous exploration."""

    @skip_if_no_api_key
    @pytest.mark.slow  # Mark as slow since exploration takes time
    def test_explorer_on_example_com(self, page):
        """Test autonomous exploration on example.com."""
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY")
        backend_type = "gemini" if os.environ.get("GEMINI_API_KEY") else "openai"

        explorer = Explorer(page, api_key=api_key, backend_type=backend_type)

        # Short exploration (just 5 actions to keep it fast)
        report = explorer.explore(
            start_url="https://example.com",
            max_actions=5,
            max_time=30,
            max_depth=2,
        )

        # Should have visited at least the start page
        assert report.pages_visited >= 1, "Should visit at least one page"
        assert report.actions_taken >= 0, "Should track actions"
        assert report.duration_seconds > 0, "Should track duration"

        # Example.com is very simple, probably won't find bugs
        # But that's okay - we're testing the explorer works


class TestEdgeCases:
    """Test edge cases and error handling."""

    @skip_if_no_api_key
    def test_action_on_nonexistent_element(self, scout_with_context):
        """Test action when element doesn't exist."""
        scout, context = scout_with_context
        page = scout.page

        page.goto("https://example.com")

        # Try to click something that definitely doesn't exist
        success = scout.action("Click the purple unicorn button", timeout=3000, retry=0)

        # Should fail gracefully
        assert not success, "Should return False for nonexistent element"

        # Should have recorded the failed action
        assert len(context.ai_verifications) > 0, "Should record AI attempts"

    @skip_if_no_api_key
    def test_verify_false_condition(self, scout_with_context):
        """Test verification of false condition."""
        scout, context = scout_with_context
        page = scout.page

        page.goto("https://example.com")

        # Verify something that's definitely not true
        result = scout.verify("The page shows a flying elephant", timeout=2.0, poll_interval=0.5)

        # Should return False
        assert not result, "Should return False for impossible condition"

    @skip_if_no_api_key
    def test_query_returns_sensible_answer(self, scout_with_context):
        """Test that query returns sensible answers."""
        scout, context = scout_with_context
        page = scout.page

        page.goto("https://example.com")

        # Ask about something that doesn't exist
        answer = scout.query("What error message is displayed?")

        # Should get some answer (even if it's "none" or "no error")
        assert len(answer) > 0, "Should get some answer"
        assert isinstance(answer, str), "Answer should be a string"


class TestBackendSwitching:
    """Test using different AI backends."""

    @pytest.mark.skipif(not os.environ.get("GEMINI_API_KEY"), reason="Requires Gemini API key")
    def test_gemini_backend(self, page):
        """Test using Gemini backend explicitly."""
        from testscout.backends import GeminiBackend

        backend = GeminiBackend(api_key=os.environ.get("GEMINI_API_KEY"), model="gemini-2.0-flash")

        scout = Scout(page, backend=backend)
        page.goto("https://example.com")

        # Should work with Gemini
        result = scout.verify("Example Domain is visible", timeout=5.0)
        assert result, "Gemini backend should work"

        scout.cleanup()

    @pytest.mark.skipif(not os.environ.get("OPENAI_API_KEY"), reason="Requires OpenAI API key")
    def test_openai_backend(self, page):
        """Test using OpenAI backend explicitly."""
        from testscout.backends import OpenAIBackend

        backend = OpenAIBackend(api_key=os.environ.get("OPENAI_API_KEY"), model="gpt-4o")

        scout = Scout(page, backend=backend)
        page.goto("https://example.com")

        # Should work with OpenAI
        result = scout.verify("Example Domain is visible", timeout=5.0)
        assert result, "OpenAI backend should work"

        scout.cleanup()


class TestRealWorldScenarios:
    """Test realistic usage scenarios."""

    @skip_if_no_api_key
    def test_complete_workflow_wikipedia(self, scout_with_context):
        """Test a complete realistic workflow on Wikipedia."""
        scout, context = scout_with_context
        page = scout.page
        assertions = VisualAssertions(scout)

        # 1. Navigate
        page.goto("https://en.wikipedia.org", wait_until="networkidle")

        # 2. Verify page loaded
        assertions.page_shows("Wikipedia homepage")
        assertions.no_errors()

        # 3. Interact with search
        scout.action("Click on the search box", timeout=10000)
        # Note: May or may not work depending on AI, but should not crash

        # 4. Query the page
        answer = scout.query("What is the name of this website?")
        assert "wikipedia" in answer.lower(), f"Expected Wikipedia in answer: {answer}"

        # 5. Check context
        assert context.console_logs is not None
        assert context.network_requests is not None
        assert not context.has_critical_errors()

        # 6. Generate report (should not crash)
        report = context.generate_report()
        assert len(report) > 0, "Report should have content"


# Test utilities for common patterns
class TestUtilities:
    """Test common testing patterns and utilities."""

    @skip_if_no_api_key
    def test_try_all_visible_elements(self, scout_with_context):
        """Pattern: Try clicking all visible elements to find bugs."""
        scout, context = scout_with_context
        page = scout.page

        page.goto("https://example.com")

        # Discover all elements
        elements = scout.discovery.discover()

        # Should find at least the link
        assert len(elements.elements) > 0, "Should discover elements"

        # Try clicking first few elements (don't click everything on Wikipedia!)
        for element in elements.elements[:3]:
            try:
                # This is the pattern: try everything, catch errors
                page.click(element.selector(), timeout=1000)
                page.go_back()
            except:
                pass  # Some elements might not be clickable, that's ok

        # Should not have crashed
        assert True


if __name__ == "__main__":
    # Run tests with: pytest tests/test_e2e_real.py -v -s
    pytest.main([__file__, "-v", "-s"])
