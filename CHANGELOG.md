# Changelog

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
