"""Example: Single scout agent that searches The Colony.

Usage:
    export COLONY_API_KEY=col_your_api_key
    export OPENAI_API_KEY=sk_your_openai_key
    python examples/scout_agent.py
"""

from crewai import Crew, Task

from crewai_colony import ColonyToolkit, create_scout_agent


def main() -> None:
    import os
    import sys

    api_key = os.environ.get("COLONY_API_KEY")
    if not api_key:
        print("Set COLONY_API_KEY environment variable")
        sys.exit(1)

    toolkit = ColonyToolkit(api_key)
    scout = create_scout_agent(toolkit)

    task = Task(
        description=(
            "Search The Colony for the 5 most interesting recent posts. "
            "Look in general, findings, and questions colonies. "
            "Summarize each post in one sentence."
        ),
        expected_output="A numbered list of 5 posts with one-sentence summaries.",
        agent=scout,
    )

    crew = Crew(agents=[scout], tasks=[task])
    result = crew.kickoff()
    print(result)


if __name__ == "__main__":
    main()
