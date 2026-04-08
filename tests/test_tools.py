"""Tests for crewai-colony tools."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

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
    ColonyRegister,
    ColonySearch,
    ColonySearchPosts,
    ColonySendMessage,
    ColonyToolkit,
    ColonyUnfollowUser,
    ColonyUpdatePost,
    ColonyUpdateProfile,
    ColonyVoteOnComment,
    ColonyVoteOnPost,
    ColonyVotePoll,
    RetryConfig,
)
from crewai_colony.tools import _is_retryable, _safe_run


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


class TestSearch:
    def test_calls_search(self, mock_client: MagicMock) -> None:
        mock_client.search.return_value = {
            "results": [
                {
                    "id": "p1",
                    "title": "AI Agents",
                    "author": {"username": "scout"},
                    "score": 10,
                    "comment_count": 3,
                    "colony": "general",
                    "body": "Great post about AI",
                }
            ]
        }
        tool = ColonySearch(client=mock_client)
        result = tool._run(query="AI agents")
        mock_client.search.assert_called_once_with("AI agents", limit=20)
        assert "AI Agents" in result
        assert "@scout" in result

    def test_no_results(self, mock_client: MagicMock) -> None:
        mock_client.search.return_value = {"results": []}
        tool = ColonySearch(client=mock_client)
        result = tool._run(query="nonexistent")
        assert "No results found" in result

    def test_custom_limit(self, mock_client: MagicMock) -> None:
        mock_client.search.return_value = {"results": []}
        tool = ColonySearch(client=mock_client)
        tool._run(query="test", limit=5)
        mock_client.search.assert_called_once_with("test", limit=5)


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
            "comments": [
                {
                    "author": {"username": "commenter"},
                    "body": "Nice!",
                    "score": 1,
                }
            ],
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
            "comments": [
                {
                    "id": "c1",
                    "author": {"username": "bot"},
                    "body": "Great post!",
                    "score": 2,
                }
            ]
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
        mock_client.get_me.return_value = {
            "username": "test-agent",
            "karma": 42,
            "bio": "I am a bot",
        }
        tool = ColonyGetMe(client=mock_client)
        result = tool._run()
        mock_client.get_me.assert_called_once()
        assert "@test-agent" in result
        assert "42" in result


class TestGetUser:
    def test_calls_get_user(self, mock_client: MagicMock) -> None:
        mock_client.get_user.return_value = {
            "username": "other-agent",
            "karma": 10,
        }
        tool = ColonyGetUser(client=mock_client)
        result = tool._run(user_id="uid-123")
        mock_client.get_user.assert_called_once_with("uid-123")
        assert "@other-agent" in result


class TestListColonies:
    def test_calls_get_colonies(self, mock_client: MagicMock) -> None:
        mock_client.get_colonies.return_value = {
            "colonies": [
                {
                    "name": "general",
                    "description": "Open discussion",
                    "member_count": 100,
                }
            ]
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
            "notifications": [
                {
                    "type": "mention",
                    "preview": "Someone mentioned you",
                    "read": False,
                }
            ]
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


class TestGetUnreadCount:
    def test_calls_get_unread_count(self, mock_client: MagicMock) -> None:
        mock_client.get_unread_count.return_value = {"count": 7}
        tool = ColonyGetUnreadCount(client=mock_client)
        result = tool._run()
        mock_client.get_unread_count.assert_called_once()
        assert "Unread DMs: 7" in result

    def test_zero_unread(self, mock_client: MagicMock) -> None:
        mock_client.get_unread_count.return_value = {"count": 0}
        tool = ColonyGetUnreadCount(client=mock_client)
        result = tool._run()
        assert "Unread DMs: 0" in result


# ── Write tools ────────────────────────────────────────────────────


class TestCreatePost:
    def test_calls_create_post(self, mock_client: MagicMock) -> None:
        mock_client.create_post.return_value = {"id": "new-post"}
        tool = ColonyCreatePost(client=mock_client)
        result = tool._run(title="Hello", body="World")
        mock_client.create_post.assert_called_once_with(
            title="Hello",
            body="World",
            colony="general",
            post_type="discussion",
        )
        assert "new-post" in result

    def test_custom_colony_and_type(self, mock_client: MagicMock) -> None:
        mock_client.create_post.return_value = {"id": "p2"}
        tool = ColonyCreatePost(client=mock_client)
        tool._run(title="T", body="B", colony="findings", post_type="analysis")
        mock_client.create_post.assert_called_once_with(title="T", body="B", colony="findings", post_type="analysis")


class TestUpdatePost:
    def test_calls_update_post(self, mock_client: MagicMock) -> None:
        mock_client.update_post.return_value = {"id": "p1"}
        tool = ColonyUpdatePost(client=mock_client)
        result = tool._run(post_id="p1", title="New Title")
        mock_client.update_post.assert_called_once_with("p1", title="New Title")
        assert "OK" in result

    def test_update_body(self, mock_client: MagicMock) -> None:
        mock_client.update_post.return_value = {"id": "p1"}
        tool = ColonyUpdatePost(client=mock_client)
        tool._run(post_id="p1", body="Updated body")
        mock_client.update_post.assert_called_once_with("p1", body="Updated body")

    def test_no_fields_returns_error(self, mock_client: MagicMock) -> None:
        tool = ColonyUpdatePost(client=mock_client)
        result = tool._run(post_id="p1")
        assert "Error" in result
        mock_client.update_post.assert_not_called()


class TestDeletePost:
    def test_calls_delete_post(self, mock_client: MagicMock) -> None:
        mock_client.delete_post.return_value = {"status": "deleted"}
        tool = ColonyDeletePost(client=mock_client)
        result = tool._run(post_id="p1")
        mock_client.delete_post.assert_called_once_with("p1")
        assert "OK" in result


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


# ── New tools ──────────────────────────────────────────────────────


class TestGetAllComments:
    def test_calls_get_all_comments(self, mock_client: MagicMock) -> None:
        mock_client.get_all_comments.return_value = [
            {"id": "c1", "author": {"username": "bot"}, "body": "First!", "score": 1},
            {"id": "c2", "author": {"username": "agent"}, "body": "Second!", "score": 2},
        ]
        tool = ColonyGetAllComments(client=mock_client)
        result = tool._run(post_id="p1")
        mock_client.get_all_comments.assert_called_once_with("p1")
        assert "@bot" in result
        assert "@agent" in result

    def test_empty_comments(self, mock_client: MagicMock) -> None:
        mock_client.get_all_comments.return_value = []
        tool = ColonyGetAllComments(client=mock_client)
        result = tool._run(post_id="p1")
        assert "No comments" in result


class TestCreateWebhook:
    def test_calls_create_webhook(self, mock_client: MagicMock) -> None:
        mock_client.create_webhook.return_value = {"id": "wh-1"}
        tool = ColonyCreateWebhook(client=mock_client)
        result = tool._run(
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


class TestGetWebhooks:
    def test_calls_get_webhooks(self, mock_client: MagicMock) -> None:
        mock_client.get_webhooks.return_value = {
            "webhooks": [{"id": "wh-1", "url": "https://test.clny.cc/hook", "events": ["post_created"]}]
        }
        tool = ColonyGetWebhooks(client=mock_client)
        result = tool._run()
        mock_client.get_webhooks.assert_called_once()
        assert "wh-1" in result
        assert "test.clny.cc" in result

    def test_no_webhooks(self, mock_client: MagicMock) -> None:
        mock_client.get_webhooks.return_value = {"webhooks": []}
        tool = ColonyGetWebhooks(client=mock_client)
        result = tool._run()
        assert "No webhooks" in result


class TestDeleteWebhook:
    def test_calls_delete_webhook(self, mock_client: MagicMock) -> None:
        mock_client.delete_webhook.return_value = {"status": "deleted"}
        tool = ColonyDeleteWebhook(client=mock_client)
        result = tool._run(webhook_id="wh-1")
        mock_client.delete_webhook.assert_called_once_with("wh-1")
        assert "OK" in result


# ── Configurable retry ─────────────────────────────────────────────


class TestRetryConfig:
    @patch("crewai_colony.tools.time.sleep")
    def test_custom_retry_config(self, mock_sleep: MagicMock) -> None:
        """Verify custom RetryConfig is used by tools."""
        exc = Exception("rate limited")
        exc.status = 429  # type: ignore[attr-defined]
        call_count = 0

        def flaky(*args: Any, **kwargs: Any) -> dict[str, str]:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise exc
            return {"status": "ok"}

        from crewai_colony.tools import _fmt_simple

        config = RetryConfig(max_retries=5, base_delay=0.1, max_delay=1.0)
        result = _safe_run(flaky, _fmt_simple, _retry=config)
        assert "OK" in result
        assert call_count == 2
        # base_delay is 0.1 so first sleep should be 0.1
        mock_sleep.assert_called_once_with(0.1)

    def test_retry_config_defaults(self) -> None:
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 10.0


# ── Error handling & retry ─────────────────────────────────────────


class TestErrorHandling:
    def test_api_error_returns_string(self, mock_client: MagicMock) -> None:
        mock_client.get_me.side_effect = Exception("401 Unauthorized")
        tool = ColonyGetMe(client=mock_client)
        result = tool._run()
        assert "Error" in result
        assert "401" in result

    def test_colony_api_error_with_status(self, mock_client: MagicMock) -> None:
        """ColonyAPIError with status code gets a human-friendly hint."""
        exc = Exception("Not found")
        exc.status = 404  # type: ignore[attr-defined]
        exc.code = None  # type: ignore[attr-defined]
        exc.response = {}  # type: ignore[attr-defined]
        mock_client.get_post.side_effect = exc
        tool = ColonyGetPost(client=mock_client)
        result = tool._run(post_id="nonexistent")
        assert "Error" in result
        assert "404" in result
        assert "not found" in result.lower()

    def test_colony_api_error_with_code(self, mock_client: MagicMock) -> None:
        """Error code is included in the message."""
        exc = Exception("Already a member")
        exc.status = 409  # type: ignore[attr-defined]
        exc.code = "COLONY_ALREADY_MEMBER"  # type: ignore[attr-defined]
        exc.response = {"detail": "You are already a member of this colony"}  # type: ignore[attr-defined]
        mock_client.join_colony.side_effect = exc
        tool = ColonyJoinColony(client=mock_client)
        result = tool._run(colony="general")
        assert "Error" in result
        assert "409" in result
        assert "COLONY_ALREADY_MEMBER" in result
        assert "already" in result.lower()

    def test_colony_api_error_429_hint(self, mock_client: MagicMock) -> None:
        """429 gets a rate limit hint."""
        exc = Exception("Too many requests")
        exc.status = 429  # type: ignore[attr-defined]
        exc.code = "RATE_LIMIT_VOTE_HOURLY"  # type: ignore[attr-defined]
        exc.response = {}  # type: ignore[attr-defined]
        mock_client.vote_post.side_effect = exc
        tool = ColonyVoteOnPost(client=mock_client)
        result = tool._run(post_id="p1")
        assert "Rate limited" in result
        assert "RATE_LIMIT_VOTE_HOURLY" in result

    def test_network_error_message(self, mock_client: MagicMock) -> None:
        """Network errors without status codes still produce readable output."""
        mock_client.get_me.side_effect = ConnectionError("Connection refused")
        tool = ColonyGetMe(client=mock_client)
        result = tool._run()
        assert "Error" in result
        assert "Connection refused" in result

    def test_error_with_response_detail(self, mock_client: MagicMock) -> None:
        """Response body detail is included when available."""
        exc = Exception("Bad request")
        exc.status = 400  # type: ignore[attr-defined]
        exc.code = None  # type: ignore[attr-defined]
        exc.response = {"detail": "title must be at least 3 characters"}  # type: ignore[attr-defined]
        mock_client.create_post.side_effect = exc
        tool = ColonyCreatePost(client=mock_client)
        result = tool._run(title="Hi", body="test")
        assert "400" in result
        assert "title must be at least 3 characters" in result


class TestRetry:
    def test_is_retryable_429(self) -> None:
        exc = Exception("rate limited")
        exc.status = 429  # type: ignore[attr-defined]
        assert _is_retryable(exc) is True

    def test_is_retryable_500(self) -> None:
        exc = Exception("server error")
        exc.status = 500  # type: ignore[attr-defined]
        assert _is_retryable(exc) is True

    def test_not_retryable_404(self) -> None:
        exc = Exception("not found")
        exc.status = 404  # type: ignore[attr-defined]
        assert _is_retryable(exc) is False

    def test_not_retryable_plain_exception(self) -> None:
        assert _is_retryable(Exception("bad")) is False

    def test_retryable_timeout(self) -> None:
        assert _is_retryable(TimeoutError()) is True

    def test_retryable_connection_error(self) -> None:
        assert _is_retryable(ConnectionError()) is True

    @patch("crewai_colony.tools.time.sleep")
    def test_retries_on_429(self, mock_sleep: MagicMock) -> None:
        exc = Exception("rate limited")
        exc.status = 429  # type: ignore[attr-defined]
        call_count = 0

        def flaky(*args: Any, **kwargs: Any) -> dict[str, str]:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise exc
            return {"status": "ok"}

        from crewai_colony.tools import _fmt_simple

        result = _safe_run(flaky, _fmt_simple)
        assert "OK" in result
        assert call_count == 3
        assert mock_sleep.call_count == 2

    @patch("crewai_colony.tools.time.sleep")
    def test_no_retry_on_400(self, mock_sleep: MagicMock) -> None:
        exc = Exception("bad request")
        exc.status = 400  # type: ignore[attr-defined]

        def always_fail(*args: Any, **kwargs: Any) -> None:
            raise exc

        from crewai_colony.tools import _fmt_simple

        result = _safe_run(always_fail, _fmt_simple)
        assert "Error" in result
        mock_sleep.assert_not_called()

    @patch("crewai_colony.tools.time.sleep")
    def test_gives_up_after_max_retries(self, mock_sleep: MagicMock) -> None:
        exc = Exception("server error")
        exc.status = 500  # type: ignore[attr-defined]

        def always_fail(*args: Any, **kwargs: Any) -> None:
            raise exc

        from crewai_colony.tools import _fmt_simple

        result = _safe_run(always_fail, _fmt_simple)
        assert "Error" in result
        assert mock_sleep.call_count == 2  # retried twice before giving up


# ── Registration ───────────────────────────────────────────────────


class TestRegister:
    @patch("crewai_colony.tools.ColonyClient")
    def test_calls_register(self, mock_cls: MagicMock) -> None:
        mock_cls.register.return_value = {"api_key": "col_new_key"}
        tool = ColonyRegister()
        result = tool._run(
            username="new-agent",
            display_name="New Agent",
            bio="I am new",
        )
        mock_cls.register.assert_called_once_with(
            username="new-agent",
            display_name="New Agent",
            bio="I am new",
        )
        assert "col_new_key" in result
        assert "@new-agent" in result

    @patch("crewai_colony.tools.ColonyClient")
    def test_register_error(self, mock_cls: MagicMock) -> None:
        mock_cls.register.side_effect = Exception("username taken")
        tool = ColonyRegister()
        result = tool._run(
            username="taken",
            display_name="Taken",
            bio="...",
        )
        assert "Error" in result
        assert "username taken" in result


# ── Toolkit ────────────────────────────────────────────────────────


class TestToolkit:
    def _toolkit(self, read_only: bool = False) -> ColonyToolkit:
        toolkit = ColonyToolkit.__new__(ColonyToolkit)
        toolkit.client = MagicMock()
        toolkit.read_only = read_only
        toolkit.callbacks = []
        toolkit.retry = None
        return toolkit

    def test_get_all_tools(self) -> None:
        tools = self._toolkit().get_tools()
        assert len(tools) == 31
        names = {t.name for t in tools}
        assert "colony_create_post" in names
        assert "colony_get_all_comments" in names
        assert "colony_create_webhook" in names
        assert "colony_get_webhooks" in names
        assert "colony_delete_webhook" in names

    def test_read_only(self) -> None:
        tools = self._toolkit(read_only=True).get_tools()
        assert len(tools) == 13
        names = {t.name for t in tools}
        assert "colony_get_all_comments" in names
        assert "colony_get_webhooks" in names
        assert "colony_create_post" not in names

    def test_include_filter(self) -> None:
        tools = self._toolkit().get_tools(include=["colony_get_me", "colony_create_post"])
        assert len(tools) == 2

    def test_exclude_filter(self) -> None:
        tools = self._toolkit().get_tools(exclude=["colony_create_post"])
        assert len(tools) == 30
        names = {t.name for t in tools}
        assert "colony_create_post" not in names


# ── Output formatting ──────────────────────────────────────────────


class TestFormatting:
    def test_posts_formatted_not_json(self, mock_client: MagicMock) -> None:
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

    def test_search_results_formatted(self, mock_client: MagicMock) -> None:
        mock_client.search.return_value = {
            "results": [
                {
                    "id": "p5",
                    "title": "Found It",
                    "author": {"username": "finder"},
                    "score": 8,
                    "comment_count": 1,
                    "colony": "findings",
                    "body": "Here it is",
                }
            ]
        }
        tool = ColonySearch(client=mock_client)
        result = tool._run(query="test")
        assert "Found It" in result
        assert "@finder" in result
        assert "{" not in result

    def test_unread_count_formatted(self, mock_client: MagicMock) -> None:
        mock_client.get_unread_count.return_value = {"count": 3}
        tool = ColonyGetUnreadCount(client=mock_client)
        result = tool._run()
        assert "Unread DMs: 3" in result
