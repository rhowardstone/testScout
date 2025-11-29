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
import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .agent import Scout
from .audit import AuditTrail
from .context import Context


class BugSeverity(Enum):
    CRITICAL = "critical"  # App crash, JS exception, 500 error
    HIGH = "high"  # Feature doesn't work, broken UI
    MEDIUM = "medium"  # Console error, slow response
    LOW = "low"  # Warning, minor UI issue
    INFO = "info"  # Observation, potential issue


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
            steps = "<br>".join(f"{j + 1}. {s}" for j, s in enumerate(bug.reproduction_steps))
            errors = "<br>".join(bug.console_errors[:5]) if bug.console_errors else "None"

            severity_color = {
                BugSeverity.CRITICAL: "#dc2626",
                BugSeverity.HIGH: "#ea580c",
                BugSeverity.MEDIUM: "#ca8a04",
                BugSeverity.LOW: "#16a34a",
                BugSeverity.INFO: "#6b7280",
            }.get(bug.severity, "#6b7280")

            bug_rows.append(
                f"""
            <tr>
                <td><span style="background:{severity_color};color:white;padding:2px 8px;border-radius:4px">{bug.severity.value.upper()}</span></td>
                <td><strong>{bug.title}</strong><br><small>{bug.description}</small></td>
                <td><small>{steps}</small></td>
                <td><small style="color:#dc2626">{errors}</small></td>
            </tr>
            """
            )

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

        {
            f'''
        <div class="observations">
            <h3>🤖 AI Observations</h3>
            <ul>
                {"".join(f"<li>{obs}</li>" for obs in self.ai_observations)}
            </ul>
        </div>
        '''
            if self.ai_observations
            else ""
        }
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
                json.dump(
                    {
                        "start_url": self.start_url,
                        "bugs": [b.to_dict() for b in self.bugs],
                        "pages_visited": self.pages_visited,
                        "actions_taken": self.actions_taken,
                        "duration_seconds": self.duration_seconds,
                        "ai_observations": self.ai_observations,
                    },
                    f,
                    indent=2,
                )
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

    EXPLORE_PROMPT = """You are an autonomous QA engineer exploring a web application as a BRAND NEW USER.

CURRENT PAGE: {url}
ALREADY CLICKED (avoid these): {clicked}

AVAILABLE ELEMENTS:
{elements}

CRITICAL RULES FOR AUTHENTICATION:
- You are a NEW user with NO existing account. The database has no record of you.
- SIGN UP vs SIGN IN: These are DIFFERENT pages. Look at form fields carefully:
  - SIGN UP page: Has "confirm password" field, "create account" button, register/signup in URL
  - SIGN IN page: Only email+password, "login"/"signin" button, login/signin in URL
- When you see a sign-up form, CREATE a new account with test data
- NEVER try to sign in with credentials that don't exist - you haven't created them yet!
- Proper flow: Sign Up first → Create Account → Then you CAN sign in

Your goal is to find BUGS by:
1. Clicking buttons that might reveal broken features
2. Testing forms and inputs with APPROPRIATE test data
3. Exploring all navigation menus
4. Looking for error states
5. Finding mock/placeholder data that should be real

Choose the MOST INTERESTING element to click next - something that:
- Hasn't been tested yet
- Might reveal bugs
- Is a core feature (not just styling)

When filling forms, use sensible test data:
- Email: test@example.com or testuser@test.com
- Password: TestPassword123!
- Name: Test User
- Use data appropriate for the FORM TYPE (sign-up vs sign-in vs search)

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
        enable_audit: bool = True,
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

        # Audit trail for complete exploration history
        self.enable_audit = enable_audit
        self.audit = AuditTrail() if enable_audit else None

    def explore(
        self,
        start_url: str,
        max_actions: int = 50,
        max_time: float = 300,
        max_depth: int = 5,
        wait_for_selector: Optional[str] = None,
        wait_timeout: float = 15.0,
        app_ready_check: Optional[str] = None,
    ) -> ExplorationReport:
        """
        Autonomously explore the application starting from a URL.

        Args:
            start_url: Where to start exploring
            max_actions: Maximum number of actions to take
            max_time: Maximum time in seconds
            max_depth: How many pages deep to go from start
            wait_for_selector: CSS selector to wait for before starting (e.g., "#root", ".app-loaded")
            wait_timeout: How long to wait for page/selector in seconds
            app_ready_check: JavaScript expression that returns true when app is ready
                            (e.g., 'document.querySelector("#root")?.innerHTML?.length > 100')

        Returns:
            ExplorationReport with all findings
        """
        start_time = time.time()
        self.state = ExplorationState()
        self.state.start_url = start_url
        self.report = ExplorationReport(start_url=start_url)

        # Start audit session
        if self.audit:
            self.audit.start_session(start_url)

        # Navigate to start with network idle wait
        try:
            self.page.goto(start_url, wait_until="networkidle", timeout=int(wait_timeout * 1000))
        except Exception as e:
            self.report.ai_observations.append(f"Navigation warning: {str(e)[:100]}")
            # Try simpler navigation
            try:
                self.page.goto(start_url, timeout=int(wait_timeout * 1000))
            except Exception as e2:
                self.report.add_bug(
                    Bug(
                        severity=BugSeverity.CRITICAL,
                        title="Failed to load page",
                        description=f"Could not navigate to {start_url}: {str(e2)[:200]}",
                        reproduction_steps=[f"Navigate to {start_url}"],
                        url=start_url,
                    )
                )
                return self.report

        # Wait for specific selector if provided (for SPA frameworks)
        if wait_for_selector:
            try:
                self.page.wait_for_selector(wait_for_selector, timeout=int(wait_timeout * 1000))
            except Exception:
                self.report.ai_observations.append(
                    f"Selector '{wait_for_selector}' not found within {wait_timeout}s - app may not have loaded"
                )

        # Wait for app ready check (JavaScript condition)
        if app_ready_check:
            try:
                self.page.wait_for_function(app_ready_check, timeout=int(wait_timeout * 1000))
            except Exception:
                self.report.ai_observations.append(
                    f"App ready check failed: {app_ready_check[:50]}... - app may not have initialized"
                )

        # Additional settle time for JavaScript frameworks
        time.sleep(2)

        # Pre-flight blank page detection
        blank_page_issue = self._detect_blank_page()
        if blank_page_issue:
            self.report.add_bug(blank_page_issue)
            # Still continue exploring to capture any console errors

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
                    if self.audit:
                        self.audit.record_observation(obs)

            # Execute the action
            next_action = decision.get("next_action", {})
            action_type = next_action.get("action", "done")
            action_reason = next_action.get("reason", "")

            # Record decision in audit
            if self.audit:
                self.audit.record_decision(next_action, action_reason)

            if action_type == "done":
                self.report.ai_observations.append("AI decided exploration is complete")
                # Complete the audit action
                if self.audit:
                    self.audit.complete_action(success=True, duration_ms=0)
                break

            action_exec_start = time.time()
            success = self._execute_exploration_action(next_action)
            action_duration_ms = (time.time() - action_exec_start) * 1000
            action_count += 1
            self.report.actions_taken = action_count

            # Complete the audit action
            if self.audit:
                self.audit.complete_action(success=success, duration_ms=action_duration_ms)

            # Action history is now updated inside _execute_exploration_action
            # with the actual element description instead of the AI's reason

            # Check if we navigated to a new page
            current_url = self.page.url
            if current_url not in self.state.visited_urls:
                self.state.visited_urls.add(current_url)
                self.report.pages_visited += 1

            # Small delay between actions
            time.sleep(0.5)

        self.report.duration_seconds = time.time() - start_time

        # End audit session and capture final context
        if self.audit:
            self.audit.end_session()
            # Capture network and console logs from context
            for req in self.context.network_requests:
                self.audit.record_network_request(
                    url=req.url,
                    method=req.method,
                    status=req.status,
                    failed=req.failed,
                    failure_reason=req.failure_reason,
                )
            for log in self.context.console_logs:
                self.audit.record_console_log(
                    level=log.level.value,
                    text=log.text,
                    source=log.source,
                    line=log.line,
                )

        return self.report

    def save_audit(self, output_dir: str):
        """
        Save the complete audit trail to a directory.

        Creates a directory with:
        - summary.html/json - Overview
        - timeline.jsonl - Event timeline
        - actions/NNN/ - Per-action details with screenshots
        - network/ - Network request logs
        - console/ - Console output logs
        - bugs/ - Bug details with screenshots

        Args:
            output_dir: Path to save audit trail. If None, auto-generates
                       name like 'exploration_2024-11-29_153042/'
        """
        if not self.audit:
            raise ValueError("Audit trail not enabled. Set enable_audit=True when creating Explorer.")

        self.audit.save(output_dir)

    def _detect_blank_page(self) -> Optional[Bug]:
        """
        Detect if the page is blank/empty (JavaScript didn't execute).

        This catches common issues like:
        - React/Vue/Angular apps that failed to hydrate
        - JavaScript errors that prevented rendering
        - Headless browser compatibility issues

        Returns a Bug if blank page detected, None otherwise.
        """
        try:
            # Check multiple indicators of a blank page
            checks = []

            # Check 1: Body has minimal content
            body_length = self.page.evaluate("document.body?.innerHTML?.length || 0")
            checks.append(("body_content", body_length > 100))

            # Check 2: Check for common SPA root elements with content
            root_selectors = ["#root", "#app", "#__next", ".app", "[data-reactroot]"]
            has_spa_content = False
            for selector in root_selectors:
                try:
                    content_length = self.page.evaluate(
                        f'document.querySelector("{selector}")?.innerHTML?.length || 0'
                    )
                    if content_length > 50:
                        has_spa_content = True
                        break
                except Exception:
                    pass
            checks.append(("spa_root_content", has_spa_content))

            # Check 3: Page has visible text content
            visible_text_length = self.page.evaluate(
                "document.body?.innerText?.trim()?.length || 0"
            )
            checks.append(("visible_text", visible_text_length > 20))

            # Check 4: Page has interactive elements
            interactive_count = self.page.evaluate(
                """
                document.querySelectorAll('button, a, input, select, [role="button"]').length
            """
            )
            checks.append(("interactive_elements", interactive_count > 0))

            # If most checks fail, it's likely a blank page
            passed = sum(1 for _, result in checks if result)

            if passed <= 1:  # Only 0-1 checks passed = definitely blank
                # Gather diagnostic info
                diagnostics = []
                for name, result in checks:
                    diagnostics.append(f"{name}: {'PASS' if result else 'FAIL'}")

                # Check for console errors that might explain why
                console_errors = list(self.context.errors[-5:]) if self.context.errors else []

                description = (
                    f"The page appears to be blank or failed to render. "
                    f"This usually means JavaScript didn't execute properly. "
                    f"Diagnostics: {', '.join(diagnostics)}. "
                    f"Possible causes: JS errors, missing dependencies, CORS issues, "
                    f"or headless browser compatibility problems."
                )

                return Bug(
                    severity=BugSeverity.CRITICAL,
                    title="Blank page - application failed to render",
                    description=description,
                    reproduction_steps=[f"Navigate to {self.page.url}"],
                    url=self.page.url,
                    console_errors=console_errors,
                )

            return None

        except Exception as e:
            # If we can't even check, something is very wrong
            return Bug(
                severity=BugSeverity.CRITICAL,
                title="Page unresponsive",
                description=f"Could not inspect page state: {str(e)[:200]}",
                reproduction_steps=[f"Navigate to {self.page.url}"],
                url=self.page.url,
            )

    def _check_for_bugs(self):
        """Check current page state for bugs."""
        # Check context for console errors
        if self.context.has_critical_errors():
            for error in self.context.get_critical_errors():
                self.report.add_bug(
                    Bug(
                        severity=BugSeverity.CRITICAL,
                        title="JavaScript Error",
                        description=error[:200],
                        reproduction_steps=list(self.state.action_history[-5:]),
                        url=self.page.url,
                        console_errors=[error],
                    )
                )

        # Check for network errors
        for req in self.context.network_errors:
            if req.status == 500:
                self.report.add_bug(
                    Bug(
                        severity=BugSeverity.CRITICAL,
                        title=f"Server Error 500: {req.url[:50]}",
                        description=f"Backend returned 500 error for {req.method} {req.url}",
                        reproduction_steps=list(self.state.action_history[-5:]),
                        url=self.page.url,
                        network_errors=[f"{req.status} {req.method} {req.url}"],
                    )
                )
            elif req.status and req.status >= 400:
                self.report.add_bug(
                    Bug(
                        severity=BugSeverity.MEDIUM,
                        title=f"HTTP Error {req.status}",
                        description=f"Request failed: {req.method} {req.url}",
                        reproduction_steps=list(self.state.action_history[-5:]),
                        url=self.page.url,
                        network_errors=[f"{req.status} {req.method} {req.url}"],
                    )
                )

    def _get_next_action(self) -> Optional[Dict[str, Any]]:
        """Ask AI what to do next with retry logic for JSON parsing failures."""
        action_start_time = time.time()
        max_retries = 3

        try:
            # Get current elements
            elements = self.scout.discovery.discover()
            element_summary = elements.to_prompt_summary() if elements else "No elements"

            # Get screenshots (clean and marked)
            screenshot_marked = self.scout.discovery.screenshot_with_markers()
            screenshot_clean = self.page.screenshot()
            screenshot_b64 = base64.b64encode(screenshot_marked).decode("utf-8")

            # Build prompt - show clicked elements (e.g., "clicked button: Menu Toggle")
            clicked_summary = ", ".join(list(self.state.action_history[-10:])) or "None yet"

            prompt = self.EXPLORE_PROMPT.format(
                url=self.page.url,
                clicked=clicked_summary,
                elements=element_summary,
            )

            # Start audit action recording
            if self.audit:
                # Convert elements to serializable format
                visible_elements = []
                if elements:
                    for el in elements.elements:
                        visible_elements.append({
                            "ai_id": el.ai_id,
                            "tag": el.tag,
                            "text": el.text[:100] if el.text else "",
                            "type": el.element_type.value if el.element_type else "unknown",
                            "visible": el.is_visible,
                            "aria_label": el.aria_label if el.aria_label else None,
                        })

                self.audit.start_action(
                    url=self.page.url,
                    screenshot_clean=screenshot_clean,
                    screenshot_marked=screenshot_marked,
                    visible_elements=visible_elements,
                    depth=self.state.current_depth,
                    action_history=list(self.state.action_history),
                )
                self.audit.record_ai_prompt(prompt)

            # Ask AI with retry logic
            last_error = None
            for attempt in range(max_retries):
                try:
                    # On retry, add a reminder about JSON format
                    current_prompt = prompt
                    if attempt > 0:
                        current_prompt = prompt + "\n\nIMPORTANT: Return ONLY valid JSON, no markdown, no explanation text."

                    response = self.scout.backend.model.generate_content(
                        [
                            current_prompt,
                            {"mime_type": "image/png", "data": screenshot_b64},
                        ]
                    )

                    # Check for empty response
                    if not response.text or not response.text.strip():
                        last_error = "Empty response from AI"
                        time.sleep(0.5)  # Brief pause before retry
                        continue

                    # Parse response
                    raw_text = response.text.strip()
                    text = raw_text

                    # Handle markdown code blocks
                    if text.startswith("```"):
                        parts = text.split("```")
                        if len(parts) >= 2:
                            text = parts[1]
                            if text.startswith("json"):
                                text = text[4:]
                    text = text.strip()

                    # Try to extract JSON if there's extra text
                    if not text.startswith("{"):
                        # Look for JSON object in the response
                        start_idx = text.find("{")
                        end_idx = text.rfind("}") + 1
                        if start_idx != -1 and end_idx > start_idx:
                            text = text[start_idx:end_idx]

                    parsed = json.loads(text)

                    # Record AI response in audit
                    if self.audit:
                        self.audit.record_ai_response(raw_text, parsed)

                    return parsed

                except json.JSONDecodeError as e:
                    last_error = f"JSON parse error (attempt {attempt + 1}/{max_retries}): {str(e)[:50]}"
                    time.sleep(0.5)  # Brief pause before retry
                    continue
                except Exception as e:
                    last_error = f"AI error (attempt {attempt + 1}/{max_retries}): {str(e)[:50]}"
                    time.sleep(0.5)
                    continue

            # All retries failed
            error_msg = f"AI error after {max_retries} retries: {last_error}"
            self.report.ai_observations.append(error_msg)

            # Record error in audit
            if self.audit:
                duration_ms = (time.time() - action_start_time) * 1000
                self.audit.complete_action(success=False, error=error_msg, duration_ms=duration_ms)

            return None

        except Exception as e:
            error_msg = f"AI error: {str(e)[:100]}"
            self.report.ai_observations.append(error_msg)

            # Record error in audit
            if self.audit:
                duration_ms = (time.time() - action_start_time) * 1000
                self.audit.complete_action(success=False, error=error_msg, duration_ms=duration_ms)

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
                    # Store a clear element description, not the AI's reason
                    element_desc = f"{element.tag}"
                    if element.text:
                        element_desc += f": {element.text[:50]}"
                    elif element.aria_label:
                        element_desc += f": {element.aria_label[:50]}"
                    self.state.mark_element_visited(self.page.url, element_desc)
                    # Add to action_history so AI knows what was clicked
                    self.state.add_action(f"clicked {element_desc}")
                    return True

            elif action_type == "fill" and element_id is not None and text:
                elements = self.scout.discovery.discover()
                element = elements.find_by_id(element_id)
                if element:
                    self.page.fill(element.selector(), text, timeout=5000)
                    # Add to action_history
                    element_desc = f"{element.tag}"
                    if element.aria_label:
                        element_desc += f": {element.aria_label[:30]}"
                    self.state.add_action(f"filled {element_desc} with '{text[:20]}'")
                    return True

            elif action_type == "scroll":
                direction = action.get("direction", "down")
                delta = -300 if direction == "up" else 300
                self.page.mouse.wheel(0, delta)
                self.state.add_action(f"scrolled {direction}")
                return True

        except Exception as e:
            # Action failed - might be a bug
            self.report.add_bug(
                Bug(
                    severity=BugSeverity.MEDIUM,
                    title=f"Action Failed: {action_type}",
                    description=f"Could not {action_type}: {str(e)[:100]}",
                    reproduction_steps=list(self.state.action_history[-5:]) + [reason],
                    url=self.page.url,
                )
            )

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

        title = bug_data.get("title", "Unknown Issue")
        description = bug_data.get("description", "")
        reproduction_steps = list(self.state.action_history[-5:])
        console_errors = list(self.context.errors[-5:])

        self.report.add_bug(
            Bug(
                severity=severity,
                title=title,
                description=description,
                reproduction_steps=reproduction_steps,
                url=self.page.url,
                screenshot=screenshot,
                console_errors=console_errors,
            )
        )

        # Also record to audit trail
        if self.audit:
            self.audit.record_bug(
                severity=severity.value,
                title=title,
                description=description,
                reproduction_steps=reproduction_steps,
                url=self.page.url,
                screenshot=screenshot,
                console_errors=console_errors,
            )


def create_explorer(
    page,
    api_key: Optional[str] = None,
    backend_type: str = "gemini",
    enable_audit: bool = True,
) -> Explorer:
    """
    Create an Explorer with sensible defaults.

    Will try to get API key from environment if not provided.

    Args:
        page: Playwright page instance
        api_key: API key for AI backend (uses env var if not provided)
        backend_type: "gemini" or "openai"
        enable_audit: Whether to enable audit trail (default True)
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

    return Explorer(page, api_key=api_key, backend_type=backend_type, enable_audit=enable_audit)
