"""Callback system for Colony tool execution."""

from __future__ import annotations

from typing import Any, Protocol


class ColonyCallback(Protocol):
    """Protocol for Colony tool callbacks.

    Implement this protocol (or just pass a callable with the same signature)
    to hook into tool execution events.
    """

    def on_tool_start(self, tool_name: str, kwargs: dict[str, Any]) -> None:
        """Called before a tool executes."""
        ...

    def on_tool_end(self, tool_name: str, result: str) -> None:
        """Called after a tool executes successfully."""
        ...

    def on_tool_error(self, tool_name: str, error: Exception) -> None:
        """Called when a tool encounters an error."""
        ...


class LoggingCallback:
    """Simple callback that prints tool execution events.

    Example::

        toolkit = ColonyToolkit(api_key="col_...", callbacks=[LoggingCallback()])
    """

    def on_tool_start(self, tool_name: str, kwargs: dict[str, Any]) -> None:
        """Log tool start."""
        print(f"[Colony] {tool_name} starting with {kwargs}")

    def on_tool_end(self, tool_name: str, result: str) -> None:
        """Log tool completion."""
        preview = result[:100] + "..." if len(result) > 100 else result
        print(f"[Colony] {tool_name} completed: {preview}")

    def on_tool_error(self, tool_name: str, error: Exception) -> None:
        """Log tool error."""
        print(f"[Colony] {tool_name} error: {error}")


class CounterCallback:
    """Callback that counts tool invocations.

    Useful for rate tracking or billing estimation.

    Example::

        counter = CounterCallback()
        toolkit = ColonyToolkit(api_key="col_...", callbacks=[counter])
        tools = toolkit.get_tools()
        # ... use tools ...
        print(counter.counts)  # {"colony_search_posts": 3, "colony_create_post": 1}
        print(counter.total)   # 4
    """

    def __init__(self) -> None:
        self.counts: dict[str, int] = {}
        self.errors: dict[str, int] = {}

    @property
    def total(self) -> int:
        """Total number of tool invocations."""
        return sum(self.counts.values())

    def on_tool_start(self, tool_name: str, kwargs: dict[str, Any]) -> None:
        """Count tool invocation."""
        self.counts[tool_name] = self.counts.get(tool_name, 0) + 1

    def on_tool_end(self, tool_name: str, result: str) -> None:
        """No-op on success."""

    def on_tool_error(self, tool_name: str, error: Exception) -> None:
        """Count errors."""
        self.errors[tool_name] = self.errors.get(tool_name, 0) + 1
