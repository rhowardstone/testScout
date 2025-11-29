# 🔍 testScout

**AI-Powered End-to-End Testing Framework**

[![PyPI version](https://badge.fury.io/py/testscout.svg)](https://badge.fury.io/py/testscout)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

> Test your web applications with natural language using AI vision models. No more brittle selectors, no more flaky tests.

## ✨ What Makes testScout Different?

While other tools generate test code or rely on fragile CSS selectors, **testScout** uses a revolutionary **Set-of-Marks** approach combined with AI vision:

1. 🎯 **Visual Understanding**: AI sees your app like a human does
2. 🔢 **Reliable Targeting**: Elements are marked with stable IDs, not brittle selectors
3. 🤖 **Natural Language**: Write tests in plain English
4. 🔍 **Autonomous Exploration**: AI finds bugs without pre-written tests
5. 📊 **Comprehensive Context**: Captures console logs, network requests, screenshots

```python
# Instead of this brittle code:
page.click("button.MuiButton-root.MuiButton-containedPrimary:nth-child(3)")

# Write this:
scout.action("Click the Submit button")
scout.verify("The success message should appear")
```

## 🚀 Quick Start

### Installation

```bash
pip install testscout[gemini]  # Recommended
# or
pip install testscout[openai]  # Alternative
# or
pip install testscout[all]     # Both backends

playwright install chromium
```

### Basic Usage

```python
from playwright.sync_api import sync_playwright
from testscout import Scout, VisualAssertions

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()

    # Create AI-powered scout
    scout = Scout(page, api_key="your-gemini-api-key")

    # Navigate and interact with natural language
    page.goto("https://example.com")
    scout.action("Click the login button")
    scout.action("Fill email with test@example.com")
    scout.action("Fill password with secret123")
    scout.action("Click submit")

    # Verify with AI
    assert scout.verify("Dashboard should be visible")

    # Use assertion helpers
    assertions = VisualAssertions(scout)
    assertions.no_errors()
    assertions.element_visible("Welcome message")

    browser.close()
```

## 📋 Table of Contents

- [Key Features](#-key-features)
- [How It Works](#-how-it-works)
- [Installation](#-installation)
- [Usage Guide](#-usage-guide)
  - [Basic Testing](#basic-testing)
  - [Visual Assertions](#visual-assertions)
  - [Autonomous Exploration](#autonomous-exploration)
  - [Custom Backends](#custom-ai-backends)
- [API Reference](#-api-reference)
- [Examples](#-examples)
- [Supported AI Backends](#-supported-ai-backends)
- [Comparison with Other Tools](#-comparison-with-other-tools)
- [Contributing](#-contributing)
- [License](#-license)

## 🎯 Key Features

### 🔢 Set-of-Marks Technology

testScout uses **Set-of-Marks (SoM)**, a technique from Microsoft Research, to solve the selector brittleness problem:

1. JavaScript finds all interactive elements
2. Elements are tagged with stable `data-testscout-id` attributes
3. Visual markers (numbers) are overlaid on the screenshot
4. AI sees numbered elements and picks by ID

**Result**: AI can see "button labeled Submit in bottom right" and reliably click it using `[data-testscout-id="7"]` instead of fragile CSS selectors.

### 🤖 Natural Language Actions

```python
# Clicks
scout.action("Click the Sign In button")
scout.action("Click the blue Add to Cart button on the right")

# Form filling
scout.action("Fill the email field with test@example.com")
scout.action("Type 'San Francisco' into the city input")

# Selections
scout.action("Select 'United States' from the country dropdown")

# Navigation
scout.action("Scroll down to see more products")
```

### ✅ AI-Powered Assertions

```python
# Visual verification
scout.verify("The dashboard shows a welcome message")
scout.verify("An error message saying 'Invalid password' is visible")
scout.verify("The loading spinner is gone")

# Assertion helpers
assertions = VisualAssertions(scout)
assertions.page_shows("Product listing with 12 items")
assertions.no_errors()  # Checks visual AND console errors
assertions.element_visible("User profile menu")
assertions.text_present("Welcome back, John")
assertions.loading_complete(timeout=30)
```

### 🔍 Autonomous Exploration

Let AI explore your application and find bugs automatically:

```python
from testscout import Explorer

explorer = Explorer(page, api_key="your-api-key")
report = explorer.explore(
    start_url="http://localhost:8888",
    max_actions=100,
    max_time=600,  # 10 minutes
)

# Save HTML report with screenshots
report.save("exploration_report.html")

print(report.summary())
# EXPLORATION REPORT
# ==================
# URL: http://localhost:8888
# Duration: 423.2s
# Pages Visited: 47
# Actions Taken: 95
#
# BUGS FOUND: 12
#   Critical: 2
#   High: 3
#   Medium: 5
#   Low: 2
```

### 📊 Comprehensive Context Capture

```python
from testscout import Context

context = Context()
context.attach_to_page(page)

# Captures automatically:
# - Console logs (errors, warnings, info)
# - Network requests/failures
# - Page errors (uncaught exceptions)
# - AI decisions and verifications
# - Screenshots (deduplicated)

# Generate detailed report
context.save_report("test_report.txt")

# Check for critical errors (React, Vue, Angular patterns)
if context.has_critical_errors():
    print(context.get_critical_errors())
```

## 🛠️ How It Works

```
┌─────────────────────────────────────────────────────────┐
│                    Your Test Code                       │
│   scout.action("Click the login button")               │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│              1. Element Discovery                       │
│  JavaScript finds ALL interactive elements on page      │
│  Tags each with data-testscout-id="N"                   │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│           2. Screenshot with Markers                    │
│  Red borders + number badges overlaid on elements       │
│  [1] Login    [2] Sign Up    [3] Forgot Password        │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│              3. AI Vision Analysis                      │
│  Gemini/GPT-4V receives:                                │
│  - Screenshot with numbered elements                    │
│  - List of elements with metadata                       │
│  Returns: {"action": "click", "element_id": 1}          │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│           4. Reliable Execution                         │
│  page.click('[data-testscout-id="1"]')                  │
│  100% reliable - no selector breakage                   │
└─────────────────────────────────────────────────────────┘
```

## 📦 Installation

### Requirements

- Python 3.8+
- Playwright
- AI API key (Gemini or OpenAI)

### Install testScout

```bash
# Basic installation
pip install testscout

# With Gemini support (default)
pip install testscout[gemini]

# With OpenAI support
pip install testscout[openai]

# With both
pip install testscout[all]

# Development mode
pip install -e .[dev]
```

### Install Playwright browsers

```bash
playwright install chromium
```

### Get API Keys

**Gemini (Recommended)**:
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Set environment variable: `export GEMINI_API_KEY=your-key`

**OpenAI** (Alternative):
1. Visit [OpenAI Platform](https://platform.openai.com/api-keys)
2. Create a new API key
3. Set environment variable: `export OPENAI_API_KEY=your-key`

## 📖 Usage Guide

### Basic Testing

```python
from playwright.sync_api import sync_playwright
from testscout import Scout, Context

def test_login():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # Setup context and scout
        context = Context()
        context.attach_to_page(page)
        scout = Scout(page, api_key="...", context=context)

        # Your test
        page.goto("https://your-app.com")
        scout.action("Click login")
        scout.action("Fill email with test@example.com")
        scout.action("Fill password with Test123!")
        scout.action("Click submit button")

        assert scout.verify("Dashboard is visible with user name")

        # Check for errors
        assert not context.has_critical_errors()

        # Save detailed report
        context.save_report("login_test_report.txt")

        browser.close()
```

### Visual Assertions

```python
from testscout import VisualAssertions

assertions = VisualAssertions(scout)

# Page state
assertions.page_shows("Product catalog with grid layout")
assertions.no_errors()

# Element visibility
assertions.element_visible("Shopping cart icon")
assertions.element_not_visible("Loading spinner")

# Text presence
assertions.text_present("Welcome, John")

# Form validation
assertions.form_filled({
    "email": "test@example.com",
    "name": "John Doe"
})

# Loading states
assertions.loading_complete(timeout=30)

# Modals
assertions.modal_open("Confirmation dialog")
# ... do something ...
assertions.modal_closed()
```

### Batch Assertions

```python
from testscout import AssertionContext

# All assertions run, failures collected
with AssertionContext(scout) as check:
    check.page_shows("Login form")
    check.element_visible("Email input")
    check.element_visible("Password input")
    check.no_errors()
# Raises AssertionError with all failures if any failed
```

### Autonomous Exploration

```python
from testscout import Explorer

# Create explorer
explorer = Explorer(page, api_key="your-api-key")

# Explore with custom settings
report = explorer.explore(
    start_url="http://localhost:8888",
    max_actions=100,        # Max clicks/interactions
    max_time=600,           # Max 10 minutes
    max_depth=5,            # How deep to navigate
    wait_for_selector="#root",  # Wait for SPA to load
    wait_timeout=15.0,      # Timeout for waits
)

# Access findings
print(f"Found {len(report.bugs)} bugs")
for bug in report.bugs:
    print(f"[{bug.severity.value}] {bug.title}")
    print(f"  {bug.description}")
    print(f"  Steps: {' -> '.join(bug.reproduction_steps)}")

# Save reports
report.save("report.html")   # Beautiful HTML report
report.save("report.json")   # Machine-readable JSON
report.save("report.txt")    # Plain text summary
```

### Custom AI Backends

```python
from testscout.backends import VisionBackend, ActionPlan, AssertionResult

class MyCustomBackend(VisionBackend):
    def plan_action(self, instruction, screenshot_b64, elements):
        # Your AI logic here
        # Call your custom model API
        # Parse response into ActionPlan
        return ActionPlan(
            action=ActionType.CLICK,
            element_id=5,
            reason="This looks like the button",
            confidence=0.95
        )

    def verify_assertion(self, assertion, screenshot_b64, elements):
        # Your verification logic
        return AssertionResult(
            passed=True,
            reason="I can see the element",
            confidence=0.9
        )

    def query(self, question, screenshot_b64, elements):
        # Your query logic
        return "The error message says..."

    def discover_elements(self, screenshot_b64, element_type):
        # Your element discovery logic
        return [{"type": "button", "label": "Submit", ...}]

# Use custom backend
backend = MyCustomBackend()
scout = Scout(page, backend=backend)
```

### CLI Tool

```bash
# Explore any website
testscout explore http://localhost:8888 \
    --max-actions 100 \
    --max-time 600 \
    --output report.html

# Specify backend
testscout explore http://localhost:8888 \
    --backend openai \
    --api-key your-key \
    --output report.html
```

## 📚 API Reference

### Scout

Main class for AI-powered testing.

```python
Scout(
    page,                    # Playwright page object
    api_key=None,           # API key for AI backend
    backend=None,           # Custom VisionBackend instance
    backend_type="gemini",  # "gemini" or "openai"
    model=None,             # Specific model name (optional)
    context=None            # Context object for capturing data
)
```

**Methods:**
- `action(instruction, timeout=5000, retry=1)` - Execute natural language action
- `verify(assertion, timeout=10.0, poll_interval=1.0)` - Verify visual state
- `query(question)` - Ask AI about current page
- `discover_elements(element_type=None)` - AI-powered element discovery
- `check_no_errors()` - Verify no critical errors
- `cleanup()` - Remove visual markers

### Explorer

Autonomous QA agent for bug hunting.

```python
Explorer(
    page,                   # Playwright page object
    api_key=None,          # API key for AI backend
    backend_type="gemini", # "gemini" or "openai"
    context=None           # Context object
)
```

**Methods:**
- `explore(start_url, max_actions=50, max_time=300, max_depth=5, ...)` - Autonomous exploration

### Context

Captures all test activity.

```python
Context()
```

**Methods:**
- `attach_to_page(page)` - Start capturing
- `save_report(filepath)` - Save text report
- `save_screenshots(directory)` - Save all screenshots
- `has_critical_errors()` - Check for critical errors
- `get_critical_errors()` - Get list of critical errors

**Properties:**
- `errors` - All error messages
- `warnings` - All warnings
- `network_errors` - Failed network requests

### VisualAssertions

High-level assertion helpers.

```python
VisualAssertions(scout)
```

**Methods:**
- `page_shows(description, timeout=10.0)`
- `no_errors(timeout=5.0)`
- `element_visible(description, timeout=10.0)`
- `element_not_visible(description, timeout=5.0)`
- `text_present(text, timeout=10.0)`
- `form_filled(field_values, timeout=5.0)`
- `loading_complete(timeout=30.0)`
- `modal_open(description=None, timeout=5.0)`
- `modal_closed(timeout=5.0)`

## 💡 Examples

See the [`examples/`](./examples/) directory for complete examples:

- `basic_usage.py` - Simple login test
- `explore_app.py` - Autonomous exploration
- `login_example.py` - Comprehensive login flow
- `custom_backend.py` - Custom AI backend

## 🤖 Supported AI Backends

| Backend | Model | Speed | Cost | Quality |
|---------|-------|-------|------|---------|
| **Gemini** | gemini-2.0-flash | ⚡ Fast | 💰 Low | ⭐⭐⭐⭐⭐ |
| **OpenAI** | gpt-4o | 🐌 Medium | 💰💰 High | ⭐⭐⭐⭐⭐ |
| **Custom** | Your choice | - | - | - |

### Backend Recommendations

- **Gemini 2.0 Flash** (Default): Best balance of speed, cost, and quality
- **GPT-4o**: Slightly better at complex layouts, but more expensive
- **Custom**: Integrate any vision-capable model (Claude, Ollama, etc.)

## 🆚 Comparison with Other Tools

| Feature | testScout | ZeroStep | Checksum | Playwright |
|---------|-----------|----------|----------|------------|
| **Natural Language** | ✅ | ✅ | ✅ | ❌ |
| **Visual Understanding** | ✅ | ✅ | ✅ | ❌ |
| **Set-of-Marks** | ✅ | ❌ | ❌ | ❌ |
| **Autonomous Exploration** | ✅ | ❌ | ✅ | ❌ |
| **Open Source** | ✅ | ❌ | ❌ | ✅ |
| **Pluggable Backends** | ✅ | ❌ | ❌ | N/A |
| **Context Capture** | ✅ | ❌ | ✅ | ❌ |
| **Self-Hosted** | ✅ | ❌ | ❌ | ✅ |
| **Pricing** | Free + API | SaaS | SaaS | Free |

**Why testScout?**

- ✅ **100% Open Source**: No vendor lock-in, full control
- ✅ **Pluggable Architecture**: Swap AI backends, customize everything
- ✅ **Set-of-Marks**: Unique approach for maximum reliability
- ✅ **Autonomous QA**: AI finds bugs you didn't know existed
- ✅ **Production Ready**: Well-tested, documented, supported

## 🏗️ Architecture

testScout is built with modularity in mind:

```
testscout/
├── backends/          # Pluggable AI backends
│   ├── base.py       # VisionBackend interface
│   ├── gemini.py     # Google Gemini implementation
│   └── openai.py     # OpenAI GPT-4V implementation
├── discovery.py       # Set-of-Marks element discovery
├── agent.py          # Scout class (main orchestrator)
├── context.py        # Context capture and reporting
├── assertions.py     # Visual assertion helpers
└── explorer.py       # Autonomous QA agent
```

**Key Design Principles:**
1. **Separation of Concerns**: Each module has one responsibility
2. **Pluggable Backends**: Easy to add new AI providers
3. **Framework Agnostic**: Works with any web framework
4. **Type Safety**: Full type hints for better IDE support

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

**Areas we'd love help with:**
- 🔌 New AI backend integrations (Claude, Ollama, local models)
- 📚 More examples and tutorials
- 🐛 Bug reports and fixes
- 📖 Documentation improvements
- ✨ New assertion helpers

## 📝 License

MIT License - see [LICENSE](./LICENSE) for details.

## 🙏 Acknowledgments

- **Set-of-Marks**: Inspired by [Microsoft Research's SoM](https://github.com/microsoft/SoM)
- **Playwright**: Built on top of the excellent [Playwright](https://playwright.dev/) framework
- **AI Vision Models**: Powered by Google Gemini and OpenAI GPT-4V

## 📞 Support

- 📖 [Documentation](./docs/)
- 💬 [GitHub Discussions](https://github.com/rhowardstone/testscout/discussions)
- 🐛 [Issue Tracker](https://github.com/rhowardstone/testscout/issues)

---

**Made with ❤️ by the testScout team**

[Get Started](#-quick-start) | [Documentation](./docs/) | [Examples](./examples/) | [Contributing](./CONTRIBUTING.md)
