"""
Google Gemini backend implementation for testScout.

Supports Gemini 2.0 Flash and other Gemini models for visual AI testing.
Includes automatic fallback to cheaper models on rate limits.
"""

import json
import time
from typing import Any, Dict, List, Optional, Tuple

from .base import ActionPlan, AssertionResult, VisionBackend


# Model hierarchy: primary -> fallback (on rate limits)
MODEL_FALLBACKS = {
    "gemini-2.5-pro": "gemini-2.0-flash",
    "gemini-2.5-flash": "gemini-2.0-flash",
    "gemini-2.0-flash": "gemini-1.5-flash",
    "gemini-1.5-flash": None,  # No fallback for cheapest model
}


class GeminiBackend(VisionBackend):
    """
    Google Gemini implementation of VisionBackend.

    Uses Google's Generative AI SDK to power visual testing with Gemini models.
    Automatically falls back to cheaper models on rate limits.

    Example:
        ```python
        backend = GeminiBackend(
            api_key="your-gemini-api-key",
            model="gemini-2.0-flash"
        )
        scout = Scout(page, backend=backend)
        ```
    """

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash", fallback_model: str = "gemini-1.5-flash"):
        """
        Initialize Gemini backend.

        Args:
            api_key: Google Generative AI API key
            model: Gemini model name (default: gemini-2.0-flash)
            fallback_model: Model to use when primary hits rate limits (default: gemini-1.5-flash)
        """
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        self.genai = genai
        self.primary_model_name = model
        self.fallback_model_name = fallback_model
        self.model = genai.GenerativeModel(model)
        self.fallback_model = genai.GenerativeModel(fallback_model) if fallback_model else None
        self.model_name = model  # Current active model name
        self.last_used_model = model  # Track which model was used for last call

    def _make_image_part(self, screenshot_b64: str) -> Dict[str, Any]:
        """Create image part for Gemini API."""
        return {
            "mime_type": "image/png",
            "data": screenshot_b64,
        }

    def _generate_with_fallback(self, content: List, max_retries: int = 3) -> Tuple[Any, str]:
        """
        Generate content with automatic fallback on rate limits.

        Returns:
            Tuple of (response, model_name_used)
        """
        models_to_try = [
            (self.model, self.primary_model_name),
        ]
        if self.fallback_model:
            models_to_try.append((self.fallback_model, self.fallback_model_name))

        last_error = None

        for model, model_name in models_to_try:
            for attempt in range(max_retries):
                try:
                    response = model.generate_content(content)
                    self.last_used_model = model_name
                    return response, model_name
                except Exception as e:
                    error_str = str(e).lower()
                    is_rate_limit = "429" in str(e) or "quota" in error_str or "rate" in error_str
                    last_error = e

                    if is_rate_limit:
                        if attempt < max_retries - 1:
                            # Wait before retry on same model
                            wait_time = 10 * (attempt + 1)  # 10s, 20s, 30s
                            print(f"Rate limit on {model_name}, waiting {wait_time}s (attempt {attempt + 1}/{max_retries})...")
                            time.sleep(wait_time)
                        else:
                            # Move to fallback model
                            print(f"Rate limit exhausted on {model_name}, trying fallback...")
                            break
                    else:
                        # Non-rate-limit error, retry briefly
                        if attempt < max_retries - 1:
                            time.sleep(1)
                        else:
                            raise e

        # If we get here, all models failed
        raise last_error or Exception("All models failed")

    def generate_raw(self, content: List) -> Tuple[str, str]:
        """
        Generate raw content with automatic fallback.

        Args:
            content: List of content parts (prompts, images, etc.)

        Returns:
            Tuple of (response_text, model_name_used)
        """
        response, model_name = self._generate_with_fallback(content)
        return response.text, model_name

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

        try:
            response, model_used = self._generate_with_fallback([
                prompt,
                self._make_image_part(screenshot_b64),
            ])

            # Clean response - remove markdown code blocks if present
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()

            data = json.loads(text)
            plan = ActionPlan.from_dict(data)
            plan.model_used = model_used  # Track which model made this decision
            return plan
        except (json.JSONDecodeError, AttributeError) as e:
            from .base import ActionType

            plan = ActionPlan(
                action=ActionType.NONE,
                reason=f"Failed to parse AI response: {e}",
                confidence=0.0,
            )
            plan.model_used = self.last_used_model
            return plan
        except Exception as e:
            from .base import ActionType

            plan = ActionPlan(
                action=ActionType.NONE,
                reason=f"AI error: {str(e)[:100]}",
                confidence=0.0,
            )
            plan.model_used = self.last_used_model
            return plan

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

        try:
            response, model_used = self._generate_with_fallback([
                prompt,
                self._make_image_part(screenshot_b64),
            ])

            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()

            data = json.loads(text)
            result = AssertionResult.from_dict(data)
            result.model_used = model_used
            return result
        except (json.JSONDecodeError, AttributeError) as e:
            result = AssertionResult(
                passed=False,
                reason=f"Failed to parse AI response: {e}",
                confidence=0.0,
            )
            result.model_used = self.last_used_model
            return result
        except Exception as e:
            result = AssertionResult(
                passed=False,
                reason=f"AI error: {str(e)[:100]}",
                confidence=0.0,
            )
            result.model_used = self.last_used_model
            return result

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

        try:
            response, _ = self._generate_with_fallback([
                prompt,
                self._make_image_part(screenshot_b64),
            ])
            return response.text.strip()
        except Exception as e:
            return f"Error querying AI: {str(e)[:100]}"

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

        try:
            response, _ = self._generate_with_fallback([
                prompt,
                self._make_image_part(screenshot_b64),
            ])

            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()

            return json.loads(text)
        except (json.JSONDecodeError, AttributeError, Exception):
            return []
