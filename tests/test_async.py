"""Async tests for crewai-colony tools — verifies all _arun() methods work."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from crewai_colony import (
    ColonyCommentOnPost,
    ColonyCreatePost,
    ColonyCreateWebhook,
    ColonyDeletePost,
    ColonyDeleteWebhook,
    ColonyFollowUser,
    ColonyGetAllComments,
    ColonyGetComments,
    ColonyGetConversation,
    ColonyGetMe,
    ColonyGetNotifications,
    ColonyGetPoll,
    ColonyGetPost,
    ColonyGetUnreadCount,
    ColonyGetUser,
    ColonyGetWebhooks,
    ColonyJoinColony,
    ColonyLeaveColony,
    ColonyListColonies,
    ColonyMarkNotificationsRead,
    ColonyReactToComment,
    ColonyReactToPost,
    ColonySearch,
    ColonySearchPosts,
    ColonySendMessage,
    ColonyUnfollowUser,
    ColonyUpdatePost,
    ColonyUpdateProfile,
    ColonyVoteOnComment,
    ColonyVoteOnPost,
    ColonyVotePoll,
)


@pytest.fixture
def mock_client() -> MagicMock:
    return MagicMock()


# ── Read tools ─────────────────────────────────────────────────────


class TestAsyncSearchPosts:
    async def test_arun_search(self, mock_client: MagicMock) -> None:
        mock_client.get_posts.return_value = {
            "posts": [
                {
                    "id": "p1",
                    "title": "Hello",
                    "author": {"username": "bot"},
                    "score": 1,
                    "comment_count": 0,
                    "colony": "general",
                    "body": "",
                }
            ]
        }
        tool = ColonySearchPosts(client=mock_client)
        result = await tool._arun(query="hello")
        mock_client.get_posts.assert_called_once()
        assert "Hello" in result


class TestAsyncSearch:
    async def test_arun_search(self, mock_client: MagicMock) -> None:
        mock_client.search.return_value = {"results": []}
        tool = ColonySearch(client=mock_client)
        result = await tool._arun(query="test")
        mock_client.search.assert_called_once()
        assert "No results" in result


class TestAsyncGetPost:
    async def test_arun(self, mock_client: MagicMock) -> None:
        mock_client.get_post.return_value = {
            "id": "p1",
            "title": "T",
            "author": {"username": "a"},
            "score": 0,
            "comment_count": 0,
            "colony": "general",
            "body": "B",
        }
        tool = ColonyGetPost(client=mock_client)
        result = await tool._arun(post_id="p1")
        mock_client.get_post.assert_called_once_with("p1")
        assert "T" in result


class TestAsyncGetComments:
    async def test_arun(self, mock_client: MagicMock) -> None:
        mock_client.get_comments.return_value = {"comments": []}
        tool = ColonyGetComments(client=mock_client)
        result = await tool._arun(post_id="p1", page=2)
        mock_client.get_comments.assert_called_once_with("p1", page=2)
        assert "No comments" in result


class TestAsyncGetAllComments:
    async def test_arun(self, mock_client: MagicMock) -> None:
        mock_client.get_all_comments.return_value = [
            {"id": "c1", "author": {"username": "bot"}, "body": "Hi", "score": 1}
        ]
        tool = ColonyGetAllComments(client=mock_client)
        result = await tool._arun(post_id="p1")
        mock_client.get_all_comments.assert_called_once_with("p1")
        assert "@bot" in result


class TestAsyncGetMe:
    async def test_arun(self, mock_client: MagicMock) -> None:
        mock_client.get_me.return_value = {"username": "me", "karma": 5}
        tool = ColonyGetMe(client=mock_client)
        result = await tool._arun()
        mock_client.get_me.assert_called_once()
        assert "@me" in result


class TestAsyncGetUser:
    async def test_arun(self, mock_client: MagicMock) -> None:
        mock_client.get_user.return_value = {"username": "other", "karma": 1}
        tool = ColonyGetUser(client=mock_client)
        result = await tool._arun(user_id="uid")
        mock_client.get_user.assert_called_once_with("uid")
        assert "@other" in result


class TestAsyncListColonies:
    async def test_arun(self, mock_client: MagicMock) -> None:
        mock_client.get_colonies.return_value = {"colonies": []}
        tool = ColonyListColonies(client=mock_client)
        result = await tool._arun()
        mock_client.get_colonies.assert_called_once()
        assert "No colonies" in result


class TestAsyncGetConversation:
    async def test_arun(self, mock_client: MagicMock) -> None:
        mock_client.get_conversation.return_value = {"messages": []}
        tool = ColonyGetConversation(client=mock_client)
        result = await tool._arun(username="buddy")
        mock_client.get_conversation.assert_called_once_with("buddy")
        assert "No messages" in result


class TestAsyncGetNotifications:
    async def test_arun(self, mock_client: MagicMock) -> None:
        mock_client.get_notifications.return_value = {"notifications": []}
        tool = ColonyGetNotifications(client=mock_client)
        result = await tool._arun(unread_only=False)
        mock_client.get_notifications.assert_called_once_with(unread_only=False)
        assert "No notifications" in result


class TestAsyncGetPoll:
    async def test_arun(self, mock_client: MagicMock) -> None:
        mock_client.get_poll.return_value = {"options": [], "total_votes": 0}
        tool = ColonyGetPoll(client=mock_client)
        result = await tool._arun(post_id="p1")
        mock_client.get_poll.assert_called_once_with("p1")
        assert "0 total votes" in result


class TestAsyncGetUnreadCount:
    async def test_arun(self, mock_client: MagicMock) -> None:
        mock_client.get_unread_count.return_value = {"count": 3}
        tool = ColonyGetUnreadCount(client=mock_client)
        result = await tool._arun()
        mock_client.get_unread_count.assert_called_once()
        assert "3" in result


class TestAsyncGetWebhooks:
    async def test_arun(self, mock_client: MagicMock) -> None:
        mock_client.get_webhooks.return_value = {"webhooks": []}
        tool = ColonyGetWebhooks(client=mock_client)
        result = await tool._arun()
        mock_client.get_webhooks.assert_called_once()
        assert "No webhooks" in result


# ── Write tools ────────────────────────────────────────────────────


class TestAsyncCreatePost:
    async def test_arun(self, mock_client: MagicMock) -> None:
        mock_client.create_post.return_value = {"id": "new"}
        tool = ColonyCreatePost(client=mock_client)
        result = await tool._arun(title="T", body="B")
        mock_client.create_post.assert_called_once()
        assert "new" in result


class TestAsyncUpdatePost:
    async def test_arun(self, mock_client: MagicMock) -> None:
        mock_client.update_post.return_value = {"id": "p1"}
        tool = ColonyUpdatePost(client=mock_client)
        result = await tool._arun(post_id="p1", title="New")
        mock_client.update_post.assert_called_once_with("p1", title="New")
        assert "OK" in result

    async def test_arun_no_fields(self, mock_client: MagicMock) -> None:
        tool = ColonyUpdatePost(client=mock_client)
        result = await tool._arun(post_id="p1")
        assert "Error" in result


class TestAsyncDeletePost:
    async def test_arun(self, mock_client: MagicMock) -> None:
        mock_client.delete_post.return_value = {}
        tool = ColonyDeletePost(client=mock_client)
        result = await tool._arun(post_id="p1")
        mock_client.delete_post.assert_called_once_with("p1")
        assert "OK" in result


class TestAsyncCommentOnPost:
    async def test_arun(self, mock_client: MagicMock) -> None:
        mock_client.create_comment.return_value = {"id": "c1"}
        tool = ColonyCommentOnPost(client=mock_client)
        result = await tool._arun(post_id="p1", body="Nice!")
        mock_client.create_comment.assert_called_once()
        assert "c1" in result


class TestAsyncVoteOnPost:
    async def test_arun(self, mock_client: MagicMock) -> None:
        mock_client.vote_post.return_value = {"score": 5}
        tool = ColonyVoteOnPost(client=mock_client)
        result = await tool._arun(post_id="p1", value=-1)
        mock_client.vote_post.assert_called_once_with("p1", value=-1)
        assert "score: 5" in result


class TestAsyncVoteOnComment:
    async def test_arun(self, mock_client: MagicMock) -> None:
        mock_client.vote_comment.return_value = {"score": 2}
        tool = ColonyVoteOnComment(client=mock_client)
        result = await tool._arun(comment_id="c1")
        mock_client.vote_comment.assert_called_once_with("c1", value=1)
        assert "score: 2" in result


class TestAsyncSendMessage:
    async def test_arun(self, mock_client: MagicMock) -> None:
        mock_client.send_message.return_value = {"id": "m1"}
        tool = ColonySendMessage(client=mock_client)
        result = await tool._arun(username="friend", body="Hey")
        mock_client.send_message.assert_called_once_with("friend", "Hey")
        assert "m1" in result


class TestAsyncFollowUser:
    async def test_arun(self, mock_client: MagicMock) -> None:
        mock_client.follow.return_value = {}
        tool = ColonyFollowUser(client=mock_client)
        result = await tool._arun(user_id="u1")
        mock_client.follow.assert_called_once_with("u1")
        assert "OK" in result


class TestAsyncUnfollowUser:
    async def test_arun(self, mock_client: MagicMock) -> None:
        mock_client.unfollow.return_value = {}
        tool = ColonyUnfollowUser(client=mock_client)
        result = await tool._arun(user_id="u1")
        mock_client.unfollow.assert_called_once_with("u1")
        assert "OK" in result


class TestAsyncUpdateProfile:
    async def test_arun(self, mock_client: MagicMock) -> None:
        mock_client.update_profile.return_value = {}
        tool = ColonyUpdateProfile(client=mock_client)
        result = await tool._arun(bio="new bio")
        mock_client.update_profile.assert_called_once_with(bio="new bio")
        assert "OK" in result

    async def test_arun_no_fields(self, mock_client: MagicMock) -> None:
        tool = ColonyUpdateProfile(client=mock_client)
        result = await tool._arun()
        assert "Error" in result


class TestAsyncReactToPost:
    async def test_arun(self, mock_client: MagicMock) -> None:
        mock_client.react_post.return_value = {}
        tool = ColonyReactToPost(client=mock_client)
        result = await tool._arun(post_id="p1", emoji="fire")
        mock_client.react_post.assert_called_once_with("p1", "fire")
        assert "OK" in result


class TestAsyncReactToComment:
    async def test_arun(self, mock_client: MagicMock) -> None:
        mock_client.react_comment.return_value = {}
        tool = ColonyReactToComment(client=mock_client)
        result = await tool._arun(comment_id="c1", emoji="heart")
        mock_client.react_comment.assert_called_once_with("c1", "heart")
        assert "OK" in result


class TestAsyncVotePoll:
    async def test_arun(self, mock_client: MagicMock) -> None:
        mock_client.vote_poll.return_value = {}
        tool = ColonyVotePoll(client=mock_client)
        result = await tool._arun(post_id="p1", option_id="opt1")
        mock_client.vote_poll.assert_called_once_with("p1", "opt1")
        assert "OK" in result


class TestAsyncMarkNotificationsRead:
    async def test_arun(self, mock_client: MagicMock) -> None:
        mock_client.mark_notifications_read.return_value = None
        tool = ColonyMarkNotificationsRead(client=mock_client)
        result = await tool._arun()
        mock_client.mark_notifications_read.assert_called_once()
        assert "OK" in result


class TestAsyncJoinColony:
    async def test_arun(self, mock_client: MagicMock) -> None:
        mock_client.join_colony.return_value = {}
        tool = ColonyJoinColony(client=mock_client)
        result = await tool._arun(colony="general")
        mock_client.join_colony.assert_called_once_with("general")
        assert "OK" in result


class TestAsyncLeaveColony:
    async def test_arun(self, mock_client: MagicMock) -> None:
        mock_client.leave_colony.return_value = {}
        tool = ColonyLeaveColony(client=mock_client)
        result = await tool._arun(colony="general")
        mock_client.leave_colony.assert_called_once_with("general")
        assert "OK" in result


class TestAsyncCreateWebhook:
    async def test_arun(self, mock_client: MagicMock) -> None:
        mock_client.create_webhook.return_value = {"id": "wh-1"}
        tool = ColonyCreateWebhook(client=mock_client)
        result = await tool._arun(
            url="https://test.clny.cc/hook",
            events="post_created,comment_created",
            secret="supersecretkey1234",
        )
        mock_client.create_webhook.assert_called_once_with(
            "https://test.clny.cc/hook",
            ["post_created", "comment_created"],
            "supersecretkey1234",
        )
        assert "wh-1" in result


class TestAsyncDeleteWebhook:
    async def test_arun(self, mock_client: MagicMock) -> None:
        mock_client.delete_webhook.return_value = {}
        tool = ColonyDeleteWebhook(client=mock_client)
        result = await tool._arun(webhook_id="wh-1")
        mock_client.delete_webhook.assert_called_once_with("wh-1")
        assert "OK" in result


# ── Error handling in async ────────────────────────────────────────


class TestAsyncErrorHandling:
    async def test_arun_error_returns_string(self, mock_client: MagicMock) -> None:
        mock_client.get_me.side_effect = Exception("401 Unauthorized")
        tool = ColonyGetMe(client=mock_client)
        result = await tool._arun()
        assert "Error" in result
        assert "401" in result
