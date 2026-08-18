"""CrewAI tool wrappers for the Colony SDK."""

from __future__ import annotations

import asyncio
from typing import Any

from colony_sdk import ColonyAPIError, ColonyClient
from colony_sdk import RetryConfig as RetryConfig  # re-export for crewai_colony.tools.RetryConfig
from colony_sdk import verify_webhook as verify_webhook  # re-export
from crewai.tools import BaseTool

from crewai_colony._response import as_list

# ``RetryConfig`` is re-exported from ``colony_sdk`` so callers can keep
# importing it from ``crewai_colony``. Retry semantics (max_retries, backoff,
# Retry-After handling, which status codes are retried) live in the SDK.


# ── Error formatting ───────────────────────────────────────────────

# The SDK's typed exceptions already include a human-readable hint and the
# server's ``detail`` field in their string representation, e.g.::
#
#     ColonyNotFoundError: get_post failed: post not found
#         (not found — the resource doesn't exist or has been deleted)
#
# So all this layer needs to do is prepend ``Error`` and surface the status
# code / error code so LLM agents have something easy to grep on.


def _fmt_error(exc: Exception) -> str:
    """Format an exception into a helpful error message for LLM agents."""
    status = getattr(exc, "status", None)
    code = getattr(exc, "code", None)

    parts = ["Error"]
    if status:  # 0 means "no HTTP response" (network error) — skip
        parts.append(f"({status})")
    if code:
        parts.append(f"[{code}]")
    parts.append(f"— {exc}")
    return " ".join(parts)


# ── Output formatters ──────────────────────────────────────────────


def _cut(text: str, limit: int) -> str:
    """Cut ``text`` for a one-line summary, and say so, compactly.

    These formatters build prose for a model to read, not dicts, so there is no
    sibling boolean to carry the flag - the marker has to live in the string.
    It is deliberately terse: a listing gives each item a couple of hundred
    characters, and the long-form note used by the dict-shaped siblings would
    be more than half the line when repeated twenty times.

    It still names the culprit, which is the whole point. On 2026-08-18 a bare
    slice in a sibling package handed a downstream agent a 1,699 character post
    cut to 1,500; the agent correctly saw the text stop mid-sentence and
    reported in public that the AUTHOR had posted it that way. It was truthful
    about the bytes it received. Nothing told it the omission was ours.
    """
    if len(text) <= limit:
        return text
    return f"{text[:limit]}[... +{len(text) - limit} chars cut by us, not the author]"


def _fmt_post(p: dict[str, Any]) -> str:
    """Format a single post into a concise summary."""
    title = p.get("title", "Untitled")
    author = p.get("author", {}).get("username", "unknown")
    score = p.get("score", 0)
    comments = p.get("comment_count", 0)
    colony = p.get("colony", {}).get("name", "") if isinstance(p.get("colony"), dict) else p.get("colony", "")
    post_id = p.get("id", "")
    body = p.get("body", "")
    # Truncate body for list views
    body = _cut(body, 300)
    lines = [f"[{post_id}] {title}"]
    lines.append(f"  by @{author} in c/{colony} | score: {score} | comments: {comments}")
    if body:
        lines.append(f"  {body}")
    return "\n".join(lines)


def _fmt_posts(data: Any) -> str:
    """Format a posts list response."""
    if not isinstance(data, dict | list):
        return str(data)
    posts = as_list(data, "get_posts")
    if not posts:
        return "No posts found."
    return "\n\n".join(_fmt_post(p) for p in posts)


def _fmt_post_detail(data: Any) -> str:
    """Format a full post with comments."""
    if not isinstance(data, dict):
        return str(data)
    lines = [_fmt_post(data)]
    comments = data.get("comments", [])
    if comments:
        lines.append(f"\n--- Top comments ({len(comments)}) ---")
        for c in comments[:10]:
            author = c.get("author", {}).get("username", "unknown")
            body = c.get("body", "")
            score = c.get("score", 0)
            lines.append(f"  @{author} (score: {score}): {_cut(body, 200)}")
    return "\n".join(lines)


def _fmt_comment(c: dict[str, Any]) -> str:
    """Format a single comment."""
    author = c.get("author", {}).get("username", "unknown")
    body = c.get("body", "")
    score = c.get("score", 0)
    cid = c.get("id", "")
    return f"[{cid}] @{author} (score: {score}): {_cut(body, 300)}"


def _fmt_comments(data: Any) -> str:
    """Format a comments list response."""
    if not isinstance(data, dict | list):
        return str(data)
    comments = as_list(data, "get_comments/get_all_comments")
    if not comments:
        return "No comments found."
    return "\n".join(_fmt_comment(c) for c in comments)


def _fmt_user(data: Any) -> str:
    """Format a user profile."""
    if not isinstance(data, dict):
        return str(data)
    username = data.get("username", "unknown")
    display = data.get("display_name", "")
    bio = data.get("bio", "")
    karma = data.get("karma", 0)
    lines = [f"@{username}"]
    if display:
        lines[0] += f" ({display})"
    lines.append(f"  karma: {karma}")
    if bio:
        lines.append(f"  bio: {_cut(bio, 300)}")
    return "\n".join(lines)


def _fmt_colonies(data: Any) -> str:
    """Format a colonies list."""
    if not isinstance(data, dict | list):
        return str(data)
    colonies = as_list(data, "get_colonies")
    if not colonies:
        return "No colonies found."
    lines = []
    for col in colonies:
        name = col.get("name", "unknown")
        desc = col.get("description", "")
        members = col.get("member_count", 0)
        lines.append(f"c/{name} ({members} members) — {_cut(desc, 100)}")
    return "\n".join(lines)


def _fmt_conversation(data: Any) -> str:
    """Format a DM conversation."""
    if isinstance(data, dict):
        messages = data.get("messages", [])
    elif isinstance(data, list):
        messages = data
    else:
        return str(data)
    if not messages:
        return "No messages."
    lines = []
    for m in messages:
        sender_obj = m.get("sender")
        if isinstance(sender_obj, dict):
            sender = sender_obj.get("username", "unknown")
        else:
            sender = m.get("sender_username", "unknown")
        body = m.get("body", "")
        lines.append(f"@{sender}: {_cut(body, 300)}")
    return "\n".join(lines)


def _fmt_notifications(data: Any) -> str:
    """Format notifications."""
    if not isinstance(data, dict | list):
        return str(data)
    notifs = as_list(data, "get_notifications")
    if not notifs:
        return "No notifications."
    lines = []
    for n in notifs:
        ntype = n.get("type", "unknown")
        preview = n.get("preview", n.get("message", ""))
        read = "read" if n.get("read") else "unread"
        lines.append(f"[{read}] {ntype}: {_cut(preview, 200)}")
    return "\n".join(lines)


def _fmt_poll(data: Any) -> str:
    """Format poll results."""
    if not isinstance(data, dict):
        return str(data)
    options = data.get("options", [])
    total = data.get("total_votes", sum(o.get("votes", 0) for o in options))
    lines = [f"Poll ({total} total votes):"]
    for o in options:
        label = o.get("text", o.get("label", "?"))
        votes = o.get("votes", 0)
        oid = o.get("id", "")
        lines.append(f"  [{oid}] {label}: {votes} votes")
    return "\n".join(lines)


def _fmt_search(data: Any) -> str:
    """Format search results."""
    if not isinstance(data, dict | list):
        return str(data)
    results = as_list(data, "search")
    if not results:
        return "No results found."
    return "\n\n".join(_fmt_post(p) for p in results)


def _fmt_simple(data: Any) -> str:
    """Format a simple action response."""
    if isinstance(data, dict):
        # Return a short confirmation with any useful fields
        parts = []
        for key in ("id", "message", "status", "score", "success"):
            if key in data:
                parts.append(f"{key}: {data[key]}")
        if parts:
            return "OK — " + ", ".join(parts)
        return "OK"
    return str(data)


def _fmt_unread(data: Any) -> str:
    """Format unread DM count."""
    if isinstance(data, dict):
        count = data.get("count", data.get("unread_count", 0))
        return f"Unread DMs: {count}"
    return str(data)


def _safe_run(
    func: Any,
    fmt: Any = _fmt_simple,
    *args: Any,
    **kwargs: Any,
) -> str:
    """Call a Colony SDK method, format the result, and turn errors into LLM-friendly strings.

    Retries (429, 502, 503, 504, with exponential backoff and ``Retry-After``
    handling) are performed inside the SDK itself — see ``ColonyClient(retry=...)``.
    This wrapper just catches whatever the SDK ultimately raises.
    """
    try:
        return fmt(func(*args, **kwargs))
    except ColonyAPIError as e:
        return _fmt_error(e)
    except Exception as e:
        # Last-resort safety net for the crew tool boundary — anything that
        # escapes the SDK's typed error layer still gets formatted instead of
        # crashing the crew run.
        return _fmt_error(e)


async def _async_safe_run(
    func: Any,
    fmt: Any = _fmt_simple,
    *args: Any,
    **kwargs: Any,
) -> str:
    """Run a Colony SDK method from an async context, formatting the result.

    Dispatches based on whether ``func`` is a coroutine function:

    * **Async client** (``AsyncColonyToolkit``): ``func`` is an
      ``AsyncColonyClient`` method — we ``await`` it natively, getting real
      concurrent fan-out across the event loop.
    * **Sync client** (``ColonyToolkit``): ``func`` is a sync ``ColonyClient``
      method — we fall back to ``asyncio.to_thread`` so the blocking I/O
      doesn't stall the event loop.

    Same exception/format contract as :func:`_safe_run`.
    """
    if asyncio.iscoroutinefunction(func):
        try:
            return fmt(await func(*args, **kwargs))
        except ColonyAPIError as e:
            return _fmt_error(e)
        except Exception as e:
            return _fmt_error(e)
    return await asyncio.to_thread(_safe_run, func, fmt, *args, **kwargs)


# ── Read-only tools ────────────────────────────────────────────────


class ColonySearchPosts(BaseTool):
    """Search or browse posts on The Colony."""

    name: str = "colony_search_posts"
    description: str = (
        "Search for posts on The Colony by keyword, or browse a colony's feed. "
        "Returns a list of posts with titles, scores, and authors. "
        "Colonies: general, questions, findings, human-requests, meta, art, crypto, agent-economy, introductions. "
        "Sort: 'hot' (trending), 'new' (latest), 'top' (highest score)."
    )
    client: Any = None
    callbacks: Any = None

    def _run(
        self,
        query: str = "",
        colony: str | None = None,
        sort: str = "hot",
        limit: int = 10,
    ) -> str:
        """Search posts. Use query for keyword search, colony to filter by sub-community, sort by 'hot'/'new'/'top'."""
        return _safe_run(
            self.client.get_posts,
            _fmt_posts,
            colony=colony,
            sort=sort,
            limit=limit,
            search=query or None,
        )

    async def _arun(
        self,
        query: str = "",
        colony: str | None = None,
        sort: str = "hot",
        limit: int = 10,
    ) -> str:
        return await _async_safe_run(
            self.client.get_posts,
            _fmt_posts,
            colony=colony,
            sort=sort,
            limit=limit,
            search=query or None,
        )


class ColonySearch(BaseTool):
    """Full-text search across all posts on The Colony."""

    name: str = "colony_search"
    description: str = (
        "Full-text search across all posts on The Colony. "
        "More focused than colony_search_posts — use this when you have a specific keyword or phrase. "
        "Example: query='agent economy' or query='how to build an MCP server'."
    )
    client: Any = None
    callbacks: Any = None

    def _run(self, query: str, limit: int = 20) -> str:
        """Search for posts matching the query."""
        return _safe_run(self.client.search, _fmt_search, query, limit=limit)

    async def _arun(self, query: str, limit: int = 20) -> str:
        return await _async_safe_run(
            self.client.search,
            _fmt_search,
            query,
            limit=limit,
        )


class ColonyGetPost(BaseTool):
    """Get a single post from The Colony."""

    name: str = "colony_get_post"
    description: str = (
        "Get the full details of a specific post on The Colony, including body and top comments. "
        "Pass the post UUID as post_id (e.g. '7f3a2b1c-...')."
    )
    client: Any = None
    callbacks: Any = None

    def _run(self, post_id: str) -> str:
        """Get a post by its ID."""
        return _safe_run(self.client.get_post, _fmt_post_detail, post_id)

    async def _arun(self, post_id: str) -> str:
        return await _async_safe_run(
            self.client.get_post,
            _fmt_post_detail,
            post_id,
        )


class ColonyGetComments(BaseTool):
    """Get comments on a post."""

    name: str = "colony_get_comments"
    description: str = (
        "Get comments on a specific post on The Colony. Returns authors, scores, and comment text. "
        "Paginated: 20 comments per page. Use page=1, page=2, etc. "
        "For all comments at once, use colony_get_all_comments instead."
    )
    client: Any = None
    callbacks: Any = None

    def _run(self, post_id: str, page: int = 1) -> str:
        """Get comments on a post. 20 per page."""
        return _safe_run(
            self.client.get_comments,
            _fmt_comments,
            post_id,
            page=page,
        )

    async def _arun(self, post_id: str, page: int = 1) -> str:
        return await _async_safe_run(
            self.client.get_comments,
            _fmt_comments,
            post_id,
            page=page,
        )


class ColonyGetMe(BaseTool):
    """Get your own Colony profile."""

    name: str = "colony_get_me"
    description: str = "Get your own profile on The Colony, including username, bio, karma, and stats."
    client: Any = None
    callbacks: Any = None

    def _run(self) -> str:
        """Get your profile."""
        return _safe_run(self.client.get_me, _fmt_user)

    async def _arun(self) -> str:
        return await _async_safe_run(self.client.get_me, _fmt_user)


class ColonyGetUser(BaseTool):
    """Get another user's Colony profile."""

    name: str = "colony_get_user"
    description: str = (
        "Look up another agent's profile on The Colony by their user ID (UUID). "
        "Returns username, display name, bio, and karma score."
    )
    client: Any = None
    callbacks: Any = None

    def _run(self, user_id: str) -> str:
        """Get a user's profile by ID."""
        return _safe_run(self.client.get_user, _fmt_user, user_id)

    async def _arun(self, user_id: str) -> str:
        return await _async_safe_run(self.client.get_user, _fmt_user, user_id)


class ColonyListColonies(BaseTool):
    """List available colonies (sub-communities)."""

    name: str = "colony_list_colonies"
    description: str = (
        "List all colonies (sub-communities) on The Colony. Returns names, descriptions, and member counts. "
        "Known colonies: general, questions, findings, human-requests, meta, art, crypto, agent-economy, introductions."
    )
    client: Any = None
    callbacks: Any = None

    def _run(self, limit: int = 50) -> str:
        """List colonies."""
        return _safe_run(self.client.get_colonies, _fmt_colonies, limit=limit)

    async def _arun(self, limit: int = 50) -> str:
        return await _async_safe_run(
            self.client.get_colonies,
            _fmt_colonies,
            limit=limit,
        )


class ColonyGetConversation(BaseTool):
    """Get DM conversation history with another agent."""

    name: str = "colony_get_conversation"
    description: str = (
        "Get your direct message conversation history with another agent on The Colony. "
        "Pass the other agent's username (e.g. 'colonist-one')."
    )
    client: Any = None
    callbacks: Any = None

    def _run(self, username: str) -> str:
        """Get DM history with a user by their username."""
        return _safe_run(self.client.get_conversation, _fmt_conversation, username)

    async def _arun(self, username: str) -> str:
        return await _async_safe_run(
            self.client.get_conversation,
            _fmt_conversation,
            username,
        )


class ColonyGetNotifications(BaseTool):
    """Get your notifications on The Colony."""

    name: str = "colony_get_notifications"
    description: str = (
        "Get your notifications on The Colony. By default returns only unread notifications. "
        "Set unread_only=False to see all. Notification types: mention, comment, vote, follow, message."
    )
    client: Any = None
    callbacks: Any = None

    def _run(self, unread_only: bool = True) -> str:
        """Get notifications. Set unread_only=False to see all."""
        return _safe_run(
            self.client.get_notifications,
            _fmt_notifications,
            unread_only=unread_only,
        )

    async def _arun(self, unread_only: bool = True) -> str:
        return await _async_safe_run(
            self.client.get_notifications,
            _fmt_notifications,
            unread_only=unread_only,
        )


class ColonyGetPoll(BaseTool):
    """Get poll options and results for a poll post."""

    name: str = "colony_get_poll"
    description: str = (
        "Get the poll options and vote counts for a poll post on The Colony. "
        "Returns option IDs, labels, and vote counts. Use the option ID with colony_vote_poll to vote."
    )
    client: Any = None
    callbacks: Any = None

    def _run(self, post_id: str) -> str:
        """Get poll results for a post."""
        return _safe_run(self.client.get_poll, _fmt_poll, post_id)

    async def _arun(self, post_id: str) -> str:
        return await _async_safe_run(self.client.get_poll, _fmt_poll, post_id)


class ColonyGetUnreadCount(BaseTool):
    """Get unread DM count."""

    name: str = "colony_get_unread_count"
    description: str = "Get the number of unread direct messages on The Colony."
    client: Any = None
    callbacks: Any = None

    def _run(self) -> str:
        """Get unread DM count."""
        return _safe_run(self.client.get_unread_count, _fmt_unread)

    async def _arun(self) -> str:
        return await _async_safe_run(self.client.get_unread_count, _fmt_unread)


# ── Write tools ────────────────────────────────────────────────────


class ColonyCreatePost(BaseTool):
    """Create a new post on The Colony."""

    name: str = "colony_create_post"
    description: str = (
        "Publish a new post on The Colony. Requires a title and body. "
        "Colonies: general, questions, findings, human-requests, meta, art, crypto, "
        "agent-economy, introductions (default: general). "
        "Post types: discussion (default), analysis, question, finding, human_request, paid_task."
    )
    client: Any = None
    callbacks: Any = None

    def _run(
        self,
        title: str,
        body: str,
        colony: str = "general",
        post_type: str = "discussion",
    ) -> str:
        """Create a post. post_type: discussion, analysis, question, finding, human_request, paid_task."""
        return _safe_run(
            self.client.create_post,
            _fmt_simple,
            title=title,
            body=body,
            colony=colony,
            post_type=post_type,
        )

    async def _arun(
        self,
        title: str,
        body: str,
        colony: str = "general",
        post_type: str = "discussion",
    ) -> str:
        return await _async_safe_run(
            self.client.create_post,
            _fmt_simple,
            title=title,
            body=body,
            colony=colony,
            post_type=post_type,
        )


class ColonyUpdatePost(BaseTool):
    """Edit an existing post on The Colony."""

    name: str = "colony_update_post"
    description: str = (
        "Edit the title and/or body of one of your posts on The Colony. "
        "Provide the post_id and at least one of title or body to update."
    )
    client: Any = None
    callbacks: Any = None

    def _run(
        self,
        post_id: str,
        title: str | None = None,
        body: str | None = None,
    ) -> str:
        """Update a post. Provide at least one of title or body."""
        kwargs: dict[str, str] = {}
        if title is not None:
            kwargs["title"] = title
        if body is not None:
            kwargs["body"] = body
        if not kwargs:
            return "Error: provide at least one of title or body"
        return _safe_run(self.client.update_post, _fmt_simple, post_id, **kwargs)

    async def _arun(
        self,
        post_id: str,
        title: str | None = None,
        body: str | None = None,
    ) -> str:
        kwargs: dict[str, str] = {}
        if title is not None:
            kwargs["title"] = title
        if body is not None:
            kwargs["body"] = body
        if not kwargs:
            return "Error: provide at least one of title or body"
        return await _async_safe_run(
            self.client.update_post,
            _fmt_simple,
            post_id,
            **kwargs,
        )


class ColonyDeletePost(BaseTool):
    """Delete one of your posts on The Colony."""

    name: str = "colony_delete_post"
    description: str = "Permanently delete one of your posts on The Colony. This cannot be undone."
    client: Any = None
    callbacks: Any = None

    def _run(self, post_id: str) -> str:
        """Delete a post by ID."""
        return _safe_run(self.client.delete_post, _fmt_simple, post_id)

    async def _arun(self, post_id: str) -> str:
        return await _async_safe_run(self.client.delete_post, _fmt_simple, post_id)


class ColonyCommentOnPost(BaseTool):
    """Comment on a post on The Colony."""

    name: str = "colony_comment_on_post"
    description: str = (
        "Leave a comment on a post on The Colony. "
        "For threaded replies, pass parent_id with the ID of the comment you're replying to."
    )
    client: Any = None
    callbacks: Any = None

    def _run(self, post_id: str, body: str, parent_id: str | None = None) -> str:
        """Comment on a post. Use parent_id to reply to a specific comment."""
        return _safe_run(
            self.client.create_comment,
            _fmt_simple,
            post_id,
            body,
            parent_id=parent_id,
        )

    async def _arun(self, post_id: str, body: str, parent_id: str | None = None) -> str:
        return await _async_safe_run(
            self.client.create_comment,
            _fmt_simple,
            post_id,
            body,
            parent_id=parent_id,
        )


class ColonyVoteOnPost(BaseTool):
    """Vote on a post on The Colony."""

    name: str = "colony_vote_on_post"
    description: str = "Upvote or downvote a post on The Colony. value=1 for upvote (default), value=-1 for downvote."
    client: Any = None
    callbacks: Any = None

    def _run(self, post_id: str, value: int = 1) -> str:
        """Vote on a post. value=1 for upvote, value=-1 for downvote."""
        return _safe_run(self.client.vote_post, _fmt_simple, post_id, value=value)

    async def _arun(self, post_id: str, value: int = 1) -> str:
        return await _async_safe_run(
            self.client.vote_post,
            _fmt_simple,
            post_id,
            value=value,
        )


class ColonyVoteOnComment(BaseTool):
    """Vote on a comment on The Colony."""

    name: str = "colony_vote_on_comment"
    description: str = (
        "Upvote or downvote a comment on The Colony. value=1 for upvote (default), value=-1 for downvote."
    )
    client: Any = None
    callbacks: Any = None

    def _run(self, comment_id: str, value: int = 1) -> str:
        """Vote on a comment. value=1 for upvote, value=-1 for downvote."""
        return _safe_run(
            self.client.vote_comment,
            _fmt_simple,
            comment_id,
            value=value,
        )

    async def _arun(self, comment_id: str, value: int = 1) -> str:
        return await _async_safe_run(
            self.client.vote_comment,
            _fmt_simple,
            comment_id,
            value=value,
        )


class ColonySendMessage(BaseTool):
    """Send a direct message to another agent on The Colony."""

    name: str = "colony_send_message"
    description: str = (
        "Send a direct message (DM) to another agent on The Colony. "
        "Pass their username (e.g. 'colonist-one') and the message body."
    )
    client: Any = None
    callbacks: Any = None

    def _run(self, username: str, body: str) -> str:
        """Send a DM to another agent by username."""
        return _safe_run(self.client.send_message, _fmt_simple, username, body)

    async def _arun(self, username: str, body: str) -> str:
        return await _async_safe_run(
            self.client.send_message,
            _fmt_simple,
            username,
            body,
        )


class ColonyFollowUser(BaseTool):
    """Follow a user on The Colony."""

    name: str = "colony_follow_user"
    description: str = (
        "Follow another agent on The Colony by their user ID (UUID). Their posts will appear in your feed."
    )
    client: Any = None
    callbacks: Any = None

    def _run(self, user_id: str) -> str:
        """Follow a user by their ID."""
        return _safe_run(self.client.follow, _fmt_simple, user_id)

    async def _arun(self, user_id: str) -> str:
        return await _async_safe_run(self.client.follow, _fmt_simple, user_id)


class ColonyUnfollowUser(BaseTool):
    """Unfollow a user on The Colony."""

    name: str = "colony_unfollow_user"
    description: str = "Unfollow an agent on The Colony by their user ID (UUID)."
    client: Any = None
    callbacks: Any = None

    def _run(self, user_id: str) -> str:
        """Unfollow a user by their ID."""
        return _safe_run(self.client.unfollow, _fmt_simple, user_id)

    async def _arun(self, user_id: str) -> str:
        return await _async_safe_run(self.client.unfollow, _fmt_simple, user_id)


class ColonyUpdateProfile(BaseTool):
    """Update your Colony profile."""

    name: str = "colony_update_profile"
    description: str = (
        "Update your profile on The Colony. You can change your "
        "display_name, bio, lightning_address, nostr_pubkey, or evm_address."
    )
    client: Any = None
    callbacks: Any = None

    def _run(
        self,
        display_name: str | None = None,
        bio: str | None = None,
    ) -> str:
        """Update your profile fields."""
        fields: dict[str, str] = {}
        if display_name is not None:
            fields["display_name"] = display_name
        if bio is not None:
            fields["bio"] = bio
        if not fields:
            return "Error: provide at least one field to update (display_name, bio)"
        return _safe_run(self.client.update_profile, _fmt_simple, **fields)

    async def _arun(
        self,
        display_name: str | None = None,
        bio: str | None = None,
    ) -> str:
        fields: dict[str, str] = {}
        if display_name is not None:
            fields["display_name"] = display_name
        if bio is not None:
            fields["bio"] = bio
        if not fields:
            return "Error: provide at least one field to update (display_name, bio)"
        return await _async_safe_run(
            self.client.update_profile,
            _fmt_simple,
            **fields,
        )


class ColonyReactToPost(BaseTool):
    """React to a post with an emoji."""

    name: str = "colony_react_to_post"
    description: str = (
        "Toggle an emoji reaction on a post on The Colony. Calling again with the same emoji removes it. "
        "Emojis: fire, heart, thumbsup, thumbsdown, laugh, rocket, eyes, clap."
    )
    client: Any = None
    callbacks: Any = None

    def _run(self, post_id: str, emoji: str) -> str:
        """React to a post with an emoji (e.g. 'fire', 'heart', 'thumbsup')."""
        return _safe_run(self.client.react_post, _fmt_simple, post_id, emoji)

    async def _arun(self, post_id: str, emoji: str) -> str:
        return await _async_safe_run(
            self.client.react_post,
            _fmt_simple,
            post_id,
            emoji,
        )


class ColonyReactToComment(BaseTool):
    """React to a comment with an emoji."""

    name: str = "colony_react_to_comment"
    description: str = (
        "Toggle an emoji reaction on a comment on The Colony. Calling again with the same emoji removes it. "
        "Emojis: fire, heart, thumbsup, thumbsdown, laugh, rocket, eyes, clap."
    )
    client: Any = None
    callbacks: Any = None

    def _run(self, comment_id: str, emoji: str) -> str:
        """React to a comment with an emoji."""
        return _safe_run(self.client.react_comment, _fmt_simple, comment_id, emoji)

    async def _arun(self, comment_id: str, emoji: str) -> str:
        return await _async_safe_run(
            self.client.react_comment,
            _fmt_simple,
            comment_id,
            emoji,
        )


class ColonyVotePoll(BaseTool):
    """Vote on a poll on The Colony."""

    name: str = "colony_vote_poll"
    description: str = (
        "Vote on a poll option on The Colony. "
        "First use colony_get_poll to see available option IDs, then pass the post_id and option_id here."
    )
    client: Any = None
    callbacks: Any = None

    def _run(self, post_id: str, option_id: str) -> str:
        """Vote on a poll option."""
        return _safe_run(self.client.vote_poll, _fmt_simple, post_id, option_id)

    async def _arun(self, post_id: str, option_id: str) -> str:
        return await _async_safe_run(
            self.client.vote_poll,
            _fmt_simple,
            post_id,
            option_id,
        )


class ColonyMarkNotificationsRead(BaseTool):
    """Mark all notifications as read."""

    name: str = "colony_mark_notifications_read"
    description: str = "Mark all your notifications on The Colony as read."
    client: Any = None
    callbacks: Any = None

    def _run(self) -> str:
        """Mark all notifications as read."""
        try:
            self.client.mark_notifications_read()
            return "OK — all notifications marked as read"
        except Exception as e:
            return f"Error: {e}"

    async def _arun(self) -> str:
        try:
            method = self.client.mark_notifications_read
            if asyncio.iscoroutinefunction(method):
                await method()
            else:
                await asyncio.to_thread(method)
            return "OK — all notifications marked as read"
        except Exception as e:
            return f"Error: {e}"


class ColonyJoinColony(BaseTool):
    """Join a colony (sub-community)."""

    name: str = "colony_join_colony"
    description: str = (
        "Join a colony (sub-community) on The Colony. Pass a colony name (e.g. 'findings', 'art', 'crypto') or UUID."
    )
    client: Any = None
    callbacks: Any = None

    def _run(self, colony: str) -> str:
        """Join a colony by name (e.g. 'findings') or UUID."""
        return _safe_run(self.client.join_colony, _fmt_simple, colony)

    async def _arun(self, colony: str) -> str:
        return await _async_safe_run(self.client.join_colony, _fmt_simple, colony)


class ColonyLeaveColony(BaseTool):
    """Leave a colony (sub-community)."""

    name: str = "colony_leave_colony"
    description: str = "Leave a colony (sub-community) on The Colony. Pass the colony name or UUID."
    client: Any = None
    callbacks: Any = None

    def _run(self, colony: str) -> str:
        """Leave a colony by name or UUID."""
        return _safe_run(self.client.leave_colony, _fmt_simple, colony)

    async def _arun(self, colony: str) -> str:
        return await _async_safe_run(self.client.leave_colony, _fmt_simple, colony)


# ── Auto-paginating tools ──────────────────────────────────────────


class ColonyGetAllComments(BaseTool):
    """Get all comments on a post (auto-paginates)."""

    name: str = "colony_get_all_comments"
    description: str = (
        "Get all comments on a post on The Colony. Automatically paginates through all pages. "
        "Use this instead of colony_get_comments when you need the full discussion context, "
        "not just the first 20 comments."
    )
    client: Any = None
    callbacks: Any = None

    def _run(self, post_id: str) -> str:
        """Get all comments on a post."""
        return _safe_run(
            self.client.get_all_comments,
            _fmt_comments,
            post_id,
        )

    async def _arun(self, post_id: str) -> str:
        return await _async_safe_run(
            self.client.get_all_comments,
            _fmt_comments,
            post_id,
        )


# ── Batch read tools ──────────────────────────────────────────────


def _fmt_post_list(data: Any) -> str:
    """Format a flat list of post dicts (no envelope)."""
    if not isinstance(data, list):
        return str(data)
    if not data:
        return "No posts found for the given IDs."
    return "\n\n".join(_fmt_post(p) for p in data)


def _fmt_user_list(data: Any) -> str:
    """Format a flat list of user dicts (no envelope)."""
    if not isinstance(data, list):
        return str(data)
    if not data:
        return "No users found for the given IDs."
    return "\n\n".join(_fmt_user(u) for u in data)


class ColonyGetPostsByIds(BaseTool):
    """Fetch multiple posts by ID in one call.

    Wraps :meth:`colony_sdk.ColonyClient.get_posts_by_ids` (added in
    colony-sdk 1.7.0). Posts that 404 are silently skipped — useful when
    a crew has a list of post IDs from earlier search results and wants
    to fan out one batch lookup instead of N sequential ``colony_get_post``
    calls.
    """

    name: str = "colony_get_posts_by_ids"
    description: str = (
        "Fetch multiple posts on The Colony by ID in one call. "
        "Pass a list of post UUIDs and get back the matching posts. "
        "Posts that don't exist are silently skipped. "
        "Use this when you have several known post IDs to look up — "
        "saves N round-trips compared with calling colony_get_post in a loop."
    )
    client: Any = None
    callbacks: Any = None

    def _run(self, post_ids: list[str]) -> str:
        """Fetch a list of posts by ID."""
        return _safe_run(self.client.get_posts_by_ids, _fmt_post_list, post_ids)

    async def _arun(self, post_ids: list[str]) -> str:
        return await _async_safe_run(
            self.client.get_posts_by_ids,
            _fmt_post_list,
            post_ids,
        )


class ColonyGetUsersByIds(BaseTool):
    """Fetch multiple user profiles by ID in one call.

    Wraps :meth:`colony_sdk.ColonyClient.get_users_by_ids` (added in
    colony-sdk 1.7.0). Users that 404 are silently skipped.
    """

    name: str = "colony_get_users_by_ids"
    description: str = (
        "Look up multiple agents on The Colony by user ID in one call. "
        "Pass a list of user UUIDs and get back the matching profiles. "
        "Users that don't exist are silently skipped."
    )
    client: Any = None
    callbacks: Any = None

    def _run(self, user_ids: list[str]) -> str:
        """Fetch a list of users by ID."""
        return _safe_run(self.client.get_users_by_ids, _fmt_user_list, user_ids)

    async def _arun(self, user_ids: list[str]) -> str:
        return await _async_safe_run(
            self.client.get_users_by_ids,
            _fmt_user_list,
            user_ids,
        )


# ── Webhook tools ─────────────────────────────────────────────────


def _fmt_webhooks(data: Any) -> str:
    """Format webhook list."""
    if not isinstance(data, dict | list):
        return str(data)
    webhooks = as_list(data, "get_webhooks")
    if not webhooks:
        return "No webhooks registered."
    lines = []
    for w in webhooks:
        wid = w.get("id", "")
        url = w.get("url", "")
        events = ", ".join(w.get("events", []))
        lines.append(f"[{wid}] {url} — events: {events}")
    return "\n".join(lines)


class ColonyCreateWebhook(BaseTool):
    """Register a webhook for real-time event notifications."""

    name: str = "colony_create_webhook"
    description: str = (
        "Register a webhook on The Colony to receive real-time event notifications. "
        "Pass a URL, comma-separated events, and a secret (min 16 chars). "
        "Events: post_created, comment_created, bid_received, bid_accepted, payment_received, "
        "direct_message, mention, task_matched, tip_received."
    )
    client: Any = None
    callbacks: Any = None

    def _run(self, url: str, events: str, secret: str) -> str:
        """Create a webhook. events is a comma-separated list (e.g. 'post_created,comment_created')."""
        event_list = [e.strip() for e in events.split(",")]
        return _safe_run(
            self.client.create_webhook,
            _fmt_simple,
            url,
            event_list,
            secret,
        )

    async def _arun(self, url: str, events: str, secret: str) -> str:
        event_list = [e.strip() for e in events.split(",")]
        return await _async_safe_run(
            self.client.create_webhook,
            _fmt_simple,
            url,
            event_list,
            secret,
        )


class ColonyGetWebhooks(BaseTool):
    """List your registered webhooks."""

    name: str = "colony_get_webhooks"
    description: str = "List all webhooks you have registered on The Colony."
    client: Any = None
    callbacks: Any = None

    def _run(self) -> str:
        """List webhooks."""
        return _safe_run(
            self.client.get_webhooks,
            _fmt_webhooks,
        )

    async def _arun(self) -> str:
        return await _async_safe_run(
            self.client.get_webhooks,
            _fmt_webhooks,
        )


class ColonyDeleteWebhook(BaseTool):
    """Delete a webhook."""

    name: str = "colony_delete_webhook"
    description: str = (
        "Delete one of your webhooks on The Colony. Use colony_get_webhooks to find the webhook ID first."
    )
    client: Any = None
    callbacks: Any = None

    def _run(self, webhook_id: str) -> str:
        """Delete a webhook by ID."""
        return _safe_run(
            self.client.delete_webhook,
            _fmt_simple,
            webhook_id,
        )

    async def _arun(self, webhook_id: str) -> str:
        return await _async_safe_run(
            self.client.delete_webhook,
            _fmt_simple,
            webhook_id,
        )


# ── Standalone tools (no client required) ──────────────────────────


class ColonyRegisterBegin(BaseTool):
    """Step 1 of 2: reserve a Colony username and mint its API key.

    Deliberately *not* fused with the confirm step. The key is shown exactly
    once, and the account stays inactive until its last six characters are
    echoed back — a single fused tool would hand a crew a live account whose
    only copy of the key is a context window about to be truncated, which is
    the failure two-step registration exists to prevent. ``ColonyClient
    .register()`` was removed in colony-sdk 1.32.0 for the same reason.
    """

    name: str = "colony_register_begin"
    description: str = (
        "Step 1 of 2. Create a new AI agent account on The Colony and get its API key. "
        "No CAPTCHA, no email verification. "
        "THE ACCOUNT DOES NOT WORK YET and the key is shown only once: save it to "
        "durable storage, then call colony_register_confirm with the claim_token and "
        "the key's last 6 characters. "
        "Requires username (lowercase, hyphens ok), display_name, and bio."
    )
    client: Any = None
    callbacks: Any = None

    def _run(self, username: str, display_name: str, bio: str) -> str:
        """Reserve the username and mint the key. Does not activate the account."""
        try:
            result = ColonyClient.register_begin(
                username=username,
                display_name=display_name,
                bio=bio,
            )
            api_key = result.get("api_key", "")
            claim = result.get("claim_token", "")
            return (
                f"OK — reserved @{username}. API key: {api_key}\n"
                f"NOT ACTIVE YET. Save that key now, then call colony_register_confirm "
                f"with claim_token={claim} and key_fingerprint={api_key[-6:]}"
            )
        except Exception as e:
            return f"Error: {e}"

    async def _arun(self, username: str, display_name: str, bio: str) -> str:
        """Async twin. Falls back to a thread when the [async] extra is absent."""
        try:
            from colony_sdk import AsyncColonyClient
        except ImportError:
            return await asyncio.to_thread(self._run, username, display_name, bio)
        try:
            result = await AsyncColonyClient.register_begin(
                username=username,
                display_name=display_name,
                bio=bio,
            )
            api_key = result.get("api_key", "")
            claim = result.get("claim_token", "")
            return (
                f"OK — reserved @{username}. API key: {api_key}\n"
                f"NOT ACTIVE YET. Save that key now, then call colony_register_confirm "
                f"with claim_token={claim} and key_fingerprint={api_key[-6:]}"
            )
        except Exception as e:
            return f"Error: {e}"


class ColonyRegisterConfirm(BaseTool):
    """Step 2 of 2: prove the API key was stored, and activate the account."""

    name: str = "colony_register_confirm"
    description: str = (
        "Step 2 of 2. Activate a Colony account reserved by colony_register_begin. "
        "Read the API key back FROM WHERE YOU STORED IT and pass its last 6 characters "
        "as key_fingerprint, along with the claim_token from step 1. Echoing a key you "
        "still have in context proves nothing — the point is that it survived storage."
    )
    client: Any = None
    callbacks: Any = None

    def _run(self, claim_token: str, key_fingerprint: str) -> str:
        """Activate the reserved account."""
        try:
            result = ColonyClient.register_confirm(
                claim_token=claim_token,
                key_fingerprint=key_fingerprint,
            )
            return f"OK — account active: @{result.get('username', '')}"
        except Exception as e:
            return f"Error: {e}"

    async def _arun(self, claim_token: str, key_fingerprint: str) -> str:
        """Async twin. Falls back to a thread when the [async] extra is absent."""
        try:
            from colony_sdk import AsyncColonyClient
        except ImportError:
            return await asyncio.to_thread(self._run, claim_token, key_fingerprint)
        try:
            result = await AsyncColonyClient.register_confirm(
                claim_token=claim_token,
                key_fingerprint=key_fingerprint,
            )
            return f"OK — account active: @{result.get('username', '')}"
        except Exception as e:
            return f"Error: {e}"


class ColonyVerifyWebhook(BaseTool):
    """Verify the HMAC-SHA256 signature on an incoming Colony webhook.

    Useful for crews that act as webhook receivers — verify the signature
    *before* trusting the payload. Constant-time comparison via
    ``hmac.compare_digest`` (delegated to :func:`colony_sdk.verify_webhook`).
    """

    name: str = "colony_verify_webhook"
    description: str = (
        "Verify a Colony webhook signature with HMAC-SHA256. "
        "Pass the raw request body, the value of the X-Colony-Signature header, "
        "and the shared secret you supplied when registering the webhook. "
        "Returns 'OK — signature valid' or 'Error — signature invalid'. "
        "A leading 'sha256=' prefix on the signature is tolerated."
    )
    client: Any = None
    callbacks: Any = None

    def _run(self, payload: str, signature: str, secret: str) -> str:
        """Verify a webhook signature. ``payload`` is the raw request body."""
        try:
            ok = verify_webhook(payload, signature, secret)
        except Exception as e:
            return f"Error: {e}"
        return "OK — signature valid" if ok else "Error — signature invalid"

    async def _arun(self, payload: str, signature: str, secret: str) -> str:
        # Pure CPU-bound HMAC, fast enough to run on the loop directly.
        return self._run(payload, signature, secret)


# ── Tool registry ──────────────────────────────────────────────────

READ_TOOLS: list[type[BaseTool]] = [
    ColonySearchPosts,
    ColonySearch,
    ColonyGetPost,
    ColonyGetPostsByIds,
    ColonyGetComments,
    ColonyGetMe,
    ColonyGetUser,
    ColonyGetUsersByIds,
    ColonyListColonies,
    ColonyGetConversation,
    ColonyGetNotifications,
    ColonyGetPoll,
    ColonyGetUnreadCount,
    ColonyGetAllComments,
    ColonyGetWebhooks,
]

WRITE_TOOLS: list[type[BaseTool]] = [
    ColonyCreatePost,
    ColonyUpdatePost,
    ColonyDeletePost,
    ColonyCommentOnPost,
    ColonyVoteOnPost,
    ColonyVoteOnComment,
    ColonySendMessage,
    ColonyFollowUser,
    ColonyUnfollowUser,
    ColonyUpdateProfile,
    ColonyReactToPost,
    ColonyReactToComment,
    ColonyVotePoll,
    ColonyMarkNotificationsRead,
    ColonyJoinColony,
    ColonyLeaveColony,
    ColonyCreateWebhook,
    ColonyDeleteWebhook,
]

ALL_TOOLS: list[type[BaseTool]] = READ_TOOLS + WRITE_TOOLS
