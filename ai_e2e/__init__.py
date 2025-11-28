"""
testScout - AI-Powered E2E Testing Framework

A hybrid approach combining:
1. Rule-based DOM discovery (Set-of-Marks)
2. AI vision for intent matching and verification
3. AI-powered element discovery

The AI sees BOTH the screenshot AND the element list, enabling it to:
- Match visual elements to clickable DOM elements
- Make intelligent decisions about which element to interact with
- Verify visual state through natural language assertions

Supported AI Backends:
- Gemini (default)
- OpenAI GPT-4V
- Extensible for other providers

Usage:
    from playwright.sync_api import sync_playwright
    from ai_e2e import Scout, Context, VisualAssertions

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        # Create context to capture console/network
        context = Context()
        context.attach_to_page(page)

        # Create scout with AI
        scout = Scout(page, api_key="...", context=context)

        # Navigate and interact
        page.goto("https://example.com")
        scout.action("Click the login button")
        scout.action("Fill email field with test@example.com")
        scout.action("Fill password field with secret123")
        scout.action("Click submit")

        # Verify with AI vision
        assert scout.verify("Dashboard should show welcome message")

        # Use assertion helpers
        assertions = VisualAssertions(scout)
        assertions.no_errors()
        assertions.element_visible("User profile dropdown")

        # Save report
        context.save_report("test_report.txt")

        browser.close()
"""

from .discovery import (
    ElementDiscovery,
    ElementDiscoverySync,
    DiscoveredElement,
    PageElements,
    ElementType,
)
from .context import (
    Context,
    ConsoleLog,
    NetworkRequest,
    AIVerification,
    LogLevel,
)
from .agent import (
    Scout,
    create_scout,
    VisionBackend,
    GeminiBackend,
    OpenAIBackend,
    ActionPlan,
    ActionType,
    AssertionResult,
)
from .assertions import (
    VisualAssertions,
    AssertionContext,
    wait_until,
    wait_for_element,
    wait_for_navigation,
    RetryConfig,
)
from .explorer import (
    Explorer,
    create_explorer,
    ExplorationReport,
    ExplorationState,
    Bug,
    BugSeverity,
)

__version__ = "0.1.0"
__all__ = [
    # Main classes
    "Scout",
    "create_scout",
    "Context",
    "VisualAssertions",
    "AssertionContext",
    # Discovery
    "ElementDiscovery",
    "ElementDiscoverySync",
    "DiscoveredElement",
    "PageElements",
    "ElementType",
    # Context
    "ConsoleLog",
    "NetworkRequest",
    "AIVerification",
    "LogLevel",
    # Agent
    "VisionBackend",
    "GeminiBackend",
    "OpenAIBackend",
    "ActionPlan",
    "ActionType",
    "AssertionResult",
    # Assertions
    "wait_until",
    "wait_for_element",
    "wait_for_navigation",
    "RetryConfig",
    # Explorer (Autonomous QA)
    "Explorer",
    "create_explorer",
    "ExplorationReport",
    "ExplorationState",
    "Bug",
    "BugSeverity",
]
