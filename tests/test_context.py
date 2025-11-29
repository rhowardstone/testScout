"""Tests for the Context module."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from testscout.context import AIVerification, ConsoleLog, Context, LogLevel


class TestContext:
    """Test Context data capture."""

    def test_context_initialization(self):
        """Context should initialize with empty collections."""
        ctx = Context()
        assert len(ctx.console_logs) == 0
        assert len(ctx.network_requests) == 0
        assert len(ctx.page_errors) == 0
        assert len(ctx.ai_verifications) == 0

    def test_add_console_log(self):
        """Should track console logs by level."""
        ctx = Context()

        ctx.console_logs.append(ConsoleLog(level=LogLevel.ERROR, text="Error message"))
        ctx.console_logs.append(ConsoleLog(level=LogLevel.WARNING, text="Warning message"))
        ctx.console_logs.append(ConsoleLog(level=LogLevel.LOG, text="Info message"))

        assert len(ctx.errors) == 1
        assert len(ctx.warnings) == 1
        assert "Error message" in ctx.errors[0]

    def test_critical_error_detection(self):
        """Should detect critical JS errors."""
        ctx = Context()

        # Non-critical error
        ctx.console_logs.append(ConsoleLog(level=LogLevel.ERROR, text="Some API error"))
        assert not ctx.has_critical_errors()

        # Critical error
        ctx.console_logs.append(
            ConsoleLog(level=LogLevel.ERROR, text="Uncaught ReferenceError: x is not defined")
        )
        assert ctx.has_critical_errors()

    def test_critical_error_patterns(self):
        """Should recognize various critical error patterns."""
        test_cases = [
            ("TypeError: Cannot read property 'x' of undefined", True),
            ("SyntaxError: Unexpected token", True),
            ("Hydration failed because...", True),
            ("Maximum update depth exceeded", True),
            ("ChunkLoadError: Loading chunk", True),
            ("API returned 500", False),
            ("Network request failed", False),
        ]

        for error_text, should_be_critical in test_cases:
            ctx = Context()
            ctx.console_logs.append(ConsoleLog(level=LogLevel.ERROR, text=error_text))
            result = ctx.has_critical_errors()
            assert (
                result == should_be_critical
            ), f"'{error_text}' should {'be' if should_be_critical else 'not be'} critical"

    def test_ai_verification_recording(self):
        """Should record AI verification results."""
        ctx = Context()

        ctx.add_ai_verification(
            AIVerification(
                action_type="assert",
                description="Page shows login form",
                result=True,
                reason="Login form visible",
            )
        )

        ctx.add_ai_verification(
            AIVerification(
                action_type="action",
                description="Click submit",
                result=False,
                reason="Button not found",
            )
        )

        summary = ctx.summary()
        assert summary["ai_verifications"] == 2
        assert summary["ai_passes"] == 1
        assert summary["ai_failures"] == 1

    def test_screenshot_caching(self):
        """Should detect duplicate screenshots."""
        ctx = Context()

        # Same screenshot data
        data1 = b"screenshot_data_abc"
        data2 = b"screenshot_data_abc"
        data3 = b"different_screenshot"

        ctx.save_screenshot("shot1", data1)
        assert not ctx.is_screenshot_cached(data3)
        assert ctx.is_screenshot_cached(data2)

    def test_report_generation(self):
        """Should generate readable report."""
        ctx = Context()

        ctx.console_logs.append(ConsoleLog(level=LogLevel.ERROR, text="Test error"))
        ctx.console_logs.append(ConsoleLog(level=LogLevel.WARNING, text="Test warning"))
        ctx.page_errors.append("Uncaught exception")
        ctx.add_ai_verification(
            AIVerification(
                action_type="assert",
                description="Page loads correctly",
                result=True,
            )
        )

        report = ctx.generate_report()

        assert "TESTSCOUT E2E REPORT" in report
        assert "Test error" in report
        assert "Test warning" in report
        assert "PASS" in report
        assert "Page loads correctly" in report

    def test_summary_stats(self):
        """Should calculate correct summary statistics."""
        ctx = Context()

        # Add various items
        for _ in range(3):
            ctx.console_logs.append(ConsoleLog(level=LogLevel.ERROR, text="err"))
        for _ in range(2):
            ctx.console_logs.append(ConsoleLog(level=LogLevel.WARNING, text="warn"))
        for _ in range(5):
            ctx.console_logs.append(ConsoleLog(level=LogLevel.LOG, text="log"))

        summary = ctx.summary()

        assert summary["console_logs"] == 10
        assert summary["errors"] == 3
        assert summary["warnings"] == 2

    def test_reset_clears_all(self):
        """Reset should clear all captured data."""
        ctx = Context()

        ctx.console_logs.append(ConsoleLog(level=LogLevel.ERROR, text="err"))
        ctx.page_errors.append("error")
        ctx.save_screenshot("test", b"data")

        ctx.reset()

        assert len(ctx.console_logs) == 0
        assert len(ctx.page_errors) == 0
        assert len(ctx.screenshots) == 0


class TestConsoleLog:
    """Test ConsoleLog dataclass."""

    def test_to_dict(self):
        """Should serialize to dict."""
        log = ConsoleLog(
            level=LogLevel.ERROR,
            text="Test error message",
            source="app.js",
            line=42,
        )

        data = log.to_dict()

        assert data["level"] == "error"
        assert data["text"] == "Test error message"
        assert data["source"] == "app.js"
        assert data["line"] == 42


class TestAIVerification:
    """Test AIVerification dataclass."""

    def test_to_dict(self):
        """Should serialize to dict with PASS/FAIL status."""
        v_pass = AIVerification(
            action_type="assert",
            description="Test passed",
            result=True,
            reason="All good",
            element_id=5,
            duration_ms=123.5,
        )

        v_fail = AIVerification(
            action_type="action",
            description="Click failed",
            result=False,
            reason="Element not found",
        )

        pass_dict = v_pass.to_dict()
        fail_dict = v_fail.to_dict()

        assert pass_dict["result"] == "PASS"
        assert fail_dict["result"] == "FAIL"
        assert pass_dict["element_id"] == 5
        assert pass_dict["duration_ms"] == 123.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
