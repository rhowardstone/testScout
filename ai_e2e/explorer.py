"""
Autonomous QA Explorer - AI-Powered Bug Hunter

An intelligent agent that autonomously explores web applications,
clicking buttons, filling forms, and detecting bugs without
any pre-written test scripts.

Features:
- Autonomous navigation: AI decides what to click next
- State tracking: Avoids infinite loops, remembers visited pages
- Bug detection: Console errors, network failures, broken UI, mock data
- Smart prioritization: Focuses on important/visible elements first
- Comprehensive reporting: Screenshots, context, reproduction steps

Usage:
    from ai_e2e import Explorer

    explorer = Explorer(page, api_key="...")
    report = explorer.explore(
        start_url="http://localhost:8888",
        max_actions=50,
        max_time=300,  # 5 minutes
    )
    report.save("exploration_report.html")
"""

import base64
import json
import time
import hashlib
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Set, Tuple
from datetime import datetime
from enum import Enum
from pathlib import Path

from .agent import Scout, ActionType
from .context import Context, LogLevel


class BugSeverity(Enum):
    CRITICAL = "critical"  # App crash, JS exception, 500 error
    HIGH = "high"          # Feature doesn't work, broken UI
    MEDIUM = "medium"      # Console error, slow response
    LOW = "low"            # Warning, minor UI issue
    INFO = "info"          # Observation, potential issue


@dataclass
class Bug:
    """A discovered bug or issue."""
    severity: BugSeverity
    title: str
    description: str
    reproduction_steps: List[str]
    url: str
    screenshot: Optional[bytes] = None
    console_errors: List[str] = field(default_factory=list)
    network_errors: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    element_context: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "reproduction_steps": self.reproduction_steps,
            "url": self.url,
            "console_errors": self.console_errors,
            "network_errors": self.network_errors,
            "timestamp": self.timestamp.isoformat(),
            "element_context": self.element_context,
        }


@dataclass
class ExplorationState:
    """Tracks the exploration state to avoid loops."""
    visited_urls: Set[str] = field(default_factory=set)
    clicked_elements: Set[str] = field(default_factory=set)  # hash of element + url
    page_states: Dict[str, str] = field(default_factory=dict)  # url -> dom_hash
    action_history: List[str] = field(default_factory=list)
    current_depth: int = 0
    start_url: str = ""

    def element_key(self, url: str, element_desc: str) -> str:
        """Create unique key for an element on a page."""
        return hashlib.md5(f"{url}:{element_desc}".encode()).hexdigest()

    def has_visited_element(self, url: str, element_desc: str) -> bool:
        return self.element_key(url, element_desc) in self.clicked_elements

    def mark_element_visited(self, url: str, element_desc: str):
        self.clicked_elements.add(self.element_key(url, element_desc))

    def add_action(self, action: str):
        self.action_history.append(action)


@dataclass
class ExplorationReport:
    """Complete report of an exploration session."""
    start_url: str
    bugs: List[Bug] = field(default_factory=list)
    pages_visited: int = 0
    actions_taken: int = 0
    duration_seconds: float = 0
    coverage_summary: Dict[str, int] = field(default_factory=dict)
    ai_observations: List[str] = field(default_factory=list)
    screenshots: Dict[str, bytes] = field(default_factory=dict)

    def add_bug(self, bug: Bug):
        self.bugs.append(bug)

    def summary(self) -> str:
        critical = sum(1 for b in self.bugs if b.severity == BugSeverity.CRITICAL)
        high = sum(1 for b in self.bugs if b.severity == BugSeverity.HIGH)
        medium = sum(1 for b in self.bugs if b.severity == BugSeverity.MEDIUM)
        low = sum(1 for b in self.bugs if b.severity == BugSeverity.LOW)

        return f"""
EXPLORATION REPORT
==================
URL: {self.start_url}
Duration: {self.duration_seconds:.1f}s
Pages Visited: {self.pages_visited}
Actions Taken: {self.actions_taken}

BUGS FOUND: {len(self.bugs)}
  Critical: {critical}
  High: {high}
  Medium: {medium}
  Low: {low}
"""

    def to_html(self) -> str:
        """Generate HTML report."""
        bug_rows = []
        for i, bug in enumerate(self.bugs):
            steps = "<br>".join(f"{j+1}. {s}" for j, s in enumerate(bug.reproduction_steps))
            errors = "<br>".join(bug.console_errors[:5]) if bug.console_errors else "None"

            severity_color = {
                BugSeverity.CRITICAL: "#dc2626",
                BugSeverity.HIGH: "#ea580c",
                BugSeverity.MEDIUM: "#ca8a04",
                BugSeverity.LOW: "#16a34a",
                BugSeverity.INFO: "#6b7280",
            }.get(bug.severity, "#6b7280")

            bug_rows.append(f"""
            <tr>
                <td><span style="background:{severity_color};color:white;padding:2px 8px;border-radius:4px">{bug.severity.value.upper()}</span></td>
                <td><strong>{bug.title}</strong><br><small>{bug.description}</small></td>
                <td><small>{steps}</small></td>
                <td><small style="color:#dc2626">{errors}</small></td>
            </tr>
            """)

        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>TestScout Exploration Report</title>
    <style>
        body {{ font-family: system-ui, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        h1 {{ color: #1f2937; }}
        .summary {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 20px 0; }}
        .stat {{ background: #f3f4f6; padding: 20px; border-radius: 8px; text-align: center; }}
        .stat-value {{ font-size: 2em; font-weight: bold; color: #4f46e5; }}
        .stat-label {{ color: #6b7280; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e5e7eb; }}
        th {{ background: #f9fafb; }}
        .observations {{ background: #fef3c7; padding: 20px; border-radius: 8px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 TestScout Exploration Report</h1>
        <p>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        <p>Start URL: <a href="{self.start_url}">{self.start_url}</a></p>

        <div class="summary">
            <div class="stat">
                <div class="stat-value">{len(self.bugs)}</div>
                <div class="stat-label">Bugs Found</div>
            </div>
            <div class="stat">
                <div class="stat-value">{self.pages_visited}</div>
                <div class="stat-label">Pages Visited</div>
            </div>
            <div class="stat">
                <div class="stat-value">{self.actions_taken}</div>
                <div class="stat-label">Actions Taken</div>
            </div>
            <div class="stat">
                <div class="stat-value">{self.duration_seconds:.0f}s</div>
                <div class="stat-label">Duration</div>
            </div>
        </div>

        <h2>🐛 Bugs Found</h2>
        <table>
            <tr>
                <th>Severity</th>
                <th>Issue</th>
                <th>Reproduction Steps</th>
                <th>Errors</th>
            </tr>
            {"".join(bug_rows) if bug_rows else "<tr><td colspan='4'>No bugs found! 🎉</td></tr>"}
        </table>

        {f'''
        <div class="observations">
            <h3>🤖 AI Observations</h3>
            <ul>
                {"".join(f"<li>{obs}</li>" for obs in self.ai_observations)}
            </ul>
        </div>
        ''' if self.ai_observations else ""}
    </div>
</body>
</html>
"""

    def save(self, filepath: str):
        """Save report to file."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        if filepath.endswith(".html"):
            with open(filepath, "w") as f:
                f.write(self.to_html())
        elif filepath.endswith(".json"):
            with open(filepath, "w") as f:
                json.dump({
                    "start_url": self.start_url,
                    "bugs": [b.to_dict() for b in self.bugs],
                    "pages_visited": self.pages_visited,
                    "actions_taken": self.actions_taken,
                    "duration_seconds": self.duration_seconds,
                    "ai_observations": self.ai_observations,
                }, f, indent=2)
        else:
            with open(filepath, "w") as f:
                f.write(self.summary())
                f.write("\n\nBUGS:\n")
                for bug in self.bugs:
                    f.write(f"\n[{bug.severity.value.upper()}] {bug.title}\n")
                    f.write(f"  {bug.description}\n")
                    f.write(f"  Steps: {' -> '.join(bug.reproduction_steps)}\n")


class Explorer:
    """
    Autonomous QA Agent that explores web applications to find bugs.

    The Explorer:
    1. Starts at a URL and autonomously navigates
    2. Clicks buttons, fills forms, explores menus
    3. Detects JS errors, network failures, broken UI
    4. Reports bugs with reproduction steps

    Usage:
        explorer = Explorer(page, api_key="...")
        report = explorer.explore("http://localhost:8888", max_actions=100)
        print(report.summary())
        report.save("report.html")
    """

    EXPLORE_PROMPT = """You are an autonomous QA engineer exploring a web application.

CURRENT PAGE: {url}
ALREADY CLICKED (avoid these): {clicked}

AVAILABLE ELEMENTS:
{elements}

Your goal is to find BUGS by:
1. Clicking buttons that might reveal broken features
2. Testing forms and inputs
3. Exploring all navigation menus
4. Looking for error states
5. Finding mock/placeholder data that should be real

Choose the MOST INTERESTING element to click next - something that:
- Hasn't been tested yet
- Might reveal bugs
- Is a core feature (not just styling)

If you see any BUGS or ISSUES on the current page, describe them.

Return JSON:
{{
    "next_action": {{
        "action": "click" | "fill" | "scroll" | "done",
        "element_id": <number or null>,
        "text": "<text to fill or null>",
        "reason": "why this action"
    }},
    "bugs_found": [
        {{
            "severity": "critical" | "high" | "medium" | "low" | "info",
            "title": "short title",
            "description": "what's wrong"
        }}
    ],
    "observations": ["interesting things noticed"]
}}
"""

    def __init__(
        self,
        page,
        api_key: Optional[str] = None,
        backend_type: str = "gemini",
        context: Optional[Context] = None,
    ):
        self.page = page
        self.context = context or Context()
        self.context.attach_to_page(page)
        self.scout = Scout(
            page,
            api_key=api_key,
            backend_type=backend_type,
            context=self.context,
        )
        self.state = ExplorationState()
        self.report = ExplorationReport(start_url="")

    def explore(
        self,
        start_url: str,
        max_actions: int = 50,
        max_time: float = 300,
        max_depth: int = 5,
    ) -> ExplorationReport:
        """
        Autonomously explore the application starting from a URL.

        Args:
            start_url: Where to start exploring
            max_actions: Maximum number of actions to take
            max_time: Maximum time in seconds
            max_depth: How many pages deep to go from start

        Returns:
            ExplorationReport with all findings
        """
        start_time = time.time()
        self.state = ExplorationState()
        self.state.start_url = start_url
        self.report = ExplorationReport(start_url=start_url)

        # Navigate to start
        self.page.goto(start_url)
        time.sleep(1)  # Let page settle
        self.state.visited_urls.add(start_url)
        self.report.pages_visited = 1

        action_count = 0

        while action_count < max_actions:
            elapsed = time.time() - start_time
            if elapsed > max_time:
                self.report.ai_observations.append(f"Stopped: time limit ({max_time}s) reached")
                break

            # Check for bugs on current page
            self._check_for_bugs()

            # Get AI's decision for next action
            decision = self._get_next_action()

            if decision is None:
                self.report.ai_observations.append("AI could not decide next action")
                break

            # Record any bugs AI found
            for bug_data in decision.get("bugs_found", []):
                self._record_bug(bug_data)

            # Record observations
            for obs in decision.get("observations", []):
                if obs not in self.report.ai_observations:
                    self.report.ai_observations.append(obs)

            # Execute the action
            next_action = decision.get("next_action", {})
            action_type = next_action.get("action", "done")

            if action_type == "done":
                self.report.ai_observations.append("AI decided exploration is complete")
                break

            success = self._execute_exploration_action(next_action)
            action_count += 1
            self.report.actions_taken = action_count

            if success:
                self.state.add_action(next_action.get("reason", "unknown"))

            # Check if we navigated to a new page
            current_url = self.page.url
            if current_url not in self.state.visited_urls:
                self.state.visited_urls.add(current_url)
                self.report.pages_visited += 1

            # Small delay between actions
            time.sleep(0.5)

        self.report.duration_seconds = time.time() - start_time
        return self.report

    def _check_for_bugs(self):
        """Check current page state for bugs."""
        # Check context for console errors
        if self.context.has_critical_errors():
            for error in self.context.get_critical_errors():
                self.report.add_bug(Bug(
                    severity=BugSeverity.CRITICAL,
                    title="JavaScript Error",
                    description=error[:200],
                    reproduction_steps=list(self.state.action_history[-5:]),
                    url=self.page.url,
                    console_errors=[error],
                ))

        # Check for network errors
        for req in self.context.network_errors:
            if req.status == 500:
                self.report.add_bug(Bug(
                    severity=BugSeverity.CRITICAL,
                    title=f"Server Error 500: {req.url[:50]}",
                    description=f"Backend returned 500 error for {req.method} {req.url}",
                    reproduction_steps=list(self.state.action_history[-5:]),
                    url=self.page.url,
                    network_errors=[f"{req.status} {req.method} {req.url}"],
                ))
            elif req.status and req.status >= 400:
                self.report.add_bug(Bug(
                    severity=BugSeverity.MEDIUM,
                    title=f"HTTP Error {req.status}",
                    description=f"Request failed: {req.method} {req.url}",
                    reproduction_steps=list(self.state.action_history[-5:]),
                    url=self.page.url,
                    network_errors=[f"{req.status} {req.method} {req.url}"],
                ))

    def _get_next_action(self) -> Optional[Dict[str, Any]]:
        """Ask AI what to do next."""
        try:
            # Get current elements
            elements = self.scout.discovery.discover()
            element_summary = elements.to_prompt_summary() if elements else "No elements"

            # Get screenshot
            screenshot_b64 = base64.b64encode(
                self.scout.discovery.screenshot_with_markers()
            ).decode("utf-8")

            # Build prompt
            clicked_summary = ", ".join(list(self.state.action_history[-10:])) or "None yet"

            prompt = self.EXPLORE_PROMPT.format(
                url=self.page.url,
                clicked=clicked_summary,
                elements=element_summary,
            )

            # Ask AI
            response = self.scout.backend.model.generate_content([
                prompt,
                {"mime_type": "image/png", "data": screenshot_b64},
            ])

            # Parse response
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()

            return json.loads(text)

        except Exception as e:
            self.report.ai_observations.append(f"AI error: {str(e)[:100]}")
            return None

    def _execute_exploration_action(self, action: Dict[str, Any]) -> bool:
        """Execute an exploration action."""
        action_type = action.get("action", "none")
        element_id = action.get("element_id")
        text = action.get("text")
        reason = action.get("reason", "")

        try:
            if action_type == "click" and element_id is not None:
                elements = self.scout.discovery.discover()
                element = elements.find_by_id(element_id)
                if element:
                    self.page.click(element.selector(), timeout=5000)
                    self.state.mark_element_visited(self.page.url, reason)
                    return True

            elif action_type == "fill" and element_id is not None and text:
                elements = self.scout.discovery.discover()
                element = elements.find_by_id(element_id)
                if element:
                    self.page.fill(element.selector(), text, timeout=5000)
                    return True

            elif action_type == "scroll":
                direction = action.get("direction", "down")
                delta = -300 if direction == "up" else 300
                self.page.mouse.wheel(0, delta)
                return True

        except Exception as e:
            # Action failed - might be a bug
            self.report.add_bug(Bug(
                severity=BugSeverity.MEDIUM,
                title=f"Action Failed: {action_type}",
                description=f"Could not {action_type}: {str(e)[:100]}",
                reproduction_steps=list(self.state.action_history[-5:]) + [reason],
                url=self.page.url,
            ))

        return False

    def _record_bug(self, bug_data: Dict[str, Any]):
        """Record a bug found by AI."""
        severity_map = {
            "critical": BugSeverity.CRITICAL,
            "high": BugSeverity.HIGH,
            "medium": BugSeverity.MEDIUM,
            "low": BugSeverity.LOW,
            "info": BugSeverity.INFO,
        }

        severity = severity_map.get(bug_data.get("severity", "info"), BugSeverity.INFO)

        # Take screenshot
        screenshot = None
        try:
            screenshot = self.page.screenshot()
        except:
            pass

        self.report.add_bug(Bug(
            severity=severity,
            title=bug_data.get("title", "Unknown Issue"),
            description=bug_data.get("description", ""),
            reproduction_steps=list(self.state.action_history[-5:]),
            url=self.page.url,
            screenshot=screenshot,
            console_errors=list(self.context.errors[-5:]),
        ))


def create_explorer(
    page,
    api_key: Optional[str] = None,
    backend_type: str = "gemini",
) -> Explorer:
    """
    Create an Explorer with sensible defaults.

    Will try to get API key from environment if not provided.
    """
    import os

    if not api_key:
        if backend_type == "gemini":
            api_key = os.environ.get("GEMINI_API_KEY")
        elif backend_type == "openai":
            api_key = os.environ.get("OPENAI_API_KEY")

    if not api_key:
        raise ValueError(
            f"No API key provided and {backend_type.upper()}_API_KEY not in environment"
        )

    return Explorer(page, api_key=api_key, backend_type=backend_type)
