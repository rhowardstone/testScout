"""
Visual Assertions with Smart Retry

High-level assertion helpers that wrap the Scout agent.
Provides pytest-friendly assertion syntax.
"""

import time
from typing import Optional, Callable, Any
from dataclasses import dataclass


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    timeout: float = 10.0  # Total timeout in seconds
    poll_interval: float = 1.0  # Time between retries
    initial_delay: float = 0.0  # Wait before first check


def wait_until(
    condition: Callable[[], bool],
    timeout: float = 10.0,
    poll_interval: float = 0.5,
    message: str = "Condition not met",
) -> bool:
    """
    Wait until a condition becomes true.

    Args:
        condition: Callable that returns True when condition is met
        timeout: Maximum time to wait
        poll_interval: Time between checks
        message: Error message if timeout

    Returns:
        True if condition was met, raises AssertionError if timeout
    """
    start = time.time()
    last_error = None

    while time.time() - start < timeout:
        try:
            if condition():
                return True
        except Exception as e:
            last_error = e

        time.sleep(poll_interval)

    if last_error:
        raise AssertionError(f"{message}: {last_error}")
    raise AssertionError(message)


def wait_for_element(
    page,
    selector: str,
    timeout: float = 10.0,
    state: str = "visible",
) -> bool:
    """
    Wait for an element to be in a specific state.

    Args:
        page: Playwright page
        selector: CSS selector
        timeout: Maximum wait time
        state: "visible", "hidden", "attached", "detached"
    """
    try:
        page.wait_for_selector(selector, timeout=timeout * 1000, state=state)
        return True
    except Exception:
        return False


def wait_for_navigation(
    page,
    url_pattern: Optional[str] = None,
    timeout: float = 10.0,
) -> bool:
    """
    Wait for navigation to complete.

    Args:
        page: Playwright page
        url_pattern: Optional URL pattern to match
        timeout: Maximum wait time
    """
    try:
        if url_pattern:
            page.wait_for_url(url_pattern, timeout=timeout * 1000)
        else:
            page.wait_for_load_state("networkidle", timeout=timeout * 1000)
        return True
    except Exception:
        return False


class VisualAssertions:
    """
    Collection of visual assertions using AI.

    Usage:
        assertions = VisualAssertions(scout)

        assertions.page_shows("A login form with email and password fields")
        assertions.no_errors()
        assertions.element_visible("Submit button")
    """

    def __init__(self, scout):
        self.scout = scout

    def page_shows(
        self,
        description: str,
        timeout: float = 10.0,
    ) -> bool:
        """Assert that the page shows something matching the description."""
        result = self.scout.verify(description, timeout=timeout)
        if not result:
            raise AssertionError(f"Page does not show: {description}")
        return True

    def no_errors(self, timeout: float = 5.0) -> bool:
        """Assert that no error messages are visible."""
        result = self.scout.verify(
            "The page should not display any error messages, broken layouts, or crash screens",
            timeout=timeout,
        )
        if not result:
            raise AssertionError("Errors detected on page")

        # Also check console errors
        if self.scout.context.has_critical_errors():
            errors = self.scout.context.get_critical_errors()
            raise AssertionError(f"Critical console errors: {errors[:3]}")

        return True

    def element_visible(
        self,
        description: str,
        timeout: float = 10.0,
    ) -> bool:
        """Assert that an element matching the description is visible."""
        result = self.scout.verify(
            f"An element matching '{description}' should be visible on the page",
            timeout=timeout,
        )
        if not result:
            raise AssertionError(f"Element not visible: {description}")
        return True

    def element_not_visible(
        self,
        description: str,
        timeout: float = 5.0,
    ) -> bool:
        """Assert that an element is NOT visible."""
        result = self.scout.verify(
            f"No element matching '{description}' should be visible",
            timeout=timeout,
        )
        if not result:
            raise AssertionError(f"Element is still visible: {description}")
        return True

    def text_present(
        self,
        text: str,
        timeout: float = 10.0,
    ) -> bool:
        """Assert that specific text is present on the page."""
        result = self.scout.verify(
            f"The text '{text}' should be visible somewhere on the page",
            timeout=timeout,
        )
        if not result:
            raise AssertionError(f"Text not found: {text}")
        return True

    def form_filled(
        self,
        field_values: dict,
        timeout: float = 5.0,
    ) -> bool:
        """Assert that form fields contain expected values."""
        for field, value in field_values.items():
            result = self.scout.verify(
                f"The '{field}' field should contain '{value}'",
                timeout=timeout,
            )
            if not result:
                raise AssertionError(f"Field '{field}' does not contain '{value}'")
        return True

    def loading_complete(self, timeout: float = 30.0) -> bool:
        """Assert that any loading indicators have disappeared."""
        result = self.scout.verify(
            "No loading spinners, skeletons, or 'Loading...' text should be visible",
            timeout=timeout,
        )
        if not result:
            raise AssertionError("Page still loading")
        return True

    def modal_open(
        self,
        description: Optional[str] = None,
        timeout: float = 5.0,
    ) -> bool:
        """Assert that a modal/dialog is open."""
        assertion = "A modal or dialog box should be open"
        if description:
            assertion += f" showing {description}"
        result = self.scout.verify(assertion, timeout=timeout)
        if not result:
            raise AssertionError("Modal not open")
        return True

    def modal_closed(self, timeout: float = 5.0) -> bool:
        """Assert that no modal/dialog is open."""
        result = self.scout.verify(
            "No modal or dialog boxes should be visible",
            timeout=timeout,
        )
        if not result:
            raise AssertionError("Modal still open")
        return True


# Pytest integration
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "ai_e2e: marks tests as AI-powered E2E tests (may be skipped without API key)",
    )


# Context manager for cleaner test syntax
class AssertionContext:
    """
    Context manager for batching assertions.

    Usage:
        with AssertionContext(scout) as check:
            check.page_shows("Login form")
            check.no_errors()
            check.element_visible("Email input")

        # All assertions run, failures collected and reported together
    """

    def __init__(self, scout):
        self.scout = scout
        self.assertions = VisualAssertions(scout)
        self.failures = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.failures:
            raise AssertionError(
                f"{len(self.failures)} assertion(s) failed:\n" +
                "\n".join(f"  - {f}" for f in self.failures)
            )
        return False

    def page_shows(self, description: str, timeout: float = 10.0):
        try:
            self.assertions.page_shows(description, timeout)
        except AssertionError as e:
            self.failures.append(str(e))

    def no_errors(self, timeout: float = 5.0):
        try:
            self.assertions.no_errors(timeout)
        except AssertionError as e:
            self.failures.append(str(e))

    def element_visible(self, description: str, timeout: float = 10.0):
        try:
            self.assertions.element_visible(description, timeout)
        except AssertionError as e:
            self.failures.append(str(e))

    def text_present(self, text: str, timeout: float = 10.0):
        try:
            self.assertions.text_present(text, timeout)
        except AssertionError as e:
            self.failures.append(str(e))
