"""
Audit Trail for Explorer - Complete auditability of AI exploration.

Captures every detail of an exploration session:
- Screenshots (clean and marked with set-of-marks)
- AI prompts and responses
- Element visibility data
- Decisions and reasoning
- Network activity
- Console logs

Directory structure:
    exploration_2024-11-29_153042/
    ├── summary.html              # Human-readable report
    ├── summary.json              # Machine-readable summary
    ├── timeline.jsonl            # Streaming event log
    ├── actions/
    │   ├── 001/
    │   │   ├── screenshot.png         # Clean screenshot before action
    │   │   ├── screenshot_marked.png  # Screenshot with set-of-marks overlay
    │   │   ├── visible_elements.json  # Elements AI could see
    │   │   ├── ai_prompt.txt          # Exact prompt sent to AI
    │   │   ├── ai_response.json       # Raw AI response
    │   │   ├── decision.json          # Parsed decision + reasoning
    │   │   └── state.json             # Page state (URL, depth, history)
    │   └── 002/
    │       └── ...
    ├── network/
    │   ├── requests.jsonl        # All network requests
    │   └── failures.jsonl        # Failed requests only
    ├── console/
    │   ├── all.jsonl             # All console messages
    │   ├── errors.jsonl          # Errors only
    │   └── warnings.jsonl        # Warnings only
    └── bugs/
        └── bug_001/
            ├── screenshot.png
            └── details.json
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ActionRecord:
    """Record of a single action during exploration."""

    action_number: int
    timestamp: datetime
    url: str

    # Screenshots
    screenshot_clean: Optional[bytes] = None
    screenshot_marked: Optional[bytes] = None

    # AI interaction
    ai_prompt: str = ""
    ai_response_raw: str = ""
    ai_response_parsed: Optional[Dict[str, Any]] = None

    # Elements visible to AI
    visible_elements: List[Dict[str, Any]] = field(default_factory=list)

    # Decision made
    decision: Optional[Dict[str, Any]] = None
    decision_reason: str = ""

    # State
    depth: int = 0
    action_history: List[str] = field(default_factory=list)

    # Execution result
    success: bool = False
    error: Optional[str] = None
    duration_ms: float = 0


@dataclass
class TimelineEvent:
    """A single event in the exploration timeline."""

    timestamp: datetime
    event_type: str  # "navigate", "action", "bug", "observation", "error"
    action_number: Optional[int] = None
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "action_number": self.action_number,
            **self.data,
        }


class AuditTrail:
    """
    Captures complete audit trail of an exploration session.

    Usage:
        audit = AuditTrail()
        audit.start_session(start_url)

        # For each action:
        audit.record_action_start(...)
        audit.record_ai_response(...)
        audit.record_action_complete(...)

        # Save everything:
        audit.save("./exploration_output")
    """

    def __init__(self):
        self.session_id: str = ""
        self.start_url: str = ""
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

        self.actions: List[ActionRecord] = []
        self.timeline: List[TimelineEvent] = []

        self.network_requests: List[Dict[str, Any]] = []
        self.network_failures: List[Dict[str, Any]] = []

        self.console_all: List[Dict[str, Any]] = []
        self.console_errors: List[Dict[str, Any]] = []
        self.console_warnings: List[Dict[str, Any]] = []

        self.bugs: List[Dict[str, Any]] = []

        self._current_action: Optional[ActionRecord] = None
        self._action_counter: int = 0

    def start_session(self, start_url: str):
        """Begin a new audit session."""
        self.start_time = datetime.now()
        self.session_id = self.start_time.strftime("%Y-%m-%d_%H%M%S")
        self.start_url = start_url

        self._add_timeline_event("session_start", {"url": start_url})

    def end_session(self):
        """End the audit session."""
        self.end_time = datetime.now()
        self._add_timeline_event(
            "session_end",
            {
                "duration_seconds": (self.end_time - self.start_time).total_seconds()
                if self.start_time
                else 0,
                "total_actions": len(self.actions),
                "total_bugs": len(self.bugs),
            },
        )

    def start_action(
        self,
        url: str,
        screenshot_clean: Optional[bytes] = None,
        screenshot_marked: Optional[bytes] = None,
        visible_elements: Optional[List[Dict[str, Any]]] = None,
        depth: int = 0,
        action_history: Optional[List[str]] = None,
    ) -> int:
        """
        Start recording a new action.

        Returns the action number for reference.
        """
        self._action_counter += 1
        action_num = self._action_counter

        self._current_action = ActionRecord(
            action_number=action_num,
            timestamp=datetime.now(),
            url=url,
            screenshot_clean=screenshot_clean,
            screenshot_marked=screenshot_marked,
            visible_elements=visible_elements or [],
            depth=depth,
            action_history=list(action_history or []),
        )

        self._add_timeline_event(
            "action_start",
            {"url": url, "depth": depth},
            action_number=action_num,
        )

        return action_num

    def record_ai_prompt(self, prompt: str):
        """Record the prompt sent to AI."""
        if self._current_action:
            self._current_action.ai_prompt = prompt

    def record_ai_response(self, raw_response: str, parsed_response: Optional[Dict[str, Any]]):
        """Record AI's response."""
        if self._current_action:
            self._current_action.ai_response_raw = raw_response
            self._current_action.ai_response_parsed = parsed_response

    def record_decision(self, decision: Dict[str, Any], reason: str = ""):
        """Record the decision made based on AI response."""
        if self._current_action:
            self._current_action.decision = decision
            self._current_action.decision_reason = reason

            self._add_timeline_event(
                "decision",
                {
                    "action_type": decision.get("action", "unknown"),
                    "element_id": decision.get("element_id"),
                    "reason": reason,
                },
                action_number=self._current_action.action_number,
            )

    def complete_action(self, success: bool, error: Optional[str] = None, duration_ms: float = 0):
        """Mark the current action as complete."""
        if self._current_action:
            self._current_action.success = success
            self._current_action.error = error
            self._current_action.duration_ms = duration_ms

            self.actions.append(self._current_action)

            self._add_timeline_event(
                "action_complete",
                {"success": success, "error": error, "duration_ms": duration_ms},
                action_number=self._current_action.action_number,
            )

            self._current_action = None

    def record_navigation(self, from_url: str, to_url: str):
        """Record page navigation."""
        self._add_timeline_event(
            "navigation",
            {"from_url": from_url, "to_url": to_url},
        )

    def record_bug(
        self,
        severity: str,
        title: str,
        description: str,
        reproduction_steps: List[str],
        url: str,
        screenshot: Optional[bytes] = None,
        console_errors: Optional[List[str]] = None,
        network_errors: Optional[List[str]] = None,
    ):
        """Record a discovered bug."""
        bug_number = len(self.bugs) + 1
        bug_data = {
            "bug_number": bug_number,
            "severity": severity,
            "title": title,
            "description": description,
            "reproduction_steps": reproduction_steps,
            "url": url,
            "screenshot": screenshot,  # Will be saved separately
            "console_errors": console_errors or [],
            "network_errors": network_errors or [],
            "timestamp": datetime.now().isoformat(),
            "action_number": self._current_action.action_number if self._current_action else None,
        }
        self.bugs.append(bug_data)

        self._add_timeline_event(
            "bug_found",
            {
                "bug_number": bug_number,
                "severity": severity,
                "title": title,
            },
        )

    def record_observation(self, observation: str):
        """Record an AI observation."""
        self._add_timeline_event(
            "observation",
            {"text": observation},
            action_number=self._current_action.action_number if self._current_action else None,
        )

    def record_network_request(
        self,
        url: str,
        method: str,
        status: Optional[int] = None,
        failed: bool = False,
        failure_reason: Optional[str] = None,
    ):
        """Record a network request."""
        request_data = {
            "url": url,
            "method": method,
            "status": status,
            "failed": failed,
            "failure_reason": failure_reason,
            "timestamp": datetime.now().isoformat(),
        }
        self.network_requests.append(request_data)

        if failed or (status and status >= 400):
            self.network_failures.append(request_data)

    def record_console_log(
        self,
        level: str,
        text: str,
        source: Optional[str] = None,
        line: Optional[int] = None,
    ):
        """Record a console log message."""
        log_data = {
            "level": level,
            "text": text,
            "source": source,
            "line": line,
            "timestamp": datetime.now().isoformat(),
        }
        self.console_all.append(log_data)

        if level == "error":
            self.console_errors.append(log_data)
        elif level in ("warning", "warn"):
            self.console_warnings.append(log_data)

    def _add_timeline_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        action_number: Optional[int] = None,
    ):
        """Add an event to the timeline."""
        self.timeline.append(
            TimelineEvent(
                timestamp=datetime.now(),
                event_type=event_type,
                action_number=action_number,
                data=data,
            )
        )

    def save(self, output_dir: str):
        """
        Save the complete audit trail to a directory.

        Args:
            output_dir: Directory to save to (will be created if needed).
                       Use None to auto-generate from session ID.
        """
        base_path = Path(output_dir)
        base_path.mkdir(parents=True, exist_ok=True)

        # Save summary files
        self._save_summary_json(base_path / "summary.json")
        self._save_summary_html(base_path / "summary.html")
        self._save_timeline(base_path / "timeline.jsonl")

        # Save action details
        actions_dir = base_path / "actions"
        for action in self.actions:
            self._save_action(actions_dir, action)

        # Save network logs
        network_dir = base_path / "network"
        network_dir.mkdir(parents=True, exist_ok=True)
        self._save_jsonl(network_dir / "requests.jsonl", self.network_requests)
        self._save_jsonl(network_dir / "failures.jsonl", self.network_failures)

        # Save console logs
        console_dir = base_path / "console"
        console_dir.mkdir(parents=True, exist_ok=True)
        self._save_jsonl(console_dir / "all.jsonl", self.console_all)
        self._save_jsonl(console_dir / "errors.jsonl", self.console_errors)
        self._save_jsonl(console_dir / "warnings.jsonl", self.console_warnings)

        # Save bugs
        bugs_dir = base_path / "bugs"
        for bug in self.bugs:
            self._save_bug(bugs_dir, bug)

    def _save_action(self, actions_dir: Path, action: ActionRecord):
        """Save a single action's data."""
        action_dir = actions_dir / f"{action.action_number:03d}"
        action_dir.mkdir(parents=True, exist_ok=True)

        # Save screenshots
        if action.screenshot_clean:
            with open(action_dir / "screenshot.png", "wb") as f:
                f.write(action.screenshot_clean)

        if action.screenshot_marked:
            with open(action_dir / "screenshot_marked.png", "wb") as f:
                f.write(action.screenshot_marked)

        # Save visible elements
        with open(action_dir / "visible_elements.json", "w") as f:
            json.dump(action.visible_elements, f, indent=2)

        # Save AI prompt
        with open(action_dir / "ai_prompt.txt", "w") as f:
            f.write(action.ai_prompt)

        # Save AI response
        ai_response_data = {
            "raw": action.ai_response_raw,
            "parsed": action.ai_response_parsed,
        }
        with open(action_dir / "ai_response.json", "w") as f:
            json.dump(ai_response_data, f, indent=2)

        # Save decision
        decision_data = {
            "decision": action.decision,
            "reason": action.decision_reason,
            "success": action.success,
            "error": action.error,
            "duration_ms": action.duration_ms,
        }
        with open(action_dir / "decision.json", "w") as f:
            json.dump(decision_data, f, indent=2)

        # Save state
        state_data = {
            "action_number": action.action_number,
            "timestamp": action.timestamp.isoformat(),
            "url": action.url,
            "depth": action.depth,
            "action_history": action.action_history,
        }
        with open(action_dir / "state.json", "w") as f:
            json.dump(state_data, f, indent=2)

    def _save_bug(self, bugs_dir: Path, bug: Dict[str, Any]):
        """Save a single bug's data."""
        bug_dir = bugs_dir / f"bug_{bug['bug_number']:03d}"
        bug_dir.mkdir(parents=True, exist_ok=True)

        # Save screenshot if present
        screenshot = bug.pop("screenshot", None)
        if screenshot:
            with open(bug_dir / "screenshot.png", "wb") as f:
                f.write(screenshot)

        # Save details
        with open(bug_dir / "details.json", "w") as f:
            json.dump(bug, f, indent=2)

    def _save_summary_json(self, filepath: Path):
        """Save JSON summary."""
        summary = {
            "session_id": self.session_id,
            "start_url": self.start_url,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": (
                (self.end_time - self.start_time).total_seconds()
                if self.start_time and self.end_time
                else None
            ),
            "total_actions": len(self.actions),
            "successful_actions": sum(1 for a in self.actions if a.success),
            "failed_actions": sum(1 for a in self.actions if not a.success),
            "total_bugs": len(self.bugs),
            "bugs_by_severity": self._count_bugs_by_severity(),
            "network_requests": len(self.network_requests),
            "network_failures": len(self.network_failures),
            "console_errors": len(self.console_errors),
            "console_warnings": len(self.console_warnings),
        }
        with open(filepath, "w") as f:
            json.dump(summary, f, indent=2)

    def _save_summary_html(self, filepath: Path):
        """Save HTML summary report."""
        duration = (
            (self.end_time - self.start_time).total_seconds()
            if self.start_time and self.end_time
            else 0
        )
        bugs_by_severity = self._count_bugs_by_severity()

        # Build action timeline HTML
        action_rows = []
        for action in self.actions:
            status = "success" if action.success else "failed"
            status_color = "#22c55e" if action.success else "#ef4444"
            decision_type = (
                action.decision.get("action", "unknown") if action.decision else "unknown"
            )
            action_rows.append(
                f"""
                <tr>
                    <td>{action.action_number:03d}</td>
                    <td>{action.timestamp.strftime("%H:%M:%S")}</td>
                    <td>{decision_type}</td>
                    <td>{action.decision_reason[:50] if action.decision_reason else ""}...</td>
                    <td style="color: {status_color}">{status}</td>
                    <td><a href="actions/{action.action_number:03d}/">View</a></td>
                </tr>
            """
            )

        # Build bug rows
        bug_rows = []
        for bug in self.bugs:
            severity = bug.get("severity", "info")
            severity_colors = {
                "critical": "#dc2626",
                "high": "#ea580c",
                "medium": "#ca8a04",
                "low": "#16a34a",
                "info": "#6b7280",
            }
            color = severity_colors.get(severity, "#6b7280")
            bug_rows.append(
                f"""
                <tr>
                    <td><span style="background:{color};color:white;padding:2px 8px;border-radius:4px">{severity.upper()}</span></td>
                    <td>{bug.get("title", "Unknown")}</td>
                    <td>{bug.get("description", "")[:100]}...</td>
                    <td><a href="bugs/bug_{bug['bug_number']:03d}/">View</a></td>
                </tr>
            """
            )

        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>TestScout Audit Trail - {self.session_id}</title>
    <style>
        body {{ font-family: system-ui, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        .card {{ background: white; padding: 24px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin-bottom: 24px; }}
        h1 {{ color: #1f2937; margin: 0 0 8px 0; }}
        h2 {{ color: #374151; margin: 24px 0 16px 0; }}
        .subtitle {{ color: #6b7280; margin-bottom: 24px; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; margin: 24px 0; }}
        .stat {{ background: #f9fafb; padding: 16px; border-radius: 8px; text-align: center; }}
        .stat-value {{ font-size: 2em; font-weight: bold; color: #4f46e5; }}
        .stat-label {{ color: #6b7280; font-size: 0.9em; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e5e7eb; }}
        th {{ background: #f9fafb; font-weight: 600; }}
        a {{ color: #4f46e5; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .severity-critical {{ background: #dc2626; }}
        .severity-high {{ background: #ea580c; }}
        .severity-medium {{ background: #ca8a04; }}
        .severity-low {{ background: #16a34a; }}
        .severity-info {{ background: #6b7280; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>TestScout Audit Trail</h1>
            <p class="subtitle">
                Session: {self.session_id}<br>
                URL: <a href="{self.start_url}">{self.start_url}</a><br>
                Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            </p>

            <div class="stats">
                <div class="stat">
                    <div class="stat-value">{len(self.actions)}</div>
                    <div class="stat-label">Actions Taken</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{len(self.bugs)}</div>
                    <div class="stat-label">Bugs Found</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{duration:.0f}s</div>
                    <div class="stat-label">Duration</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{len(self.network_failures)}</div>
                    <div class="stat-label">Network Errors</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{len(self.console_errors)}</div>
                    <div class="stat-label">Console Errors</div>
                </div>
            </div>

            <div class="stats">
                <div class="stat">
                    <div class="stat-value" style="color: #dc2626">{bugs_by_severity.get("critical", 0)}</div>
                    <div class="stat-label">Critical</div>
                </div>
                <div class="stat">
                    <div class="stat-value" style="color: #ea580c">{bugs_by_severity.get("high", 0)}</div>
                    <div class="stat-label">High</div>
                </div>
                <div class="stat">
                    <div class="stat-value" style="color: #ca8a04">{bugs_by_severity.get("medium", 0)}</div>
                    <div class="stat-label">Medium</div>
                </div>
                <div class="stat">
                    <div class="stat-value" style="color: #16a34a">{bugs_by_severity.get("low", 0)}</div>
                    <div class="stat-label">Low</div>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>Bugs Found</h2>
            <table>
                <tr>
                    <th>Severity</th>
                    <th>Title</th>
                    <th>Description</th>
                    <th>Details</th>
                </tr>
                {"".join(bug_rows) if bug_rows else "<tr><td colspan='4'>No bugs found</td></tr>"}
            </table>
        </div>

        <div class="card">
            <h2>Action Timeline</h2>
            <table>
                <tr>
                    <th>#</th>
                    <th>Time</th>
                    <th>Action</th>
                    <th>Reason</th>
                    <th>Result</th>
                    <th>Details</th>
                </tr>
                {"".join(action_rows) if action_rows else "<tr><td colspan='6'>No actions taken</td></tr>"}
            </table>
        </div>

        <div class="card">
            <h2>Files</h2>
            <ul>
                <li><a href="summary.json">summary.json</a> - Machine-readable summary</li>
                <li><a href="timeline.jsonl">timeline.jsonl</a> - Full event timeline</li>
                <li><a href="network/">network/</a> - Network request logs</li>
                <li><a href="console/">console/</a> - Console output logs</li>
                <li><a href="actions/">actions/</a> - Per-action details with screenshots</li>
                <li><a href="bugs/">bugs/</a> - Bug details with screenshots</li>
            </ul>
        </div>
    </div>
</body>
</html>
"""
        with open(filepath, "w") as f:
            f.write(html)

    def _save_timeline(self, filepath: Path):
        """Save timeline as JSONL."""
        with open(filepath, "w") as f:
            for event in self.timeline:
                f.write(json.dumps(event.to_dict()) + "\n")

    def _save_jsonl(self, filepath: Path, data: List[Dict[str, Any]]):
        """Save a list of dicts as JSONL."""
        with open(filepath, "w") as f:
            for item in data:
                f.write(json.dumps(item) + "\n")

    def _count_bugs_by_severity(self) -> Dict[str, int]:
        """Count bugs grouped by severity."""
        counts: Dict[str, int] = {}
        for bug in self.bugs:
            severity = bug.get("severity", "info")
            counts[severity] = counts.get(severity, 0) + 1
        return counts
