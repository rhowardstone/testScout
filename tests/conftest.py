"""
Pytest configuration and shared fixtures for testScout tests.

Provides utilities for testing with real browsers and AI backends.
"""

import os
from typing import Generator

import pytest
from playwright.sync_api import Page, sync_playwright


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow (exploration, etc.)")
    config.addinivalue_line("markers", "ai_e2e: marks tests as requiring AI API keys")


@pytest.fixture(scope="session")
def playwright_browser():
    """Session-scoped browser for faster tests."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def browser_page(playwright_browser) -> Generator[Page, None, None]:
    """Page fixture that creates a fresh page for each test."""
    page = playwright_browser.new_page()
    yield page
    page.close()


# Utility functions for tests
def has_api_key() -> bool:
    """Check if any AI API key is available."""
    return bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY"))


def get_api_key_and_backend():
    """Get available API key and backend type."""
    if os.environ.get("GEMINI_API_KEY"):
        return os.environ.get("GEMINI_API_KEY"), "gemini"
    elif os.environ.get("OPENAI_API_KEY"):
        return os.environ.get("OPENAI_API_KEY"), "openai"
    return None, None
