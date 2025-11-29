"""
AI Vision Backends for testScout.

This module provides pluggable AI backends for visual testing.
Each backend implements the VisionBackend interface.

Available Backends:
    - GeminiBackend: Google Gemini (gemini-2.0-flash)
    - OpenAIBackend: OpenAI GPT-4V (gpt-4o)

You can also implement custom backends by extending VisionBackend.

Example:
    ```python
    from testscout.backends import GeminiBackend, OpenAIBackend
    from testscout import Scout

    # Use Gemini
    gemini = GeminiBackend(api_key="...")
    scout = Scout(page, backend=gemini)

    # Use OpenAI
    openai = OpenAIBackend(api_key="...")
    scout = Scout(page, backend=openai)
    ```
"""

from .base import (
    ActionPlan,
    ActionType,
    AssertionResult,
    VisionBackend,
)
from .gemini import GeminiBackend
from .openai import OpenAIBackend

__all__ = [
    "VisionBackend",
    "ActionPlan",
    "AssertionResult",
    "ActionType",
    "GeminiBackend",
    "OpenAIBackend",
]
