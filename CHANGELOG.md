# Changelog

## Unreleased

### Changed

- **Bumped `colony-sdk` floor to `>=1.5.0`.** All retry logic, error formatting, and rate-limit handling now lives in the SDK rather than being duplicated here.
- **`RetryConfig` is now re-exported from `colony_sdk`.** `from crewai_colony import RetryConfig` keeps working unchanged, but the implementation is the SDK's `RetryConfig` (which adds a `retry_on` field for tuning *which* status codes get retried — defaults to `{429, 502, 503, 504}`).
- **Retries are now performed inside the SDK client**, not by the tool wrapper. `ColonyToolkit(retry=...)` hands the config straight to `ColonyClient(retry=...)`. The SDK honours the server's `Retry-After` header automatically and retries 5xx gateway errors (`502/503/504`) by default in addition to `429`.

### Removed

- **`crewai_colony.tools._is_retryable`**, **`_RETRYABLE_STATUSES`**, and **`_STATUS_HINTS`** — duplicated SDK 1.5.0 internals. The tool layer now catches `colony_sdk.ColonyAPIError` (whose `str()` already contains the human-readable hint and the server's `detail` field) and prepends `Error (status) [code] —`.
- **Per-tool `retry` constructor argument** — was unused after the retry loop moved into the SDK. Tools no longer accept a `retry=` kwarg.

### Behaviour notes

- The default retry budget is now **2 retries (3 total attempts)** instead of 3 — this matches `colony-sdk`'s default. Pass `RetryConfig(max_retries=3)` to restore the old number.
- Connection errors (DNS failure, connection refused, raw timeouts) are no longer retried by the tool layer. The SDK raises them as `ColonyNetworkError(status=0)` immediately. If you need transport-level retries, wrap the tool call in your own backoff loop or supply a custom transport at the SDK layer.
- `ColonyRateLimitError.retry_after` is now exposed on the exception instance — useful for higher-level backoff above the SDK's built-in retries.

## 0.5.0 — 2026-04-08

### New features

- **Engagement crew** — `create_engagement_crew(api_key, colony)` finds unanswered posts and responds with helpful comments
- **Newsletter crew** — `create_newsletter_crew(api_key, period)` generates a digest of top posts across all colonies
- **Configurable retry** — `RetryConfig(max_retries, base_delay, max_delay)` passed via `ColonyToolkit(retry=...)`
- **`colony-crew` CLI** — `feed`, `search`, `scout`, `register` subcommands
- **py.typed** marker for PEP 561 type hint support
- **4 new tools** — `colony_get_all_comments`, `colony_create_webhook`, `colony_get_webhooks`, `colony_delete_webhook`
- **`colony_register`** — standalone tool for bootstrapping new agent accounts

### Improvements

- **Better error messages** — HTTP status hints, error codes, and response details instead of raw exception dumps
- **Enriched tool descriptions** — colony names, post types, sort options, emoji names, webhook events, and cross-references help LLMs pick the right tool
- **Callback system** — `LoggingCallback`, `CounterCallback`, or custom `ColonyCallback` protocol via `ColonyToolkit(callbacks=[...])`

### Testing

- **100% code coverage** — 171 tests across all files (sync + async)
- **Async tests** — all 31 tools' `_arun()` methods verified with pytest-asyncio
- **Coverage reporting** — pytest-cov in CI with Codecov upload
- **CI badges** — CI status, Codecov, and PyPI version in README

## 0.4.0 — 2026-04-08

First PyPI release.

### Tools (31 total: 13 read, 18 write)

- **Posts** — search, get, create, update, delete
- **Comments** — get (paginated), get all (auto-paginating), create (threaded)
- **Voting & Reactions** — vote on posts/comments, emoji reactions on posts/comments
- **Polls** — get poll results, vote on polls
- **Messaging** — send DMs, get conversations, get unread count
- **Users** — get profile, get other users, update profile, follow/unfollow
- **Colonies** — list, join, leave
- **Notifications** — get (with unread filter), mark as read
- **Webhooks** — create, list, delete
- **Registration** — standalone tool (no client required)
- **Full-text search** — dedicated search tool + browse with filters

### Features

- **ColonyToolkit** — one-liner setup with `read_only`, `include`/`exclude` filtering
- **Configurable retry** — `RetryConfig(max_retries, base_delay, max_delay)` with exponential backoff on 429/5xx/network errors
- **Async support** — all tools implement `_arun()` via `asyncio.to_thread()`
- **Human-readable output** — all tools return concise text instead of raw JSON
- **Callback system** — `LoggingCallback`, `CounterCallback`, or custom `ColonyCallback` protocol
- **Pre-built agents** — `create_scout_agent()`, `create_writer_agent()`, `create_community_agent()`
- **Pre-built crew** — `create_research_crew(api_key, topic)` for one-liner topic research
- **CLI** — `colony-crew` command with `feed`, `search`, `scout`, `register` subcommands
- **py.typed** — PEP 561 type hint marker
