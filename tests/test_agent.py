"""Tests for the Agent module with mock backend."""

import os
import sys
from typing import Any, Dict, List, Optional

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from testscout.backends import (
    ActionPlan,
    ActionType,
    AssertionResult,
    VisionBackend,
)
from testscout.discovery import PageElements


class MockVisionBackend(VisionBackend):
    """Mock backend for testing without real AI."""

    def __init__(self):
        self.action_responses = []
        self.assertion_responses = []
        self.query_responses = []
        self.discover_responses = []
        self._action_calls = []
        self._assertion_calls = []

    def set_action_response(self, plan: ActionPlan):
        """Set the next action response."""
        self.action_responses.append(plan)

    def set_assertion_response(self, result: AssertionResult):
        """Set the next assertion response."""
        self.assertion_responses.append(result)

    def set_query_response(self, response: str):
        """Set the next query response."""
        self.query_responses.append(response)

    def plan_action(
        self,
        instruction: str,
        screenshot_b64: str,
        elements: PageElements,
    ) -> ActionPlan:
        self._action_calls.append(
            {
                "instruction": instruction,
                "elements_count": len(elements.elements) if elements else 0,
            }
        )

        if self.action_responses:
            return self.action_responses.pop(0)

        return ActionPlan(
            action=ActionType.NONE,
            reason="No mock response set",
        )

    def verify_assertion(
        self,
        assertion: str,
        screenshot_b64: str,
        elements: Optional[PageElements] = None,
    ) -> AssertionResult:
        self._assertion_calls.append({"assertion": assertion})

        if self.assertion_responses:
            return self.assertion_responses.pop(0)

        return AssertionResult(passed=False, reason="No mock response set")

    def query(
        self,
        question: str,
        screenshot_b64: str,
        elements: Optional[PageElements] = None,
    ) -> str:
        if self.query_responses:
            return self.query_responses.pop(0)
        return "Mock response"

    def discover_elements(
        self,
        screenshot_b64: str,
        element_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if self.discover_responses:
            return self.discover_responses.pop(0)
        return []


class TestActionPlan:
    """Test ActionPlan dataclass."""

    def test_from_dict_click(self):
        """Should parse click action from dict."""
        data = {
            "action": "click",
            "element_id": 5,
            "reason": "Clicking submit button",
            "confidence": 0.95,
        }

        plan = ActionPlan.from_dict(data)

        assert plan.action == ActionType.CLICK
        assert plan.element_id == 5
        assert plan.reason == "Clicking submit button"
        assert plan.confidence == 0.95

    def test_from_dict_fill(self):
        """Should parse fill action from dict."""
        data = {
            "action": "fill",
            "element_id": 2,
            "text": "test@example.com",
            "reason": "Filling email field",
        }

        plan = ActionPlan.from_dict(data)

        assert plan.action == ActionType.FILL
        assert plan.element_id == 2
        assert plan.text == "test@example.com"

    def test_from_dict_scroll(self):
        """Should parse scroll action from dict."""
        data = {
            "action": "scroll",
            "direction": "down",
            "reason": "Scrolling to see more",
        }

        plan = ActionPlan.from_dict(data)

        assert plan.action == ActionType.SCROLL
        assert plan.direction == "down"

    def test_from_dict_wait(self):
        """Should parse wait action from dict."""
        data = {
            "action": "wait",
            "duration_ms": 2000,
            "reason": "Waiting for page load",
        }

        plan = ActionPlan.from_dict(data)

        assert plan.action == ActionType.WAIT
        assert plan.duration_ms == 2000

    def test_from_dict_unknown_action(self):
        """Should handle unknown action type."""
        data = {
            "action": "unknown_action",
            "reason": "Some reason",
        }

        plan = ActionPlan.from_dict(data)

        assert plan.action == ActionType.NONE

    def test_from_dict_defaults(self):
        """Should use defaults for missing fields."""
        data = {"action": "click"}

        plan = ActionPlan.from_dict(data)

        assert plan.element_id is None
        assert plan.text is None
        assert plan.reason == ""
        assert plan.confidence == 1.0


class TestAssertionResult:
    """Test AssertionResult dataclass."""

    def test_from_dict_passed(self):
        """Should parse passed assertion."""
        data = {
            "passed": True,
            "reason": "Login form is visible",
            "confidence": 0.98,
        }

        result = AssertionResult.from_dict(data)

        assert result.passed is True
        assert result.reason == "Login form is visible"
        assert result.confidence == 0.98

    def test_from_dict_failed(self):
        """Should parse failed assertion."""
        data = {
            "passed": False,
            "reason": "Dashboard not visible",
            "confidence": 0.85,
        }

        result = AssertionResult.from_dict(data)

        assert result.passed is False
        assert result.reason == "Dashboard not visible"

    def test_from_dict_defaults(self):
        """Should use defaults for missing fields."""
        data = {}

        result = AssertionResult.from_dict(data)

        assert result.passed is False
        assert result.reason == ""
        assert result.confidence == 1.0


class TestMockBackend:
    """Test that mock backend works correctly."""

    def test_action_queuing(self):
        """Should return queued action responses in order."""
        backend = MockVisionBackend()

        backend.set_action_response(
            ActionPlan(
                action=ActionType.CLICK,
                element_id=1,
            )
        )
        backend.set_action_response(
            ActionPlan(
                action=ActionType.FILL,
                element_id=2,
                text="test",
            )
        )

        elements = PageElements(elements=[])

        r1 = backend.plan_action("click button", "", elements)
        r2 = backend.plan_action("fill input", "", elements)

        assert r1.action == ActionType.CLICK
        assert r2.action == ActionType.FILL

    def test_assertion_queuing(self):
        """Should return queued assertion responses in order."""
        backend = MockVisionBackend()

        backend.set_assertion_response(AssertionResult(passed=True, reason="OK"))
        backend.set_assertion_response(AssertionResult(passed=False, reason="Not OK"))

        r1 = backend.verify_assertion("first", "")
        r2 = backend.verify_assertion("second", "")

        assert r1.passed is True
        assert r2.passed is False

    def test_tracks_calls(self):
        """Should track API calls for debugging."""
        backend = MockVisionBackend()
        backend.set_action_response(ActionPlan(action=ActionType.CLICK))
        backend.set_assertion_response(AssertionResult(passed=True, reason="OK"))

        elements = PageElements(elements=[])

        backend.plan_action("click login", "", elements)
        backend.verify_assertion("page visible", "")

        assert len(backend._action_calls) == 1
        assert backend._action_calls[0]["instruction"] == "click login"
        assert len(backend._assertion_calls) == 1
        assert backend._assertion_calls[0]["assertion"] == "page visible"


class TestActionType:
    """Test ActionType enum."""

    def test_all_types(self):
        """Should have all expected action types."""
        expected = ["click", "fill", "type", "select", "scroll", "wait", "hover", "none"]

        for type_name in expected:
            assert ActionType(type_name) is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
