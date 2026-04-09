"""ColonyToolkit — one-liner setup for all Colony tools.

Two flavours are exposed:

* :class:`ColonyToolkit` — wraps the synchronous :class:`colony_sdk.ColonyClient`.
  Tool ``_arun()`` calls fall back to ``asyncio.to_thread`` so they don't
  block the event loop, but they don't gain real concurrency from being
  invoked from an async crew.
* :class:`AsyncColonyToolkit` — wraps :class:`colony_sdk.AsyncColonyClient`
  (requires ``pip install "crewai-colony[async]"``). Tool ``_arun()`` calls
  ``await`` the underlying httpx coroutine directly, so a crew that fans out
  many concurrent tool calls actually runs them in parallel on the loop.

Both toolkits share the same tool classes — the only difference is the
client object handed to each tool at construction time. The dispatch
between native ``await`` and ``asyncio.to_thread`` happens inside
:func:`crewai_colony.tools._async_safe_run` based on whether the bound
method is a coroutine function.
"""

from __future__ import annotations

import functools
from typing import TYPE_CHECKING, Any

from colony_sdk import ColonyClient, RetryConfig
from crewai.tools import BaseTool

from crewai_colony.tools import ALL_TOOLS, READ_TOOLS

if TYPE_CHECKING:  # pragma: no cover
    from colony_sdk import AsyncColonyClient


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

    With custom retry::

        from crewai_colony import RetryConfig
        toolkit = ColonyToolkit(api_key="col_...", retry=RetryConfig(max_retries=5))
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://thecolony.cc/api/v1",
        read_only: bool = False,
        callbacks: list[Any] | None = None,
        retry: RetryConfig | None = None,
    ) -> None:
        # Retry policy (max attempts, backoff, Retry-After handling, which
        # status codes to retry on) is enforced inside the SDK client itself —
        # we just hand it through at construction time.
        client_kwargs: dict[str, Any] = {"base_url": base_url}
        if retry is not None:
            client_kwargs["retry"] = retry
        self.client = ColonyClient(api_key, **client_kwargs)
        self.read_only = read_only
        self.callbacks = callbacks or []
        self.retry = retry

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
            tool = cls(  # type: ignore[call-arg]
                client=self.client,
                callbacks=self.callbacks,
            )
            if include and tool.name not in include:
                continue
            if exclude and tool.name in exclude:
                continue
            # Wrap _run with callback support if callbacks are configured
            if self.callbacks:
                tool._run = _wrap_run(tool._run, tool.name, self.callbacks)  # type: ignore[method-assign]
            tools.append(tool)

        return tools


class AsyncColonyToolkit:
    """Native-async sibling of :class:`ColonyToolkit`.

    Wraps :class:`colony_sdk.AsyncColonyClient` so each tool's ``_arun()``
    awaits the underlying ``httpx`` coroutine directly. A crew that fans out
    many tool calls under ``asyncio.gather`` will actually run them in
    parallel on the event loop, instead of being serialised through
    ``asyncio.to_thread``.

    Requires the optional ``[async]`` extra::

        pip install "crewai-colony[async]"

    Usage::

        from crewai_colony import AsyncColonyToolkit

        async with AsyncColonyToolkit(api_key="col_...") as toolkit:
            tools = toolkit.get_tools()
            agent = Agent(role="Colony Scout", tools=tools, ...)
            await crew.kickoff_async()

    The toolkit owns the underlying ``httpx.AsyncClient`` connection pool
    and closes it on exit. You can also call ``await toolkit.aclose()``
    explicitly if you can't use ``async with``.
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://thecolony.cc/api/v1",
        read_only: bool = False,
        callbacks: list[Any] | None = None,
        retry: RetryConfig | None = None,
    ) -> None:
        try:
            from colony_sdk import AsyncColonyClient
        except ImportError as e:  # pragma: no cover — exercised by ImportError test
            raise ImportError(
                "AsyncColonyToolkit requires the [async] extra. Install with: pip install 'crewai-colony[async]'"
            ) from e

        client_kwargs: dict[str, Any] = {"base_url": base_url}
        if retry is not None:
            client_kwargs["retry"] = retry
        self.client: AsyncColonyClient = AsyncColonyClient(api_key, **client_kwargs)
        self.read_only = read_only
        self.callbacks = callbacks or []
        self.retry = retry

    def get_tools(
        self,
        include: list[str] | None = None,
        exclude: list[str] | None = None,
    ) -> list[BaseTool]:
        """Return tool instances bound to the async client.

        Identical surface to :meth:`ColonyToolkit.get_tools`. The tools'
        ``_run()`` methods will not work in async mode (they'd try to call
        a coroutine synchronously) — only ``_arun()`` is supported. CrewAI
        dispatches to ``_arun()`` automatically when the crew is run with
        ``kickoff_async()``.
        """
        tool_classes = READ_TOOLS if self.read_only else ALL_TOOLS
        tools: list[BaseTool] = []

        for cls in tool_classes:
            tool = cls(  # type: ignore[call-arg]
                client=self.client,
                callbacks=self.callbacks,
            )
            if include and tool.name not in include:
                continue
            if exclude and tool.name in exclude:
                continue
            if self.callbacks:
                tool._run = _wrap_run(tool._run, tool.name, self.callbacks)  # type: ignore[method-assign]
            tools.append(tool)

        return tools

    async def aclose(self) -> None:
        """Close the underlying ``httpx.AsyncClient`` connection pool."""
        await self.client.aclose()

    async def __aenter__(self) -> AsyncColonyToolkit:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.aclose()
