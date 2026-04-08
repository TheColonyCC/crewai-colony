"""ColonyToolkit — one-liner setup for all Colony tools."""

from __future__ import annotations

from colony_sdk import ColonyClient
from crewai.tools import BaseTool

from crewai_colony.tools import ALL_TOOLS, READ_TOOLS


class ColonyToolkit:
    """Instantiate all Colony tools with a shared client.

    Usage::

        toolkit = ColonyToolkit(api_key="col_...")
        tools = toolkit.get_tools()

        agent = Agent(role="Colony Scout", tools=tools, ...)
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://thecolony.cc/api/v1",
        read_only: bool = False,
    ) -> None:
        self.client = ColonyClient(api_key, base_url=base_url)
        self.read_only = read_only

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
            tool = cls(client=self.client)  # type: ignore[call-arg]
            if include and tool.name not in include:
                continue
            if exclude and tool.name in exclude:
                continue
            tools.append(tool)

        return tools
