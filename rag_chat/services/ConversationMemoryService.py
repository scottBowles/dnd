import logging
from typing import Iterable, List, Tuple

from django.conf import settings
from django.db import transaction
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

from ..models import ChatMessage, ChatSession
from ..utils import count_tokens

logger = logging.getLogger(__name__)

# Initialize OpenAI client
openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)


class ConversationMemoryService:
    """
    Service to manage conversation memory within token limits
    """

    def __init__(
        self,
        session: ChatSession,
        max_tokens_before_summary: int = 1000,  # High-water mark - triggers summarization
        target_tokens_after_summary: int = 500,  # Low-water mark - how much to keep after summary
        model: str = settings.OPENAI_CHEAP_CHAT_MODEL,
    ):
        self.session = session
        self.max_tokens_before_summary = max_tokens_before_summary
        self.target_tokens_after_summary = target_tokens_after_summary
        self.model = model

    def _divide_messages_for_conversation_memory(
        self: "ConversationMemoryService", new_message: str
    ) -> Tuple[List[ChatMessage], List[ChatMessage]]:
        """
        Based on the max_tokens limit, determine which previous messages to include in full
        and which to add to the session summary. Uses high/low watermark approach to reduce
        summarization frequency.
        """
        # Get all messages in the session not already included in the summary, most recent first
        messages = self.session.messages.filter(included_in_summary=False).order_by(
            "-created_at"
        )

        new_message_token_count = count_tokens(new_message)

        # First pass: check if we need to summarize at all
        total_unsummarized_tokens = new_message_token_count
        for msg in messages:
            total_unsummarized_tokens += count_tokens(msg.message) + count_tokens(
                msg.response
            )

        # If we're under the high-water mark, include everything
        if total_unsummarized_tokens <= self.max_tokens_before_summary:
            return list(messages), []

        # We need to summarize - find the cutoff point for the low-water mark
        messages_to_include = []
        messages_to_add_to_summary = []
        tokens_to_keep = new_message_token_count

        for msg in messages:
            msg_token_count = count_tokens(msg.message) + count_tokens(msg.response)

            # If adding this message would keep us under the target, include it
            if tokens_to_keep + msg_token_count <= self.target_tokens_after_summary:
                messages_to_include.append(msg)
                tokens_to_keep += msg_token_count
            else:
                # Add this and all remaining older messages to summary
                messages_to_add_to_summary.append(msg)

        return messages_to_include, messages_to_add_to_summary

    def _get_new_conversation_summary(
        self: "ConversationMemoryService",
        existing_summary: str,
        messages_to_add_to_summary: List[ChatMessage],
    ):
        """
        Generate a new summary for the conversation based on messages not yet included in the summary
        """
        new_messages_text = "\n".join(
            f"User: {m.message}\nAssistant: {m.response}"
            for m in messages_to_add_to_summary
        )
        summary_prompt = f"""
You are summarizing a chat log for long-term memory. 
Preserve important facts, entities, and context that may be useful later.
Do NOT simply shorten; keep key details.

Existing summary:
{existing_summary}

New content to summarize and merge:
{new_messages_text}
"""
        summary_response = openai_client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You summarize past conversation context.",
                },
                {"role": "user", "content": summary_prompt},
            ],
            temperature=0.2,
        )

        new_summary = summary_response.choices[0].message.content.strip()

        return new_summary

    def _add_messages_to_summary(self, messages: List[ChatMessage]) -> str:
        """
        Add specified messages to the conversation summary
        """
        if not messages:
            return self.session.conversation_summary

        logger.info(
            f"Adding {len(messages)} messages to conversation summary for session {self.session.id}."
        )
        new_summary = self._get_new_conversation_summary(
            self.session.conversation_summary, messages
        )
        with transaction.atomic():
            self.session.conversation_summary = new_summary
            self.session.save()
            ChatMessage.objects.filter(id__in=[m.id for m in messages]).update(
                included_in_summary=True
            )
            logger.info(
                f"Updated conversation summary for session {self.session.id}. "
                f"Included {len(messages)} messages in summary."
            )

        return new_summary

    def get_prompt_messages(
        self, new_message: str
    ) -> Iterable[ChatCompletionMessageParam]:
        """
        Get the list of messages to include in the prompt for the LLM for conversation context.
        """
        messages_to_include, messages_to_add_to_summary = (
            self._divide_messages_for_conversation_memory(new_message)
        )

        if messages_to_add_to_summary:
            self._add_messages_to_summary(messages_to_add_to_summary)

        conversation_summary = self.session.conversation_summary

        prompt_messages: list[ChatCompletionMessageParam] = []

        if conversation_summary:
            prompt_messages.append(
                {
                    "role": "system",
                    "content": f"Summary of earlier conversation: {conversation_summary}",
                }
            )

        for msg in reversed(messages_to_include):
            prompt_messages.append({"role": "user", "content": msg.message})
            prompt_messages.append({"role": "assistant", "content": msg.response})

        return prompt_messages

    def get_prompt_messages_str(self, new_message: str) -> str:
        """
        Get the list of messages to include in the prompt for the LLM for conversation context as a string.
        """
        messages = self.get_prompt_messages(new_message)
        return "\n".join(
            f"{msg['role']}: {msg['content']}" for msg in messages if "content" in msg
        )
