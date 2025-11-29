# Contributing to testScout

Thank you for considering contributing to testScout! We welcome contributions from the community.

## 🌟 Ways to Contribute

- 🐛 Report bugs and issues
- 💡 Suggest new features or enhancements
- 📝 Improve documentation
- 🔧 Submit bug fixes
- ✨ Add new features
- 🔌 Create new AI backend integrations
- 📚 Write tutorials and examples

## 🚀 Getting Started

### 1. Fork and Clone

```bash
git fork https://github.com/rhowardstone/testScout
git clone https://github.com/YOUR_USERNAME/testScout
cd testScout
```

### 2. Set Up Development Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .[dev,all]

# Install Playwright browsers
playwright install chromium
```

### 3. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

## 📝 Development Guidelines

### Code Style

We use **Black** for code formatting and **Ruff** for linting:

```bash
# Format code
black src tests examples

# Lint code
ruff check src tests examples

# Type check
mypy src
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=testscout --cov-report=html

# Run specific test file
pytest tests/test_agent.py

# Run with output
pytest -v -s
```

### Type Hints

- All new code should include type hints
- Use `from typing import` for type annotations
- Run `mypy src` to check types

### Documentation

- Add docstrings to all public functions and classes
- Use Google-style docstrings
- Update README.md if adding new features
- Add examples for new functionality

Example docstring:

```python
def action(self, instruction: str, timeout: int = 5000) -> bool:
    """
    Execute an action based on natural language instruction.

    Args:
        instruction: Natural language instruction (e.g., "Click the login button")
        timeout: Timeout for the action in milliseconds

    Returns:
        True if action was executed successfully

    Examples:
        >>> scout.action("Click the Sign In button")
        True
        >>> scout.action("Fill email with test@example.com")
        True
    """
```

## 🔌 Adding a New AI Backend

To add support for a new AI provider:

1. Create a new file in `src/testscout/backends/` (e.g., `claude.py`)
2. Implement the `VisionBackend` interface:

```python
from .base import VisionBackend, ActionPlan, AssertionResult

class ClaudeBackend(VisionBackend):
    def __init__(self, api_key: str, model: str = "claude-3-opus"):
        # Initialize your backend
        pass

    def plan_action(self, instruction, screenshot_b64, elements):
        # Implement action planning
        pass

    def verify_assertion(self, assertion, screenshot_b64, elements):
        # Implement assertion verification
        pass

    def query(self, question, screenshot_b64, elements):
        # Implement query answering
        pass

    def discover_elements(self, screenshot_b64, element_type):
        # Implement element discovery
        pass
```

3. Add it to `src/testscout/backends/__init__.py`
4. Update `pyproject.toml` with optional dependency
5. Add tests in `tests/test_backends.py`
6. Update documentation

## 🧪 Pull Request Process

### Before Submitting

- [ ] Code follows style guidelines (Black + Ruff)
- [ ] All tests pass (`pytest`)
- [ ] Type hints added (`mypy src` passes)
- [ ] Documentation updated
- [ ] Examples added (if applicable)
- [ ] CHANGELOG.md updated

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How was this tested?

## Checklist
- [ ] Tests pass
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Follows code style
```

### Review Process

1. Submit your PR
2. Maintainers will review within 3-5 days
3. Address feedback if requested
4. Once approved, maintainers will merge

## 📋 Commit Message Guidelines

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```bash
feat(backends): add Claude backend support
fix(agent): handle timeout in verify() method
docs: update README with new examples
test(explorer): add tests for bug detection
```

## 🐛 Reporting Bugs

Use GitHub Issues with this template:

```markdown
**Describe the bug**
Clear description of what the bug is.

**To Reproduce**
Steps to reproduce:
1. Go to '...'
2. Click on '....'
3. See error

**Expected behavior**
What you expected to happen.

**Screenshots**
If applicable, add screenshots.

**Environment:**
 - OS: [e.g., macOS, Windows, Linux]
 - Python version: [e.g., 3.10]
 - testScout version: [e.g., 0.1.0]
 - Backend: [e.g., Gemini, OpenAI]

**Additional context**
Any other context about the problem.
```

## 💡 Feature Requests

Use GitHub Issues with this template:

```markdown
**Is your feature request related to a problem?**
Clear description of the problem.

**Describe the solution you'd like**
What you want to happen.

**Describe alternatives you've considered**
Other solutions you've thought about.

**Additional context**
Any other context or screenshots.
```

## 📜 Code of Conduct

### Our Pledge

We are committed to providing a friendly, safe, and welcoming environment for all contributors.

### Our Standards

**Positive behavior:**
- Being respectful and inclusive
- Gracefully accepting constructive criticism
- Focusing on what's best for the community
- Showing empathy toward others

**Unacceptable behavior:**
- Harassment or discrimination
- Trolling or insulting comments
- Public or private harassment
- Publishing others' private information

### Enforcement

Instances of abusive behavior may be reported to the maintainers. All complaints will be reviewed and investigated.

## 📞 Questions?

- 💬 [GitHub Discussions](https://github.com/rhowardstone/testScout/discussions)
- 🐛 [GitHub Issues](https://github.com/rhowardstone/testScout/issues)

## 🙏 Thank You!

Your contributions make testScout better for everyone. We appreciate your time and effort!
