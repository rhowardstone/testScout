"""
Presentation generator for testScout audit trails.

Converts audit directories into presentation-friendly formats:
- HTML slideshow with auto-advance
- Interactive timeline viewer
- PDF export (via print)

Usage:
    from testscout.presentation import generate_slideshow

    # Generate from audit directory
    generate_slideshow("audit_dir/", "presentation.html")

    # Or use CLI
    python -m testscout.presentation audit_dir/ --output slides.html
"""

import os
import json
import base64
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any


def generate_slideshow(
    audit_dir: str,
    output_file: str = "slideshow.html",
    title: str = "testScout Exploration",
    auto_advance: int = 0,  # seconds, 0 = manual
    show_prompt: bool = False,  # Full prompts can be long
    show_response: bool = True,
    theme: str = "dark",  # dark or light
) -> str:
    """
    Generate an HTML slideshow from an audit directory.

    Args:
        audit_dir: Path to the audit trail directory
        output_file: Output HTML file path
        title: Presentation title
        auto_advance: Auto-advance interval in seconds (0 for manual)
        show_prompt: Whether to show the full AI prompt
        show_response: Whether to show AI response
        theme: Color theme (dark or light)

    Returns:
        Path to the generated HTML file
    """
    audit_path = Path(audit_dir)

    # Load summary
    summary = {}
    summary_file = audit_path / "summary.json"
    if summary_file.exists():
        with open(summary_file) as f:
            summary = json.load(f)

    # Load timeline events
    timeline = []
    timeline_file = audit_path / "timeline.jsonl"
    if timeline_file.exists():
        with open(timeline_file) as f:
            for line in f:
                if line.strip():
                    timeline.append(json.loads(line))

    # Find action directories
    actions_dir = audit_path / "actions"
    actions = []

    if actions_dir.exists():
        for action_dir in sorted(actions_dir.iterdir()):
            if action_dir.is_dir() and action_dir.name.isdigit():
                action_data = _load_action(action_dir)
                if action_data:
                    actions.append(action_data)

    # Generate HTML
    html = _generate_html(
        title=title,
        summary=summary,
        timeline=timeline,
        actions=actions,
        auto_advance=auto_advance,
        show_prompt=show_prompt,
        show_response=show_response,
        theme=theme,
    )

    # Write output
    output_path = Path(output_file)
    with open(output_path, "w") as f:
        f.write(html)

    return str(output_path)


def _load_action(action_dir: Path) -> Optional[Dict[str, Any]]:
    """Load action data from an action directory."""
    action_data = {
        "number": int(action_dir.name),
        "screenshot": None,
        "screenshot_marked": None,
        "decision": None,
        "prompt": None,
        "response": None,
        "context": None,
    }

    # Load screenshots
    for img_file in ["screenshot.png", "screenshot_clean.png"]:
        img_path = action_dir / img_file
        if img_path.exists():
            with open(img_path, "rb") as f:
                action_data["screenshot"] = base64.b64encode(f.read()).decode()
            break

    marked_path = action_dir / "screenshot_marked.png"
    if marked_path.exists():
        with open(marked_path, "rb") as f:
            action_data["screenshot_marked"] = base64.b64encode(f.read()).decode()

    # Load decision
    decision_path = action_dir / "decision.json"
    if decision_path.exists():
        with open(decision_path) as f:
            raw_decision = json.load(f)
            # Normalize to expected format: decision -> next_action
            if "decision" in raw_decision and "next_action" not in raw_decision:
                # Convert {decision: {action, element_id, ...}} to {next_action: {...}}
                action_data["decision"] = {
                    "next_action": raw_decision.get("decision", {}),
                    "observations": [],
                    "bugs_found": [],
                }
            else:
                action_data["decision"] = raw_decision

    # Load ai_response for observations/bugs
    ai_response_path = action_dir / "ai_response.json"
    if ai_response_path.exists():
        with open(ai_response_path) as f:
            ai_response = json.load(f)
            parsed = ai_response.get("parsed") or {}  # Handle None case
            if action_data["decision"]:
                action_data["decision"]["observations"] = parsed.get("observations", [])
                action_data["decision"]["bugs_found"] = parsed.get("bugs_found", [])

    # Load context
    context_path = action_dir / "context.json"
    if context_path.exists():
        with open(context_path) as f:
            action_data["context"] = json.load(f)

    # Load prompt
    prompt_path = action_dir / "prompt.txt"
    if prompt_path.exists():
        with open(prompt_path) as f:
            action_data["prompt"] = f.read()

    # Load response
    response_path = action_dir / "response.txt"
    if response_path.exists():
        with open(response_path) as f:
            action_data["response"] = f.read()

    # Only return if we have at least a screenshot
    if action_data["screenshot"]:
        return action_data
    return None


def _generate_html(
    title: str,
    summary: Dict,
    timeline: List[Dict],
    actions: List[Dict],
    auto_advance: int,
    show_prompt: bool,
    show_response: bool,
    theme: str,
) -> str:
    """Generate the HTML slideshow."""

    # Theme colors
    if theme == "dark":
        bg = "#1a1a2e"
        bg2 = "#16213e"
        text = "#eee"
        accent = "#4f46e5"
        muted = "#888"
    else:
        bg = "#f8f9fa"
        bg2 = "#ffffff"
        text = "#333"
        accent = "#4f46e5"
        muted = "#666"

    # Build slides HTML
    slides_html = []

    # Title slide
    slides_html.append(f'''
    <div class="slide" data-slide="0">
        <div class="title-slide">
            <h1>{title}</h1>
            <div class="meta">
                <p>URL: {summary.get("start_url", "Unknown")}</p>
                <p>Duration: {summary.get("duration_seconds", 0):.1f}s</p>
                <p>Actions: {summary.get("total_actions", len(actions))}</p>
                <p>Bugs Found: {summary.get("total_bugs", 0)}</p>
            </div>
            <p class="hint">Press <kbd>&rarr;</kbd> or click to advance</p>
        </div>
    </div>
    ''')

    # Action slides
    for i, action in enumerate(actions):
        decision = action.get("decision") or {}
        next_action = decision.get("next_action") or {}

        action_type = next_action.get("action", "unknown")
        reason = next_action.get("reason", "")
        target = next_action.get("target", "")

        # Format observations
        observations = decision.get("observations", [])
        obs_html = ""
        if observations:
            obs_items = "".join(f"<li>{obs}</li>" for obs in observations[:3])
            obs_html = f"<div class='observations'><strong>Observations:</strong><ul>{obs_items}</ul></div>"

        # Format bugs found
        bugs = decision.get("bugs_found", [])
        bugs_html = ""
        if bugs:
            bug_items = ""
            for b in bugs:
                sev = b.get('severity', 'info')
                title = b.get('title', '')
                bug_items += f"<li class='bug bug-{sev}'><strong>[{sev.upper()}]</strong> {title}</li>"
            bugs_html = f"<div class='bugs'><strong>Bugs Found:</strong><ul>{bug_items}</ul></div>"

        # Screenshot (prefer marked)
        screenshot = action.get("screenshot_marked") or action.get("screenshot")
        screenshot_html = ""
        if screenshot:
            screenshot_html = f'<img src="data:image/png;base64,{screenshot}" alt="Screenshot {i+1}" class="screenshot">'

        # Response excerpt
        response_html = ""
        if show_response and action.get("response"):
            response = action["response"][:500] + "..." if len(action.get("response", "")) > 500 else action.get("response", "")
            response_html = f"<div class='response'><strong>AI Response:</strong><pre>{response}</pre></div>"

        slides_html.append(f'''
    <div class="slide" data-slide="{i+1}">
        <div class="slide-header">
            <span class="slide-number">Action {action["number"]}</span>
            <span class="action-badge action-{action_type}">{action_type.upper()}</span>
        </div>
        <div class="slide-content">
            <div class="screenshot-panel">
                {screenshot_html}
            </div>
            <div class="info-panel">
                <div class="decision">
                    <h3>Decision</h3>
                    <p class="reason">{reason}</p>
                    {f'<p class="target"><strong>Target:</strong> {target}</p>' if target else ''}
                </div>
                {obs_html}
                {bugs_html}
                {response_html}
            </div>
        </div>
    </div>
    ''')

    # Summary slide
    slides_html.append(f'''
    <div class="slide" data-slide="{len(actions)+1}">
        <div class="title-slide summary-slide">
            <h1>Exploration Complete</h1>
            <div class="final-stats">
                <div class="stat">
                    <span class="stat-value">{summary.get("total_actions", len(actions))}</span>
                    <span class="stat-label">Actions</span>
                </div>
                <div class="stat">
                    <span class="stat-value">{summary.get("total_bugs", 0)}</span>
                    <span class="stat-label">Bugs Found</span>
                </div>
                <div class="stat">
                    <span class="stat-value">{summary.get("network_failures", 0)}</span>
                    <span class="stat-label">Network Errors</span>
                </div>
                <div class="stat">
                    <span class="stat-value">{summary.get("console_errors", 0)}</span>
                    <span class="stat-label">Console Errors</span>
                </div>
            </div>
        </div>
    </div>
    ''')

    # Full HTML
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: system-ui, -apple-system, sans-serif;
            background: {bg};
            color: {text};
            overflow: hidden;
        }}

        .slideshow {{
            position: relative;
            width: 100vw;
            height: 100vh;
        }}

        .slide {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            padding: 40px;
            display: none;
            flex-direction: column;
            animation: fadeIn 0.3s ease;
        }}

        .slide.active {{
            display: flex;
        }}

        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateX(20px); }}
            to {{ opacity: 1; transform: translateX(0); }}
        }}

        /* Title slide */
        .title-slide {{
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            height: 100%;
        }}

        .title-slide h1 {{
            font-size: 3rem;
            margin-bottom: 2rem;
            background: linear-gradient(135deg, {accent}, #818cf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .title-slide .meta {{
            font-size: 1.2rem;
            color: {muted};
            line-height: 2;
        }}

        .title-slide .hint {{
            margin-top: 3rem;
            color: {muted};
        }}

        .title-slide kbd {{
            background: {bg2};
            padding: 4px 12px;
            border-radius: 4px;
            border: 1px solid {muted};
        }}

        /* Action slides */
        .slide-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }}

        .slide-number {{
            font-size: 1.5rem;
            font-weight: bold;
        }}

        .action-badge {{
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 0.9rem;
            font-weight: bold;
            text-transform: uppercase;
        }}

        .action-click {{ background: #22c55e; color: white; }}
        .action-type {{ background: #3b82f6; color: white; }}
        .action-scroll {{ background: #f59e0b; color: white; }}
        .action-navigate {{ background: #8b5cf6; color: white; }}
        .action-done {{ background: #6b7280; color: white; }}

        .slide-content {{
            display: grid;
            grid-template-columns: 1fr 400px;
            gap: 30px;
            flex: 1;
            min-height: 0;
        }}

        .screenshot-panel {{
            display: flex;
            align-items: center;
            justify-content: center;
            background: {bg2};
            border-radius: 12px;
            padding: 20px;
            overflow: hidden;
        }}

        .screenshot {{
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
            border-radius: 8px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }}

        .info-panel {{
            display: flex;
            flex-direction: column;
            gap: 20px;
            overflow-y: auto;
        }}

        .decision {{
            background: {bg2};
            padding: 20px;
            border-radius: 12px;
            border-left: 4px solid {accent};
        }}

        .decision h3 {{
            font-size: 1rem;
            color: {muted};
            margin-bottom: 10px;
        }}

        .decision .reason {{
            font-size: 1.1rem;
            line-height: 1.6;
        }}

        .decision .target {{
            margin-top: 10px;
            color: {muted};
            font-size: 0.9rem;
        }}

        .observations, .bugs, .response {{
            background: {bg2};
            padding: 16px;
            border-radius: 8px;
        }}

        .observations ul, .bugs ul {{
            margin-left: 20px;
            margin-top: 8px;
        }}

        .observations li, .bugs li {{
            margin-bottom: 6px;
            line-height: 1.4;
        }}

        .bug-critical {{ color: #ef4444; }}
        .bug-high {{ color: #f97316; }}
        .bug-medium {{ color: #eab308; }}
        .bug-low {{ color: #22c55e; }}

        .response pre {{
            margin-top: 8px;
            font-size: 0.85rem;
            white-space: pre-wrap;
            color: {muted};
            max-height: 150px;
            overflow-y: auto;
        }}

        /* Summary slide */
        .final-stats {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 30px;
            margin-top: 2rem;
        }}

        .stat {{
            background: {bg2};
            padding: 30px;
            border-radius: 12px;
            text-align: center;
        }}

        .stat-value {{
            display: block;
            font-size: 3rem;
            font-weight: bold;
            color: {accent};
        }}

        .stat-label {{
            display: block;
            margin-top: 8px;
            color: {muted};
        }}

        /* Navigation */
        .nav {{
            position: fixed;
            bottom: 30px;
            left: 50%;
            transform: translateX(-50%);
            display: flex;
            gap: 10px;
            z-index: 100;
        }}

        .nav button {{
            background: {bg2};
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            color: {text};
            cursor: pointer;
            font-size: 1rem;
            transition: background 0.2s;
        }}

        .nav button:hover {{
            background: {accent};
        }}

        .progress {{
            position: fixed;
            bottom: 0;
            left: 0;
            height: 4px;
            background: {accent};
            transition: width 0.3s ease;
        }}

        /* Thumbnail nav */
        .thumbnails {{
            position: fixed;
            top: 20px;
            right: 20px;
            display: flex;
            gap: 8px;
            z-index: 100;
        }}

        .thumb {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: {muted};
            cursor: pointer;
            transition: all 0.2s;
        }}

        .thumb.active {{
            background: {accent};
            transform: scale(1.3);
        }}

        .thumb:hover {{
            background: {accent};
        }}
    </style>
</head>
<body>
    <div class="slideshow">
        {''.join(slides_html)}
    </div>

    <div class="thumbnails">
        {' '.join(f'<div class="thumb" data-goto="{i}"></div>' for i in range(len(actions) + 2))}
    </div>

    <nav class="nav">
        <button id="prev">&larr; Previous</button>
        <button id="next">Next &rarr;</button>
        {f'<button id="auto">Auto ({auto_advance}s)</button>' if auto_advance > 0 else ''}
    </nav>

    <div class="progress" id="progress"></div>

    <script>
        const slides = document.querySelectorAll('.slide');
        const thumbs = document.querySelectorAll('.thumb');
        const progress = document.getElementById('progress');
        const totalSlides = slides.length;
        let currentSlide = 0;
        let autoInterval = null;

        function showSlide(n) {{
            slides.forEach(s => s.classList.remove('active'));
            thumbs.forEach(t => t.classList.remove('active'));

            currentSlide = (n + totalSlides) % totalSlides;
            slides[currentSlide].classList.add('active');
            thumbs[currentSlide].classList.add('active');

            progress.style.width = ((currentSlide + 1) / totalSlides * 100) + '%';
        }}

        function nextSlide() {{
            showSlide(currentSlide + 1);
        }}

        function prevSlide() {{
            showSlide(currentSlide - 1);
        }}

        // Navigation buttons
        document.getElementById('prev').addEventListener('click', prevSlide);
        document.getElementById('next').addEventListener('click', nextSlide);

        // Thumbnail navigation
        thumbs.forEach((thumb, i) => {{
            thumb.addEventListener('click', () => showSlide(i));
        }});

        // Keyboard navigation
        document.addEventListener('keydown', (e) => {{
            if (e.key === 'ArrowRight' || e.key === ' ') nextSlide();
            if (e.key === 'ArrowLeft') prevSlide();
            if (e.key === 'Home') showSlide(0);
            if (e.key === 'End') showSlide(totalSlides - 1);
        }});

        // Click to advance
        document.querySelector('.slideshow').addEventListener('click', (e) => {{
            if (!e.target.closest('.nav') && !e.target.closest('.thumbnails')) {{
                nextSlide();
            }}
        }});

        // Auto-advance
        {'const autoBtn = document.getElementById("auto");' if auto_advance > 0 else ''}
        {'if (autoBtn) { autoBtn.addEventListener("click", () => { if (autoInterval) { clearInterval(autoInterval); autoInterval = null; autoBtn.textContent = "Auto (" + ' + str(auto_advance) + ' + "s)"; } else { autoInterval = setInterval(nextSlide, ' + str(auto_advance * 1000) + '); autoBtn.textContent = "Stop"; } }); }' if auto_advance > 0 else ''}

        // Initialize
        showSlide(0);
    </script>
</body>
</html>'''

    return html


# CLI
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate slideshow from testScout audit")
    parser.add_argument("audit_dir", help="Path to audit directory")
    parser.add_argument("-o", "--output", default="slideshow.html", help="Output file")
    parser.add_argument("-t", "--title", default="testScout Exploration", help="Presentation title")
    parser.add_argument("-a", "--auto", type=int, default=0, help="Auto-advance seconds")
    parser.add_argument("--theme", choices=["dark", "light"], default="dark", help="Color theme")
    parser.add_argument("--show-prompt", action="store_true", help="Show full AI prompts")
    parser.add_argument("--show-response", action="store_true", help="Show AI responses")

    args = parser.parse_args()

    output = generate_slideshow(
        audit_dir=args.audit_dir,
        output_file=args.output,
        title=args.title,
        auto_advance=args.auto,
        theme=args.theme,
        show_prompt=args.show_prompt,
        show_response=args.show_response,
    )

    print(f"Generated: {output}")
