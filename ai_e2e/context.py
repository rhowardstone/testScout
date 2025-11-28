"""
Context capture for E2E tests.

Captures everything that happens during a test:
- Console logs (info, warn, error)
- Network requests/failures
- Page errors (uncaught exceptions)
- AI decisions and verifications
- Screenshots at key moments
"""

import time
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
from pathlib import Path


class LogLevel(Enum):
    DEBUG = "debug"
    INFO = "info"
    LOG = "log"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ConsoleLog:
    """A single console message."""
    level: LogLevel
    text: str
    timestamp: datetime = field(default_factory=datetime.now)
    source: Optional[str] = None
    line: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level.value,
            "text": self.text,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "line": self.line,
        }


@dataclass
class NetworkRequest:
    """A network request/response."""
    url: str
    method: str
    status: Optional[int] = None
    failed: bool = False
    failure_reason: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "method": self.method,
            "status": self.status,
            "failed": self.failed,
            "failure_reason": self.failure_reason,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class AIVerification:
    """Record of an AI decision or verification."""
    action_type: str  # "assert", "action", "query"
    description: str
    result: bool
    reason: Optional[str] = None
    ai_response: Optional[str] = None
    element_id: Optional[int] = None
    screenshot_hash: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    duration_ms: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.action_type,
            "description": self.description,
            "result": "PASS" if self.result else "FAIL",
            "reason": self.reason,
            "element_id": self.element_id,
            "timestamp": self.timestamp.isoformat(),
            "duration_ms": self.duration_ms,
        }


@dataclass
class Context:
    """
    Captures all context during an E2E test session.

    Usage:
        context = Context()
        context.attach_to_page(page)  # Start capturing

        # ... run tests ...

        context.save_report("test_report.txt")
    """
    console_logs: List[ConsoleLog] = field(default_factory=list)
    network_requests: List[NetworkRequest] = field(default_factory=list)
    page_errors: List[str] = field(default_factory=list)
    ai_verifications: List[AIVerification] = field(default_factory=list)
    screenshots: Dict[str, bytes] = field(default_factory=dict)
    _screenshot_cache: Dict[str, str] = field(default_factory=dict)  # hash -> timestamp

    # Critical error patterns (framework-specific)
    CRITICAL_PATTERNS = [
        # JavaScript errors
        "ReferenceError",
        "TypeError",
        "SyntaxError",
        "RangeError",
        "URIError",
        # React errors
        "Hydration failed",
        "Maximum update depth exceeded",
        "Minified React error",
        "Invalid hook call",
        # Vue errors
        "Vue warn",
        "[Vue warn]",
        # Angular errors
        "ExpressionChangedAfterItHasBeenCheckedError",
        # Webpack/build errors
        "ChunkLoadError",
        "Loading chunk",
        # Generic
        "is not defined",
        "Cannot read property",
        "Cannot read properties",
        "null is not an object",
        "undefined is not an object",
    ]

    def attach_to_page(self, page):
        """Attach event listeners to capture page activity."""

        def on_console(msg):
            level_map = {
                "log": LogLevel.LOG,
                "info": LogLevel.INFO,
                "warning": LogLevel.WARNING,
                "warn": LogLevel.WARNING,
                "error": LogLevel.ERROR,
                "debug": LogLevel.DEBUG,
            }
            level = level_map.get(msg.type, LogLevel.LOG)
            self.console_logs.append(ConsoleLog(
                level=level,
                text=msg.text,
                source=msg.location.get("url") if msg.location else None,
                line=msg.location.get("lineNumber") if msg.location else None,
            ))

        def on_page_error(error):
            self.page_errors.append(str(error))

        def on_response(response):
            self.network_requests.append(NetworkRequest(
                url=response.url,
                method=response.request.method,
                status=response.status,
                failed=response.status >= 400,
            ))

        def on_request_failed(request):
            failure = request.failure
            self.network_requests.append(NetworkRequest(
                url=request.url,
                method=request.method,
                failed=True,
                failure_reason=failure.error_text if failure else "Unknown",
            ))

        page.on("console", on_console)
        page.on("pageerror", on_page_error)
        page.on("response", on_response)
        page.on("requestfailed", on_request_failed)

    def add_ai_verification(self, verification: AIVerification):
        """Record an AI verification result."""
        self.ai_verifications.append(verification)

    def save_screenshot(self, name: str, data: bytes) -> str:
        """Save a screenshot with deduplication."""
        hash_val = hashlib.sha256(data).hexdigest()[:16]
        if hash_val in self._screenshot_cache:
            return self._screenshot_cache[hash_val]
        self.screenshots[name] = data
        self._screenshot_cache[hash_val] = name
        return name

    def is_screenshot_cached(self, data: bytes) -> bool:
        """Check if we've seen this exact screenshot before."""
        hash_val = hashlib.sha256(data).hexdigest()[:16]
        return hash_val in self._screenshot_cache

    def get_screenshot_hash(self, data: bytes) -> str:
        """Get hash for a screenshot."""
        return hashlib.sha256(data).hexdigest()[:16]

    @property
    def errors(self) -> List[str]:
        """Get all error messages."""
        console_errors = [
            log.text for log in self.console_logs
            if log.level == LogLevel.ERROR
        ]
        return console_errors + self.page_errors

    @property
    def warnings(self) -> List[str]:
        """Get all warning messages."""
        return [
            log.text for log in self.console_logs
            if log.level == LogLevel.WARNING
        ]

    @property
    def network_errors(self) -> List[NetworkRequest]:
        """Get all failed network requests."""
        return [req for req in self.network_requests if req.failed]

    def has_critical_errors(self) -> bool:
        """Check if any critical errors occurred."""
        all_errors = " ".join(self.errors)
        return any(pattern in all_errors for pattern in self.CRITICAL_PATTERNS)

    def get_critical_errors(self) -> List[str]:
        """Get list of critical errors."""
        critical = []
        for error in self.errors:
            if any(pattern in error for pattern in self.CRITICAL_PATTERNS):
                critical.append(error)
        return critical

    def summary(self) -> Dict[str, Any]:
        """Generate summary statistics."""
        return {
            "console_logs": len(self.console_logs),
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "network_requests": len(self.network_requests),
            "network_errors": len(self.network_errors),
            "page_errors": len(self.page_errors),
            "ai_verifications": len(self.ai_verifications),
            "ai_passes": sum(1 for v in self.ai_verifications if v.result),
            "ai_failures": sum(1 for v in self.ai_verifications if not v.result),
            "has_critical_errors": self.has_critical_errors(),
            "screenshots_saved": len(self.screenshots),
        }

    def generate_report(self) -> str:
        """Generate a detailed text report."""
        lines = [
            "=" * 60,
            "TESTSCOUT E2E REPORT",
            "=" * 60,
            "",
            f"Generated: {datetime.now().isoformat()}",
            "",
        ]

        # Summary
        s = self.summary()
        lines.extend([
            f"Console Logs: {s['console_logs']}",
            f"Errors: {s['errors']}",
            f"Warnings: {s['warnings']}",
            f"Network Errors: {s['network_errors']}",
            f"AI Verifications: {s['ai_verifications']} ({s['ai_passes']} pass, {s['ai_failures']} fail)",
            "",
        ])

        # Critical errors
        critical = self.get_critical_errors()
        if critical:
            lines.extend([
                "--- CRITICAL ERRORS ---",
                *[f"  - {e[:200]}" for e in critical[:10]],
                "",
            ])

        # All errors
        if self.errors:
            lines.extend([
                "--- ERRORS (F12 Console) ---",
                *[f"  - {e[:200]}" for e in self.errors[:20]],
                "",
            ])

        # Warnings
        if self.warnings:
            lines.extend([
                "--- WARNINGS (F12 Console) ---",
                *[f"  - {w[:200]}" for w in self.warnings[:10]],
                "",
            ])

        # Network errors
        if self.network_errors:
            lines.extend([
                "--- NETWORK ERRORS ---",
                *[f"  - {r.status or 'FAIL'} {r.method} {r.url[:100]}"
                  for r in self.network_errors[:10]],
                "",
            ])

        # AI verifications
        if self.ai_verifications:
            lines.extend([
                "--- AI VERIFICATIONS ---",
            ])
            for v in self.ai_verifications:
                status = "PASS" if v.result else "FAIL"
                lines.append(f"  [{status}] {v.action_type}: {v.description[:80]}")
                if v.reason:
                    lines.append(f"         Reason: {v.reason[:100]}")
            lines.append("")

        # Full console log
        if self.console_logs:
            lines.extend([
                "--- FULL CONSOLE LOG (F12) ---",
            ])
            for log in self.console_logs[-50:]:  # Last 50 logs
                lines.append(f"  [{log.level.value.upper()}] {log.text[:150]}")
            lines.append("")

        return "\n".join(lines)

    def save_report(self, filepath: str):
        """Save report to file."""
        report = self.generate_report()
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            f.write(report)

    def save_screenshots(self, directory: str):
        """Save all screenshots to a directory."""
        dir_path = Path(directory)
        dir_path.mkdir(parents=True, exist_ok=True)
        for name, data in self.screenshots.items():
            filepath = dir_path / f"{name}.png"
            with open(filepath, "wb") as f:
                f.write(data)

    def reset(self):
        """Clear all captured data."""
        self.console_logs.clear()
        self.network_requests.clear()
        self.page_errors.clear()
        self.ai_verifications.clear()
        self.screenshots.clear()
        self._screenshot_cache.clear()
