# testScout - AI-Powered E2E Testing Framework

**Test any web app with natural language. No selectors. No brittle tests.**

testScout combines rule-based DOM discovery with AI vision to create reliable, human-readable E2E tests.

## The Problem

Traditional E2E tests are:
- **Brittle** - CSS selectors break when UI changes
- **Hard to read** - `page.click("#btn-submit-v2")` means nothing
- **App-specific** - Each app needs custom test code

## The Solution

testScout uses a **hybrid approach**:

1. **Set-of-Marks (SoM)** - Automatically finds all interactive elements via DOM queries and tags them with IDs
2. **AI Vision** - Sees both the screenshot AND the element list to make intelligent decisions
3. **Natural Language** - Write tests in plain English

```python
# Instead of this:
page.click("#login-btn")
page.fill("#email-input", "test@example.com")
page.fill("#password-input", "secret")
page.click("button[type='submit']")

# Write this:
scout.action("Click the login button")
scout.action("Fill email with test@example.com")
scout.action("Fill password with secret123")
scout.action("Click submit")
assert scout.verify("Dashboard should show welcome message")
```

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                        testScout                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   1. DOM Discovery (Set-of-Marks)                          │
│      └─ Find all buttons, inputs, links                    │
│      └─ Tag with data-testscout-id="N"                     │
│      └─ Extract text, aria-labels, positions               │
│                                                             │
│   2. Screenshot with Markers                                │
│      └─ Red borders + number badges on elements            │
│      └─ AI can see "[7]" on the login button              │
│                                                             │
│   3. AI Fusion (Screenshot + Element List)                 │
│      └─ "Click login" → AI sees button [7] labeled "Login" │
│      └─ Returns: {"action": "click", "element_id": 7}     │
│                                                             │
│   4. Reliable Execution                                     │
│      └─ Click via [data-testscout-id="7"]                  │
│      └─ 100% reliable - no CSS selector guessing           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Installation

```bash
pip install testscout[gemini]  # For Gemini backend
# or
pip install testscout[openai]  # For OpenAI backend
# or
pip install testscout[all]     # Both backends

# Install Playwright browsers
playwright install chromium
```

## Quick Start

```python
import os
from playwright.sync_api import sync_playwright
from ai_e2e import Scout, Context, VisualAssertions

# Set your API key
os.environ["GEMINI_API_KEY"] = "your-key-here"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # Set True for CI
    page = browser.new_page()

    # Capture console logs, network errors, etc.
    context = Context()
    context.attach_to_page(page)

    # Create the AI scout
    scout = Scout(page, api_key=os.environ["GEMINI_API_KEY"], context=context)

    # Test any website!
    page.goto("https://your-app.com")

    # Natural language actions
    scout.action("Click the Sign Up button")
    scout.action("Fill in email with test@example.com")
    scout.action("Fill in password with SecurePass123!")
    scout.action("Check the Terms of Service checkbox")
    scout.action("Click Create Account")

    # Natural language assertions
    assert scout.verify("A welcome message or dashboard should appear")
    assert scout.verify("No error messages should be visible")

    # Use assertion helpers
    assertions = VisualAssertions(scout)
    assertions.no_errors()  # Checks console + visual errors
    assertions.loading_complete()

    # Save detailed report
    context.save_report("test_report.txt")

    browser.close()
```

## Features

### AI-Powered Actions

```python
# Click elements
scout.action("Click the blue Submit button")
scout.action("Click on 'Learn More' link")

# Fill forms
scout.action("Enter 'john@example.com' in the email field")
scout.action("Type 'Hello World' into the message textarea")

# Select options
scout.action("Select 'California' from the state dropdown")

# Scroll
scout.action("Scroll down to see more content")

# Complex actions
scout.action("If there's a cookie banner, click Accept")
scout.action("Close any popup dialogs")
```

### AI-Powered Verification

```python
# Visual assertions
assert scout.verify("A table with user data should be visible")
assert scout.verify("The page should show 'Success' message")
assert scout.verify("No loading spinners should be visible")

# With smart retry (waits up to 10 seconds)
assert scout.verify("Search results should appear", timeout=10.0)
```

### AI-Powered Discovery

```python
# Ask AI to find elements visually
buttons = scout.discover_elements("button")
for btn in buttons:
    print(f"Found: {btn['label']} at {btn['position']}")

# Ask questions about the page
answer = scout.query("What is the error message shown?")
print(answer)  # "The error says 'Invalid email format'"
```

### Console & Network Capture

```python
context = Context()
context.attach_to_page(page)

# After your test...
print(f"Errors: {len(context.errors)}")
print(f"Warnings: {len(context.warnings)}")
print(f"Network failures: {len(context.network_errors)}")

# Check for critical errors
if context.has_critical_errors():
    print("Critical errors found!")
    for err in context.get_critical_errors():
        print(f"  - {err}")

# Generate detailed report
context.save_report("test_report.txt")
```

## Supported AI Backends

### Gemini (Default)

```python
scout = Scout(page, api_key="...", backend_type="gemini")
# or
scout = Scout(page, api_key="...", model="gemini-2.0-flash")
```

### OpenAI

```python
scout = Scout(page, api_key="...", backend_type="openai", model="gpt-4o")
```

### Custom Backend

```python
from ai_e2e import VisionBackend

class MyBackend(VisionBackend):
    def plan_action(self, instruction, screenshot_b64, elements):
        # Your implementation
        pass

    def verify_assertion(self, assertion, screenshot_b64, elements):
        # Your implementation
        pass

scout = Scout(page, backend=MyBackend())
```

## pytest Integration

```python
import pytest
from ai_e2e import Scout, Context

@pytest.fixture
def scout(page):
    context = Context()
    context.attach_to_page(page)
    scout = Scout(page, api_key=os.environ["GEMINI_API_KEY"], context=context)
    yield scout
    scout.cleanup()
    context.save_report(f"reports/{request.node.name}.txt")

@pytest.mark.ai_e2e
def test_login(scout, page):
    page.goto("https://myapp.com")
    scout.action("Click Login")
    scout.action("Enter credentials")
    assert scout.verify("Dashboard visible")
```

## Environment Variables

```bash
GEMINI_API_KEY=your-gemini-key
OPENAI_API_KEY=your-openai-key
```

## Comparison

| Feature | testScout | Playwright | Selenium | Cypress |
|---------|-----------|------------|----------|---------|
| Natural language | Yes | No | No | No |
| AI vision | Yes | No | No | No |
| Console capture | Yes | Manual | Manual | Yes |
| Works on any app | Yes | Yes | Yes | Yes |
| Selector brittleness | None | High | High | Medium |
| Setup complexity | Low | Medium | High | Medium |

## License

MIT
