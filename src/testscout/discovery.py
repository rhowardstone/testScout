"""
Element Discovery with Set-of-Marks (SoM)

Hybrid approach:
1. Rule-based DOM queries find ALL interactive elements
2. Inject visual markers (borders + IDs) onto the page
3. AI sees numbered elements and picks by ID - 100% reliable targeting

This solves the core problem: AI can SEE a button visually but fails to
generate a working CSS selector. With SoM, AI just says "click element 4".
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ElementType(Enum):
    BUTTON = "button"
    LINK = "link"
    INPUT = "input"
    SELECT = "select"
    TEXTAREA = "textarea"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    IMAGE = "image"
    CUSTOM = "custom"


@dataclass
class DiscoveredElement:
    """An element found on the page with its properties."""

    ai_id: int
    element_type: ElementType
    tag: str
    text: str
    placeholder: str
    aria_label: str
    name: str
    id: str
    classes: List[str]
    href: Optional[str]
    src: Optional[str]
    is_visible: bool
    is_enabled: bool
    bounding_box: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ai_id": self.ai_id,
            "type": self.element_type.value,
            "tag": self.tag,
            "text": self.text[:100] if self.text else "",
            "placeholder": self.placeholder,
            "aria_label": self.aria_label,
            "name": self.name,
            "id": self.id,
            "visible": self.is_visible,
            "enabled": self.is_enabled,
        }

    def selector(self) -> str:
        """Return reliable selector for this element."""
        return f'[data-testscout-id="{self.ai_id}"]'


@dataclass
class PageElements:
    """All discovered elements on a page."""

    elements: List[DiscoveredElement] = field(default_factory=list)
    screenshot_hash: Optional[str] = None

    def find_by_id(self, ai_id: int) -> Optional[DiscoveredElement]:
        for el in self.elements:
            if el.ai_id == ai_id:
                return el
        return None

    def find_by_text(self, text: str, partial: bool = True) -> List[DiscoveredElement]:
        results = []
        text_lower = text.lower()
        for el in self.elements:
            el_text = (el.text or "").lower()
            if partial and text_lower in el_text:
                results.append(el)
            elif not partial and text_lower == el_text:
                results.append(el)
        return results

    def find_by_type(self, element_type: ElementType) -> List[DiscoveredElement]:
        return [el for el in self.elements if el.element_type == element_type]

    def to_prompt_summary(self) -> str:
        """Generate a summary for AI prompts."""
        if not self.elements:
            return "No interactive elements found on page."

        lines = ["Interactive elements on page:"]
        for el in self.elements:
            desc = f"  [{el.ai_id}] {el.element_type.value}"
            if el.text:
                desc += f' "{el.text[:50]}"'
            if el.placeholder:
                desc += f" (placeholder: {el.placeholder})"
            if el.aria_label:
                desc += f" (aria: {el.aria_label})"
            lines.append(desc)
        return "\n".join(lines)


# JavaScript to inject into page for Set-of-Marks
SOM_INJECT_SCRIPT = """
() => {
    // Remove any existing markers
    document.querySelectorAll('[data-testscout-id]').forEach(el => {
        el.removeAttribute('data-testscout-id');
        el.style.outline = '';
    });
    document.querySelectorAll('.testscout-marker').forEach(el => el.remove());

    // Find all interactive elements
    const selectors = [
        'button',
        'a[href]',
        'input:not([type="hidden"])',
        'select',
        'textarea',
        '[role="button"]',
        '[role="link"]',
        '[role="checkbox"]',
        '[role="radio"]',
        '[role="tab"]',
        '[role="menuitem"]',
        '[onclick]',
        '[tabindex]:not([tabindex="-1"])',
    ];

    const elements = [];
    const seen = new Set();

    selectors.forEach(selector => {
        document.querySelectorAll(selector).forEach(el => {
            if (seen.has(el)) return;
            seen.add(el);

            const rect = el.getBoundingClientRect();
            const isVisible = rect.width > 0 && rect.height > 0 &&
                             window.getComputedStyle(el).visibility !== 'hidden' &&
                             window.getComputedStyle(el).display !== 'none';

            if (!isVisible) return;

            const id = elements.length;
            el.setAttribute('data-testscout-id', id);

            // Determine element type
            let type = 'custom';
            const tag = el.tagName.toLowerCase();
            if (tag === 'button' || el.getAttribute('role') === 'button') type = 'button';
            else if (tag === 'a') type = 'link';
            else if (tag === 'input') {
                const inputType = el.getAttribute('type') || 'text';
                if (inputType === 'checkbox') type = 'checkbox';
                else if (inputType === 'radio') type = 'radio';
                else type = 'input';
            }
            else if (tag === 'select') type = 'select';
            else if (tag === 'textarea') type = 'textarea';
            else if (tag === 'img') type = 'image';

            elements.push({
                ai_id: id,
                type: type,
                tag: tag,
                text: (el.innerText || el.textContent || '').trim().substring(0, 200),
                placeholder: el.getAttribute('placeholder') || '',
                aria_label: el.getAttribute('aria-label') || '',
                name: el.getAttribute('name') || '',
                id: el.getAttribute('id') || '',
                classes: Array.from(el.classList),
                href: el.getAttribute('href'),
                src: el.getAttribute('src'),
                is_visible: isVisible,
                is_enabled: !el.disabled,
                bounding_box: {
                    x: rect.x,
                    y: rect.y,
                    width: rect.width,
                    height: rect.height
                }
            });
        });
    });

    return elements;
}
"""

# JavaScript to add visual markers (red borders + number badges)
SOM_HIGHLIGHT_SCRIPT = """
(showMarkers) => {
    document.querySelectorAll('[data-testscout-id]').forEach(el => {
        const id = el.getAttribute('data-testscout-id');

        if (showMarkers) {
            // Add red border
            el.style.outline = '2px solid #ff0000';
            el.style.outlineOffset = '2px';

            // Add number badge
            const badge = document.createElement('div');
            badge.className = 'testscout-marker';
            badge.textContent = id;
            badge.style.cssText = `
                position: absolute;
                background: #ff0000;
                color: white;
                font-size: 10px;
                font-weight: bold;
                padding: 1px 4px;
                border-radius: 3px;
                z-index: 999999;
                pointer-events: none;
            `;

            const rect = el.getBoundingClientRect();
            badge.style.left = (rect.left + window.scrollX - 5) + 'px';
            badge.style.top = (rect.top + window.scrollY - 12) + 'px';
            document.body.appendChild(badge);
        } else {
            // Remove markers
            el.style.outline = '';
        }
    });

    if (!showMarkers) {
        document.querySelectorAll('.testscout-marker').forEach(el => el.remove());
    }
}
"""

# JavaScript to clean up all markers
SOM_CLEANUP_SCRIPT = """
() => {
    document.querySelectorAll('[data-testscout-id]').forEach(el => {
        el.removeAttribute('data-testscout-id');
        el.style.outline = '';
    });
    document.querySelectorAll('.testscout-marker').forEach(el => el.remove());
}
"""


class ElementDiscovery:
    """
    Discovers and marks interactive elements on a page.

    Usage:
        discovery = ElementDiscovery(page)
        elements = await discovery.discover()

        # Take screenshot with visual markers
        screenshot = await discovery.screenshot_with_markers()

        # AI picks element 4
        element = elements.find_by_id(4)
        await page.click(element.selector())

        # Clean up
        await discovery.cleanup()
    """

    def __init__(self, page):
        self.page = page
        self._last_elements: Optional[PageElements] = None

    async def discover(self) -> PageElements:
        """Discover all interactive elements and tag them with data-testscout-id."""
        raw_elements = await self.page.evaluate(SOM_INJECT_SCRIPT)

        elements = []
        for raw in raw_elements:
            try:
                el = DiscoveredElement(
                    ai_id=raw["ai_id"],
                    element_type=ElementType(raw["type"]),
                    tag=raw["tag"],
                    text=raw["text"],
                    placeholder=raw["placeholder"],
                    aria_label=raw["aria_label"],
                    name=raw["name"],
                    id=raw["id"],
                    classes=raw["classes"],
                    href=raw.get("href"),
                    src=raw.get("src"),
                    is_visible=raw["is_visible"],
                    is_enabled=raw["is_enabled"],
                    bounding_box=raw["bounding_box"],
                )
                elements.append(el)
            except Exception:
                continue

        self._last_elements = PageElements(elements=elements)
        return self._last_elements

    async def show_markers(self):
        """Show visual markers (red borders + number badges) on elements."""
        await self.page.evaluate(SOM_HIGHLIGHT_SCRIPT, True)

    async def hide_markers(self):
        """Hide visual markers but keep data-testscout-id attributes."""
        await self.page.evaluate(SOM_HIGHLIGHT_SCRIPT, False)

    async def cleanup(self):
        """Remove all testscout attributes and markers from page."""
        await self.page.evaluate(SOM_CLEANUP_SCRIPT)

    async def screenshot_with_markers(self) -> bytes:
        """Take a screenshot with visual markers shown."""
        await self.show_markers()
        screenshot = await self.page.screenshot()
        await self.hide_markers()
        return screenshot

    async def screenshot_clean(self) -> bytes:
        """Take a screenshot without markers."""
        await self.hide_markers()
        return await self.page.screenshot()

    @property
    def elements(self) -> Optional[PageElements]:
        """Get last discovered elements."""
        return self._last_elements


# Sync versions for non-async usage
class ElementDiscoverySync:
    """Synchronous version of ElementDiscovery."""

    def __init__(self, page):
        self.page = page
        self._last_elements: Optional[PageElements] = None

    def discover(self) -> PageElements:
        """Discover all interactive elements and tag them with data-testscout-id."""
        raw_elements = self.page.evaluate(SOM_INJECT_SCRIPT)

        elements = []
        for raw in raw_elements:
            try:
                el = DiscoveredElement(
                    ai_id=raw["ai_id"],
                    element_type=ElementType(raw["type"]),
                    tag=raw["tag"],
                    text=raw["text"],
                    placeholder=raw["placeholder"],
                    aria_label=raw["aria_label"],
                    name=raw["name"],
                    id=raw["id"],
                    classes=raw["classes"],
                    href=raw.get("href"),
                    src=raw.get("src"),
                    is_visible=raw["is_visible"],
                    is_enabled=raw["is_enabled"],
                    bounding_box=raw["bounding_box"],
                )
                elements.append(el)
            except Exception:
                continue

        self._last_elements = PageElements(elements=elements)
        return self._last_elements

    def show_markers(self):
        self.page.evaluate(SOM_HIGHLIGHT_SCRIPT, True)

    def hide_markers(self):
        self.page.evaluate(SOM_HIGHLIGHT_SCRIPT, False)

    def cleanup(self):
        self.page.evaluate(SOM_CLEANUP_SCRIPT)

    def screenshot_with_markers(self) -> bytes:
        self.show_markers()
        screenshot = self.page.screenshot()
        self.hide_markers()
        return screenshot

    def screenshot_clean(self) -> bytes:
        self.hide_markers()
        return self.page.screenshot()

    @property
    def elements(self) -> Optional[PageElements]:
        return self._last_elements
