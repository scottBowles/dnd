from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import ChatMessage, ChatSession
from ..services.build_conversation_memory import (
    _build_prompt_messages,
    _build_summary_prompt,
    _divide_messages,
    _format_prompt_messages_to_str,
    build_conversation_memory,
)


# ---------------------------------------------------------------------------
# Pure function tests — no DB, no mocks needed
# ---------------------------------------------------------------------------


class DivideMessagesTests(TestCase):
    """Tests for _divide_messages (pure)."""

    def _make_msg(self, id, message, response):
        msg = MagicMock()
        msg.id = id
        msg.message = message
        msg.response = response
        return msg

    def _make_msgs(self, texts):
        """Helper: create mock message list from (message, response) pairs."""
        return [self._make_msg(i, m, r) for i, (m, r) in enumerate(texts)]

    def test_all_included_when_under_high_water_mark(self):
        msgs = self._make_msgs([("hi", "hello"), ("how are you", "fine")])
        include, summarize = _divide_messages(
            msgs,
            "new msg",
            max_tokens_before_summary=10000,
            target_tokens_after_summary=5000,
        )
        self.assertEqual(include, msgs)
        self.assertEqual(summarize, [])

    def test_messages_split_when_over_high_water_mark(self):
        # Create enough messages to exceed a small high-water mark
        msgs = self._make_msgs([(f"message {i}", f"response {i}") for i in range(20)])
        include, summarize = _divide_messages(
            msgs, "new msg", max_tokens_before_summary=10, target_tokens_after_summary=5
        )
        # Something should be summarized
        self.assertGreater(len(summarize), 0)
        # Everything is accounted for
        self.assertEqual(len(include) + len(summarize), len(msgs))

    def test_empty_messages(self):
        include, summarize = _divide_messages(
            [], "new msg", max_tokens_before_summary=100, target_tokens_after_summary=50
        )
        self.assertEqual(include, [])
        self.assertEqual(summarize, [])

    def test_all_summarized_when_target_very_low(self):
        msgs = self._make_msgs([("hello world", "hi there")])
        include, summarize = _divide_messages(
            msgs, "new msg", max_tokens_before_summary=1, target_tokens_after_summary=0
        )
        # With target=0 and any messages, they all get summarized
        self.assertEqual(len(summarize), 1)
        self.assertEqual(len(include), 0)


class BuildSummaryPromptTests(TestCase):
    """Tests for _build_summary_prompt (pure)."""

    def _make_msg(self, id, message, response):
        msg = MagicMock()
        msg.id = id
        msg.message = message
        msg.response = response
        return msg

    def test_includes_existing_summary(self):
        prompt = _build_summary_prompt(
            "Previous context about dragons.",
            [self._make_msg(1, "Tell me about elves", "Elves are...")],
        )
        self.assertIn("Previous context about dragons.", prompt)

    def test_includes_messages(self):
        prompt = _build_summary_prompt(
            "",
            [
                self._make_msg(1, "Q1", "A1"),
                self._make_msg(2, "Q2", "A2"),
            ],
        )
        self.assertIn("User: Q1", prompt)
        self.assertIn("Assistant: A1", prompt)
        self.assertIn("User: Q2", prompt)
        self.assertIn("Assistant: A2", prompt)

    def test_empty_summary_and_messages(self):
        prompt = _build_summary_prompt("", [])
        # Should still produce the template text
        self.assertIn("Existing summary:", prompt)


class BuildPromptMessagesTests(TestCase):
    """Tests for _build_prompt_messages (pure)."""

    def _make_msg(self, id, message, response):
        msg = MagicMock()
        msg.id = id
        msg.message = message
        msg.response = response
        return msg

    def test_with_summary_and_messages(self):
        msgs = [
            self._make_msg(1, "oldest", "resp1"),
            self._make_msg(2, "newest", "resp2"),
        ]
        result = _build_prompt_messages("A summary", msgs)
        # First message is the summary
        self.assertEqual(result[0]["role"], "system")
        self.assertIn("A summary", result[0]["content"])
        # Messages are reversed (oldest first = chronological)
        self.assertEqual(result[1]["content"], "newest")
        self.assertEqual(result[2]["content"], "resp2")
        self.assertEqual(result[3]["content"], "oldest")
        self.assertEqual(result[4]["content"], "resp1")

    def test_without_summary(self):
        msgs = [self._make_msg(1, "hi", "hello")]
        result = _build_prompt_messages("", msgs)
        # No system message
        self.assertEqual(result[0]["role"], "user")
        self.assertEqual(len(result), 2)

    def test_empty(self):
        result = _build_prompt_messages("", [])
        self.assertEqual(result, [])


class FormatPromptMessagesTests(TestCase):
    """Tests for _format_prompt_messages (pure)."""

    def test_formats_messages(self):
        messages = [
            {"role": "system", "content": "Summary of earlier conversation: ctx"},
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
        result = _format_prompt_messages_to_str(messages)
        self.assertEqual(
            result,
            "system: Summary of earlier conversation: ctx\nuser: hi\nassistant: hello",
        )

    def test_empty(self):
        self.assertEqual(_format_prompt_messages_to_str([]), "")


# ---------------------------------------------------------------------------
# Integration / orchestrator tests — need DB + mocked LLM
# ---------------------------------------------------------------------------


class GetPromptMessagesStrTests(TestCase):
    """Tests for get_prompt_messages_str (orchestrator)."""

    def setUp(self):
        self.user = get_user_model().objects.create(username="testuser")
        self.session = ChatSession.objects.create(
            user=self.user, title="Test Session", conversation_summary=""
        )

    def test_no_messages_returns_empty(self):
        result = build_conversation_memory(self.session, "hello")
        self.assertEqual(result, "")

    def test_includes_recent_messages_under_limit(self):
        ChatMessage.objects.create(
            session=self.session, message="first question", response="first answer"
        )
        ChatMessage.objects.create(
            session=self.session, message="second question", response="second answer"
        )
        result = build_conversation_memory(
            self.session, "new question", max_tokens_before_summary=10000
        )
        self.assertIn("user: first question", result)
        self.assertIn("assistant: first answer", result)
        self.assertIn("user: second question", result)
        self.assertIn("assistant: second answer", result)

    def test_messages_in_chronological_order(self):
        ChatMessage.objects.create(session=self.session, message="first", response="r1")
        ChatMessage.objects.create(
            session=self.session, message="second", response="r2"
        )
        result = build_conversation_memory(
            self.session, "new", max_tokens_before_summary=10000
        )
        first_pos = result.index("user: first")
        second_pos = result.index("user: second")
        self.assertLess(first_pos, second_pos)

    def test_existing_summary_included(self):
        self.session.conversation_summary = "Previously discussed dragons."
        self.session.save()
        result = build_conversation_memory(
            self.session, "new question", max_tokens_before_summary=10000
        )
        self.assertIn("Previously discussed dragons.", result)

    @patch("rag_chat.services.build_conversation_memory.openai_client")
    def test_summarization_triggered_when_over_limit(self, mock_openai):
        # Set up mock LLM response
        mock_choice = MagicMock()
        mock_choice.message.content = "Summary of the conversation so far."
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_openai.chat.completions.create.return_value = mock_response

        # Create enough messages to exceed a very small limit
        for i in range(10):
            ChatMessage.objects.create(
                session=self.session,
                message=f"question {i} with some extra words to use tokens",
                response=f"answer {i} with some extra words to use tokens",
            )

        result = build_conversation_memory(
            self.session,
            "new question",
            max_tokens_before_summary=20,
            target_tokens_after_summary=5,
        )

        # LLM was called to generate summary
        mock_openai.chat.completions.create.assert_called_once()

        # Summary was persisted to the session
        self.session.refresh_from_db()
        self.assertEqual(
            self.session.conversation_summary,
            "Summary of the conversation so far.",
        )

        # Some messages were marked as included in summary
        summarized_count = ChatMessage.objects.filter(
            session=self.session, included_in_summary=True
        ).count()
        self.assertGreater(summarized_count, 0)

        # Result includes the new summary
        self.assertIn("Summary of the conversation so far.", result)

    @patch("rag_chat.services.build_conversation_memory.openai_client")
    def test_no_llm_call_when_under_limit(self, mock_openai):
        ChatMessage.objects.create(session=self.session, message="hi", response="hello")
        build_conversation_memory(self.session, "new", max_tokens_before_summary=10000)
        mock_openai.chat.completions.create.assert_not_called()

    def test_already_summarized_messages_excluded(self):
        ChatMessage.objects.create(
            session=self.session,
            message="old question",
            response="old answer",
            included_in_summary=True,
        )
        ChatMessage.objects.create(
            session=self.session, message="new question", response="new answer"
        )
        result = build_conversation_memory(
            self.session, "latest", max_tokens_before_summary=10000
        )
        self.assertNotIn("old question", result)
        self.assertIn("new question", result)
