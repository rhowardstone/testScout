"""
AI Agent for E2E Testing

The agent receives BOTH:
1. Screenshot (visual) - what the user sees
2. Element list (DOM) - what we can actually click

The AI fuses these to make decisions: "I see a blue button labeled 'Submit'
in the bottom right. Looking at the element list, that's [7] button 'Submit'."

Supports pluggable AI backends (Gemini, OpenAI, Anthropic, Ollama).
Uses structured JSON output for reliable parsing.
"""

import base64
import time
from typing import Optional
from dataclasses import dataclass

from .discovery import ElementDiscoverySync, PageElements
from .context import Context, AIVerification
from .backends import VisionBackend, GeminiBackend, OpenAIBackend, ActionPlan, ActionType


class Scout:
    """
    The main testScout agent - combines discovery + AI vision.

    Usage:
        scout = Scout(page, api_key="...")

        # AI picks the right element from screenshot + element list
        scout.action("Click the login button")
        scout.action("Fill in the email field with test@example.com")

        # AI verifies visual state
        assert scout.verify("A dashboard with user stats should be visible")

        # Ask AI about the page
        answer = scout.query("What error message is shown?")

        # AI-powered element discovery
        buttons = scout.discover_elements("button")
    """

    def __init__(
        self,
        page,
        api_key: Optional[str] = None,
        backend: Optional[VisionBackend] = None,
        backend_type: str = "gemini",
        model: Optional[str] = None,
        context: Optional[Context] = None,
    ):
        """
        Initialize Scout agent.

        Args:
            page: Playwright page object
            api_key: API key for the AI backend (if not using custom backend)
            backend: Custom VisionBackend instance (overrides api_key/backend_type)
            backend_type: "gemini" or "openai" (default: "gemini")
            model: Specific model name (optional, uses backend defaults)
            context: Context object for capturing test data (auto-created if None)

        Examples:
            # Using Gemini (simplest)
            scout = Scout(page, api_key="gemini-key")

            # Using OpenAI
            scout = Scout(page, api_key="openai-key", backend_type="openai")

            # Using custom backend
            custom = MyCustomBackend()
            scout = Scout(page, backend=custom)
        """
        self.page = page
        self.discovery = ElementDiscoverySync(page)
        self.context = context or Context()

        # Set up AI backend
        if backend:
            self.backend = backend
        elif api_key:
            if backend_type == "gemini":
                self.backend = GeminiBackend(api_key, model or "gemini-2.0-flash")
            elif backend_type == "openai":
                self.backend = OpenAIBackend(api_key, model or "gpt-4o")
            else:
                raise ValueError(f"Unknown backend type: {backend_type}")
        else:
            raise ValueError("Must provide either api_key or backend")

        self._action_count = 0
        self._last_screenshot_hash: Optional[str] = None

    def _get_screenshot_b64(self, with_markers: bool = True) -> str:
        """Get screenshot as base64."""
        if with_markers:
            screenshot = self.discovery.screenshot_with_markers()
        else:
            screenshot = self.discovery.screenshot_clean()
        return base64.b64encode(screenshot).decode("utf-8")

    def _refresh_elements(self) -> PageElements:
        """Re-discover elements on the page."""
        return self.discovery.discover()

    def action(
        self,
        instruction: str,
        timeout: int = 5000,
        retry: int = 1,
    ) -> bool:
        """
        Execute an action based on natural language instruction.

        The AI sees the screenshot AND the element list, and decides:
        - Which element to interact with (by ID)
        - What action to take (click, fill, etc.)

        Args:
            instruction: Natural language instruction (e.g., "Click the login button")
            timeout: Timeout for the action in milliseconds
            retry: Number of retries if action fails

        Returns:
            True if action was executed successfully

        Examples:
            scout.action("Click the Sign In button")
            scout.action("Fill in the email field with test@example.com")
            scout.action("Select 'United States' from the country dropdown")
        """
        start_time = time.time()

        for attempt in range(retry + 1):
            # Refresh element discovery
            elements = self._refresh_elements()

            # Get screenshot with markers
            screenshot_b64 = self._get_screenshot_b64(with_markers=True)

            # Ask AI to plan the action
            plan = self.backend.plan_action(instruction, screenshot_b64, elements)

            # Record the attempt
            duration_ms = (time.time() - start_time) * 1000

            if plan.action == ActionType.NONE:
                self.context.add_ai_verification(AIVerification(
                    action_type="action",
                    description=instruction,
                    result=False,
                    reason=plan.reason,
                    duration_ms=duration_ms,
                ))
                if attempt < retry:
                    time.sleep(0.5)
                    continue
                return False

            # Execute the action
            try:
                success = self._execute_action(plan, elements, timeout)
                self.context.add_ai_verification(AIVerification(
                    action_type="action",
                    description=instruction,
                    result=success,
                    reason=plan.reason,
                    element_id=plan.element_id,
                    duration_ms=duration_ms,
                ))
                if success:
                    self._action_count += 1
                    return True
            except Exception as e:
                self.context.add_ai_verification(AIVerification(
                    action_type="action",
                    description=instruction,
                    result=False,
                    reason=f"Execution error: {e}",
                    element_id=plan.element_id,
                    duration_ms=duration_ms,
                ))

            if attempt < retry:
                time.sleep(0.5)

        return False

    def _execute_action(
        self,
        plan: ActionPlan,
        elements: PageElements,
        timeout: int,
    ) -> bool:
        """Execute a planned action."""
        if plan.action == ActionType.WAIT:
            time.sleep((plan.duration_ms or 1000) / 1000)
            return True

        if plan.action == ActionType.SCROLL:
            direction = plan.direction or "down"
            delta = -300 if direction == "up" else 300
            self.page.mouse.wheel(0, delta)
            return True

        # For element-based actions, get the selector
        if plan.element_id is None:
            return False

        element = elements.find_by_id(plan.element_id)
        if not element:
            return False

        selector = element.selector()

        if plan.action == ActionType.CLICK:
            self.page.click(selector, timeout=timeout)
            return True

        elif plan.action == ActionType.HOVER:
            self.page.hover(selector, timeout=timeout)
            return True

        elif plan.action == ActionType.FILL:
            self.page.fill(selector, plan.text or "", timeout=timeout)
            return True

        elif plan.action == ActionType.TYPE:
            self.page.type(selector, plan.text or "", timeout=timeout)
            return True

        elif plan.action == ActionType.SELECT:
            self.page.select_option(selector, plan.text or "", timeout=timeout)
            return True

        return False

    def verify(
        self,
        assertion: str,
        timeout: float = 10.0,
        poll_interval: float = 1.0,
    ) -> bool:
        """
        Verify an assertion about the current page state.

        Uses smart retry - keeps checking until timeout.

        Args:
            assertion: Natural language assertion (e.g., "The login form should be visible")
            timeout: Maximum time to wait in seconds
            poll_interval: Time between retry attempts in seconds

        Returns:
            True if assertion passes, False if it fails or times out

        Examples:
            scout.verify("The dashboard should be visible")
            scout.verify("The error message says 'Invalid password'")
            scout.verify("The loading spinner should be gone", timeout=30)
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            # Get fresh screenshot (no markers for cleaner verification)
            screenshot_b64 = self._get_screenshot_b64(with_markers=False)

            # Check if screenshot changed (skip if identical to last check)
            screenshot_hash = self.context.get_screenshot_hash(
                base64.b64decode(screenshot_b64)
            )

            elements = self._refresh_elements()

            # Ask AI to verify
            result = self.backend.verify_assertion(assertion, screenshot_b64, elements)

            duration_ms = (time.time() - start_time) * 1000

            if result.passed:
                self.context.add_ai_verification(AIVerification(
                    action_type="assert",
                    description=assertion,
                    result=True,
                    reason=result.reason,
                    screenshot_hash=screenshot_hash,
                    duration_ms=duration_ms,
                ))
                return True

            # Not passed yet - wait and retry
            time.sleep(poll_interval)

        # Timeout - record failure
        self.context.add_ai_verification(AIVerification(
            action_type="assert",
            description=assertion,
            result=False,
            reason=result.reason if 'result' in locals() else "Timeout",
            duration_ms=(time.time() - start_time) * 1000,
        ))
        return False

    def query(self, question: str) -> str:
        """
        Ask AI a question about the current page state.

        Args:
            question: Natural language question

        Returns:
            String answer from the AI

        Examples:
            error = scout.query("What error message is shown?")
            count = scout.query("How many items are in the cart?")
        """
        screenshot_b64 = self._get_screenshot_b64(with_markers=False)
        elements = self._refresh_elements()
        return self.backend.query(question, screenshot_b64, elements)

    def discover_elements(self, element_type: Optional[str] = None):
        """
        Use AI to visually discover elements on the page.

        This is different from DOM discovery - it asks the AI to look at
        the screenshot and identify elements it can see, even if they
        don't have obvious DOM selectors.

        Args:
            element_type: Optional filter like "button", "link", "input"

        Returns:
            List of elements AI identified with position/description

        Examples:
            buttons = scout.discover_elements("button")
            all_elements = scout.discover_elements()
        """
        screenshot_b64 = self._get_screenshot_b64(with_markers=False)
        return self.backend.discover_elements(screenshot_b64, element_type)

    def check_no_errors(self) -> bool:
        """
        Check that no critical errors have occurred.

        Returns:
            True if no errors, False if errors detected
        """
        # Check context for console errors
        if self.context.has_critical_errors():
            return False

        # Also ask AI if there are visible errors
        result = self.verify(
            "The page should not display any error messages, crash screens, or broken layouts",
            timeout=2.0,
        )
        return result

    def cleanup(self):
        """Clean up markers from the page."""
        self.discovery.cleanup()


def create_scout(
    page,
    api_key: Optional[str] = None,
    backend_type: str = "gemini",
) -> Scout:
    """
    Create a Scout agent with sensible defaults.

    Will try to get API key from environment if not provided.

    Args:
        page: Playwright page object
        api_key: API key (optional, will check environment)
        backend_type: "gemini" or "openai"

    Returns:
        Configured Scout instance

    Example:
        # Assumes GEMINI_API_KEY in environment
        scout = create_scout(page)

        # Explicit API key
        scout = create_scout(page, api_key="...", backend_type="openai")
    """
    import os

    if not api_key:
        if backend_type == "gemini":
            api_key = os.environ.get("GEMINI_API_KEY")
        elif backend_type == "openai":
            api_key = os.environ.get("OPENAI_API_KEY")

    if not api_key:
        raise ValueError(
            f"No API key provided and {backend_type.upper()}_API_KEY not in environment"
        )

    return Scout(page, api_key=api_key, backend_type=backend_type)
