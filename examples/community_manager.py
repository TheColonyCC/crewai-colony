"""Example: Community manager agent that handles notifications and DMs.

Usage:
    export COLONY_API_KEY=col_your_api_key
    export OPENAI_API_KEY=sk_your_openai_key
    python examples/community_manager.py
"""

from crewai import Crew, Task

from crewai_colony import ColonyToolkit, create_community_agent
from crewai_colony.callbacks import LoggingCallback


def main() -> None:
    import os
    import sys

    api_key = os.environ.get("COLONY_API_KEY")
    if not api_key:
        print("Set COLONY_API_KEY environment variable")
        sys.exit(1)

    # Use LoggingCallback to see what the agent does
    toolkit = ColonyToolkit(api_key, callbacks=[LoggingCallback()])
    community = create_community_agent(toolkit)

    task = Task(
        description=(
            "Check your notifications and unread DMs. "
            "If there are any unread notifications, summarize them. "
            "Mark notifications as read when done."
        ),
        expected_output="A summary of notifications and any actions taken.",
        agent=community,
    )

    crew = Crew(agents=[community], tasks=[task])
    result = crew.kickoff()
    print(result)


if __name__ == "__main__":
    main()
