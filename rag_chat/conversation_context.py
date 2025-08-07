"""
Conversation context management with intelligent summarization for RAG chat system.

This module provides sophisticated conversation history management that balances
context preservation with token efficiency through intelligent LLM-based summarization.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

import tiktoken
from django.conf import settings
from openai import OpenAI

from .models import ChatMessage, ChatSession

logger = logging.getLogger(__name__)


class ContextStrategy(Enum):
    """Strategy for handling conversation context when approaching token limits"""
    TRUNCATE = "truncate"  # Simple truncation (current behavior)
    SUMMARIZE = "summarize"  # LLM-based summarization
    HYBRID = "hybrid"  # Combination of summarization and truncation


@dataclass
class ConversationSegment:
    """Represents a segment of conversation history"""
    messages: List[Dict[str, str]]
    token_count: int
    is_summarized: bool = False
    summary_text: Optional[str] = None


@dataclass
class ContextConfiguration:
    """Configuration for conversation context management"""
    max_conversation_tokens: int = 2000
    max_recent_messages: int = 6  # Keep this many recent messages verbatim
    summarization_threshold: int = 1500  # Start summarizing when history exceeds this
    summary_target_tokens: int = 400  # Target token count for summaries
    strategy: ContextStrategy = ContextStrategy.HYBRID
    

class ConversationContextManager:
    """
    Manages conversation context with intelligent summarization capabilities.
    
    This class handles the complex logic of deciding when and how to summarize
    conversation history to maintain context while staying within token limits.
    """
    
    def __init__(self, model: str = settings.OPENAI_CHEAP_CHAT_MODEL, config: Optional[ContextConfiguration] = None):
        self.model = model
        self.config = config or ContextConfiguration()
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Initialize tokenizer
        try:
            self.tokenizer = tiktoken.encoding_for_model(self.model)
        except (KeyError, Exception):
            try:
                self.tokenizer = tiktoken.get_encoding("cl100k_base")
            except Exception:
                self.tokenizer = None
                
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text using the model's tokenizer"""
        if not text:
            return 0
            
        try:
            if self.tokenizer:
                return len(self.tokenizer.encode(text))
        except Exception:
            pass
            
        # Fallback: rough estimate (4 chars per token average)
        return max(1, len(text) // 4)
    
    def build_conversation_context(self, session: ChatSession, current_message: str) -> List[Dict[str, str]]:
        """
        Build optimized conversation context with intelligent summarization.
        
        Args:
            session: The chat session
            current_message: The current user message
            
        Returns:
            List of message dicts optimized for the current context window
        """
        # Get all previous messages
        previous_messages = list(
            session.messages.order_by('created_at').values('message', 'response')
        )
        
        if not previous_messages:
            # No history, just return current message
            return [{"role": "user", "content": current_message}]
        
        # Convert to conversation format
        conversation = []
        for msg in previous_messages:
            conversation.append({"role": "user", "content": msg['message']})
            conversation.append({"role": "assistant", "content": msg['response']})
        
        # Add current message
        conversation.append({"role": "user", "content": current_message})
        
        # Calculate total tokens
        total_tokens = sum(self._count_tokens(msg["content"]) for msg in conversation)
        
        # Decide on strategy based on configuration and current state
        if total_tokens <= self.config.max_conversation_tokens:
            # No need for optimization
            return conversation
        
        if self.config.strategy == ContextStrategy.TRUNCATE:
            return self._truncate_conversation(conversation)
        elif self.config.strategy == ContextStrategy.SUMMARIZE:
            return self._summarize_conversation(conversation, session)
        else:  # HYBRID
            return self._hybrid_conversation(conversation, session)
    
    def _truncate_conversation(self, conversation: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Simple truncation strategy (existing logic)"""
        if not conversation:
            return conversation
        
        current_message = conversation[-1]
        history = conversation[:-1]
        
        current_tokens = self._count_tokens(current_message["content"])
        remaining_tokens = self.config.max_conversation_tokens - current_tokens
        
        if remaining_tokens <= 0:
            return [current_message]
        
        truncated_history = []
        used_tokens = 0
        
        for message in reversed(history):
            message_tokens = self._count_tokens(message["content"])
            
            if used_tokens + message_tokens <= remaining_tokens:
                truncated_history.insert(0, message)
                used_tokens += message_tokens
            else:
                break
        
        return truncated_history + [current_message]
    
    def _summarize_conversation(self, conversation: List[Dict[str, str]], session: ChatSession) -> List[Dict[str, str]]:
        """
        Full summarization strategy - summarize old history and keep recent messages.
        """
        current_message = conversation[-1]
        history = conversation[:-1]
        
        if len(history) <= self.config.max_recent_messages:
            # Not enough history to warrant summarization
            return self._truncate_conversation(conversation)
        
        # Split into recent (keep verbatim) and older (summarize) sections
        recent_messages = history[-self.config.max_recent_messages:]
        older_messages = history[:-self.config.max_recent_messages]
        
        # Summarize the older messages
        summary = self._create_conversation_summary(older_messages, session)
        
        # Build final conversation with summary + recent + current
        result = []
        
        if summary:
            result.append({"role": "system", "content": f"Previous conversation summary: {summary}"})
        
        result.extend(recent_messages)
        result.append(current_message)
        
        # Check if we're still within limits, truncate recent if needed
        total_tokens = sum(self._count_tokens(msg["content"]) for msg in result)
        if total_tokens > self.config.max_conversation_tokens:
            # Need to truncate recent messages too
            return self._truncate_conversation(recent_messages + [current_message])
        
        return result
    
    def _hybrid_conversation(self, conversation: List[Dict[str, str]], session: ChatSession) -> List[Dict[str, str]]:
        """
        Hybrid strategy - use summarization when beneficial, truncation otherwise.
        """
        current_message = conversation[-1]
        history = conversation[:-1]
        
        # Calculate tokens in history
        history_tokens = sum(self._count_tokens(msg["content"]) for msg in history)
        
        # If history is under summarization threshold, just truncate
        if history_tokens < self.config.summarization_threshold:
            return self._truncate_conversation(conversation)
        
        # If we have enough messages and tokens to make summarization worthwhile
        if len(history) >= self.config.max_recent_messages * 2:
            return self._summarize_conversation(conversation, session)
        
        # Fall back to truncation for edge cases
        return self._truncate_conversation(conversation)
    
    def _create_conversation_summary(self, messages: List[Dict[str, str]], session: ChatSession) -> Optional[str]:
        """
        Create a concise summary of conversation messages using LLM.
        
        Args:
            messages: List of conversation messages to summarize
            session: Chat session for context
            
        Returns:
            Summary text or None if summarization fails
        """
        if not messages:
            return None
        
        try:
            # Build the conversation text to summarize
            conversation_text = "\n\n".join([
                f"{msg['role'].title()}: {msg['content']}" for msg in messages
            ])
            
            # Create summarization prompt
            system_prompt = """You are summarizing a D&D campaign conversation for context preservation. Create a concise summary that captures:

1. **Key Topics Discussed**: Main subjects, questions asked, and information sought
2. **Campaign Elements**: Characters mentioned, locations discussed, events referenced
3. **Player Decisions**: Important choices made or considered
4. **Narrative Context**: Story elements, quest progress, relationships
5. **Unresolved Questions**: Ongoing topics that may be referenced later

Keep the summary concise but informative. Focus on elements that would be useful for maintaining conversational context in future messages. Use present tense and be specific about campaign details.

Example format:
"The conversation covered the party's exploration of Shadowhaven, discussing the mysterious disappearance of Captain Thorne and the strange magical disturbances in the harbor district. Players asked about the Crimson Company's involvement and learned about ancient protective wards. The group is planning to investigate the old lighthouse and is considering whether to trust the halfling merchant Pip with their information about the stolen artifact."

Summarize the following conversation:"""

            user_prompt = f"Conversation to summarize:\n\n{conversation_text}"
            
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=min(self.config.summary_target_tokens, 600)  # Cap at reasonable limit
            )
            
            summary = response.choices[0].message.content.strip()
            
            # Validate summary isn't too long
            summary_tokens = self._count_tokens(summary)
            if summary_tokens > self.config.summary_target_tokens * 1.5:
                # Summary is too long, truncate it
                if self.tokenizer:
                    tokens = self.tokenizer.encode(summary)
                    truncated_tokens = tokens[:self.config.summary_target_tokens]
                    summary = self.tokenizer.decode(truncated_tokens)
                else:
                    # Character-based truncation as fallback
                    target_chars = self.config.summary_target_tokens * 4
                    summary = summary[:target_chars] + "..."
            
            logger.info(f"Created conversation summary: {len(messages)} messages -> {summary_tokens} tokens")
            return summary
            
        except Exception as e:
            logger.error(f"Failed to create conversation summary: {str(e)}")
            return None
    
    def get_context_stats(self, session: ChatSession, current_message: str) -> Dict[str, Any]:
        """
        Get statistics about the conversation context for debugging/monitoring.
        
        Returns:
            Dictionary with context statistics
        """
        conversation = self.build_conversation_context(session, current_message)
        
        total_tokens = sum(self._count_tokens(msg["content"]) for msg in conversation)
        message_count = len(conversation)
        
        # Check if any system messages (summaries) are present
        summary_count = sum(1 for msg in conversation if msg["role"] == "system")
        
        return {
            "total_messages": message_count,
            "total_tokens": total_tokens,
            "summary_count": summary_count,
            "strategy_used": self.config.strategy.value,
            "within_limits": total_tokens <= self.config.max_conversation_tokens,
            "conversation_length": len(list(session.messages.all())),
        }