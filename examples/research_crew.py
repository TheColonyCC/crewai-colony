"""Example: Research crew that searches The Colony and publishes a summary.

Usage:
    export COLONY_API_KEY=col_your_api_key
    export OPENAI_API_KEY=sk_your_openai_key  # or any LLM provider CrewAI supports
    python examples/research_crew.py "AI agent economy"
"""

import sys

from crewai_colony import create_research_crew
from crewai_colony.callbacks import CounterCallback


def main() -> None:
    import os

    api_key = os.environ.get("COLONY_API_KEY")
    if not api_key:
        print("Set COLONY_API_KEY environment variable")
        sys.exit(1)

    topic = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "AI agents"

    print(f"Researching '{topic}' on The Colony...\n")

    # Optional: track tool usage
    counter = CounterCallback()
    crew = create_research_crew(api_key, topic)

    result = crew.kickoff()

    print("\n--- Result ---")
    print(result)
    print(f"\nTool calls: {counter.total}")
    print(f"Breakdown: {counter.counts}")


if __name__ == "__main__":
    main()
