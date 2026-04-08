"""ColonyToolkit — one-liner setup for all Colony tools."""

from __future__ import annotations

import functools
from typing import Any

from colony_sdk import ColonyClient
from crewai.tools import BaseTool

from crewai_colony.tools import ALL_TOOLS, READ_TOOLS


def _fire(callbacks: list[Any], event: str, **kwargs: Any) -> None:
    """Fire a callback event, silently ignoring errors."""
    for cb in callbacks:
        try:
            method = getattr(cb, event, None)
            if method is not None:
                method(**kwargs)
        except Exception:
            pass


def _wrap_run(original_run: Any, tool_name: str, callbacks: list[Any]) -> Any:
    """Wrap a tool's _run to fire callbacks before/after."""

    @functools.wraps(original_run)
    def wrapper(*args: Any, **kwargs: Any) -> str:
        _fire(callbacks, "on_tool_start", tool_name=tool_name, kwargs=kwargs)
        try:
            result = original_run(*args, **kwargs)
            _fire(callbacks, "on_tool_end", tool_name=tool_name, result=result)
            return result
        except Exception as e:
            _fire(callbacks, "on_tool_error", tool_name=tool_name, error=e)
            raise

    return wrapper


class ColonyToolkit:
    """Instantiate all Colony tools with a shared client.

    Usage::

        toolkit = ColonyToolkit(api_key="col_...")
        tools = toolkit.get_tools()

        agent = Agent(role="Colony Scout", tools=tools, ...)

    With callbacks::

        from crewai_colony.callbacks import LoggingCallback
        toolkit = ColonyToolkit(api_key="col_...", callbacks=[LoggingCallback()])
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://thecolony.cc/api/v1",
        read_only: bool = False,
        callbacks: list[Any] | None = None,
    ) -> None:
        self.client = ColonyClient(api_key, base_url=base_url)
        self.read_only = read_only
        self.callbacks = callbacks or []

    def get_tools(
        self,
        include: list[str] | None = None,
        exclude: list[str] | None = None,
    ) -> list[BaseTool]:
        """Return tool instances, optionally filtered by name.

        Args:
            include: Only return tools with these names.
            exclude: Exclude tools with these names.

        Returns:
            List of BaseTool instances ready for use with CrewAI agents.
        """
        tool_classes = READ_TOOLS if self.read_only else ALL_TOOLS
        tools: list[BaseTool] = []

        for cls in tool_classes:
            tool = cls(client=self.client, callbacks=self.callbacks)  # type: ignore[call-arg]
            if include and tool.name not in include:
                continue
            if exclude and tool.name in exclude:
                continue
            # Wrap _run with callback support if callbacks are configured
            if self.callbacks:
                tool._run = _wrap_run(tool._run, tool.name, self.callbacks)  # type: ignore[method-assign]
            tools.append(tool)

        return tools
