"""
Command-line interface for testScout.

Provides commands for autonomous exploration and testing.
"""

import argparse
import os
import sys


def explore_command(args):
    """Run autonomous exploration on a URL."""
    from playwright.sync_api import sync_playwright

    from .explorer import Explorer

    print("🔍 testScout Explorer")
    print(f"Target: {args.url}")
    print(f"Max actions: {args.max_actions}")
    print(f"Max time: {args.max_time}s")
    print()

    # Get API key
    api_key = args.api_key or os.environ.get(f"{args.backend.upper()}_API_KEY")
    if not api_key:
        print("❌ Error: No API key provided.")
        print(f"   Set {args.backend.upper()}_API_KEY environment variable or use --api-key")
        sys.exit(1)

    # Run exploration
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        page = browser.new_page()

        explorer = Explorer(
            page,
            api_key=api_key,
            backend_type=args.backend,
        )

        print("🤖 Starting autonomous exploration...")
        report = explorer.explore(
            start_url=args.url,
            max_actions=args.max_actions,
            max_time=args.max_time,
            max_depth=args.max_depth,
        )

        browser.close()

    # Save report
    report.save(args.output)
    print()
    print(report.summary())
    print()
    print(f"📊 Report saved to: {args.output}")
    print("   Open in browser to see detailed findings")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="testScout - AI-Powered E2E Testing Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Explore a website
  testscout explore http://localhost:8888

  # Explore with custom settings
  testscout explore http://localhost:8888 \\
      --max-actions 100 \\
      --max-time 600 \\
      --output report.html

  # Use OpenAI instead of Gemini
  testscout explore http://localhost:8888 \\
      --backend openai \\
      --api-key your-key

For more information, visit: https://github.com/rhowardstone/testScout
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Explore command
    explore_parser = subparsers.add_parser(
        "explore", help="Autonomously explore a website to find bugs"
    )
    explore_parser.add_argument("url", help="URL to explore (e.g., http://localhost:8888)")
    explore_parser.add_argument(
        "--max-actions",
        type=int,
        default=50,
        help="Maximum number of actions to take (default: 50)",
    )
    explore_parser.add_argument(
        "--max-time", type=int, default=300, help="Maximum time in seconds (default: 300)"
    )
    explore_parser.add_argument(
        "--max-depth", type=int, default=5, help="Maximum navigation depth (default: 5)"
    )
    explore_parser.add_argument(
        "--backend",
        choices=["gemini", "openai"],
        default="gemini",
        help="AI backend to use (default: gemini)",
    )
    explore_parser.add_argument(
        "--api-key", help="API key for the backend (or set GEMINI_API_KEY/OPENAI_API_KEY env var)"
    )
    explore_parser.add_argument(
        "--output",
        default="exploration_report.html",
        help="Output file path (default: exploration_report.html)",
    )
    explore_parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run browser in headless mode (default: True)",
    )
    explore_parser.add_argument(
        "--headed",
        action="store_false",
        dest="headless",
        help="Run browser in headed mode (show browser window)",
    )
    explore_parser.set_defaults(func=explore_command)

    # Parse args
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Run command
    args.func(args)


if __name__ == "__main__":
    main()
