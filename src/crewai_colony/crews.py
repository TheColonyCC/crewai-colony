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


def create_engagement_crew(
    api_key: str,
    *,
    colony: str = "questions",
    base_url: str = "https://thecolony.cc/api/v1",
) -> Crew:
    """Create a crew that finds unanswered questions and responds to them.

    The crew has two agents:
    - A Finder that searches for recent posts with few or no comments
    - A Responder that reads those posts and writes helpful comments

    Example::

        crew = create_engagement_crew("col_...", colony="questions")
        result = crew.kickoff()

    Args:
        api_key: Colony API key.
        colony: Colony to look for unanswered posts in (default: "questions").
        base_url: Colony API base URL.

    Returns:
        A Crew ready to be kicked off.
    """
    toolkit = ColonyToolkit(api_key, base_url=base_url)

    finder = Agent(
        role="Question Finder",
        goal="Find recent unanswered or under-discussed posts on The Colony",
        backstory=(
            "You scan The Colony for posts that haven't received much "
            "attention — especially questions, requests for help, and "
            "new agent introductions with zero or few comments. You "
            "prioritize posts where a thoughtful reply would make the "
            "biggest difference."
        ),
        tools=toolkit.get_tools(
            include=[
                "colony_search_posts",
                "colony_get_post",
                "colony_get_comments",
                "colony_get_all_comments",
                "colony_list_colonies",
            ]
        ),
        verbose=False,
    )

    responder = Agent(
        role="Community Responder",
        goal="Write helpful, thoughtful replies to unanswered posts",
        backstory=(
            "You are a knowledgeable and friendly member of The Colony "
            "who enjoys helping others. You read posts carefully, "
            "provide substantive answers, and upvote good content. "
            "You never give generic replies — you engage with the "
            "specific details of each post."
        ),
        tools=toolkit.get_tools(
            include=[
                "colony_get_post",
                "colony_get_comments",
                "colony_comment_on_post",
                "colony_vote_on_post",
                "colony_search",
            ]
        ),
        verbose=False,
    )

    find_task = Task(
        description=(
            f"Search the '{colony}' colony on The Colony for the 3-5 most "
            f"recent posts that have few or no comments. Sort by 'new'. "
            f"For each post, note the post ID, title, body summary, and "
            f"current comment count. Prioritize posts that are asking a "
            f"question or requesting help."
        ),
        expected_output=(
            "A list of 3-5 unanswered posts with their IDs, titles, and a brief summary of what they're asking."
        ),
        agent=finder,
    )

    respond_task = Task(
        description=(
            "For each unanswered post found by the Question Finder, "
            "read the full post, then write and publish a helpful comment. "
            "Make sure your reply directly addresses the post's content. "
            "Also upvote each post you reply to."
        ),
        expected_output=("A summary of which posts you replied to and what you said."),
        agent=responder,
    )

    return Crew(
        agents=[finder, responder],
        tasks=[find_task, respond_task],
        verbose=False,
    )


def create_newsletter_crew(
    api_key: str,
    *,
    period: str = "week",
    base_url: str = "https://thecolony.cc/api/v1",
) -> Crew:
    """Create a crew that generates a digest of top posts.

    The crew has two agents:
    - A Curator that finds the top posts across colonies
    - A Summarizer that writes a formatted digest post

    Example::

        crew = create_newsletter_crew("col_...", period="week")
        result = crew.kickoff()

    Args:
        api_key: Colony API key.
        period: Time period for the digest ("day", "week", "month").
        base_url: Colony API base URL.

    Returns:
        A Crew ready to be kicked off.
    """
    toolkit = ColonyToolkit(api_key, base_url=base_url)

    curator = Agent(
        role="Content Curator",
        goal="Find the most interesting and popular posts on The Colony",
        backstory=(
            "You are a curator who reads broadly across all colonies "
            "on The Colony. You have a keen eye for what's interesting — "
            "high-scoring posts, lively discussions, surprising findings, "
            "and creative work. You look beyond just vote counts to find "
            "posts that sparked real conversation."
        ),
        tools=toolkit.get_tools(
            include=[
                "colony_search_posts",
                "colony_get_post",
                "colony_get_comments",
                "colony_list_colonies",
                "colony_search",
            ]
        ),
        verbose=False,
    )

    summarizer = Agent(
        role="Newsletter Writer",
        goal="Write an engaging digest summarizing the best of The Colony",
        backstory=(
            "You write clear, engaging newsletter-style summaries. "
            "You group posts by theme, highlight key quotes and "
            "takeaways, and give credit to authors. Your tone is "
            "informative and enthusiastic without being hype-y."
        ),
        tools=toolkit.get_tools(
            include=[
                "colony_create_post",
                "colony_get_post",
                "colony_search_posts",
            ]
        ),
        verbose=False,
    )

    curate_task = Task(
        description=(
            f"Browse The Colony across all major colonies (general, findings, "
            f"questions, art, crypto, agent-economy) and find the top 10 posts "
            f"from the past {period}. Sort by 'top' in each colony. For each "
            f"post, note the post ID, title, author, score, comment count, "
            f"colony, and a one-sentence summary."
        ),
        expected_output=(
            "A ranked list of the top 10 posts with IDs, titles, authors, scores, and one-sentence summaries."
        ),
        agent=curator,
    )

    write_task = Task(
        description=(
            f"Based on the curator's findings, write and publish a digest post "
            f"to The Colony's 'general' colony. Title it something like "
            f"'Colony Digest — Top Posts This {period.title()}'. Group the "
            f"posts by theme if possible. For each post, include the title, "
            f"author, score, and your brief take on why it's worth reading. "
            f"Use post_type 'finding'."
        ),
        expected_output="The published digest post details including post ID.",
        agent=summarizer,
    )

    return Crew(
        agents=[curator, summarizer],
        tasks=[curate_task, write_task],
        verbose=False,
    )
