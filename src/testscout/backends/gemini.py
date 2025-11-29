"""
Google Gemini backend implementation for testScout.

Supports Gemini 2.0 Flash and other Gemini models for visual AI testing.
"""

import json
from typing import Any, Dict, List, Optional

from .base import ActionPlan, AssertionResult, VisionBackend


class GeminiBackend(VisionBackend):
    """
    Google Gemini implementation of VisionBackend.

    Uses Google's Generative AI SDK to power visual testing with Gemini models.

    Example:
        ```python
        backend = GeminiBackend(
            api_key="your-gemini-api-key",
            model="gemini-2.0-flash"
        )
        scout = Scout(page, backend=backend)
        ```
    """

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        """
        Initialize Gemini backend.

        Args:
            api_key: Google Generative AI API key
            model: Gemini model name (default: gemini-2.0-flash)
        """
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
        self.genai = genai
        self.model_name = model

    def _make_image_part(self, screenshot_b64: str) -> Dict[str, Any]:
        """Create image part for Gemini API."""
        return {
            "mime_type": "image/png",
            "data": screenshot_b64,
        }

    def plan_action(
        self,
        instruction: str,
        screenshot_b64: str,
        elements,
    ) -> ActionPlan:
        """Plan an action using Gemini vision."""
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

        response = self.model.generate_content(
            [
                prompt,
                self._make_image_part(screenshot_b64),
            ]
        )

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
            from .base import ActionType

            return ActionPlan(
                action=ActionType.NONE,
                reason=f"Failed to parse AI response: {e}. Raw: {response.text[:200]}",
                confidence=0.0,
            )

    def verify_assertion(
        self,
        assertion: str,
        screenshot_b64: str,
        elements=None,
    ) -> AssertionResult:
        """Verify an assertion using Gemini vision."""
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

        response = self.model.generate_content(
            [
                prompt,
                self._make_image_part(screenshot_b64),
            ]
        )

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
        elements=None,
    ) -> str:
        """Ask Gemini a question about the page."""
        element_context = ""
        if elements:
            element_context = f"\n\nAvailable elements:\n{elements.to_prompt_summary()}"

        prompt = f"""Look at this screenshot and answer the question.
{element_context}

QUESTION: {question}

Give a concise, direct answer.
"""

        response = self.model.generate_content(
            [
                prompt,
                self._make_image_part(screenshot_b64),
            ]
        )

        return response.text.strip()

    def discover_elements(
        self,
        screenshot_b64: str,
        element_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Use Gemini to visually identify elements on the page."""
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

        response = self.model.generate_content(
            [
                prompt,
                self._make_image_part(screenshot_b64),
            ]
        )

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
