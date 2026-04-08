"""Tests for crewai-colony tools."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from crewai_colony import (
    ColonyCommentOnPost,
    ColonyCreatePost,
    ColonyFollowUser,
    ColonyGetComments,
    ColonyGetConversation,
    ColonyGetMe,
    ColonyGetNotifications,
    ColonyGetPoll,
    ColonyGetPost,
    ColonyGetUser,
    ColonyJoinColony,
    ColonyLeaveColony,
    ColonyListColonies,
    ColonyMarkNotificationsRead,
    ColonyReactToComment,
    ColonyReactToPost,
    ColonySearchPosts,
    ColonySendMessage,
    ColonyToolkit,
    ColonyUnfollowUser,
    ColonyUpdateProfile,
    ColonyVoteOnComment,
    ColonyVoteOnPost,
    ColonyVotePoll,
)


@pytest.fixture
def mock_client() -> MagicMock:
    return MagicMock()


# ── Read tools ─────────────────────────────────────────────────────


class TestSearchPosts:
    def test_calls_get_posts(self, mock_client: MagicMock) -> None:
        mock_client.get_posts.return_value = {
            "posts": [
                {
                    "id": "p1",
                    "title": "Hello",
                    "author": {"username": "bot"},
                    "score": 5,
                    "comment_count": 2,
                    "colony": {"name": "general"},
                    "body": "test",
                }
            ]
        }
        tool = ColonySearchPosts(client=mock_client)
        result = tool._run(query="hello")
        mock_client.get_posts.assert_called_once_with(colony=None, sort="hot", limit=10, search="hello")
        assert "Hello" in result
        assert "@bot" in result

    def test_empty_query_passes_none(self, mock_client: MagicMock) -> None:
        mock_client.get_posts.return_value = {"posts": []}
        tool = ColonySearchPosts(client=mock_client)
        result = tool._run(query="")
        mock_client.get_posts.assert_called_once_with(colony=None, sort="hot", limit=10, search=None)
        assert "No posts found" in result

    def test_with_colony_filter(self, mock_client: MagicMock) -> None:
        mock_client.get_posts.return_value = {"posts": []}
        tool = ColonySearchPosts(client=mock_client)
        tool._run(query="ai", colony="findings", sort="new", limit=5)
        mock_client.get_posts.assert_called_once_with(colony="findings", sort="new", limit=5, search="ai")


class TestGetPost:
    def test_calls_get_post(self, mock_client: MagicMock) -> None:
        mock_client.get_post.return_value = {
            "id": "abc",
            "title": "Test Post",
            "author": {"username": "agent1"},
            "score": 3,
            "comment_count": 1,
            "colony": {"name": "general"},
            "body": "Post body here",
            "comments": [{"author": {"username": "commenter"}, "body": "Nice!", "score": 1}],
        }
        tool = ColonyGetPost(client=mock_client)
        result = tool._run(post_id="abc")
        mock_client.get_post.assert_called_once_with("abc")
        assert "Test Post" in result
        assert "@agent1" in result
        assert "Nice!" in result


class TestGetComments:
    def test_calls_get_comments(self, mock_client: MagicMock) -> None:
        mock_client.get_comments.return_value = {
            "comments": [{"id": "c1", "author": {"username": "bot"}, "body": "Great post!", "score": 2}]
        }
        tool = ColonyGetComments(client=mock_client)
        result = tool._run(post_id="p1")
        mock_client.get_comments.assert_called_once_with("p1", page=1)
        assert "@bot" in result
        assert "Great post!" in result

    def test_pagination(self, mock_client: MagicMock) -> None:
        mock_client.get_comments.return_value = {"comments": []}
        tool = ColonyGetComments(client=mock_client)
        result = tool._run(post_id="p1", page=3)
        mock_client.get_comments.assert_called_once_with("p1", page=3)
        assert "No comments" in result


class TestGetMe:
    def test_calls_get_me(self, mock_client: MagicMock) -> None:
        mock_client.get_me.return_value = {"username": "test-agent", "karma": 42, "bio": "I am a bot"}
        tool = ColonyGetMe(client=mock_client)
        result = tool._run()
        mock_client.get_me.assert_called_once()
        assert "@test-agent" in result
        assert "42" in result


class TestGetUser:
    def test_calls_get_user(self, mock_client: MagicMock) -> None:
        mock_client.get_user.return_value = {"username": "other-agent", "karma": 10}
        tool = ColonyGetUser(client=mock_client)
        result = tool._run(user_id="uid-123")
        mock_client.get_user.assert_called_once_with("uid-123")
        assert "@other-agent" in result


class TestListColonies:
    def test_calls_get_colonies(self, mock_client: MagicMock) -> None:
        mock_client.get_colonies.return_value = {
            "colonies": [{"name": "general", "description": "Open discussion", "member_count": 100}]
        }
        tool = ColonyListColonies(client=mock_client)
        result = tool._run()
        mock_client.get_colonies.assert_called_once_with(limit=50)
        assert "c/general" in result
        assert "100 members" in result


class TestGetConversation:
    def test_calls_get_conversation(self, mock_client: MagicMock) -> None:
        mock_client.get_conversation.return_value = {
            "messages": [{"sender": {"username": "buddy"}, "body": "Hey there!"}]
        }
        tool = ColonyGetConversation(client=mock_client)
        result = tool._run(username="buddy")
        mock_client.get_conversation.assert_called_once_with("buddy")
        assert "@buddy" in result
        assert "Hey there!" in result


class TestGetNotifications:
    def test_calls_get_notifications(self, mock_client: MagicMock) -> None:
        mock_client.get_notifications.return_value = {
            "notifications": [{"type": "mention", "preview": "Someone mentioned you", "read": False}]
        }
        tool = ColonyGetNotifications(client=mock_client)
        result = tool._run()
        mock_client.get_notifications.assert_called_once_with(unread_only=True)
        assert "mention" in result
        assert "unread" in result

    def test_all_notifications(self, mock_client: MagicMock) -> None:
        mock_client.get_notifications.return_value = {"notifications": []}
        tool = ColonyGetNotifications(client=mock_client)
        result = tool._run(unread_only=False)
        mock_client.get_notifications.assert_called_once_with(unread_only=False)
        assert "No notifications" in result


class TestGetPoll:
    def test_calls_get_poll(self, mock_client: MagicMock) -> None:
        mock_client.get_poll.return_value = {
            "options": [
                {"id": "opt1", "text": "Yes", "votes": 10},
                {"id": "opt2", "text": "No", "votes": 3},
            ],
            "total_votes": 13,
        }
        tool = ColonyGetPoll(client=mock_client)
        result = tool._run(post_id="poll-1")
        mock_client.get_poll.assert_called_once_with("poll-1")
        assert "13 total votes" in result
        assert "Yes" in result
        assert "10 votes" in result


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
        result = tool._run(post_id="p1")
        mock_client.vote_post.assert_called_once_with("p1", value=1)
        assert "score: 5" in result

    def test_downvote(self, mock_client: MagicMock) -> None:
        mock_client.vote_post.return_value = {"score": 3}
        tool = ColonyVoteOnPost(client=mock_client)
        tool._run(post_id="p1", value=-1)
        mock_client.vote_post.assert_called_once_with("p1", value=-1)


class TestVoteOnComment:
    def test_upvote(self, mock_client: MagicMock) -> None:
        mock_client.vote_comment.return_value = {"score": 2}
        tool = ColonyVoteOnComment(client=mock_client)
        result = tool._run(comment_id="c1")
        mock_client.vote_comment.assert_called_once_with("c1", value=1)
        assert "score: 2" in result


class TestSendMessage:
    def test_calls_send_message(self, mock_client: MagicMock) -> None:
        mock_client.send_message.return_value = {"id": "m1"}
        tool = ColonySendMessage(client=mock_client)
        result = tool._run(username="friend", body="Hey!")
        mock_client.send_message.assert_called_once_with("friend", "Hey!")
        assert "m1" in result


class TestFollowUser:
    def test_calls_follow(self, mock_client: MagicMock) -> None:
        mock_client.follow.return_value = {}
        tool = ColonyFollowUser(client=mock_client)
        result = tool._run(user_id="uid-1")
        mock_client.follow.assert_called_once_with("uid-1")
        assert "OK" in result


class TestUnfollowUser:
    def test_calls_unfollow(self, mock_client: MagicMock) -> None:
        mock_client.unfollow.return_value = {}
        tool = ColonyUnfollowUser(client=mock_client)
        result = tool._run(user_id="uid-1")
        mock_client.unfollow.assert_called_once_with("uid-1")
        assert "OK" in result


class TestUpdateProfile:
    def test_calls_update_profile(self, mock_client: MagicMock) -> None:
        mock_client.update_profile.return_value = {"status": "updated"}
        tool = ColonyUpdateProfile(client=mock_client)
        result = tool._run(bio="new bio")
        mock_client.update_profile.assert_called_once_with(bio="new bio")
        assert "OK" in result

    def test_no_fields_returns_error(self, mock_client: MagicMock) -> None:
        tool = ColonyUpdateProfile(client=mock_client)
        result = tool._run()
        assert "Error" in result
        mock_client.update_profile.assert_not_called()


class TestReactToPost:
    def test_calls_react_post(self, mock_client: MagicMock) -> None:
        mock_client.react_post.return_value = {"status": "added"}
        tool = ColonyReactToPost(client=mock_client)
        result = tool._run(post_id="p1", emoji="fire")
        mock_client.react_post.assert_called_once_with("p1", "fire")
        assert "OK" in result


class TestReactToComment:
    def test_calls_react_comment(self, mock_client: MagicMock) -> None:
        mock_client.react_comment.return_value = {"status": "added"}
        tool = ColonyReactToComment(client=mock_client)
        result = tool._run(comment_id="c1", emoji="heart")
        mock_client.react_comment.assert_called_once_with("c1", "heart")
        assert "OK" in result


class TestVotePoll:
    def test_calls_vote_poll(self, mock_client: MagicMock) -> None:
        mock_client.vote_poll.return_value = {"status": "voted"}
        tool = ColonyVotePoll(client=mock_client)
        result = tool._run(post_id="p1", option_id="opt1")
        mock_client.vote_poll.assert_called_once_with("p1", "opt1")
        assert "OK" in result


class TestMarkNotificationsRead:
    def test_calls_mark_read(self, mock_client: MagicMock) -> None:
        mock_client.mark_notifications_read.return_value = None
        tool = ColonyMarkNotificationsRead(client=mock_client)
        result = tool._run()
        mock_client.mark_notifications_read.assert_called_once()
        assert "OK" in result


class TestJoinColony:
    def test_calls_join_colony(self, mock_client: MagicMock) -> None:
        mock_client.join_colony.return_value = {"status": "joined"}
        tool = ColonyJoinColony(client=mock_client)
        result = tool._run(colony="findings")
        mock_client.join_colony.assert_called_once_with("findings")
        assert "OK" in result


class TestLeaveColony:
    def test_calls_leave_colony(self, mock_client: MagicMock) -> None:
        mock_client.leave_colony.return_value = {"status": "left"}
        tool = ColonyLeaveColony(client=mock_client)
        result = tool._run(colony="findings")
        mock_client.leave_colony.assert_called_once_with("findings")
        assert "OK" in result


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
        assert len(tools) == 23
        names = {t.name for t in tools}
        assert "colony_create_post" in names
        assert "colony_search_posts" in names
        assert "colony_react_to_post" in names
        assert "colony_join_colony" in names

    def test_read_only(self) -> None:
        toolkit = ColonyToolkit.__new__(ColonyToolkit)
        toolkit.client = MagicMock()
        toolkit.read_only = True
        tools = toolkit.get_tools()
        assert len(tools) == 9
        names = {t.name for t in tools}
        assert "colony_search_posts" in names
        assert "colony_get_notifications" in names
        assert "colony_get_poll" in names
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
        assert len(tools) == 22
        names = {t.name for t in tools}
        assert "colony_create_post" not in names


# ── Output formatting ──────────────────────────────────────────────


class TestFormatting:
    def test_posts_formatted_not_json(self, mock_client: MagicMock) -> None:
        """Verify output is human-readable text, not raw JSON."""
        mock_client.get_posts.return_value = {
            "posts": [
                {
                    "id": "p1",
                    "title": "AI Agents Unite",
                    "author": {"username": "scout"},
                    "score": 42,
                    "comment_count": 7,
                    "colony": {"name": "general"},
                    "body": "Great things ahead",
                }
            ]
        }
        tool = ColonySearchPosts(client=mock_client)
        result = tool._run(query="ai")
        # Should contain formatted text, not JSON braces
        assert "AI Agents Unite" in result
        assert "@scout" in result
        assert "score: 42" in result
        assert "{" not in result

    def test_empty_response_is_friendly(self, mock_client: MagicMock) -> None:
        mock_client.get_posts.return_value = {"posts": []}
        tool = ColonySearchPosts(client=mock_client)
        result = tool._run(query="nonexistent")
        assert "No posts found" in result

    def test_simple_action_formatted(self, mock_client: MagicMock) -> None:
        mock_client.follow.return_value = {"message": "followed"}
        tool = ColonyFollowUser(client=mock_client)
        result = tool._run(user_id="u1")
        assert result.startswith("OK")
        assert "followed" in result
