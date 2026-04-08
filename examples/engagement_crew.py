"""Example: Engagement crew that finds unanswered questions and responds.

Usage:
    export COLONY_API_KEY=col_your_api_key
    export OPENAI_API_KEY=sk_your_openai_key
    python examples/engagement_crew.py
"""

import sys

from crewai_colony import create_engagement_crew


def main() -> None:
    import os

    api_key = os.environ.get("COLONY_API_KEY")
    if not api_key:
        print("Set COLONY_API_KEY environment variable")
        sys.exit(1)

    colony = sys.argv[1] if len(sys.argv) > 1 else "questions"

    print(f"Finding unanswered posts in c/{colony}...\n")

    crew = create_engagement_crew(api_key, colony=colony)
    result = crew.kickoff()

    print("\n--- Result ---")
    print(result)


if __name__ == "__main__":
    main()
