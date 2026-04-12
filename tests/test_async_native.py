"""Native-async tests — verifies AsyncColonyToolkit dispatches tool ``_arun()``
calls through ``AsyncColonyClient`` (real coroutines on the event loop) rather
than falling back to ``asyncio.to_thread`` on a sync ``ColonyClient``.

These tests use ``httpx.MockTransport`` so we exercise the full SDK 1.5.0 async
stack without hitting the network."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from colony_sdk import AsyncColonyClient, RetryConfig

from crewai_colony import (
    AsyncColonyToolkit,
    ColonyGetMe,
    ColonyGetPost,
    ColonyMarkNotificationsRead,
    ColonySearchPosts,
)
from crewai_colony.tools import _async_safe_run, _safe_run

# ── Dispatcher behaviour ───────────────────────────────────────────


class TestDispatcher:
    """``_async_safe_run`` should ``await`` async client methods natively
    and only fall back to ``to_thread`` for sync methods."""

    async def test_native_await_for_coroutine_function(self) -> None:
        """When the bound method is a coroutine function, no thread is used."""
        called_in_thread: list[bool] = []

        async def fake_method(post_id: str) -> dict:
            # Capture which thread we're in — should be the event-loop thread.
            import threading

            called_in_thread.append(threading.current_thread() is threading.main_thread())
            return {"id": post_id, "title": "ok", "author": {"username": "u"}, "score": 0, "comment_count": 0}

        # Patch to_thread so we can prove it was NOT called.
        with patch("asyncio.to_thread") as mock_to_thread:
            result = await _async_safe_run(fake_method, lambda d: d.get("title", ""), "p1")
            assert result == "ok"
            mock_to_thread.assert_not_called()
        assert called_in_thread == [True]

    async def test_to_thread_fallback_for_sync_function(self) -> None:
        """A plain (non-coroutine) callable goes through ``asyncio.to_thread``
        so it can't block the event loop."""

        def sync_method(post_id: str) -> dict:
            return {"id": post_id}

        with patch("asyncio.to_thread", wraps=asyncio.to_thread) as mock_to_thread:
            await _async_safe_run(sync_method, lambda d: f"id={d['id']}", "p1")
            mock_to_thread.assert_called_once()

    async def test_native_await_propagates_sdk_error(self) -> None:
        """Errors raised by the awaited coroutine are formatted, not bubbled."""
        from colony_sdk import ColonyNotFoundError

        async def fake_method(post_id: str) -> dict:
            raise ColonyNotFoundError(
                "get_post failed: not found (not found — the resource doesn't exist or has been deleted)",
                status=404,
            )

        result = await _async_safe_run(fake_method, lambda d: d, "p1")
        assert "Error" in result
        assert "404" in result
        assert "not found" in result.lower()

    async def test_native_await_catches_unexpected_exception(self) -> None:
        async def fake_method() -> dict:
            raise RuntimeError("unexpected")

        result = await _async_safe_run(fake_method, lambda d: d)
        assert "Error" in result
        assert "unexpected" in result


# ── AsyncColonyToolkit construction ────────────────────────────────


class TestAsyncToolkit:
    def test_constructs_async_client(self) -> None:
        toolkit = AsyncColonyToolkit(api_key="col_test")
        assert isinstance(toolkit.client, AsyncColonyClient)

    def test_passes_retry_to_client(self) -> None:
        with patch("colony_sdk.AsyncColonyClient") as mock_cls:
            retry = RetryConfig(max_retries=5, base_delay=0.1)
            AsyncColonyToolkit(api_key="col_test", retry=retry)
            kwargs = mock_cls.call_args.kwargs
            assert kwargs["retry"] is retry

    def test_omits_retry_when_unset(self) -> None:
        with patch("colony_sdk.AsyncColonyClient") as mock_cls:
            AsyncColonyToolkit(api_key="col_test")
            kwargs = mock_cls.call_args.kwargs
            assert "retry" not in kwargs

    def test_get_tools_returns_all(self) -> None:
        toolkit = AsyncColonyToolkit(api_key="col_test")
        tools = toolkit.get_tools()
        assert len(tools) == 33
        names = {t.name for t in tools}
        assert "colony_create_post" in names
        assert "colony_get_all_comments" in names
        assert "colony_get_posts_by_ids" in names
        assert "colony_get_users_by_ids" in names

    def test_get_tools_read_only(self) -> None:
        toolkit = AsyncColonyToolkit(api_key="col_test", read_only=True)
        tools = toolkit.get_tools()
        assert len(tools) == 15
        names = {t.name for t in tools}
        assert "colony_create_post" not in names
        assert "colony_get_posts_by_ids" in names
        assert "colony_get_users_by_ids" in names

    def test_get_tools_include_exclude(self) -> None:
        toolkit = AsyncColonyToolkit(api_key="col_test")
        tools = toolkit.get_tools(include=["colony_get_me"])
        assert len(tools) == 1
        tools = toolkit.get_tools(exclude=["colony_create_post"])
        assert len(tools) == 32

    def test_get_tools_with_callbacks(self) -> None:
        from crewai_colony.callbacks import CounterCallback

        counter = CounterCallback()
        toolkit = AsyncColonyToolkit(api_key="col_test", callbacks=[counter])
        tools = toolkit.get_tools()
        assert len(tools) == 33

    async def test_async_context_manager(self) -> None:
        async with AsyncColonyToolkit(api_key="col_test") as toolkit:
            tools = toolkit.get_tools()
            assert len(tools) == 33

    async def test_aclose_idempotent(self) -> None:
        toolkit = AsyncColonyToolkit(api_key="col_test")
        await toolkit.aclose()


# ── End-to-end via httpx.MockTransport ─────────────────────────────


def _mock_transport(responses: dict[str, dict]) -> httpx.MockTransport:
    """Build an httpx.MockTransport that returns the given JSON for any
    request matching a path key."""

    def handler(request: httpx.Request) -> httpx.Response:
        for path, body in responses.items():
            if request.url.path.endswith(path):
                return httpx.Response(200, json=body)
        return httpx.Response(404, json={"detail": "no mock for this path"})

    return httpx.MockTransport(handler)


@pytest.fixture
def mock_async_client() -> AsyncColonyClient:
    """An ``AsyncColonyClient`` whose underlying httpx.AsyncClient uses
    ``MockTransport`` instead of real HTTP."""
    transport = _mock_transport(
        {
            "/auth/token": {"access_token": "jwt.fake", "expires_in": 3600},
            "/posts": {
                "posts": [
                    {
                        "id": "p1",
                        "title": "Hello",
                        "author": {"username": "bot"},
                        "score": 5,
                        "comment_count": 2,
                        "colony": {"name": "general"},
                        "body": "test body",
                    }
                ]
            },
            "/posts/p1": {
                "id": "p1",
                "title": "Hello",
                "author": {"username": "bot"},
                "score": 5,
                "comment_count": 0,
                "colony": "general",
                "body": "full",
                "comments": [],
            },
            "/users/me": {
                "username": "colonist-one",
                "display_name": "Colonist One",
                "bio": "the AI agent CMO",
                "karma": 99,
            },
            "/notifications/read-all": {"status": "ok"},
        }
    )
    httpx_client = httpx.AsyncClient(transport=transport, base_url="https://thecolony.cc/api/v1")
    return AsyncColonyClient("col_test", client=httpx_client)


class TestEndToEnd:
    """Tools wired to a real ``AsyncColonyClient`` with a mocked transport."""

    async def test_search_posts_native(self, mock_async_client: AsyncColonyClient) -> None:
        tool = ColonySearchPosts(client=mock_async_client)
        result = await tool._arun(query="hello")
        assert "Hello" in result
        assert "@bot" in result
        await mock_async_client.aclose()

    async def test_get_post_native(self, mock_async_client: AsyncColonyClient) -> None:
        tool = ColonyGetPost(client=mock_async_client)
        result = await tool._arun(post_id="p1")
        assert "Hello" in result
        await mock_async_client.aclose()

    async def test_get_me_native(self, mock_async_client: AsyncColonyClient) -> None:
        tool = ColonyGetMe(client=mock_async_client)
        result = await tool._arun()
        assert "@colonist-one" in result
        assert "karma: 99" in result
        await mock_async_client.aclose()

    async def test_mark_notifications_read_native(self, mock_async_client: AsyncColonyClient) -> None:
        """Special-cased tool that doesn't go through ``_async_safe_run`` —
        it should still ``await`` the coroutine method, not call ``to_thread``."""
        tool = ColonyMarkNotificationsRead(client=mock_async_client)

        with patch("asyncio.to_thread") as mock_to_thread:
            result = await tool._arun()
            mock_to_thread.assert_not_called()
        assert "OK" in result
        await mock_async_client.aclose()

    async def test_mark_notifications_read_sync_client_uses_thread(self) -> None:
        """Same tool, sync client — must use ``to_thread`` to avoid blocking."""
        sync_client = MagicMock()
        sync_client.mark_notifications_read = MagicMock(return_value=None)
        tool = ColonyMarkNotificationsRead(client=sync_client)

        with patch("asyncio.to_thread", wraps=asyncio.to_thread) as mock_to_thread:
            result = await tool._arun()
            mock_to_thread.assert_called_once()
        assert "OK" in result

    async def test_mark_notifications_read_native_error(self) -> None:
        """Async client whose method raises — error gets formatted at the
        tool boundary."""

        class BoomClient:
            async def mark_notifications_read(self) -> None:
                raise RuntimeError("kaboom")

        tool = ColonyMarkNotificationsRead(client=BoomClient())
        result = await tool._arun()
        assert "Error" in result
        assert "kaboom" in result

    async def test_concurrent_fan_out(self, mock_async_client: AsyncColonyClient) -> None:
        """The whole point of native async — many tool calls in parallel
        on a single event loop, no thread pool."""
        tool = ColonySearchPosts(client=mock_async_client)
        results = await asyncio.gather(*[tool._arun(query=f"q{i}") for i in range(10)])
        assert len(results) == 10
        assert all("Hello" in r for r in results)
        await mock_async_client.aclose()


# ── Sanity: sync _safe_run still rejects coroutine results gracefully ──


class TestSyncSafeRunUnchanged:
    def test_sync_path_unchanged(self) -> None:
        result = _safe_run(lambda: {"status": "ok"}, lambda d: f"ok={d['status']}")
        assert "ok=ok" in result
