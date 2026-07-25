"""Regression tests for three tools that returned "nothing found" on every call.

Proven against the live API on 2026-07-25 before the fix:

    colony_get_posts      API returned 3 rows  ->  "No posts found."
    colony_search         API returned 3 rows  ->  "No results found."
    colony_get_comments   API returned 7 rows  ->  "No comments found."

The formatters looked for `posts` / `results` / `comments`; the API sends
`items`. Every lookup missed and fell through to `[]`.

Why nothing caught it: the existing tests fed the formatters the shape the
formatters expected, so they confirmed the guess rather than checking it. These
tests use the shapes the API **actually** returns, captured from live responses,
which is the only fixture that can catch a wrong-key bug.

Every case is paired with a control, because a formatter that rendered
everything would pass the positive tests too.
"""

from __future__ import annotations

import logging
from typing import Any

import pytest

from crewai_colony._response import as_list
from crewai_colony.tools import (
    _fmt_colonies,
    _fmt_comments,
    _fmt_notifications,
    _fmt_posts,
    _fmt_search,
    _fmt_webhooks,
)

# Rows trimmed from real API responses.
POST = {
    "id": "p1",
    "title": "A title",
    "body": "A body",
    "author": {"username": "someone"},
    "score": 3,
    "comment_count": 1,
    "created_at": "2026-07-25T10:00:00Z",
}
COMMENT = {
    "id": "c1",
    "body": "A comment",
    "author": {"username": "someone"},
    "score": 1,
    "created_at": "2026-07-25T10:00:00Z",
}
COLONY = {"name": "general", "description": "General discussion", "member_count": 42}
NOTIF = {"id": "n1", "type": "reply", "preview": "hello", "read": False}
HOOK = {"id": "w1", "url": "https://example.test/hook", "events": ["post.created"]}


# ── the shapes the API really sends ───────────────────────────────────


class TestRealApiShapes:
    """Each fixture is the measured live shape, so a wrong-key regression fails."""

    def test_get_posts_paginates_under_items(self) -> None:
        """THE bug. `get_posts()` -> {"items", "total", "next_cursor"}."""
        out = _fmt_posts({"items": [POST], "total": 1, "next_cursor": None})
        assert "No posts found." not in out
        assert "A title" in out

    def test_search_paginates_under_items(self) -> None:
        """`search()` -> {"items", "total", "next_cursor", "users"}."""
        out = _fmt_search({"items": [POST], "total": 1, "next_cursor": None, "users": []})
        assert "No results found." not in out
        assert "A title" in out

    def test_get_comments_paginates_under_items(self) -> None:
        """`get_comments()` -> {"items", "total", "next_cursor", "page"}."""
        out = _fmt_comments({"items": [COMMENT], "total": 1, "next_cursor": None, "page": 1})
        assert "No comments found." not in out
        assert "A comment" in out

    def test_get_all_comments_is_a_bare_list(self) -> None:
        """The SAME formatter is fed by a bare-list endpoint too, which is why
        per-site key guessing could never have worked."""
        out = _fmt_comments([COMMENT])
        assert "No comments found." not in out

    @pytest.mark.parametrize(
        ("fmt", "row", "marker"),
        [
            (_fmt_colonies, COLONY, "No colonies found."),
            (_fmt_notifications, NOTIF, "No notifications."),
            (_fmt_webhooks, HOOK, "No webhooks"),
        ],
    )
    def test_bare_list_endpoints(self, fmt: Any, row: dict, marker: str) -> None:
        """`get_colonies` / `get_notifications` / `get_webhooks` -> bare list."""
        assert marker not in fmt([row])


# ── the async envelope (colony-sdk < 1.30.0) ──────────────────────────


class TestAsyncEnvelope:
    """`AsyncColonyClient` wrapped bare arrays as {"data": [...]} before
    colony-sdk 1.30.0, matching none of the old guessed keys — so the same
    formatters were silently empty under AsyncColonyToolkit."""

    @pytest.mark.parametrize(
        ("fmt", "row", "marker"),
        [
            (_fmt_posts, POST, "No posts found."),
            (_fmt_search, POST, "No results found."),
            (_fmt_comments, COMMENT, "No comments found."),
            (_fmt_colonies, COLONY, "No colonies found."),
            (_fmt_notifications, NOTIF, "No notifications."),
            (_fmt_webhooks, HOOK, "No webhooks"),
        ],
    )
    def test_data_envelope_is_unwrapped(self, fmt: Any, row: dict, marker: str) -> None:
        assert marker not in fmt({"data": [row]})


# ── controls ──────────────────────────────────────────────────────────


class TestControls:
    """Without these, a formatter that rendered everything would pass above."""

    @pytest.mark.parametrize(
        ("fmt", "marker"),
        [
            (_fmt_posts, "No posts found."),
            (_fmt_search, "No results found."),
            (_fmt_comments, "No comments found."),
            (_fmt_colonies, "No colonies found."),
            (_fmt_notifications, "No notifications."),
        ],
    )
    def test_a_genuinely_empty_result_still_reads_as_empty(self, fmt: Any, marker: str) -> None:
        """ "Nothing there" is a real answer and must survive the fix."""
        assert marker in fmt([])
        assert marker in fmt({"items": []})

    @pytest.mark.parametrize(
        "fmt",
        [_fmt_posts, _fmt_search, _fmt_comments, _fmt_colonies, _fmt_notifications, _fmt_webhooks],
    )
    def test_a_non_collection_is_still_echoed(self, fmt: Any) -> None:
        """House convention: an error string is echoed rather than hidden behind
        "nothing found" — which is the same reasoning as this whole change, so
        it is preserved."""
        assert fmt("an error string") == "an error string"


# ── the helper itself ─────────────────────────────────────────────────


class TestAsList:
    def test_items_wins_over_a_stale_key(self) -> None:
        """`items` is checked first because it is the real one."""
        assert as_list({"items": [1], "posts": [2, 3]}, "get_posts") == [1]

    def test_unrecognised_dict_is_empty_AND_logged(self, caplog: pytest.LogCaptureFixture) -> None:
        """The half that matters most: silence is what let three dead tools
        ship. An unknown shape must leave a trace."""
        with caplog.at_level(logging.WARNING, logger="crewai_colony"):
            assert as_list({"unexpected": [1]}, "get_posts") == []
        assert "get_posts" in caplog.text
        assert "no recognised list" in caplog.text

    def test_the_warning_stays_quiet_on_known_shapes(self, caplog: pytest.LogCaptureFixture) -> None:
        """CONTROL: a helper that warned on every call would satisfy the test
        above while making the logs worthless."""
        with caplog.at_level(logging.WARNING, logger="crewai_colony"):
            as_list([1], "get_colonies")
            as_list({"items": [1]}, "get_posts")
            as_list({"data": [1]}, "get_notifications")
            as_list([], "get_posts")
        assert caplog.text == ""
