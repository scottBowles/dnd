import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple, Iterable

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

from .embeddings import create_query_hash, get_embedding
from .models import ChatMessage, ChatSession, ContentChunk, QueryCache
from .source_models import SourceUnion
from .utils import count_tokens

logger = logging.getLogger(__name__)

# Initialize OpenAI client
openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)


class RAGService:
    def __init__(self, model: str = settings.OPENAI_CHEAP_CHAT_MODEL):
        self.model = model
        self.default_similarity_threshold = 0.1
        self.max_context_chunks = 8  # Increased to handle more diverse content

    def build_recent_chat_context(
        self, session: ChatSession, latest_user_message: str
    ) -> str:
        # Adjustable limits
        RECENT_CONTEXT_TOKEN_LIMIT = (
            300  # how much recent chat to include before the new message
        )
        """
        Build minimal, focused search context for semantic search
        from recent conversation history plus the latest message.

        1. Pulls messages in reverse order until hitting token limit
        2. Optionally condenses multi-turn context via LLM if long
        3. Appends the latest user message at the end
        """
        # Step 1 — Get recent messages (excluding the current one, which isn't saved yet)
        recent_msgs = session.messages.order_by("-created_at")
        token_count = 0
        collected = []

        for msg in recent_msgs:
            # Combine user + assistant for context
            turn_text = f"User: {msg.message}\nAssistant: {msg.response}"
            turn_tokens = count_tokens(turn_text)

            if token_count + turn_tokens > RECENT_CONTEXT_TOKEN_LIMIT:
                break
            collected.append(turn_text)
            token_count += turn_tokens

        # Reverse to get chronological order
        collected.reverse()

        recent_context_text = "\n".join(collected).strip()

        # Step 2 — Condense if needed (optional, keeps embeddings small & focused)
        if token_count > (RECENT_CONTEXT_TOKEN_LIMIT * 0.7):
            summary_prompt = f"""
            Summarize the following recent conversation so it keeps only the facts,
            entities, and constraints needed to understand the user's next question.
            Avoid irrelevant details and small talk.

            Conversation:
            {recent_context_text}
            """
            summary_resp = openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You summarize conversation history for search queries.",
                    },
                    {"role": "user", "content": summary_prompt},
                ],
                temperature=0.0,
            )
            recent_context_text = summary_resp.choices[0].message.content.strip()

        # Step 3 — Append latest user message
        search_query_text = (
            f"{recent_context_text}\n\nUser: {latest_user_message}"
            if recent_context_text
            else latest_user_message
        )

        return search_query_text

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
            ArtifactSource,
            AssociationSource,
            CharacterSource,
            CustomSource,
            GameLogSource,
            ItemSource,
            PlaceSource,
            RaceSource,
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
        similarity_threshold: float = None,
        content_types: List[str] = None,
        session: ChatSession = None,
    ) -> Dict[str, Any]:
        """
        Main RAG pipeline: search, build context, generate response

        Args:
            query: User's question
            similarity_threshold: Minimum similarity for chunk inclusion
            content_types: List of content types to search
            session: Optional chat session for building contextual search queries and conversation memory

        Returns:
            Dict with response, sources, tokens_used, etc.
        """
        try:
            # Build enhanced search query with recent chat context if session provided
            search_query = query
            if session:
                search_query = self.build_recent_chat_context(session, query)
                logger.info(
                    f"Enhanced search query with chat context: {search_query[:100]}..."
                )

            # Check cache first (note: we don't cache responses with conversation context)
            context_params = {
                "similarity_threshold": similarity_threshold,
                "content_types": content_types,
                "has_session_context": session is not None,
            }
            cached_response = None
            if not session:  # Only use cache for non-conversational queries
                cached_response = self.check_query_cache(search_query, context_params)
                if cached_response:
                    return {**cached_response, "from_cache": True}

            # Perform semantic search
            chunks = self.semantic_search(
                search_query,
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
                    "used_session_context": session is not None,
                }
                return response_data

            # Build context for LLM
            context, sources = self.build_context(chunks)

            # Create system prompt with enhanced instructions
            #             _system_prompt = """You are a knowledgeable D&D campaign assistant with access to detailed information from an ongoing campaign including session logs, characters, places, items, artifacts, races, associations, and other campaign elements.

            # Your role is to help players and the DM recall information, understand relationships, remember important details, and connect story elements across different aspects of the campaign.

            # Guidelines:
            # - Answer questions using the provided context from various sources
            # - When referencing game sessions, mention specific session titles/numbers and dates when available
            # - When discussing characters, places, items, etc., use their proper names and reference where they appeared
            # - Be conversational and engaging, like a helpful fellow player who has perfect recall
            # - If information spans multiple sources, weave them together naturally to tell a complete story
            # - If you can't find relevant information, say so clearly but suggest related topics that might help
            # - For entity questions (characters, places, items, artifacts, races, associations), focus on what actually happened or was described in the campaign
            # - Maintain the narrative tone of the campaign
            # - Always distinguish between different types of sources (session logs vs character descriptions vs place details, etc.)
            # - Do not make up information or editorialize.

            # The context below contains information from relevant campaign sources:"""

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

Your goal: Be the ultimate space fantasy campaign companion that understands the unique dynamics of this multi-world setting."""

            # Generate response with conversation memory if session provided
            if session:
                # Use ConversationMemoryService to get conversation history
                memory_service = ConversationMemoryService(session, model=self.model)
                conversation_messages = list(memory_service.get_prompt_messages(query))

                # Build messages with system prompt, conversation history, and current context
                messages = [
                    {"role": "system", "content": system_prompt},
                    *conversation_messages,
                    {
                        "role": "user",
                        "content": f"Context:\n{context}\n\nQuestion: {query}",
                    },
                ]
            else:
                # No session - just use system prompt and current query
                messages = [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"Context:\n{context}\n\nQuestion: {query}",
                    },
                ]

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
                "from_cache": False,
                "used_session_context": session is not None,
            }

            # Cache the response (only for non-conversational queries)
            if not session:
                self.cache_query_response(search_query, response_data, context_params)

            logger.info(
                f"Generated response for query: {query[:50]}... "
                f"(search_query: {search_query[:50]}..., tokens: {tokens_used}, content_types: {content_types_found})"
            )
            return response_data

        except Exception as e:
            logger.error(f"Failed to generate response: {str(e)}")
            return {
                "response": f"I encountered an error while processing your question: {str(e)}",
                "sources": [],
                "tokens_used": 0,
                "error": str(e),
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


class ConversationMemoryService:
    """
    Service to manage conversation memory within token limits
    """

    def __init__(
        self,
        session: ChatSession,
        max_tokens_before_summary: int = 1500,
        model: str = settings.OPENAI_CHEAP_CHAT_MODEL,
    ):
        self.session = session
        self.max_tokens_before_summary = max_tokens_before_summary
        self.model = model

    def _divide_messages_for_conversation_memory(
        self: "ConversationMemoryService", new_message: str
    ) -> Tuple[List[ChatMessage], List[ChatMessage]]:
        """
        Based on the max_tokens limit, determine which previous messages to include in full
        and which to add to the session summary.
        """
        # Get all messages in the session not already included in the summary, most recent first
        messages = self.session.messages.filter(included_in_summary=False).order_by(
            "-created_at"
        )

        new_message_token_count = count_tokens(new_message)

        messages_to_include = []
        messages_to_add_to_summary = []
        total_tokens = new_message_token_count
        for msg in messages:
            # If we're already over the limit, add remaining messages to summary -- no need to count tokens
            if total_tokens >= self.max_tokens_before_summary:
                messages_to_add_to_summary.append(msg)
            else:
                # If the message would not exceed the token limit, include it in the context in full
                msg_token_count = count_tokens(msg.message) + count_tokens(msg.response)
                if total_tokens + msg_token_count <= self.max_tokens_before_summary:
                    messages_to_include.append(msg)
                # If it would exceed, add it to the summary list
                else:
                    messages_to_add_to_summary.append(msg)
                total_tokens += msg_token_count

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
