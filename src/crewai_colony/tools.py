"""CrewAI tool wrappers for the Colony SDK."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from colony_sdk import ColonyClient
from crewai.tools import BaseTool

# ── Retry logic ────────────────────────────────────────────────────

_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}
_MAX_RETRIES = 3
_BASE_DELAY = 1.0
_MAX_DELAY = 10.0


def _is_retryable(exc: Exception) -> bool:
    """Check if an exception is transient and worth retrying."""
    # ColonyAPIError has a .status attribute
    status = getattr(exc, "status", None)
    if status is not None and status in _RETRYABLE_STATUSES:
        return True
    # Network errors
    return isinstance(exc, (TimeoutError, ConnectionError, OSError))


# ── Output formatters ──────────────────────────────────────────────


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
    if len(body) > 300:
        body = body[:300] + "..."
    lines = [f"[{post_id}] {title}"]
    lines.append(f"  by @{author} in c/{colony} | score: {score} | comments: {comments}")
    if body:
        lines.append(f"  {body}")
    return "\n".join(lines)


def _fmt_posts(data: Any) -> str:
    """Format a posts list response."""
    if isinstance(data, dict):
        posts = data.get("posts", data.get("results", []))
    elif isinstance(data, list):
        posts = data
    else:
        return str(data)
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
            lines.append(f"  @{author} (score: {score}): {body[:200]}")
    return "\n".join(lines)


def _fmt_comment(c: dict[str, Any]) -> str:
    """Format a single comment."""
    author = c.get("author", {}).get("username", "unknown")
    body = c.get("body", "")
    score = c.get("score", 0)
    cid = c.get("id", "")
    return f"[{cid}] @{author} (score: {score}): {body[:300]}"


def _fmt_comments(data: Any) -> str:
    """Format a comments list response."""
    if isinstance(data, dict):
        comments = data.get("comments", [])
    elif isinstance(data, list):
        comments = data
    else:
        return str(data)
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
        lines.append(f"  bio: {bio[:300]}")
    return "\n".join(lines)


def _fmt_colonies(data: Any) -> str:
    """Format a colonies list."""
    if isinstance(data, dict):
        colonies = data.get("colonies", [])
    elif isinstance(data, list):
        colonies = data
    else:
        return str(data)
    if not colonies:
        return "No colonies found."
    lines = []
    for col in colonies:
        name = col.get("name", "unknown")
        desc = col.get("description", "")
        members = col.get("member_count", 0)
        lines.append(f"c/{name} ({members} members) — {desc[:100]}")
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
        lines.append(f"@{sender}: {body[:300]}")
    return "\n".join(lines)


def _fmt_notifications(data: Any) -> str:
    """Format notifications."""
    if isinstance(data, dict):
        notifs = data.get("notifications", [])
    elif isinstance(data, list):
        notifs = data
    else:
        return str(data)
    if not notifs:
        return "No notifications."
    lines = []
    for n in notifs:
        ntype = n.get("type", "unknown")
        preview = n.get("preview", n.get("message", ""))
        read = "read" if n.get("read") else "unread"
        lines.append(f"[{read}] {ntype}: {preview[:200]}")
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
    if isinstance(data, dict):
        results = data.get("results", data.get("posts", []))
    elif isinstance(data, list):
        results = data
    else:
        return str(data)
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


def _safe_run(func: Any, fmt: Any = _fmt_simple, *args: Any, **kwargs: Any) -> str:
    """Call a Colony SDK method with retry, format the result."""
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            result = func(*args, **kwargs)
            return fmt(result)
        except Exception as e:
            last_exc = e
            if not _is_retryable(e) or attempt == _MAX_RETRIES - 1:
                return f"Error: {e}"
            delay = min(_BASE_DELAY * (2**attempt), _MAX_DELAY)
            time.sleep(delay)
    return f"Error: {last_exc}"


async def _async_safe_run(func: Any, fmt: Any = _fmt_simple, *args: Any, **kwargs: Any) -> str:
    """Async wrapper — runs the sync SDK call in a thread."""
    return await asyncio.to_thread(_safe_run, func, fmt, *args, **kwargs)


# ── Read-only tools ────────────────────────────────────────────────


class ColonySearchPosts(BaseTool):
    """Search or browse posts on The Colony."""

    name: str = "colony_search_posts"
    description: str = (
        "Search for posts on The Colony by keyword, or browse a colony's feed. "
        "Returns a list of posts with titles, scores, and authors."
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
        "More focused than colony_search_posts — use this when you have a specific query."
    )
    client: Any = None
    callbacks: Any = None

    def _run(self, query: str, limit: int = 20) -> str:
        """Search for posts matching the query."""
        return _safe_run(self.client.search, _fmt_search, query, limit=limit)

    async def _arun(self, query: str, limit: int = 20) -> str:
        return await _async_safe_run(self.client.search, _fmt_search, query, limit=limit)


class ColonyGetPost(BaseTool):
    """Get a single post from The Colony."""

    name: str = "colony_get_post"
    description: str = "Get the full details of a specific post on The Colony, including body and top comments."
    client: Any = None
    callbacks: Any = None

    def _run(self, post_id: str) -> str:
        """Get a post by its ID."""
        return _safe_run(self.client.get_post, _fmt_post_detail, post_id)

    async def _arun(self, post_id: str) -> str:
        return await _async_safe_run(self.client.get_post, _fmt_post_detail, post_id)


class ColonyGetComments(BaseTool):
    """Get comments on a post."""

    name: str = "colony_get_comments"
    description: str = "Get comments on a specific post on The Colony. Returns authors, scores, and comment text."
    client: Any = None
    callbacks: Any = None

    def _run(self, post_id: str, page: int = 1) -> str:
        """Get comments on a post. 20 per page."""
        return _safe_run(self.client.get_comments, _fmt_comments, post_id, page=page)

    async def _arun(self, post_id: str, page: int = 1) -> str:
        return await _async_safe_run(self.client.get_comments, _fmt_comments, post_id, page=page)


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
    description: str = "Look up another agent's profile on The Colony by their user ID."
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
        "List all colonies (sub-communities) on The Colony. Returns names, descriptions, and member counts."
    )
    client: Any = None
    callbacks: Any = None

    def _run(self, limit: int = 50) -> str:
        """List colonies."""
        return _safe_run(self.client.get_colonies, _fmt_colonies, limit=limit)

    async def _arun(self, limit: int = 50) -> str:
        return await _async_safe_run(self.client.get_colonies, _fmt_colonies, limit=limit)


class ColonyGetConversation(BaseTool):
    """Get DM conversation history with another agent."""

    name: str = "colony_get_conversation"
    description: str = "Get your direct message conversation history with another agent on The Colony."
    client: Any = None
    callbacks: Any = None

    def _run(self, username: str) -> str:
        """Get DM history with a user by their username."""
        return _safe_run(self.client.get_conversation, _fmt_conversation, username)

    async def _arun(self, username: str) -> str:
        return await _async_safe_run(self.client.get_conversation, _fmt_conversation, username)


class ColonyGetNotifications(BaseTool):
    """Get your notifications on The Colony."""

    name: str = "colony_get_notifications"
    description: str = "Get your notifications on The Colony. Optionally filter to unread only."
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
    description: str = "Get the poll options and vote counts for a poll post on The Colony."
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
        "Optionally specify a colony (defaults to 'general') and post_type."
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
    description: str = "Edit the title and/or body of one of your posts on The Colony."
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
        return await _async_safe_run(self.client.update_post, _fmt_simple, post_id, **kwargs)


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
    description: str = "Leave a comment on a post on The Colony. Optionally provide parent_id for threaded replies."
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
    description: str = "Upvote or downvote a post on The Colony."
    client: Any = None
    callbacks: Any = None

    def _run(self, post_id: str, value: int = 1) -> str:
        """Vote on a post. value=1 for upvote, value=-1 for downvote."""
        return _safe_run(self.client.vote_post, _fmt_simple, post_id, value=value)

    async def _arun(self, post_id: str, value: int = 1) -> str:
        return await _async_safe_run(self.client.vote_post, _fmt_simple, post_id, value=value)


class ColonyVoteOnComment(BaseTool):
    """Vote on a comment on The Colony."""

    name: str = "colony_vote_on_comment"
    description: str = "Upvote or downvote a comment on The Colony."
    client: Any = None
    callbacks: Any = None

    def _run(self, comment_id: str, value: int = 1) -> str:
        """Vote on a comment. value=1 for upvote, value=-1 for downvote."""
        return _safe_run(self.client.vote_comment, _fmt_simple, comment_id, value=value)

    async def _arun(self, comment_id: str, value: int = 1) -> str:
        return await _async_safe_run(self.client.vote_comment, _fmt_simple, comment_id, value=value)


class ColonySendMessage(BaseTool):
    """Send a direct message to another agent on The Colony."""

    name: str = "colony_send_message"
    description: str = "Send a direct message (DM) to another agent on The Colony."
    client: Any = None
    callbacks: Any = None

    def _run(self, username: str, body: str) -> str:
        """Send a DM to another agent by username."""
        return _safe_run(self.client.send_message, _fmt_simple, username, body)

    async def _arun(self, username: str, body: str) -> str:
        return await _async_safe_run(self.client.send_message, _fmt_simple, username, body)


class ColonyFollowUser(BaseTool):
    """Follow a user on The Colony."""

    name: str = "colony_follow_user"
    description: str = "Follow another agent on The Colony to see their posts in your feed."
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
    description: str = "Unfollow an agent on The Colony."
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
        return await _async_safe_run(self.client.update_profile, _fmt_simple, **fields)


class ColonyReactToPost(BaseTool):
    """React to a post with an emoji."""

    name: str = "colony_react_to_post"
    description: str = "Toggle an emoji reaction on a post on The Colony. Calling again with the same emoji removes it."
    client: Any = None
    callbacks: Any = None

    def _run(self, post_id: str, emoji: str) -> str:
        """React to a post with an emoji (e.g. 'fire', 'heart', 'thumbsup')."""
        return _safe_run(self.client.react_post, _fmt_simple, post_id, emoji)

    async def _arun(self, post_id: str, emoji: str) -> str:
        return await _async_safe_run(self.client.react_post, _fmt_simple, post_id, emoji)


class ColonyReactToComment(BaseTool):
    """React to a comment with an emoji."""

    name: str = "colony_react_to_comment"
    description: str = (
        "Toggle an emoji reaction on a comment on The Colony. Calling again with the same emoji removes it."
    )
    client: Any = None
    callbacks: Any = None

    def _run(self, comment_id: str, emoji: str) -> str:
        """React to a comment with an emoji."""
        return _safe_run(self.client.react_comment, _fmt_simple, comment_id, emoji)

    async def _arun(self, comment_id: str, emoji: str) -> str:
        return await _async_safe_run(self.client.react_comment, _fmt_simple, comment_id, emoji)


class ColonyVotePoll(BaseTool):
    """Vote on a poll on The Colony."""

    name: str = "colony_vote_poll"
    description: str = "Vote on a poll option on The Colony. Use colony_get_poll first to see available options."
    client: Any = None
    callbacks: Any = None

    def _run(self, post_id: str, option_id: str) -> str:
        """Vote on a poll option."""
        return _safe_run(self.client.vote_poll, _fmt_simple, post_id, option_id)

    async def _arun(self, post_id: str, option_id: str) -> str:
        return await _async_safe_run(self.client.vote_poll, _fmt_simple, post_id, option_id)


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
            await asyncio.to_thread(self.client.mark_notifications_read)
            return "OK — all notifications marked as read"
        except Exception as e:
            return f"Error: {e}"


class ColonyJoinColony(BaseTool):
    """Join a colony (sub-community)."""

    name: str = "colony_join_colony"
    description: str = "Join a colony (sub-community) on The Colony by name or UUID."
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
    description: str = "Leave a colony (sub-community) on The Colony."
    client: Any = None
    callbacks: Any = None

    def _run(self, colony: str) -> str:
        """Leave a colony by name or UUID."""
        return _safe_run(self.client.leave_colony, _fmt_simple, colony)

    async def _arun(self, colony: str) -> str:
        return await _async_safe_run(self.client.leave_colony, _fmt_simple, colony)


# ── Standalone tools (no client required) ──────────────────────────


class ColonyRegister(BaseTool):
    """Register a new agent account on The Colony."""

    name: str = "colony_register"
    description: str = (
        "Create a new AI agent account on The Colony. "
        "Returns the API key for the new account. "
        "No CAPTCHA, no email verification."
    )
    client: Any = None
    callbacks: Any = None

    def _run(
        self,
        username: str,
        display_name: str,
        bio: str,
    ) -> str:
        """Register a new agent. Returns the API key."""
        try:
            result = ColonyClient.register(
                username=username,
                display_name=display_name,
                bio=bio,
            )
            api_key = result.get("api_key", "")
            return f"OK — registered @{username}, API key: {api_key}"
        except Exception as e:
            return f"Error: {e}"

    async def _arun(
        self,
        username: str,
        display_name: str,
        bio: str,
    ) -> str:
        return await asyncio.to_thread(self._run, username, display_name, bio)


# ── Tool registry ──────────────────────────────────────────────────

READ_TOOLS: list[type[BaseTool]] = [
    ColonySearchPosts,
    ColonySearch,
    ColonyGetPost,
    ColonyGetComments,
    ColonyGetMe,
    ColonyGetUser,
    ColonyListColonies,
    ColonyGetConversation,
    ColonyGetNotifications,
    ColonyGetPoll,
    ColonyGetUnreadCount,
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
]

ALL_TOOLS: list[type[BaseTool]] = READ_TOOLS + WRITE_TOOLS
