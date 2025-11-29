"""
OpenAI GPT-4V backend implementation for testScout.

Supports GPT-4o and other OpenAI vision models for visual AI testing.
"""

import json
from typing import Any, Dict, List, Optional

from .base import ActionPlan, ActionType, AssertionResult, VisionBackend


class OpenAIBackend(VisionBackend):
    """
    OpenAI GPT-4V implementation of VisionBackend.

    Uses OpenAI's Chat Completions API with vision capabilities.

    Example:
        ```python
        backend = OpenAIBackend(
            api_key="your-openai-api-key",
            model="gpt-4o"
        )
        scout = Scout(page, backend=backend)
        ```
    """

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        """
        Initialize OpenAI backend.

        Args:
            api_key: OpenAI API key
            model: OpenAI model name (default: gpt-4o)
        """
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key)
        self.model = model

    def _call_vision(self, prompt: str, screenshot_b64: str) -> str:
        """Make a vision API call to OpenAI."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
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
                }
            ],
            max_tokens=1000,
        )
        return response.choices[0].message.content

    def plan_action(
        self,
        instruction: str,
        screenshot_b64: str,
        elements,
    ) -> ActionPlan:
        """Plan an action using GPT-4V vision."""
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
        elements=None,
    ) -> AssertionResult:
        """Verify an assertion using GPT-4V vision."""
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
        elements=None,
    ) -> str:
        """Ask GPT-4V a question about the page."""
        prompt = f"Look at this screenshot and answer: {question}"
        return self._call_vision(prompt, screenshot_b64)

    def discover_elements(
        self,
        screenshot_b64: str,
        element_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Use GPT-4V to visually identify elements on the page."""
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
