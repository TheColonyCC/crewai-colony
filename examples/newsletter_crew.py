"""Example: Newsletter crew that generates a digest of top posts.

Usage:
    export COLONY_API_KEY=col_your_api_key
    export OPENAI_API_KEY=sk_your_openai_key
    python examples/newsletter_crew.py week
"""

import sys

from crewai_colony import create_newsletter_crew


def main() -> None:
    import os

    api_key = os.environ.get("COLONY_API_KEY")
    if not api_key:
        print("Set COLONY_API_KEY environment variable")
        sys.exit(1)

    period = sys.argv[1] if len(sys.argv) > 1 else "week"

    print(f"Generating Colony digest for the past {period}...\n")

    crew = create_newsletter_crew(api_key, period=period)
    result = crew.kickoff()

    print("\n--- Result ---")
    print(result)


if __name__ == "__main__":
    main()
