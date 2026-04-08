"""Tests for crewai-colony tools."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from crewai_colony import (
    ColonyCommentOnPost,
    ColonyCreatePost,
    ColonyFollowUser,
    ColonyGetConversation,
    ColonyGetMe,
    ColonyGetPost,
    ColonyGetUser,
    ColonyListColonies,
    ColonySearchPosts,
    ColonySendMessage,
    ColonyToolkit,
    ColonyUnfollowUser,
    ColonyUpdateProfile,
    ColonyVoteOnComment,
    ColonyVoteOnPost,
)


@pytest.fixture
def mock_client() -> MagicMock:
    return MagicMock()


# ── Read tools ─────────────────────────────────────────────────────


class TestSearchPosts:
    def test_calls_get_posts(self, mock_client: MagicMock) -> None:
        mock_client.get_posts.return_value = {"posts": []}
        tool = ColonySearchPosts(client=mock_client)
        result = tool._run(query="hello")
        mock_client.get_posts.assert_called_once_with(colony=None, sort="hot", limit=10, search="hello")
        assert "posts" in result

    def test_empty_query_passes_none(self, mock_client: MagicMock) -> None:
        mock_client.get_posts.return_value = {"posts": []}
        tool = ColonySearchPosts(client=mock_client)
        tool._run(query="")
        mock_client.get_posts.assert_called_once_with(colony=None, sort="hot", limit=10, search=None)

    def test_with_colony_filter(self, mock_client: MagicMock) -> None:
        mock_client.get_posts.return_value = {"posts": []}
        tool = ColonySearchPosts(client=mock_client)
        tool._run(query="ai", colony="findings", sort="new", limit=5)
        mock_client.get_posts.assert_called_once_with(colony="findings", sort="new", limit=5, search="ai")


class TestGetPost:
    def test_calls_get_post(self, mock_client: MagicMock) -> None:
        mock_client.get_post.return_value = {"id": "abc", "title": "Test"}
        tool = ColonyGetPost(client=mock_client)
        result = tool._run(post_id="abc")
        mock_client.get_post.assert_called_once_with("abc")
        data = json.loads(result)
        assert data["id"] == "abc"


class TestGetMe:
    def test_calls_get_me(self, mock_client: MagicMock) -> None:
        mock_client.get_me.return_value = {"username": "test-agent"}
        tool = ColonyGetMe(client=mock_client)
        result = tool._run()
        mock_client.get_me.assert_called_once()
        assert "test-agent" in result


class TestGetUser:
    def test_calls_get_user(self, mock_client: MagicMock) -> None:
        mock_client.get_user.return_value = {"username": "other-agent"}
        tool = ColonyGetUser(client=mock_client)
        result = tool._run(user_id="uid-123")
        mock_client.get_user.assert_called_once_with("uid-123")
        assert "other-agent" in result


class TestListColonies:
    def test_calls_get_colonies(self, mock_client: MagicMock) -> None:
        mock_client.get_colonies.return_value = {"colonies": []}
        tool = ColonyListColonies(client=mock_client)
        result = tool._run()
        mock_client.get_colonies.assert_called_once_with(limit=50)
        assert "colonies" in result


class TestGetConversation:
    def test_calls_get_conversation(self, mock_client: MagicMock) -> None:
        mock_client.get_conversation.return_value = {"messages": []}
        tool = ColonyGetConversation(client=mock_client)
        result = tool._run(username="buddy")
        mock_client.get_conversation.assert_called_once_with("buddy")
        assert "messages" in result


# ── Write tools ────────────────────────────────────────────────────


class TestCreatePost:
    def test_calls_create_post(self, mock_client: MagicMock) -> None:
        mock_client.create_post.return_value = {"id": "new-post"}
        tool = ColonyCreatePost(client=mock_client)
        result = tool._run(title="Hello", body="World")
        mock_client.create_post.assert_called_once_with(
            title="Hello", body="World", colony="general", post_type="discussion"
        )
        assert "new-post" in result

    def test_custom_colony_and_type(self, mock_client: MagicMock) -> None:
        mock_client.create_post.return_value = {"id": "p2"}
        tool = ColonyCreatePost(client=mock_client)
        tool._run(title="T", body="B", colony="findings", post_type="analysis")
        mock_client.create_post.assert_called_once_with(title="T", body="B", colony="findings", post_type="analysis")


class TestCommentOnPost:
    def test_calls_create_comment(self, mock_client: MagicMock) -> None:
        mock_client.create_comment.return_value = {"id": "c1"}
        tool = ColonyCommentOnPost(client=mock_client)
        result = tool._run(post_id="p1", body="Nice!")
        mock_client.create_comment.assert_called_once_with("p1", "Nice!", parent_id=None)
        assert "c1" in result

    def test_threaded_reply(self, mock_client: MagicMock) -> None:
        mock_client.create_comment.return_value = {"id": "c2"}
        tool = ColonyCommentOnPost(client=mock_client)
        tool._run(post_id="p1", body="Reply", parent_id="c1")
        mock_client.create_comment.assert_called_once_with("p1", "Reply", parent_id="c1")


class TestVoteOnPost:
    def test_upvote(self, mock_client: MagicMock) -> None:
        mock_client.vote_post.return_value = {"score": 5}
        tool = ColonyVoteOnPost(client=mock_client)
        tool._run(post_id="p1")
        mock_client.vote_post.assert_called_once_with("p1", value=1)

    def test_downvote(self, mock_client: MagicMock) -> None:
        mock_client.vote_post.return_value = {"score": 3}
        tool = ColonyVoteOnPost(client=mock_client)
        tool._run(post_id="p1", value=-1)
        mock_client.vote_post.assert_called_once_with("p1", value=-1)


class TestVoteOnComment:
    def test_upvote(self, mock_client: MagicMock) -> None:
        mock_client.vote_comment.return_value = {"score": 2}
        tool = ColonyVoteOnComment(client=mock_client)
        tool._run(comment_id="c1")
        mock_client.vote_comment.assert_called_once_with("c1", value=1)


class TestSendMessage:
    def test_calls_send_message(self, mock_client: MagicMock) -> None:
        mock_client.send_message.return_value = {"id": "m1"}
        tool = ColonySendMessage(client=mock_client)
        tool._run(username="friend", body="Hey!")
        mock_client.send_message.assert_called_once_with("friend", "Hey!")


class TestFollowUser:
    def test_calls_follow(self, mock_client: MagicMock) -> None:
        mock_client.follow.return_value = {}
        tool = ColonyFollowUser(client=mock_client)
        tool._run(user_id="uid-1")
        mock_client.follow.assert_called_once_with("uid-1")


class TestUnfollowUser:
    def test_calls_unfollow(self, mock_client: MagicMock) -> None:
        mock_client.unfollow.return_value = {}
        tool = ColonyUnfollowUser(client=mock_client)
        tool._run(user_id="uid-1")
        mock_client.unfollow.assert_called_once_with("uid-1")


class TestUpdateProfile:
    def test_calls_update_profile(self, mock_client: MagicMock) -> None:
        mock_client.update_profile.return_value = {"bio": "new bio"}
        tool = ColonyUpdateProfile(client=mock_client)
        tool._run(bio="new bio")
        mock_client.update_profile.assert_called_once_with(bio="new bio")

    def test_no_fields_returns_error(self, mock_client: MagicMock) -> None:
        tool = ColonyUpdateProfile(client=mock_client)
        result = tool._run()
        assert "Error" in result
        mock_client.update_profile.assert_not_called()


# ── Error handling ─────────────────────────────────────────────────


class TestErrorHandling:
    def test_api_error_returns_string(self, mock_client: MagicMock) -> None:
        mock_client.get_me.side_effect = Exception("401 Unauthorized")
        tool = ColonyGetMe(client=mock_client)
        result = tool._run()
        assert "Error" in result
        assert "401" in result


# ── Toolkit ────────────────────────────────────────────────────────


class TestToolkit:
    def test_get_all_tools(self) -> None:
        toolkit = ColonyToolkit.__new__(ColonyToolkit)
        toolkit.client = MagicMock()
        toolkit.read_only = False
        tools = toolkit.get_tools()
        assert len(tools) == 14
        names = {t.name for t in tools}
        assert "colony_create_post" in names
        assert "colony_search_posts" in names

    def test_read_only(self) -> None:
        toolkit = ColonyToolkit.__new__(ColonyToolkit)
        toolkit.client = MagicMock()
        toolkit.read_only = True
        tools = toolkit.get_tools()
        assert len(tools) == 6
        names = {t.name for t in tools}
        assert "colony_search_posts" in names
        assert "colony_create_post" not in names

    def test_include_filter(self) -> None:
        toolkit = ColonyToolkit.__new__(ColonyToolkit)
        toolkit.client = MagicMock()
        toolkit.read_only = False
        tools = toolkit.get_tools(include=["colony_get_me", "colony_create_post"])
        assert len(tools) == 2

    def test_exclude_filter(self) -> None:
        toolkit = ColonyToolkit.__new__(ColonyToolkit)
        toolkit.client = MagicMock()
        toolkit.read_only = False
        tools = toolkit.get_tools(exclude=["colony_create_post"])
        assert len(tools) == 13
        names = {t.name for t in tools}
        assert "colony_create_post" not in names
