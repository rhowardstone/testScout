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
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Union
from enum import Enum

from .discovery import ElementDiscoverySync, PageElements, DiscoveredElement
from .context import Context, AIVerification


class ActionType(Enum):
    CLICK = "click"
    FILL = "fill"
    TYPE = "type"
    SELECT = "select"
    SCROLL = "scroll"
    WAIT = "wait"
    HOVER = "hover"
    NONE = "none"  # No action needed


@dataclass
class ActionPlan:
    """Structured action plan from AI."""
    action: ActionType
    element_id: Optional[int] = None  # data-testscout-id
    text: Optional[str] = None  # For fill/type/select
    direction: Optional[str] = None  # For scroll: up/down
    duration_ms: Optional[int] = None  # For wait
    reason: str = ""  # Why this action
    confidence: float = 1.0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActionPlan":
        action_str = data.get("action", "none").lower()
        try:
            action = ActionType(action_str)
        except ValueError:
            action = ActionType.NONE

        return cls(
            action=action,
            element_id=data.get("element_id"),
            text=data.get("text"),
            direction=data.get("direction"),
            duration_ms=data.get("duration_ms"),
            reason=data.get("reason", ""),
            confidence=data.get("confidence", 1.0),
        )


@dataclass
class AssertionResult:
    """Result of an AI assertion."""
    passed: bool
    reason: str
    confidence: float = 1.0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AssertionResult":
        return cls(
            passed=data.get("passed", False),
            reason=data.get("reason", ""),
            confidence=data.get("confidence", 1.0),
        )


# =============================================================================
# Pluggable AI Backend Interface
# =============================================================================

class VisionBackend(ABC):
    """Abstract interface for vision AI backends."""

    @abstractmethod
    def plan_action(
        self,
        instruction: str,
        screenshot_b64: str,
        elements: PageElements,
    ) -> ActionPlan:
        """Plan an action given instruction, screenshot, and available elements."""
        pass

    @abstractmethod
    def verify_assertion(
        self,
        assertion: str,
        screenshot_b64: str,
        elements: Optional[PageElements] = None,
    ) -> AssertionResult:
        """Verify an assertion about the current page state."""
        pass

    @abstractmethod
    def query(
        self,
        question: str,
        screenshot_b64: str,
        elements: Optional[PageElements] = None,
    ) -> str:
        """Ask a question about the current page."""
        pass

    @abstractmethod
    def discover_elements(
        self,
        screenshot_b64: str,
        element_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        AI-powered element discovery - ask AI to identify elements visually.
        Returns list of elements AI can see with approximate positions.
        """
        pass


# =============================================================================
# Gemini Backend Implementation
# =============================================================================

class GeminiBackend(VisionBackend):
    """Google Gemini implementation of VisionBackend."""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
        self.genai = genai

    def _make_image_part(self, screenshot_b64: str) -> Dict[str, Any]:
        return {
            "mime_type": "image/png",
            "data": screenshot_b64,
        }

    def plan_action(
        self,
        instruction: str,
        screenshot_b64: str,
        elements: PageElements,
    ) -> ActionPlan:
        element_summary = elements.to_prompt_summary() if elements else "No elements discovered."

        prompt = f"""You are a browser automation agent. You see a screenshot and a list of interactive elements.

TASK: {instruction}

AVAILABLE ELEMENTS (use element_id to target):
{element_summary}

Based on the screenshot AND the element list, decide what action to take.
If the visual element you want to interact with matches an element in the list, use that element_id.

Return ONLY valid JSON (no markdown, no explanation):
{{
    "action": "click" | "fill" | "type" | "select" | "scroll" | "wait" | "hover" | "none",
    "element_id": <number from list, or null>,
    "text": "<text to fill/type, or null>",
    "direction": "up" | "down" | null,
    "duration_ms": <milliseconds to wait, or null>,
    "reason": "<brief explanation>",
    "confidence": <0.0 to 1.0>
}}
"""

        response = self.model.generate_content([
            prompt,
            self._make_image_part(screenshot_b64),
        ])

        try:
            # Clean response - remove markdown code blocks if present
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()

            data = json.loads(text)
            return ActionPlan.from_dict(data)
        except (json.JSONDecodeError, AttributeError) as e:
            return ActionPlan(
                action=ActionType.NONE,
                reason=f"Failed to parse AI response: {e}. Raw: {response.text[:200]}",
                confidence=0.0,
            )

    def verify_assertion(
        self,
        assertion: str,
        screenshot_b64: str,
        elements: Optional[PageElements] = None,
    ) -> AssertionResult:
        element_context = ""
        if elements:
            element_context = f"\n\nAvailable elements on page:\n{elements.to_prompt_summary()}"

        prompt = f"""You are verifying a UI assertion. Look at the screenshot carefully.

ASSERTION: {assertion}
{element_context}

Is this assertion TRUE or FALSE based on what you see?

Return ONLY valid JSON (no markdown, no explanation):
{{
    "passed": true | false,
    "reason": "<brief explanation of what you see>",
    "confidence": <0.0 to 1.0>
}}
"""

        response = self.model.generate_content([
            prompt,
            self._make_image_part(screenshot_b64),
        ])

        try:
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()

            data = json.loads(text)
            return AssertionResult.from_dict(data)
        except (json.JSONDecodeError, AttributeError) as e:
            return AssertionResult(
                passed=False,
                reason=f"Failed to parse AI response: {e}",
                confidence=0.0,
            )

    def query(
        self,
        question: str,
        screenshot_b64: str,
        elements: Optional[PageElements] = None,
    ) -> str:
        element_context = ""
        if elements:
            element_context = f"\n\nAvailable elements:\n{elements.to_prompt_summary()}"

        prompt = f"""Look at this screenshot and answer the question.
{element_context}

QUESTION: {question}

Give a concise, direct answer.
"""

        response = self.model.generate_content([
            prompt,
            self._make_image_part(screenshot_b64),
        ])

        return response.text.strip()

    def discover_elements(
        self,
        screenshot_b64: str,
        element_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Ask AI to visually identify elements on the page."""
        type_filter = f"of type '{element_type}'" if element_type else ""

        prompt = f"""Look at this screenshot and identify all interactive elements {type_filter}.

For each element you can see, provide:
- type: button, link, input, checkbox, dropdown, etc.
- label: visible text or aria label
- position: approximate location (top-left, center, bottom-right, etc.)
- description: brief visual description

Return ONLY valid JSON array (no markdown):
[
    {{"type": "button", "label": "Sign In", "position": "top-right", "description": "Blue button"}},
    ...
]
"""

        response = self.model.generate_content([
            prompt,
            self._make_image_part(screenshot_b64),
        ])

        try:
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()

            return json.loads(text)
        except (json.JSONDecodeError, AttributeError):
            return []


# =============================================================================
# OpenAI Backend Implementation
# =============================================================================

class OpenAIBackend(VisionBackend):
    """OpenAI GPT-4V implementation of VisionBackend."""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def _call_vision(self, prompt: str, screenshot_b64: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{screenshot_b64}",
                        },
                    },
                ],
            }],
            max_tokens=1000,
        )
        return response.choices[0].message.content

    def plan_action(
        self,
        instruction: str,
        screenshot_b64: str,
        elements: PageElements,
    ) -> ActionPlan:
        element_summary = elements.to_prompt_summary() if elements else "No elements discovered."

        prompt = f"""You are a browser automation agent.

TASK: {instruction}

AVAILABLE ELEMENTS:
{element_summary}

Return ONLY JSON:
{{"action": "click|fill|type|select|scroll|wait|hover|none", "element_id": <number or null>, "text": "<string or null>", "reason": "<brief>", "confidence": <0-1>}}
"""
        text = self._call_vision(prompt, screenshot_b64)
        try:
            text = text.strip()
            if text.startswith("```"):
                text = text.split("```")[1].replace("json", "").strip()
            return ActionPlan.from_dict(json.loads(text))
        except Exception as e:
            return ActionPlan(action=ActionType.NONE, reason=f"Parse error: {e}", confidence=0.0)

    def verify_assertion(
        self,
        assertion: str,
        screenshot_b64: str,
        elements: Optional[PageElements] = None,
    ) -> AssertionResult:
        prompt = f"""Verify this assertion about the screenshot:

ASSERTION: {assertion}

Return ONLY JSON: {{"passed": true|false, "reason": "<brief>", "confidence": <0-1>}}
"""
        text = self._call_vision(prompt, screenshot_b64)
        try:
            text = text.strip()
            if text.startswith("```"):
                text = text.split("```")[1].replace("json", "").strip()
            return AssertionResult.from_dict(json.loads(text))
        except Exception:
            return AssertionResult(passed=False, reason="Parse error", confidence=0.0)

    def query(
        self,
        question: str,
        screenshot_b64: str,
        elements: Optional[PageElements] = None,
    ) -> str:
        prompt = f"Look at this screenshot and answer: {question}"
        return self._call_vision(prompt, screenshot_b64)

    def discover_elements(
        self,
        screenshot_b64: str,
        element_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        type_filter = f"of type '{element_type}'" if element_type else ""
        prompt = f"""List all interactive elements {type_filter} you see.
Return JSON array: [{{"type": "...", "label": "...", "position": "...", "description": "..."}}]
"""
        text = self._call_vision(prompt, screenshot_b64)
        try:
            if text.startswith("```"):
                text = text.split("```")[1].replace("json", "").strip()
            return json.loads(text)
        except Exception:
            return []


# =============================================================================
# Main Scout Agent
# =============================================================================

class Scout:
    """
    The main testScout agent - combines discovery + AI vision.

    Usage:
        scout = Scout(page, api_key="...")

        # AI picks the right element from screenshot + element list
        await scout.action("Click the login button")
        await scout.action("Fill in the email field with test@example.com")

        # AI verifies visual state
        assert await scout.verify("A dashboard with user stats should be visible")

        # Ask AI about the page
        answer = await scout.query("What error message is shown?")

        # AI-powered element discovery
        buttons = await scout.discover_elements("button")
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

        Returns True if action was executed successfully.
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
        Returns True if assertion passes.
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
            reason=result.reason if result else "Timeout",
            duration_ms=(time.time() - start_time) * 1000,
        ))
        return False

    def query(self, question: str) -> str:
        """Ask AI a question about the current page state."""
        screenshot_b64 = self._get_screenshot_b64(with_markers=False)
        elements = self._refresh_elements()
        return self.backend.query(question, screenshot_b64, elements)

    def discover_elements(
        self,
        element_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Use AI to visually discover elements on the page.

        This is different from DOM discovery - it asks the AI to look at
        the screenshot and identify elements it can see, even if they
        don't have obvious DOM selectors.

        Args:
            element_type: Optional filter like "button", "link", "input"

        Returns:
            List of elements AI identified with position/description
        """
        screenshot_b64 = self._get_screenshot_b64(with_markers=False)
        return self.backend.discover_elements(screenshot_b64, element_type)

    def check_no_errors(self) -> bool:
        """Check that no critical errors have occurred."""
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


# Convenience function to create a Scout with common defaults
def create_scout(
    page,
    api_key: Optional[str] = None,
    backend_type: str = "gemini",
) -> Scout:
    """
    Create a Scout agent with sensible defaults.

    Will try to get API key from environment if not provided.
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
