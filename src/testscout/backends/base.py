"""
Abstract base interface for AI vision backends.

This module defines the contract that all AI backends must implement.
Backends can be swapped out to use different AI providers (Gemini, OpenAI, Claude, etc.)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class ActionType(Enum):
    """Types of actions the AI can plan."""

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
        """Create ActionPlan from dictionary response."""
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
        """Create AssertionResult from dictionary response."""
        return cls(
            passed=data.get("passed", False),
            reason=data.get("reason", ""),
            confidence=data.get("confidence", 1.0),
        )


class VisionBackend(ABC):
    """
    Abstract interface for AI vision backends.

    Implement this interface to add support for new AI providers.

    Example:
        class MyCustomBackend(VisionBackend):
            def plan_action(self, instruction, screenshot_b64, elements):
                # Your implementation
                pass

            # ... implement other methods
    """

    @abstractmethod
    def plan_action(
        self,
        instruction: str,
        screenshot_b64: str,
        elements,  # PageElements type
    ) -> ActionPlan:
        """
        Plan an action given instruction, screenshot, and available elements.

        Args:
            instruction: Natural language instruction (e.g., "Click the login button")
            screenshot_b64: Base64-encoded screenshot with visual markers
            elements: PageElements object containing discovered DOM elements

        Returns:
            ActionPlan with the recommended action
        """
        pass

    @abstractmethod
    def verify_assertion(
        self,
        assertion: str,
        screenshot_b64: str,
        elements=None,  # Optional[PageElements]
    ) -> AssertionResult:
        """
        Verify an assertion about the current page state.

        Args:
            assertion: Natural language assertion (e.g., "The login form should be visible")
            screenshot_b64: Base64-encoded screenshot
            elements: Optional PageElements for context

        Returns:
            AssertionResult indicating if the assertion passed
        """
        pass

    @abstractmethod
    def query(
        self,
        question: str,
        screenshot_b64: str,
        elements=None,  # Optional[PageElements]
    ) -> str:
        """
        Ask a question about the current page.

        Args:
            question: Natural language question (e.g., "What error message is shown?")
            screenshot_b64: Base64-encoded screenshot
            elements: Optional PageElements for context

        Returns:
            String answer from the AI
        """
        pass

    @abstractmethod
    def discover_elements(
        self,
        screenshot_b64: str,
        element_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        AI-powered element discovery - ask AI to identify elements visually.

        Args:
            screenshot_b64: Base64-encoded screenshot
            element_type: Optional filter (e.g., "button", "link", "input")

        Returns:
            List of elements AI identified with position/description
        """
        pass
