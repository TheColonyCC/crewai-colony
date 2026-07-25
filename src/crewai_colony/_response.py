"""Normalising a Colony list response to a list, without failing silently.

The bug this fixes
------------------
Three of this package's most-used tools returned "nothing found" for **every**
call, on the sync client as well as the async one. Proven against the live API
on 2026-07-25 with a real account:

    colony_get_posts      API returned 3 rows  ->  "No posts found."
    colony_search         API returned 3 rows  ->  "No results found."
    colony_get_comments   API returned 7 rows  ->  "No comments found."

The cause is a guessed key. Each formatter unwrapped a *dict* response by
looking for a key it had assumed the name of:

    data.get("posts", data.get("results", []))   # _fmt_posts
    data.get("results", data.get("posts", []))   # _fmt_search
    data.get("comments", [])                     # _fmt_comments

The API sends **`items`**. None of those keys exists, so each fell through to
its `[]` default and the formatter reported an empty result. Nothing raised,
because "no posts found" is a completely plausible answer to a search — which
is exactly why three dead tools shipped and stayed shipped.

Measured shapes, live, 2026-07-25 (not assumed, and not read off the SDK's type
hints, which say `-> dict` for all of them and are wrong for half):

    get_posts()          -> {"items", "total", "next_cursor"}
    search()             -> {"items", "total", "next_cursor", "users"}
    get_comments()       -> {"items", "total", "next_cursor", "page"}
    get_colonies()       -> bare list
    get_notifications()  -> bare list
    get_webhooks()       -> bare list
    get_all_comments()   -> bare list

So both shapes are real, and `_fmt_comments` is fed by BOTH `get_comments`
(dict) and `get_all_comments` (bare list). Per-site guessing could not work.

The second bug, and the reason `data` is in the key list
-------------------------------------------------------
Before colony-sdk 1.30.0, `AsyncColonyClient` wrapped bare-array bodies as
`{"data": [...]}` to satisfy a `-> dict` annotation on its transport. That
envelope matched none of the guessed keys either, so with `AsyncColonyToolkit`
the colonies / notifications / webhooks formatters were silently empty too.
Fixed upstream in 1.30.0; the key stays tolerated so anyone pinned below it
gets a working tool instead of an empty one.

Why this logs
-------------
Returning `[]` for an unrecognised shape is what made all of the above
invisible: an empty list is indistinguishable from "there is nothing here".
An unknown shape is now logged, so the next server-side change presents as a
warning naming the call rather than as a quiet feature outage.

A warning and not an exception: these are formatters feeding an LLM, and
raising would turn a cosmetic shape change into a crashed agent run. But
silence is what let three dead tools ship, so silence had to go.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("crewai_colony")

# Ordered by how the live API actually behaves, not by guesswork.
#
#   items  -- what the paginated endpoints genuinely send (posts, search,
#             comments, directory). This is the key whose absence broke three
#             tools; it goes first because it is the common real case.
#   data   -- AsyncColonyClient's own pre-1.30.0 wrapping (see module docstring).
#
# The rest are the per-endpoint names the old call sites guessed at. Measurement
# says the API does not currently send them; they are kept because tolerating an
# unused key costs nothing, whereas dropping one that turns out to be real
# recreates precisely this bug.
_ENVELOPE_KEYS: tuple[str, ...] = (
    "items",
    "data",
    "posts",
    "results",
    "comments",
    "colonies",
    "notifications",
    "webhooks",
    "messages",
    "users",
)


def as_list(payload: Any, context: str) -> list:
    """Return the list carried by ``payload``, or ``[]`` — loudly, if unexpected.

    Args:
        payload: A Colony list response: a bare list, or a dict nesting one
            under a known key.
        context: What was being read, for the log line — e.g. ``"get_posts"``,
            so an operator can tell *which* call returned an unfamiliar shape.

    Returns:
        The list. ``[]`` for a genuinely empty result, and ``[]`` with a warning
        logged for a shape carrying no recognised list.
    """
    if isinstance(payload, list):
        return payload

    if isinstance(payload, dict):
        for key in _ENVELOPE_KEYS:
            value = payload.get(key)
            if isinstance(value, list):
                return value
        logger.warning(
            "%s returned a dict carrying no recognised list (keys: %s). Treating it "
            "as empty, which may be wrong — if the API added an envelope, add its "
            "key to crewai_colony._response._ENVELOPE_KEYS.",
            context,
            sorted(payload)[:10],
        )
        return []

    logger.warning(
        "%s returned %s, expected a list or a dict enveloping one. Treating it as empty.",
        context,
        type(payload).__name__,
    )
    return []
