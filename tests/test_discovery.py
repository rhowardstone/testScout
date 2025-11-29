"""Tests for the Discovery module."""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from testscout.discovery import (
    DiscoveredElement,
    PageElements,
    ElementType,
)


class TestDiscoveredElement:
    """Test DiscoveredElement dataclass."""

    def test_selector_generation(self):
        """Should generate data-testscout-id selector."""
        el = DiscoveredElement(
            ai_id=5,
            element_type=ElementType.BUTTON,
            tag="button",
            text="Submit",
            placeholder="",
            aria_label="Submit form",
            name="submit",
            id="submit-btn",
            classes=["btn", "primary"],
            href=None,
            src=None,
            is_visible=True,
            is_enabled=True,
            bounding_box={"x": 100, "y": 200, "width": 80, "height": 40},
        )

        assert el.selector() == '[data-testscout-id="5"]'

    def test_to_dict(self):
        """Should serialize to dict."""
        el = DiscoveredElement(
            ai_id=3,
            element_type=ElementType.INPUT,
            tag="input",
            text="",
            placeholder="Enter email",
            aria_label="Email address",
            name="email",
            id="email-input",
            classes=["form-control"],
            href=None,
            src=None,
            is_visible=True,
            is_enabled=True,
            bounding_box={"x": 50, "y": 100, "width": 200, "height": 30},
        )

        data = el.to_dict()

        assert data["ai_id"] == 3
        assert data["type"] == "input"
        assert data["placeholder"] == "Enter email"
        assert data["visible"] is True
        assert data["enabled"] is True


class TestPageElements:
    """Test PageElements collection."""

    @pytest.fixture
    def sample_elements(self):
        """Create sample elements for testing."""
        return PageElements(elements=[
            DiscoveredElement(
                ai_id=0,
                element_type=ElementType.BUTTON,
                tag="button",
                text="Login",
                placeholder="",
                aria_label="",
                name="",
                id="login-btn",
                classes=[],
                href=None,
                src=None,
                is_visible=True,
                is_enabled=True,
                bounding_box={},
            ),
            DiscoveredElement(
                ai_id=1,
                element_type=ElementType.INPUT,
                tag="input",
                text="",
                placeholder="Email",
                aria_label="",
                name="email",
                id="",
                classes=[],
                href=None,
                src=None,
                is_visible=True,
                is_enabled=True,
                bounding_box={},
            ),
            DiscoveredElement(
                ai_id=2,
                element_type=ElementType.INPUT,
                tag="input",
                text="",
                placeholder="Password",
                aria_label="",
                name="password",
                id="",
                classes=[],
                href=None,
                src=None,
                is_visible=True,
                is_enabled=True,
                bounding_box={},
            ),
            DiscoveredElement(
                ai_id=3,
                element_type=ElementType.LINK,
                tag="a",
                text="Forgot Password?",
                placeholder="",
                aria_label="",
                name="",
                id="",
                classes=[],
                href="/forgot",
                src=None,
                is_visible=True,
                is_enabled=True,
                bounding_box={},
            ),
        ])

    def test_find_by_id(self, sample_elements):
        """Should find element by ai_id."""
        el = sample_elements.find_by_id(1)
        assert el is not None
        assert el.placeholder == "Email"

        # Non-existent ID
        assert sample_elements.find_by_id(99) is None

    def test_find_by_text_partial(self, sample_elements):
        """Should find elements by partial text match."""
        results = sample_elements.find_by_text("Login")
        assert len(results) == 1
        assert results[0].ai_id == 0

        results = sample_elements.find_by_text("Password", partial=True)
        assert len(results) == 1  # Only link text matches (find_by_text searches text, not placeholder)

    def test_find_by_text_exact(self, sample_elements):
        """Should find elements by exact text match."""
        results = sample_elements.find_by_text("Login", partial=False)
        assert len(results) == 1

        results = sample_elements.find_by_text("Log", partial=False)
        assert len(results) == 0

    def test_find_by_type(self, sample_elements):
        """Should find elements by type."""
        inputs = sample_elements.find_by_type(ElementType.INPUT)
        assert len(inputs) == 2

        buttons = sample_elements.find_by_type(ElementType.BUTTON)
        assert len(buttons) == 1

        links = sample_elements.find_by_type(ElementType.LINK)
        assert len(links) == 1

    def test_to_prompt_summary(self, sample_elements):
        """Should generate readable summary for AI prompts."""
        summary = sample_elements.to_prompt_summary()

        assert "Interactive elements on page:" in summary
        assert "[0] button" in summary
        assert '"Login"' in summary
        assert "[1] input" in summary
        assert "(placeholder: Email)" in summary

    def test_empty_elements(self):
        """Should handle empty element list."""
        empty = PageElements(elements=[])

        assert empty.find_by_id(0) is None
        assert empty.find_by_text("anything") == []
        assert "No interactive elements" in empty.to_prompt_summary()


class TestElementType:
    """Test ElementType enum."""

    def test_all_types_exist(self):
        """Should have all expected element types."""
        expected = ["button", "link", "input", "select", "textarea",
                   "checkbox", "radio", "image", "custom"]

        for type_name in expected:
            assert ElementType(type_name) is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
