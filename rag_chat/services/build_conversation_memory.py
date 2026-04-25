import logging
from typing import List, Tuple

from django.conf import settings
from django.db import transaction
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

from ..models import ChatMessage, ChatSession
from ..utils import count_tokens

logger = logging.getLogger(__name__)

# Initialize OpenAI client
openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)


def _divide_messages(
    messages: List[ChatMessage],
    new_message: str,
    max_tokens_before_summary: int,
    target_tokens_after_summary: int,
) -> Tuple[List[ChatMessage], List[ChatMessage]]:
    """
    Pure. Given messages (most-recent-first) and token limits,
    return (messages_to_include, messages_to_add_to_summary).
    """
    new_message_token_count = count_tokens(new_message)

    # First pass: check if we need to summarize at all
    total_unsummarized_tokens = new_message_token_count
    for msg in messages:
        total_unsummarized_tokens += count_tokens(msg.message) + count_tokens(
            msg.response
        )

    # If we're under the high-water mark, include everything
    if total_unsummarized_tokens <= max_tokens_before_summary:
        return list(messages), []

    # We need to summarize - find the cutoff point for the low-water mark
    messages_to_include = []
    messages_to_add_to_summary = []
    tokens_to_keep = new_message_token_count

    for msg in messages:
        msg_token_count = count_tokens(msg.message) + count_tokens(msg.response)

        # If adding this message would keep us under the target, include it
        if tokens_to_keep + msg_token_count <= target_tokens_after_summary:
            messages_to_include.append(msg)
            tokens_to_keep += msg_token_count
        else:
            # Add this and all remaining older messages to summary
            messages_to_add_to_summary.append(msg)

    return messages_to_include, messages_to_add_to_summary


def _build_summary_prompt(
    existing_summary: str, messages_to_add_to_summary: List[ChatMessage]
) -> str:
    """Pure. Build the prompt text for generating a new conversation summary."""
    new_messages_text = "\n".join(
        f"User: {m.message}\nAssistant: {m.response}"
        for m in messages_to_add_to_summary
    )
    return f"""You are summarizing a chat log for long-term memory. 
Preserve important facts, entities, and context that may be useful later.
Do NOT simply shorten; keep key details.

Existing summary:
{existing_summary}

New content to summarize and merge:
{new_messages_text}"""


def _build_prompt_messages(
    conversation_summary: str, messages_to_include: List[ChatMessage]
) -> List[ChatCompletionMessageParam]:
    """Pure. Build the final list of prompt messages from a summary and recent messages."""
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


def _format_prompt_messages_to_str(messages: List[ChatCompletionMessageParam]) -> str:
    """Pure. Format prompt messages as a single string."""
    return "\n".join(
        f"{msg['role']}: {msg['content']}" for msg in messages if "content" in msg
    )


def _generate_new_summary(prompt: str, model: str) -> str:
    """EFFECT: LLM call. Generate a conversation summary from the given prompt."""
    response = openai_client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You summarize past conversation context.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    return (response.choices[0].message.content or "").strip()


def build_conversation_memory(
    session: ChatSession,
    new_message: str,
    max_tokens_before_summary: int = 1000,  # High-water mark - triggers summarization
    target_tokens_after_summary: int = 500,  # Low-water mark - how much to keep after summary
    model: str = settings.OPENAI_CHEAP_CHAT_MODEL,
) -> str:
    """
    Orchestrates the conversation memory pipeline. All effects are here
    or in clearly-marked effect functions; all other helpers are pure.
    """
    # --- Fetch unsummarized messages ---
    messages_not_in_summary = list(
        session.messages.filter(included_in_summary=False).order_by("-created_at")
    )

    # --- Decide which messages to keep vs. summarize ---
    messages_to_include, messages_to_add_to_summary = _divide_messages(
        messages_not_in_summary,
        new_message,
        max_tokens_before_summary,
        target_tokens_after_summary,
    )

    # --- Update conversation summary if needed ---
    if messages_to_add_to_summary:
        summary_prompt = _build_summary_prompt(
            session.conversation_summary, messages_to_add_to_summary
        )
        new_summary = _generate_new_summary(summary_prompt, model)
        with transaction.atomic():
            session.conversation_summary = new_summary
            session.save()
            ChatMessage.objects.filter(
                id__in=[m.pk for m in messages_to_add_to_summary]
            ).update(included_in_summary=True)

    # --- Build final conversation memory prompt string ---
    prompt_messages = _build_prompt_messages(
        session.conversation_summary, messages_to_include
    )
    prompt_str = _format_prompt_messages_to_str(prompt_messages)
    return prompt_str
