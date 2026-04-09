"""Tests targeting uncovered lines to push coverage toward 100%."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from crewai_colony import (
    ColonyMarkNotificationsRead,
    ColonyRegister,
    ColonyToolkit,
    ColonyUpdatePost,
    ColonyUpdateProfile,
)
from crewai_colony.tools import (
    _fmt_colonies,
    _fmt_comments,
    _fmt_conversation,
    _fmt_error,
    _fmt_notifications,
    _fmt_poll,
    _fmt_post,
    _fmt_post_detail,
    _fmt_posts,
    _fmt_search,
    _fmt_simple,
    _fmt_unread,
    _fmt_webhooks,
)

# ── Formatter edge cases ───────────────────────────────────────────


class TestFmtPostEdgeCases:
    def test_body_truncation(self) -> None:
        """Line 114: body > 300 chars gets truncated."""
        post = {
            "id": "p1",
            "title": "T",
            "author": {"username": "u"},
            "score": 0,
            "comment_count": 0,
            "colony": "general",
            "body": "x" * 500,
        }
        result = _fmt_post(post)
        assert "..." in result
        assert "x" * 300 in result
        assert "x" * 301 not in result

    def test_colony_as_string(self) -> None:
        """Colony field as plain string instead of dict."""
        post = {
            "id": "p1",
            "title": "T",
            "author": {"username": "u"},
            "score": 0,
            "comment_count": 0,
            "colony": "findings",
            "body": "",
        }
        result = _fmt_post(post)
        assert "c/findings" in result


class TestFmtPostsEdgeCases:
    def test_list_input(self) -> None:
        """Line 126: data is a list instead of dict."""
        posts = [
            {
                "id": "p1",
                "title": "A",
                "author": {"username": "u"},
                "score": 1,
                "comment_count": 0,
                "colony": "g",
                "body": "",
            }
        ]
        result = _fmt_posts(posts)
        assert "A" in result

    def test_non_dict_non_list(self) -> None:
        """Line 138: data is neither dict nor list."""
        result = _fmt_posts("unexpected")
        assert result == "unexpected"


class TestFmtPostDetailEdgeCases:
    def test_non_dict(self) -> None:
        """Line 167: non-dict input."""
        assert _fmt_post_detail("raw") == "raw"

    def test_display_name(self) -> None:
        """Line 183: user with display_name."""
        from crewai_colony.tools import _fmt_user

        result = _fmt_user({"username": "bot", "display_name": "My Bot", "karma": 5})
        assert "My Bot" in result
        assert "@bot" in result


class TestFmtCommentsEdgeCases:
    def test_list_input(self) -> None:
        """Line 194: data is a list."""
        comments = [{"id": "c1", "author": {"username": "u"}, "body": "hi", "score": 1}]
        result = _fmt_comments(comments)
        assert "@u" in result

    def test_non_dict_non_list(self) -> None:
        result = _fmt_comments("raw")
        assert result == "raw"


class TestFmtUserEdgeCases:
    def test_non_dict(self) -> None:
        """Line 176: non-dict input."""
        from crewai_colony.tools import _fmt_user

        assert _fmt_user("raw") == "raw"


class TestFmtColoniesEdgeCases:
    def test_list_input(self) -> None:
        """Line 213: data is a list."""
        cols = [{"name": "gen", "description": "Open", "member_count": 10}]
        result = _fmt_colonies(cols)
        assert "c/gen" in result

    def test_non_dict_non_list(self) -> None:
        assert _fmt_colonies("raw") == "raw"


class TestFmtConversationEdgeCases:
    def test_sender_username_fallback(self) -> None:
        """Line 225: sender is not a dict, falls back to sender_username."""
        data = {"messages": [{"sender": "not-a-dict", "sender_username": "buddy", "body": "yo"}]}
        result = _fmt_conversation(data)
        assert "@buddy" in result

    def test_list_input(self) -> None:
        msgs = [{"sender": {"username": "a"}, "body": "hi"}]
        result = _fmt_conversation(msgs)
        assert "@a" in result

    def test_non_dict_non_list(self) -> None:
        assert _fmt_conversation("raw") == "raw"


class TestFmtNotificationsEdgeCases:
    def test_list_input(self) -> None:
        """Line 235: data is a list."""
        notifs = [{"type": "mention", "preview": "hi", "read": True}]
        result = _fmt_notifications(notifs)
        assert "[read]" in result

    def test_non_dict_non_list(self) -> None:
        assert _fmt_notifications("raw") == "raw"


class TestFmtPollEdgeCases:
    def test_non_dict(self) -> None:
        """Line 253: non-dict input."""
        assert _fmt_poll("raw") == "raw"


class TestFmtSearchEdgeCases:
    def test_non_dict_non_list(self) -> None:
        """Line 289: non-dict non-list."""
        assert _fmt_search("raw") == "raw"

    def test_list_input(self) -> None:
        results = [
            {
                "id": "p1",
                "title": "X",
                "author": {"username": "u"},
                "score": 0,
                "comment_count": 0,
                "colony": "g",
                "body": "",
            }
        ]
        result = _fmt_search(results)
        assert "X" in result


class TestFmtSimpleEdgeCases:
    def test_non_dict(self) -> None:
        """Line 297: non-dict input."""
        assert _fmt_simple("plain text") == "plain text"


class TestFmtUnreadEdgeCases:
    def test_non_dict(self) -> None:
        assert _fmt_unread("raw") == "raw"

    def test_unread_count_key(self) -> None:
        """Test the unread_count fallback key."""
        result = _fmt_unread({"unread_count": 5})
        assert "5" in result


class TestFmtWebhooksEdgeCases:
    def test_list_input(self) -> None:
        """Line 1074: data is a list."""
        webhooks = [{"id": "wh-1", "url": "https://example.com", "events": ["post_created"]}]
        result = _fmt_webhooks(webhooks)
        assert "wh-1" in result

    def test_non_dict_non_list(self) -> None:
        assert _fmt_webhooks("raw") == "raw"


# ── _safe_run edge case ───────────────────────────────────────────


class TestSafeRunEdgeCases:
    def test_safe_run_passes_result_through(self) -> None:
        from crewai_colony.tools import _safe_run

        result = _safe_run(lambda: {"status": "ok"}, _fmt_simple)
        assert "OK" in result

    def test_safe_run_catches_non_sdk_exception(self) -> None:
        """Last-resort safety net: anything that escapes SDK error types
        still gets caught at the tool boundary instead of crashing the crew."""
        from crewai_colony.tools import _safe_run

        def boom() -> None:
            raise ValueError("unexpected")

        result = _safe_run(boom, _fmt_simple)
        assert "Error" in result
        assert "unexpected" in result


# ── _fmt_error edge cases ─────────────────────────────────────────


class TestFmtErrorEdgeCases:
    def test_plain_exception(self) -> None:
        """Exception without status/code."""
        result = _fmt_error(Exception("something broke"))
        assert "Error" in result
        assert "something broke" in result

    def test_status_only(self) -> None:
        """SDK exception with status but no error code."""
        from colony_sdk import ColonyAPIError

        exc = ColonyAPIError("teapot", status=418)
        result = _fmt_error(exc)
        assert "418" in result
        assert "teapot" in result

    def test_status_zero_suppressed(self) -> None:
        """Network errors carry status=0 — that's an internal sentinel,
        not a real HTTP code. Don't surface a misleading ``(0)`` to LLMs."""
        from colony_sdk import ColonyNetworkError

        exc = ColonyNetworkError("connection refused", status=0, response={})
        result = _fmt_error(exc)
        assert "(0)" not in result
        assert "connection refused" in result


# ── Tool edge cases ───────────────────────────────────────────────


class TestUpdatePostBothFields:
    def test_update_title_and_body(self) -> None:
        mock_client = MagicMock()
        mock_client.update_post.return_value = {"id": "p1"}
        tool = ColonyUpdatePost(client=mock_client)
        tool._run(post_id="p1", title="New", body="Updated")
        mock_client.update_post.assert_called_once_with("p1", title="New", body="Updated")

    async def test_async_update_body(self) -> None:
        """Line 688: async body kwarg branch."""
        mock_client = MagicMock()
        mock_client.update_post.return_value = {"id": "p1"}
        tool = ColonyUpdatePost(client=mock_client)
        await tool._arun(post_id="p1", body="Async body")
        mock_client.update_post.assert_called_once_with("p1", body="Async body")


class TestUpdateProfileDisplayName:
    def test_display_name_only(self) -> None:
        """Line 877: display_name branch."""
        mock_client = MagicMock()
        mock_client.update_profile.return_value = {}
        tool = ColonyUpdateProfile(client=mock_client)
        tool._run(display_name="New Name")
        mock_client.update_profile.assert_called_once_with(display_name="New Name")

    async def test_async_display_name(self) -> None:
        """Line 891: async display_name branch."""
        mock_client = MagicMock()
        mock_client.update_profile.return_value = {}
        tool = ColonyUpdateProfile(client=mock_client)
        await tool._arun(display_name="Async Name")
        mock_client.update_profile.assert_called_once_with(display_name="Async Name")


class TestMarkNotificationsReadError:
    def test_sync_error(self) -> None:
        """Lines 989-990: error in mark_notifications_read."""
        mock_client = MagicMock()
        mock_client.mark_notifications_read.side_effect = Exception("fail")
        tool = ColonyMarkNotificationsRead(client=mock_client)
        result = tool._run()
        assert "Error" in result

    async def test_async_error(self) -> None:
        """Lines 996-997: async error in mark_notifications_read."""
        mock_client = MagicMock()
        mock_client.mark_notifications_read.side_effect = Exception("fail")
        tool = ColonyMarkNotificationsRead(client=mock_client)
        result = await tool._arun()
        assert "Error" in result


class TestRegisterAsync:
    async def test_arun_uses_async_client(self) -> None:
        """``_arun`` uses ``AsyncColonyClient.register`` natively when the
        ``[async]`` extra is installed."""
        from unittest.mock import AsyncMock, patch

        import colony_sdk

        async_mock = AsyncMock(return_value={"api_key": "col_new"})
        with patch.object(colony_sdk.AsyncColonyClient, "register", async_mock):
            tool = ColonyRegister()
            result = await tool._arun(
                username="new-agent",
                display_name="New",
                bio="Bio",
            )
            assert "col_new" in result
            async_mock.assert_awaited_once_with(
                username="new-agent",
                display_name="New",
                bio="Bio",
            )

    async def test_arun_handles_error(self) -> None:
        """Network/auth errors during async register are caught at the
        tool boundary instead of crashing the crew."""
        from unittest.mock import AsyncMock, patch

        import colony_sdk

        async_mock = AsyncMock(side_effect=Exception("username taken"))
        with patch.object(colony_sdk.AsyncColonyClient, "register", async_mock):
            tool = ColonyRegister()
            result = await tool._arun(
                username="taken",
                display_name="Taken",
                bio="...",
            )
            assert "Error" in result
            assert "username taken" in result

    async def test_arun_falls_back_when_async_extra_missing(self) -> None:
        """If ``colony_sdk.AsyncColonyClient`` can't be imported, the tool
        runs the sync ``_run`` path in a thread instead of failing outright."""
        import contextlib
        import sys
        from unittest.mock import patch

        # Hide AsyncColonyClient by making the lazy import raise.
        import colony_sdk

        original = colony_sdk.AsyncColonyClient

        def _raise(name: str) -> None:
            if name == "AsyncColonyClient":
                raise ImportError("httpx not installed")
            return original  # pragma: no cover

        with patch.object(colony_sdk, "__getattr__", _raise, create=True):
            # Pop any cached attribute so __getattr__ runs again.
            with contextlib.suppress(AttributeError):
                del colony_sdk.AsyncColonyClient
            sys.modules.pop("colony_sdk.async_client", None)

            with patch("crewai_colony.tools.ColonyClient") as mock_sync:
                mock_sync.register.return_value = {"api_key": "col_fallback"}
                tool = ColonyRegister()
                result = await tool._arun(
                    username="fb",
                    display_name="FB",
                    bio="Fallback path",
                )
                assert "col_fallback" in result

        # Restore for downstream tests.
        colony_sdk.AsyncColonyClient = original


# ── Toolkit __init__ ───────────────────────────────────────────────


class TestToolkitInit:
    def test_constructor(self) -> None:
        """Lines 72-75: actual __init__ constructor."""
        from unittest.mock import patch

        with patch("crewai_colony.toolkit.ColonyClient"):
            toolkit = ColonyToolkit(api_key="col_test")
            assert toolkit.read_only is False
            assert toolkit.callbacks == []
            assert toolkit.retry is None

    def test_constructor_with_options(self) -> None:
        from unittest.mock import patch

        from colony_sdk import RetryConfig

        from crewai_colony.callbacks import CounterCallback

        with patch("crewai_colony.toolkit.ColonyClient") as mock_cls:
            counter = CounterCallback()
            retry = RetryConfig(max_retries=5)
            toolkit = ColonyToolkit(
                api_key="col_test",
                read_only=True,
                callbacks=[counter],
                retry=retry,
            )
            assert toolkit.read_only is True
            assert len(toolkit.callbacks) == 1
            assert toolkit.retry.max_retries == 5
            # Retry is now enforced inside the SDK, so it must reach the client.
            assert mock_cls.call_args.kwargs["retry"] is retry


# ── Callback wrapper edge case ─────────────────────────────────────


class TestCallbackWrapperError:
    def test_callback_exception_suppressed(self) -> None:
        """Lines 21-22: callback that raises is silently ignored."""
        from crewai_colony.toolkit import _fire

        class BadCallback:
            def on_tool_start(self, **kwargs: object) -> None:
                raise RuntimeError("boom")

        # Should not raise
        _fire([BadCallback()], "on_tool_start", tool_name="test", kwargs={})

    def test_wrapper_error_fires_on_tool_error(self) -> None:
        """Lines 35-37: tool that raises through wrapper fires on_tool_error."""
        from crewai_colony.toolkit import _wrap_run

        errors: list[Exception] = []

        class ErrorTracker:
            def on_tool_start(self, **kwargs: object) -> None:
                pass

            def on_tool_end(self, **kwargs: object) -> None:
                pass

            def on_tool_error(self, **kwargs: object) -> None:
                errors.append(kwargs.get("error"))  # type: ignore[arg-type]

        def failing_run() -> str:
            raise ValueError("boom")

        wrapped = _wrap_run(failing_run, "test_tool", [ErrorTracker()])

        import pytest

        with pytest.raises(ValueError, match="boom"):
            wrapped()

        assert len(errors) == 1


# ── CLI tests ──────────────────────────────────────────────────────


class TestCLI:
    def test_no_command_shows_help(self) -> None:
        """CLI with no args exits with code 1."""
        from unittest.mock import patch

        from crewai_colony.cli import main

        with patch("sys.argv", ["colony-crew"]):
            import pytest

            with pytest.raises(SystemExit, match="1"):
                main()

    def test_feed_command(self) -> None:
        """Feed command calls search_posts tool."""
        import argparse
        from unittest.mock import patch

        from crewai_colony.cli import cmd_feed

        args = argparse.Namespace(colony=None, sort="hot", limit=10)
        with patch("crewai_colony.ColonyToolkit") as mock_tk:
            mock_tool = MagicMock()
            mock_tool._run.return_value = "No posts found."
            mock_tk.return_value.get_tools.return_value = [mock_tool]
            with patch.dict("os.environ", {"COLONY_API_KEY": "col_test"}):
                cmd_feed(args)
            mock_tool._run.assert_called_once()

    def test_register_command(self) -> None:
        """Register command calls ColonyClient.register."""
        import argparse
        from unittest.mock import patch

        from crewai_colony.cli import cmd_register

        args = argparse.Namespace(
            username="test-bot",
            display_name="Test Bot",
            bio="A test bot",
        )
        with patch("colony_sdk.ColonyClient") as mock_cls:
            mock_cls.register.return_value = {"api_key": "col_new_key"}
            cmd_register(args)
            mock_cls.register.assert_called_once_with(
                username="test-bot",
                display_name="Test Bot",
                bio="A test bot",
            )

    def test_register_error(self) -> None:
        """Register command handles errors."""
        import argparse
        from unittest.mock import patch

        from crewai_colony.cli import cmd_register

        args = argparse.Namespace(
            username="taken",
            display_name="Taken",
            bio="...",
        )
        with patch("colony_sdk.ColonyClient") as mock_cls:
            mock_cls.register.side_effect = Exception("username taken")
            import pytest

            with pytest.raises(SystemExit, match="1"):
                cmd_register(args)

    def test_get_api_key_missing(self) -> None:
        """_get_api_key exits when env var not set."""
        from unittest.mock import patch

        from crewai_colony.cli import _get_api_key

        with patch.dict("os.environ", {}, clear=True):
            import pytest

            with pytest.raises(SystemExit, match="1"):
                _get_api_key()

    def test_get_api_key_present(self) -> None:
        """_get_api_key returns the key when set."""
        from unittest.mock import patch

        from crewai_colony.cli import _get_api_key

        with patch.dict("os.environ", {"COLONY_API_KEY": "col_abc"}):
            assert _get_api_key() == "col_abc"

    def test_search_command(self) -> None:
        """cmd_search creates a research crew and kicks it off."""
        import argparse
        from unittest.mock import patch

        from crewai_colony.cli import cmd_search

        args = argparse.Namespace(topic="AI agents")
        with (
            patch("crewai_colony.crews.ColonyToolkit"),
            patch("crewai_colony.crews.Agent"),
            patch("crewai_colony.crews.Task"),
            patch("crewai_colony.crews.Crew") as mock_crew_cls,
            patch.dict("os.environ", {"COLONY_API_KEY": "col_test"}),
        ):
            mock_crew = MagicMock()
            mock_crew.kickoff.return_value = "Research results"
            mock_crew_cls.return_value = mock_crew
            cmd_search(args)
            mock_crew.kickoff.assert_called_once()

    def test_scout_command(self) -> None:
        """cmd_scout creates a scout agent and kicks off a crew."""
        import argparse
        from unittest.mock import patch

        from crewai_colony.cli import cmd_scout

        args = argparse.Namespace(limit=5)
        with (
            patch("crewai_colony.ColonyToolkit") as mock_tk,
            patch("crewai_colony.crews.Agent"),
            patch("crewai.Crew") as mock_crew_cls,
            patch("crewai.Task"),
            patch.dict("os.environ", {"COLONY_API_KEY": "col_test"}),
        ):
            mock_tk.return_value.get_tools.return_value = []
            mock_crew = MagicMock()
            mock_crew.kickoff.return_value = "Scout results"
            mock_crew_cls.return_value = mock_crew
            cmd_scout(args)
            mock_crew.kickoff.assert_called_once()

    def test_main_with_subcommand(self) -> None:
        """Line 128: main dispatches to subcommand function."""
        from unittest.mock import patch

        from crewai_colony.cli import main

        with (
            patch("sys.argv", ["colony-crew", "feed", "--sort", "new"]),
            patch("crewai_colony.ColonyToolkit") as mock_tk,
            patch.dict("os.environ", {"COLONY_API_KEY": "col_test"}),
        ):
            mock_tool = MagicMock()
            mock_tool._run.return_value = "posts"
            mock_tk.return_value.get_tools.return_value = [mock_tool]
            main()
            mock_tool._run.assert_called_once()
