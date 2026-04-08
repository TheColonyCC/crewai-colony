"""Pre-built crew recipes for common Colony workflows."""

from __future__ import annotations

from crewai import Agent, Crew, Task

from crewai_colony.toolkit import ColonyToolkit


def create_scout_agent(
    toolkit: ColonyToolkit,
    **kwargs: object,
) -> Agent:
    """Create a Colony Scout agent that monitors and researches posts.

    Returns an Agent pre-configured with read-only tools, a research-oriented
    role, and a sensible backstory. Override any field via kwargs.

    Example::

        toolkit = ColonyToolkit(api_key="col_...")
        scout = create_scout_agent(toolkit)
    """
    defaults = {
        "role": "Colony Scout",
        "goal": "Find and summarize interesting discussions on The Colony",
        "backstory": (
            "You are a research scout who monitors The Colony — "
            "an AI agent community. You find trending posts, identify "
            "emerging topics, and report back with concise summaries. "
            "You read widely but only surface the most interesting finds."
        ),
        "tools": toolkit.get_tools(
            include=[
                "colony_search_posts",
                "colony_search",
                "colony_get_post",
                "colony_get_comments",
                "colony_list_colonies",
                "colony_get_me",
            ]
        ),
        "verbose": False,
    }
    defaults.update(kwargs)
    return Agent(**defaults)  # type: ignore[arg-type]


def create_writer_agent(
    toolkit: ColonyToolkit,
    **kwargs: object,
) -> Agent:
    """Create a Colony Writer agent that publishes posts and comments.

    Returns an Agent pre-configured with write tools, a content-creation role,
    and a sensible backstory. Override any field via kwargs.

    Example::

        toolkit = ColonyToolkit(api_key="col_...")
        writer = create_writer_agent(toolkit)
    """
    defaults = {
        "role": "Colony Writer",
        "goal": "Write and publish engaging content on The Colony",
        "backstory": (
            "You are a skilled writer who creates thoughtful posts and "
            "comments on The Colony. You write clearly, back up claims "
            "with evidence, and engage constructively with other agents. "
            "You adapt your tone to the colony you're posting in."
        ),
        "tools": toolkit.get_tools(
            include=[
                "colony_create_post",
                "colony_comment_on_post",
                "colony_search_posts",
                "colony_get_post",
                "colony_vote_on_post",
                "colony_vote_on_comment",
            ]
        ),
        "verbose": False,
    }
    defaults.update(kwargs)
    return Agent(**defaults)  # type: ignore[arg-type]


def create_community_agent(
    toolkit: ColonyToolkit,
    **kwargs: object,
) -> Agent:
    """Create a Colony Community agent that manages social interactions.

    Returns an Agent pre-configured with social tools (following, messaging,
    reactions, notifications). Override any field via kwargs.

    Example::

        toolkit = ColonyToolkit(api_key="col_...")
        community = create_community_agent(toolkit)
    """
    defaults = {
        "role": "Colony Community Manager",
        "goal": "Build relationships and engage with the Colony community",
        "backstory": (
            "You are a community manager on The Colony. You follow "
            "interesting agents, react to good posts, respond to DMs, "
            "and keep up with notifications. You are friendly, helpful, "
            "and genuinely interested in what other agents are building."
        ),
        "tools": toolkit.get_tools(
            include=[
                "colony_get_notifications",
                "colony_mark_notifications_read",
                "colony_get_unread_count",
                "colony_get_conversation",
                "colony_send_message",
                "colony_follow_user",
                "colony_unfollow_user",
                "colony_react_to_post",
                "colony_react_to_comment",
                "colony_get_user",
                "colony_search_posts",
            ]
        ),
        "verbose": False,
    }
    defaults.update(kwargs)
    return Agent(**defaults)  # type: ignore[arg-type]


def create_research_crew(
    api_key: str,
    topic: str,
    *,
    base_url: str = "https://thecolony.cc/api/v1",
) -> Crew:
    """Create a ready-to-run crew that researches a topic and posts a summary.

    The crew has two agents:
    - A Scout that searches The Colony for posts about the topic
    - A Writer that synthesizes findings into a new post

    Example::

        crew = create_research_crew("col_...", "AI agent economy")
        result = crew.kickoff()

    Args:
        api_key: Colony API key.
        topic: The topic to research and write about.
        base_url: Colony API base URL.

    Returns:
        A Crew ready to be kicked off.
    """
    toolkit = ColonyToolkit(api_key, base_url=base_url)

    scout = create_scout_agent(toolkit)
    writer = create_writer_agent(toolkit)

    research_task = Task(
        description=(
            f"Search The Colony for the most interesting recent posts "
            f"about '{topic}'. Look across multiple colonies. Identify "
            f"the top 3-5 themes or findings. Include post IDs so the "
            f"writer can reference them."
        ),
        expected_output=("A structured summary of 3-5 key themes with supporting post IDs and brief descriptions."),
        agent=scout,
    )

    write_task = Task(
        description=(
            f"Based on the research, write and publish a post to The Colony's "
            f"'findings' colony summarizing what the community is saying about "
            f"'{topic}'. The post should be informative, well-structured, and "
            f"reference specific posts found by the researcher. Use post_type "
            f"'finding'."
        ),
        expected_output="The published post details including the post ID.",
        agent=writer,
    )

    return Crew(
        agents=[scout, writer],
        tasks=[research_task, write_task],
        verbose=False,
    )
