import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple

import tiktoken
from django.conf import settings
from django.utils import timezone
from openai import OpenAI

from .conversation_context import ConversationContextManager, ContextConfiguration, ContextStrategy
from .embeddings import create_query_hash, get_embedding
from .models import ChatMessage, ChatSession, ContentChunk, QueryCache
from .source_models import SourceUnion

logger = logging.getLogger(__name__)

# Initialize OpenAI client
openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)


class RAGService:
    def __init__(self, model: str = settings.OPENAI_CHEAP_CHAT_MODEL):
        self.model = model
        self.default_similarity_threshold = 0.1
        self.max_context_chunks = 8  # Increased to handle more diverse content
        
        # Token management for conversation history
        self.max_total_tokens = self._get_model_context_window() - 1200  # Reserve space for response
        self.max_conversation_tokens = 2000  # Maximum tokens for conversation history
        self.max_context_tokens = 4000  # Maximum tokens for retrieved context
        
        # Initialize conversation context manager
        context_config = ContextConfiguration(
            max_conversation_tokens=self.max_conversation_tokens,
            max_recent_messages=6,  # Keep 6 recent messages (3 exchanges) verbatim
            summarization_threshold=1500,  # Start summarizing when history > 1500 tokens
            summary_target_tokens=400,  # Target 400 tokens for summaries
            strategy=ContextStrategy.HYBRID  # Use intelligent hybrid approach
        )
        self.conversation_manager = ConversationContextManager(
            model=self.model,
            config=context_config
        )
        
        # Initialize tokenizer
        try:
            self.tokenizer = tiktoken.encoding_for_model(self.model)
        except (KeyError, Exception):
            # Fallback to a default encoding if model not found or network issues
            try:
                self.tokenizer = tiktoken.get_encoding("cl100k_base")
            except Exception:
                # Final fallback - set to None and use character-based estimation
                self.tokenizer = None

    def _get_model_context_window(self) -> int:
        """Get the context window size for the current model"""
        if not self.model:
            return 8192  # Conservative default
            
        model_limits = {
            "gpt-4o": 128000,
            "gpt-4o-mini": 128000,
            "gpt-4": 8192,
            "gpt-4-turbo": 128000,
            "gpt-3.5-turbo": 16385,
            "gpt-3.5-turbo-16k": 16385,
        }
        
        # Try to match model name (handle versioned models)
        for model_name, limit in model_limits.items():
            if model_name in self.model:
                return limit
        
        # Default to conservative limit
        return 8192

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

    def _build_conversation_history(self, session: ChatSession, current_message: str) -> List[Dict[str, str]]:
        """
        Build conversation history using the enhanced conversation context manager.
        
        This method now leverages intelligent summarization to maintain better context
        while staying within token limits.
        
        Args:
            session: The chat session
            current_message: The current user message
            
        Returns:
            List of message dicts optimized for the current context window
        """
        return self.conversation_manager.build_conversation_context(session, current_message)

    def semantic_search(
        self,
        query: str,
        limit: int = None,
        similarity_threshold: float = None,
        content_types: List[str] = None,
    ) -> List[Tuple]:
        """
        Find relevant chunks using cosine similarity across different content types

        Args:
            query: Search query
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score
            content_types: List of content types to search (None = search all)

        Returns:
            List of tuples: (chunk_text, metadata, similarity_score, chunk_id, content_type)
        """
        if limit is None:
            limit = self.max_context_chunks
        if similarity_threshold is None:
            similarity_threshold = self.default_similarity_threshold

        try:
            # Get query embedding
            query_embedding = get_embedding(query)

            # Use Django ORM with pgvector
            from pgvector.django import CosineDistance

            queryset = ContentChunk.objects.annotate(
                similarity=1 - CosineDistance("embedding", query_embedding)
            ).filter(similarity__gte=similarity_threshold)

            # Filter by content types if specified
            if content_types:
                queryset = queryset.filter(content_type__in=content_types)

            chunks = queryset.order_by("-similarity")[:limit]

            results = []
            for chunk in chunks:
                results.append(
                    (
                        chunk.chunk_text,
                        chunk.metadata,
                        float(chunk.similarity),
                        chunk.pk,
                        chunk.content_type,
                    )
                )

            logger.info(
                f"Semantic search found {len(results)} relevant chunks for query: {query[:50]}... "
                f"(content_types: {content_types or 'all'})"
            )
            return results

        except Exception as e:
            logger.error(f"Semantic search failed: {str(e)}")
            return []

    def check_query_cache(
        self, query: str, context_params: Dict[str, Any] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Check if we have a cached response for this query
        """
        try:
            query_hash = create_query_hash(query, context_params)

            cache_entry = QueryCache.objects.filter(
                query_hash=query_hash, expires_at__gt=timezone.now()
            ).first()

            if cache_entry:
                # Update hit count
                cache_entry.hit_count += 1
                cache_entry.save(update_fields=["hit_count"])

                logger.info(f"Cache hit for query: {query[:50]}...")
                return cache_entry.response_data

            return None

        except Exception as e:
            logger.error(f"Cache check failed: {str(e)}")
            return None

    def cache_query_response(
        self,
        query: str,
        response_data: Dict[str, Any],
        context_params: Dict[str, Any] = None,
        cache_hours: int = 24,
    ):
        """
        Cache a query response
        """
        try:
            query_hash = create_query_hash(query, context_params)
            expires_at = timezone.now() + timedelta(hours=cache_hours)

            QueryCache.objects.update_or_create(
                query_hash=query_hash,
                defaults={
                    "query_text": query,
                    "response_data": response_data,
                    "tokens_saved": response_data.get("tokens_used", 0),
                    "expires_at": expires_at,
                },
            )

            logger.info(f"Cached response for query: {query[:50]}...")

        except Exception as e:
            logger.error(f"Failed to cache response: {str(e)}")

    def build_context(self, chunks: List[Tuple]) -> Tuple[str, List[SourceUnion]]:
        """
        Build context string and sources list from search results

        Args:
            chunks: List of (chunk_text, metadata, similarity, chunk_id, content_type) tuples

        Returns:
            Tuple of (context_string, sources_list)
        """
        if not chunks:
            return "", []

        context_parts = []
        sources = []

        for chunk_text, metadata, similarity, chunk_id, content_type in chunks:
            # Build context entry based on content type
            context_entry = self._format_context_entry(
                chunk_text, metadata, content_type
            )
            context_parts.append(context_entry)

            # Build source info as Pydantic model
            source = self._build_source_info(
                metadata, similarity, chunk_id, content_type
            )
            sources.append(source)

        context = "\n\n---\n\n".join(context_parts)
        return context, sources

    def _format_context_entry(
        self, chunk_text: str, metadata: Dict, content_type: str
    ) -> str:
        """Format a context entry based on content type"""

        if content_type == "game_log":
            session_info = f"Session {metadata.get('session_number', 'Unknown')}"
            if metadata.get("title"):
                session_info = f"'{metadata['title']}'"
            if metadata.get("session_date"):
                date_str = metadata["session_date"]
                session_info += f" (played {date_str})"
            return f"From {session_info}:\n{chunk_text}"

        elif content_type == "character":
            name = metadata.get("name", "Unknown Character")
            return f"Character - {name}:\n{chunk_text}"

        elif content_type == "place":
            name = metadata.get("name", "Unknown Place")
            return f"Place - {name}:\n{chunk_text}"

        elif content_type == "item":
            name = metadata.get("name", "Unknown Item")
            return f"Item - {name}:\n{chunk_text}"

        elif content_type == "artifact":
            name = metadata.get("name", "Unknown Artifact")
            return f"Artifact - {name}:\n{chunk_text}"

        elif content_type == "race":
            name = metadata.get("name", "Unknown Race")
            return f"Race - {name}:\n{chunk_text}"

        elif content_type == "association":
            name = metadata.get("name", "Unknown Association")
            return f"Association - {name}:\n{chunk_text}"

        elif content_type == "custom":
            title = metadata.get("title", "Custom Content")
            return f"Reference - {title}:\n{chunk_text}"

        else:
            return f"Content ({content_type}):\n{chunk_text}"

    def _build_source_info(
        self, metadata: Dict, similarity: float, chunk_id: str, content_type: str
    ):
        from .source_models import (
            GameLogSource,
            CharacterSource,
            PlaceSource,
            ItemSource,
            ArtifactSource,
            RaceSource,
            AssociationSource,
            CustomSource,
        )

        base = dict(
            type=content_type,
            chunk_id=chunk_id,
            similarity=similarity,
            chunk_index=metadata.get("chunk_index", 0),
        )
        if content_type == "game_log":
            return GameLogSource(
                **base,
                session_number=metadata.get("session_number"),
                title=metadata.get("title", "Unknown Session"),
                url=metadata.get("google_doc_url", ""),
                session_date=metadata.get("session_date"),
                places=metadata.get("places_set_in", []),
                chunk_summary=metadata.get("chunk_summary", ""),
            )
        elif content_type == "character":
            return CharacterSource(
                **base,
                name=metadata.get("name", "Unknown Character"),
                mentioned_in_sessions=metadata.get("mentioned_in_sessions", []),
                race=metadata.get("race"),
            )
        elif content_type == "place":
            return PlaceSource(
                **base,
                name=metadata.get("name", "Unknown Place"),
                mentioned_in_sessions=metadata.get("mentioned_in_sessions", []),
            )
        elif content_type == "item":
            return ItemSource(
                **base,
                name=metadata.get("name", "Unknown Item"),
                mentioned_in_sessions=metadata.get("mentioned_in_sessions", []),
                item_type=metadata.get("item_type"),
            )
        elif content_type == "artifact":
            return ArtifactSource(
                **base,
                name=metadata.get("name", "Unknown Artifact"),
                mentioned_in_sessions=metadata.get("mentioned_in_sessions", []),
            )
        elif content_type == "race":
            return RaceSource(
                **base,
                name=metadata.get("name", "Unknown Race"),
                mentioned_in_sessions=metadata.get("mentioned_in_sessions", []),
            )
        elif content_type == "association":
            return AssociationSource(
                **base,
                name=metadata.get("name", "Unknown Association"),
                mentioned_in_sessions=metadata.get("mentioned_in_sessions", []),
            )
        elif content_type == "custom":
            extra = {
                k: v for k, v in metadata.items() if k not in ["title", "chunk_index"]
            }
            return CustomSource(
                **base,
                title=metadata.get("title", "Custom Content"),
                extra=extra,
            )
        else:
            raise ValueError(f"Unknown content_type: {content_type}")

    def generate_response(
        self,
        query: str,
        session: Optional[ChatSession] = None,
        similarity_threshold: float = None,
        content_types: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Enhanced RAG pipeline with intelligent conversation context management.
        
        Now includes LLM-based summarization for better conversation flow and context preservation.
        
        Args:
            query: User's question
            session: Chat session for conversation history (optional)
            similarity_threshold: Minimum similarity for chunk inclusion
            content_types: List of content types to search
            
        Returns:
            Dict with response, sources, tokens_used, context_stats, etc.
        """
        try:
            # Check cache first
            context_params = {
                "similarity_threshold": similarity_threshold,
                "content_types": content_types,
            }
            # cached_response = self.check_query_cache(query, context_params)
            # if cached_response:
            #     return {**cached_response, "from_cache": True}

            # Perform semantic search
            chunks = self.semantic_search(
                query,
                limit=self.max_context_chunks,
                similarity_threshold=similarity_threshold,
                content_types=content_types,
            )

            if not chunks:
                response_data = {
                    "response": "I couldn't find any relevant information for that question. Could you try rephrasing it or asking about something more specific?",
                    "sources": [],
                    "tokens_used": 0,
                    "similarity_threshold": similarity_threshold
                    or self.default_similarity_threshold,
                    "chunks_found": 0,
                    "content_types_searched": content_types or ["all"],
                    "context_stats": {},
                }
                return response_data

            # Build context for LLM
            context, sources = self.build_context(chunks)

            # Create system prompt with enhanced instructions
            system_prompt = """# D&D Bi-Solar Campaign Assistant
You are a knowledgeable assistant for a D&D homebrew campaign set in a bi-solar system with multiple planets connected by spaceship travel. You have access to embeddings containing game logs, places, characters, items, artifacts, associations, and races from this space fantasy setting.

## Core Rules
1. **Always prioritize campaign-specific information** from your knowledge base over standard D&D lore
2. **Never contradict established campaign facts** - maintain absolute consistency with the homebrew setting
3. **Use hierarchical location context**: Pay attention to place types and their parent locations (planet > region > district > location)
4. **For questions**: Search thoroughly across all planets/locations and provide contextual answers that consider interplanetary relationships
5. **For creative requests**: Blend fantasy and sci-fi elements authentically while respecting established world-building

## Setting-Specific Guidelines
- This is a **space fantasy** setting - magic and technology coexist across multiple worlds
- **Planetary differences** matter - cultures, environments, and magical phenomena may vary by world
- Races may have different distributions, adaptations, or relationships across planets

## Response Guidelines
- Act like a DM deeply familiar with this unique bi-solar campaign
- Blend fantasy terminology with appropriate space/planetary concepts
- When discussing locations, consider which planet/system they're on and how that affects context
- For creative content, ensure new elements fit both the fantasy magic system and space setting
- If you lack campaign-specific information, say so rather than defaulting to standard D&D assumptions

## Handling Future-Oriented Questions
When users ask about predictions, future events, or "what might happen next":
1. Prioritize the most recent game logs and current character/faction states
2. Look for unresolved plot threads, character goals, and brewing conflicts
3. Consider logical consequences of recent player actions
4. Use historical context to inform possibilities, but weight recent developments heavily

## Conversation Continuity
- Reference previous parts of our conversation when relevant
- Build on topics we've discussed earlier in this session
- Maintain consistency with information you've provided before
- If conversation history has been summarized, integrate that context naturally

Your goal: Be the ultimate space fantasy campaign companion that understands the unique dynamics of this multi-world setting."""

            # Build conversation messages including enhanced history
            messages = [{"role": "system", "content": system_prompt}]
            
            # Get context statistics for monitoring
            context_stats = {}
            if session:
                conversation_history = self._build_conversation_history(session, query)
                context_stats = self.conversation_manager.get_context_stats(session, query)
                
                # Remove the current message from history since we'll add it with context
                if conversation_history and conversation_history[-1]["content"] == query:
                    conversation_history = conversation_history[:-1]
                messages.extend(conversation_history)
            
            # Add current message with context
            current_content = f"Context:\n{context}\n\nQuestion: {query}" if context else query
            messages.append({"role": "user", "content": current_content})

            response = openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=1200,  # Increased for more comprehensive responses
            )

            response_text = response.choices[0].message.content
            tokens_used = response.usage.total_tokens

            # Determine what content types were actually found
            content_types_found = list(set(chunk[4] for chunk in chunks))

            response_data = {
                "response": response_text,
                "sources": sources,
                "tokens_used": tokens_used,
                "similarity_threshold": similarity_threshold
                or self.default_similarity_threshold,
                "chunks_found": len(chunks),
                "content_types_searched": content_types or ["all"],
                "content_types_found": content_types_found,
                "context_stats": context_stats,  # Include conversation context statistics
                "from_cache": False,
            }

            # Cache the response
            self.cache_query_response(query, response_data, context_params)

            logger.info(
                f"Generated response for query: {query[:50]}... "
                f"(tokens: {tokens_used}, content_types: {content_types_found}, "
                f"context_strategy: {context_stats.get('strategy_used', 'none')})"
            )
            return response_data

        except Exception as e:
            logger.error(f"Failed to generate response: {str(e)}")
            return {
                "response": f"I encountered an error while processing your question: {str(e)}",
                "sources": [],
                "tokens_used": 0,
                "error": str(e),
                "context_stats": {},
            }

    def create_chat_session(self, user, title: str = None) -> ChatSession:
        """
        Create a new chat session
        """
        return ChatSession.objects.create(user=user, title=title or "")

    def save_chat_message(
        self, session: ChatSession, message: str, response_data: Dict[str, Any]
    ) -> ChatMessage:
        """
        Save a chat exchange to the database
        """
        sources = response_data.get("sources", [])
        sources_dicts = [s.dict() if hasattr(s, "dict") else s for s in sources]
        return ChatMessage.objects.create(
            session=session,
            message=message,
            response=response_data["response"],
            sources=sources_dicts,
            tokens_used=response_data.get("tokens_used", 0),
            similarity_threshold=response_data.get(
                "similarity_threshold", self.default_similarity_threshold
            ),
            content_types_searched=response_data.get("content_types_searched", []),
        )

    def parse_sources_from_db(self, sources: List[dict]) -> List[SourceUnion]:
        from .source_models import parse_source

        return [parse_source(s) for s in sources]

    def get_user_chat_sessions(self, user, limit: int = 10) -> List[ChatSession]:
        """
        Get recent chat sessions for a user
        """
        return ChatSession.objects.filter(user=user).order_by("-updated_at")[:limit]

    def get_content_type_stats(self) -> Dict[str, int]:
        """
        Get statistics about available content by type
        """
        from django.db.models import Count

        stats = {}

        # New content chunks
        chunk_stats = (
            ContentChunk.objects.values("content_type")
            .annotate(count=Count("id"))
            .order_by("content_type")
        )

        for stat in chunk_stats:
            stats[stat["content_type"]] = stat["count"]

        return stats

    def configure_conversation_strategy(
        self, 
        strategy: ContextStrategy = None,
        max_recent_messages: int = None,
        summarization_threshold: int = None,
        summary_target_tokens: int = None
    ):
        """
        Dynamically configure the conversation context strategy.
        
        Args:
            strategy: The context strategy to use (TRUNCATE, SUMMARIZE, HYBRID)
            max_recent_messages: Number of recent messages to keep verbatim
            summarization_threshold: Token threshold for triggering summarization
            summary_target_tokens: Target token count for summaries
        """
        if strategy is not None:
            self.conversation_manager.config.strategy = strategy
        if max_recent_messages is not None:
            self.conversation_manager.config.max_recent_messages = max_recent_messages
        if summarization_threshold is not None:
            self.conversation_manager.config.summarization_threshold = summarization_threshold
        if summary_target_tokens is not None:
            self.conversation_manager.config.summary_target_tokens = summary_target_tokens
            
        logger.info(f"Updated conversation strategy: {self.conversation_manager.config.strategy.value}")

    def get_conversation_stats(self, session: ChatSession, current_message: str = "") -> Dict[str, Any]:
        """
        Get detailed statistics about conversation context management.
        
        Args:
            session: Chat session to analyze
            current_message: Optional current message for context
            
        Returns:
            Detailed statistics about the conversation context
        """
        return self.conversation_manager.get_context_stats(session, current_message)
