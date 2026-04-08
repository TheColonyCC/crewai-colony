"""Tests for callback system."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from crewai_colony import ColonyToolkit, CounterCallback, LoggingCallback


class TestCounterCallback:
    def test_counts_tool_calls(self) -> None:
        counter = CounterCallback()
        counter.on_tool_start(tool_name="colony_search_posts", kwargs={})
        counter.on_tool_start(tool_name="colony_search_posts", kwargs={})
        counter.on_tool_start(tool_name="colony_get_post", kwargs={})
        assert counter.total == 3
        assert counter.counts == {"colony_search_posts": 2, "colony_get_post": 1}

    def test_counts_errors(self) -> None:
        counter = CounterCallback()
        counter.on_tool_error(tool_name="colony_create_post", error=Exception("fail"))
        assert counter.errors == {"colony_create_post": 1}

    def test_on_tool_end_is_noop(self) -> None:
        counter = CounterCallback()
        counter.on_tool_end(tool_name="test", result="ok")
        assert counter.total == 0


class TestLoggingCallback:
    def test_does_not_raise(self) -> None:
        cb = LoggingCallback()
        cb.on_tool_start(tool_name="test", kwargs={"q": "hello"})
        cb.on_tool_end(tool_name="test", result="ok")
        cb.on_tool_error(tool_name="test", error=Exception("fail"))


class TestCallbackIntegration:
    def test_callbacks_fire_on_tool_run(self) -> None:
        """Verify callbacks are fired when tools are used via toolkit."""
        mock_client = MagicMock()
        mock_client.get_posts.return_value = {"posts": []}

        counter = CounterCallback()
        toolkit = ColonyToolkit.__new__(ColonyToolkit)
        toolkit.client = mock_client
        toolkit.read_only = True
        toolkit.callbacks = [counter]

        tools = toolkit.get_tools(include=["colony_search_posts"])
        assert len(tools) == 1

        tool = tools[0]
        tool._run(query="test")

        assert counter.total == 1
        assert counter.counts == {"colony_search_posts": 1}

    def test_callbacks_fire_on_error_result(self) -> None:
        """When _safe_run catches an error, the wrapper still fires on_tool_end with the error string."""
        mock_client = MagicMock()
        mock_client.get_me.side_effect = Exception("401")

        counter = CounterCallback()
        toolkit = ColonyToolkit.__new__(ColonyToolkit)
        toolkit.client = mock_client
        toolkit.read_only = True
        toolkit.callbacks = [counter]

        tools = toolkit.get_tools(include=["colony_get_me"])
        tool = tools[0]
        result = tool._run()

        assert "Error" in result
        # on_tool_start fires, then on_tool_end fires with the error string result
        assert counter.total == 1

    def test_no_callbacks_still_works(self) -> None:
        mock_client = MagicMock()
        mock_client.get_posts.return_value = {"posts": []}

        toolkit = ColonyToolkit.__new__(ColonyToolkit)
        toolkit.client = mock_client
        toolkit.read_only = True
        toolkit.callbacks = []

        tools = toolkit.get_tools(include=["colony_search_posts"])
        result = tools[0]._run(query="test")
        assert "No posts found" in result
