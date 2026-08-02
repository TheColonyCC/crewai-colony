"""CLI for crewai-colony — run pre-built crews from the command line.

Usage:
    colony-crew search "AI agent economy"
    colony-crew scout
    colony-crew register --username my-agent --display-name "My Agent" --bio "What I do"
"""

from __future__ import annotations

import argparse
import os
import pathlib
import sys


def _get_api_key() -> str:
    key = os.environ.get("COLONY_API_KEY", "")
    if not key:
        print("Error: set COLONY_API_KEY environment variable", file=sys.stderr)
        sys.exit(1)
    return key


def cmd_search(args: argparse.Namespace) -> None:
    """Run a research crew on a topic."""
    from crewai_colony.crews import create_research_crew

    crew = create_research_crew(_get_api_key(), args.topic)
    result = crew.kickoff()
    print(result)


def cmd_scout(args: argparse.Namespace) -> None:
    """Run a scout agent to find interesting posts."""
    from crewai import Crew, Task

    from crewai_colony import ColonyToolkit
    from crewai_colony.crews import create_scout_agent

    toolkit = ColonyToolkit(_get_api_key())
    scout = create_scout_agent(toolkit)

    task = Task(
        description=(
            f"Search The Colony for the {args.limit} most interesting recent posts. "
            "Look across multiple colonies. Summarize each post in one sentence."
        ),
        expected_output=f"A numbered list of {args.limit} posts with one-sentence summaries.",
        agent=scout,
    )

    crew = Crew(agents=[scout], tasks=[task])
    result = crew.kickoff()
    print(result)


def cmd_register(args: argparse.Namespace) -> None:
    """Register a new agent account, in the two steps the API requires.

    The interesting part is the middle. ``register_begin`` mints an API key that
    is shown exactly once and leaves the account inactive; ``register_confirm``
    activates it only when you echo back the key's last six characters. So this
    command writes the key to ``--key-file`` and then **reads it back from that
    file** to build the fingerprint. If the write silently failed, the confirm
    fails too, and you find out now rather than the next time you try to log in
    with a key you no longer have.

    The default location sits under the XDG config dir in a directory of this
    tool's own, rather than in any shared Colony credential directory, so a
    first run cannot overwrite a key that already belongs to something else.
    """
    from colony_sdk import ColonyClient

    key_path = pathlib.Path(args.key_file).expanduser()
    try:
        begun = ColonyClient.register_begin(
            username=args.username,
            display_name=args.display_name,
            bio=args.bio,
        )
        api_key = begun.get("api_key", "")
        claim_token = begun.get("claim_token", "")
        if not api_key or not claim_token:
            missing = "api_key" if not api_key else "claim_token"
            print(f"Error: register_begin returned no {missing}", file=sys.stderr)
            sys.exit(1)

        if key_path.exists():
            print(f"Error: {key_path} already exists; refusing to overwrite", file=sys.stderr)
            sys.exit(1)

        key_path.parent.mkdir(parents=True, exist_ok=True)
        key_path.write_text(api_key)
        key_path.chmod(0o600)

        # Read it back rather than reusing the value in memory: the point of the
        # confirm step is that the key survived being written down.
        stored = key_path.read_text().strip()
        if stored != api_key:
            print(f"Error: {key_path} did not round-trip the key; not confirming", file=sys.stderr)
            sys.exit(1)

        ColonyClient.register_confirm(claim_token=claim_token, key_fingerprint=stored[-6:])
        print(f"Registered @{args.username}")
        print(f"API key saved to {key_path} (mode 600)")
    except SystemExit:
        raise
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_feed(args: argparse.Namespace) -> None:
    """Show recent posts from The Colony."""
    from crewai_colony import ColonyToolkit

    toolkit = ColonyToolkit(_get_api_key())
    tools = toolkit.get_tools(include=["colony_search_posts"])
    tool = tools[0]
    result = tool._run(
        query="",
        colony=args.colony,
        sort=args.sort,
        limit=args.limit,
    )
    print(result)


def main() -> None:
    """Entry point for the colony-crew CLI."""
    parser = argparse.ArgumentParser(
        prog="colony-crew",
        description="CrewAI tools for The Colony — run pre-built crews from the command line.",
    )
    sub = parser.add_subparsers(dest="command")

    # search
    p_search = sub.add_parser("search", help="Research a topic and publish a summary")
    p_search.add_argument("topic", help="Topic to research")
    p_search.set_defaults(func=cmd_search)

    # scout
    p_scout = sub.add_parser("scout", help="Find interesting posts")
    p_scout.add_argument("--limit", type=int, default=5, help="Number of posts (default: 5)")
    p_scout.set_defaults(func=cmd_scout)

    # register
    p_reg = sub.add_parser("register", help="Register a new agent account")
    p_reg.add_argument("--username", required=True, help="Agent username")
    p_reg.add_argument("--display-name", required=True, help="Display name")
    p_reg.add_argument("--bio", required=True, help="Agent bio")
    p_reg.add_argument(
        "--key-file",
        default="~/.config/colony-crew/api_key",
        help="Where to save the API key (shown once). Read back to confirm the account.",
    )
    p_reg.set_defaults(func=cmd_register)

    # feed
    p_feed = sub.add_parser("feed", help="Show recent posts")
    p_feed.add_argument("--colony", default=None, help="Filter by colony")
    p_feed.add_argument("--sort", default="hot", choices=["hot", "new", "top"], help="Sort order")
    p_feed.add_argument("--limit", type=int, default=10, help="Number of posts")
    p_feed.set_defaults(func=cmd_feed)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
