"""Tests for pre-built crew recipes."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from crewai_colony import ColonyToolkit
from crewai_colony.crews import (
    create_community_agent,
    create_engagement_crew,
    create_newsletter_crew,
    create_research_crew,
    create_scout_agent,
    create_writer_agent,
)


def _make_toolkit() -> ColonyToolkit:
    toolkit = ColonyToolkit.__new__(ColonyToolkit)
    toolkit.client = MagicMock()
    toolkit.read_only = False
    toolkit.callbacks = []
    toolkit.retry = None
    return toolkit


class TestScoutAgent:
    @patch("crewai_colony.crews.Agent")
    def test_creates_agent_with_read_tools(self, mock_agent_cls: MagicMock) -> None:
        mock_agent_cls.return_value = MagicMock()
        toolkit = _make_toolkit()

        create_scout_agent(toolkit)
        call_kwargs = mock_agent_cls.call_args[1]
        assert call_kwargs["role"] == "Colony Scout"
        tool_names = {t.name for t in call_kwargs["tools"]}
        assert "colony_search_posts" in tool_names
        assert "colony_search" in tool_names
        assert "colony_get_post" in tool_names
        assert "colony_create_post" not in tool_names

    @patch("crewai_colony.crews.Agent")
    def test_override_role(self, mock_agent_cls: MagicMock) -> None:
        mock_agent_cls.return_value = MagicMock()
        toolkit = _make_toolkit()

        create_scout_agent(toolkit, role="Custom Scout")
        call_kwargs = mock_agent_cls.call_args[1]
        assert call_kwargs["role"] == "Custom Scout"


class TestWriterAgent:
    @patch("crewai_colony.crews.Agent")
    def test_creates_agent_with_write_tools(self, mock_agent_cls: MagicMock) -> None:
        mock_agent_cls.return_value = MagicMock()
        toolkit = _make_toolkit()

        create_writer_agent(toolkit)
        call_kwargs = mock_agent_cls.call_args[1]
        assert call_kwargs["role"] == "Colony Writer"
        tool_names = {t.name for t in call_kwargs["tools"]}
        assert "colony_create_post" in tool_names
        assert "colony_comment_on_post" in tool_names


class TestCommunityAgent:
    @patch("crewai_colony.crews.Agent")
    def test_creates_agent_with_social_tools(self, mock_agent_cls: MagicMock) -> None:
        mock_agent_cls.return_value = MagicMock()
        toolkit = _make_toolkit()

        create_community_agent(toolkit)
        call_kwargs = mock_agent_cls.call_args[1]
        assert call_kwargs["role"] == "Colony Community Manager"
        tool_names = {t.name for t in call_kwargs["tools"]}
        assert "colony_get_notifications" in tool_names
        assert "colony_send_message" in tool_names
        assert "colony_follow_user" in tool_names
        assert "colony_react_to_post" in tool_names


class TestResearchCrew:
    @patch("crewai_colony.crews.Crew")
    @patch("crewai_colony.crews.Task")
    @patch("crewai_colony.crews.Agent")
    @patch("crewai_colony.crews.ColonyToolkit")
    def test_creates_crew_with_two_agents(
        self,
        mock_toolkit_cls: MagicMock,
        mock_agent_cls: MagicMock,
        mock_task_cls: MagicMock,
        mock_crew_cls: MagicMock,
    ) -> None:
        mock_toolkit = MagicMock()
        mock_toolkit.get_tools.return_value = []
        mock_toolkit_cls.return_value = mock_toolkit

        create_research_crew("col_test", "AI agents")

        # Two agents created (scout + writer)
        assert mock_agent_cls.call_count == 2
        # Two tasks created
        assert mock_task_cls.call_count == 2
        # One crew created
        mock_crew_cls.assert_called_once()


class TestEngagementCrew:
    @patch("crewai_colony.crews.Crew")
    @patch("crewai_colony.crews.Task")
    @patch("crewai_colony.crews.Agent")
    @patch("crewai_colony.crews.ColonyToolkit")
    def test_creates_crew_with_finder_and_responder(
        self,
        mock_toolkit_cls: MagicMock,
        mock_agent_cls: MagicMock,
        mock_task_cls: MagicMock,
        mock_crew_cls: MagicMock,
    ) -> None:
        mock_toolkit = MagicMock()
        mock_toolkit.get_tools.return_value = []
        mock_toolkit_cls.return_value = mock_toolkit

        create_engagement_crew("col_test")

        assert mock_agent_cls.call_count == 2
        assert mock_task_cls.call_count == 2
        mock_crew_cls.assert_called_once()

        # Verify agents have correct roles
        roles = [call[1]["role"] for call in mock_agent_cls.call_args_list]
        assert "Question Finder" in roles
        assert "Community Responder" in roles

    @patch("crewai_colony.crews.Crew")
    @patch("crewai_colony.crews.Task")
    @patch("crewai_colony.crews.Agent")
    @patch("crewai_colony.crews.ColonyToolkit")
    def test_custom_colony(
        self,
        mock_toolkit_cls: MagicMock,
        mock_agent_cls: MagicMock,
        mock_task_cls: MagicMock,
        mock_crew_cls: MagicMock,
    ) -> None:
        mock_toolkit = MagicMock()
        mock_toolkit.get_tools.return_value = []
        mock_toolkit_cls.return_value = mock_toolkit

        create_engagement_crew("col_test", colony="general")

        # Task description should mention the colony
        task_desc = mock_task_cls.call_args_list[0][1]["description"]
        assert "general" in task_desc


class TestNewsletterCrew:
    @patch("crewai_colony.crews.Crew")
    @patch("crewai_colony.crews.Task")
    @patch("crewai_colony.crews.Agent")
    @patch("crewai_colony.crews.ColonyToolkit")
    def test_creates_crew_with_curator_and_summarizer(
        self,
        mock_toolkit_cls: MagicMock,
        mock_agent_cls: MagicMock,
        mock_task_cls: MagicMock,
        mock_crew_cls: MagicMock,
    ) -> None:
        mock_toolkit = MagicMock()
        mock_toolkit.get_tools.return_value = []
        mock_toolkit_cls.return_value = mock_toolkit

        create_newsletter_crew("col_test")

        assert mock_agent_cls.call_count == 2
        assert mock_task_cls.call_count == 2
        mock_crew_cls.assert_called_once()

        roles = [call[1]["role"] for call in mock_agent_cls.call_args_list]
        assert "Content Curator" in roles
        assert "Newsletter Writer" in roles

    @patch("crewai_colony.crews.Crew")
    @patch("crewai_colony.crews.Task")
    @patch("crewai_colony.crews.Agent")
    @patch("crewai_colony.crews.ColonyToolkit")
    def test_custom_period(
        self,
        mock_toolkit_cls: MagicMock,
        mock_agent_cls: MagicMock,
        mock_task_cls: MagicMock,
        mock_crew_cls: MagicMock,
    ) -> None:
        mock_toolkit = MagicMock()
        mock_toolkit.get_tools.return_value = []
        mock_toolkit_cls.return_value = mock_toolkit

        create_newsletter_crew("col_test", period="month")

        # Both tasks should mention the period
        for call in mock_task_cls.call_args_list:
            assert "month" in call[1]["description"].lower()
