# rag_chat/services.py
from openai import OpenAI
from django.conf import settings
from typing import List, Dict, Any, Tuple, Optional
from .models import ContentChunk, ChatSession, ChatMessage, QueryCache

# from .models import ContentChunk, ChatSession, ChatMessage, QueryCache, GameLogChunk
from .embeddings import get_embedding, create_query_hash
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

# Initialize OpenAI client
openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)


class RAGService:
    def __init__(self, model: str = settings.OPENAI_CHEAP_CHAT_MODEL):
        self.model = model
        self.default_similarity_threshold = 0.1
        self.max_context_chunks = 8  # Increased to handle more diverse content

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

    # def semantic_search_legacy(
    #     self, query: str, limit: int = None, similarity_threshold: float = None
    # ) -> List[Tuple]:
    #     """
    #     Search legacy GameLogChunk model for backward compatibility during migration
    #     """
    #     if limit is None:
    #         limit = self.max_context_chunks
    #     if similarity_threshold is None:
    #         similarity_threshold = self.default_similarity_threshold

    #     try:
    #         query_embedding = get_embedding(query)
    #         from pgvector.django import CosineDistance

    #         chunks = (
    #             GameLogChunk.objects.select_related("game_log")
    #             .annotate(similarity=1 - CosineDistance("embedding", query_embedding))
    #             .filter(similarity__gte=similarity_threshold)
    #             .order_by("-similarity")[:limit]
    #         )

    #         results = []
    #         for chunk in chunks:
    #             # Convert legacy format to new format
    #             results.append(
    #                 (
    #                     chunk.chunk_text,
    #                     chunk.metadata,
    #                     float(chunk.similarity),
    #                     f"legacy_{chunk.id}",
    #                     "game_log",
    #                 )
    #             )

    #         return results

    #     except Exception as e:
    #         logger.error(f"Legacy semantic search failed: {str(e)}")
    #         return []

    # def combined_search(
    #     self,
    #     query: str,
    #     limit: int = None,
    #     similarity_threshold: float = None,
    #     content_types: List[str] = None,
    #     include_legacy: bool = True,
    # ) -> List[Tuple]:
    #     """
    #     Search both new ContentChunk and legacy GameLogChunk models
    #     """
    #     results = []

    #     # Search new content chunks
    #     new_results = self.semantic_search(
    #         query, limit, similarity_threshold, content_types
    #     )
    #     results.extend(new_results)

    #     # Search legacy chunks if requested and game_log is in content_types (or no filter)
    #     if include_legacy and (not content_types or "game_log" in content_types):
    #         remaining_limit = (limit or self.max_context_chunks) - len(results)
    #         if remaining_limit > 0:
    #             legacy_results = self.semantic_search_legacy(
    #                 query, remaining_limit, similarity_threshold
    #             )
    #             results.extend(legacy_results)

    #     # Sort combined results by similarity and trim to limit
    #     results.sort(key=lambda x: x[2], reverse=True)  # Sort by similarity score
    #     if limit:
    #         results = results[:limit]

    #     return results

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

    def build_context(self, chunks: List[Tuple]) -> Tuple[str, List[Dict]]:
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

            # Build source info
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

        elif content_type == "custom":
            title = metadata.get("title", "Custom Content")
            return f"Reference - {title}:\n{chunk_text}"

        else:
            return f"Content ({content_type}):\n{chunk_text}"

    def _build_source_info(
        self, metadata: Dict, similarity: float, chunk_id: str, content_type: str
    ) -> Dict:
        """Build source information based on content type"""

        base_source = {
            "type": content_type,
            "chunk_id": chunk_id,
            "similarity": similarity,
            "chunk_index": metadata.get("chunk_index", 0),
        }

        if content_type == "game_log":
            base_source.update(
                {
                    "session_number": metadata.get("session_number"),
                    "title": metadata.get("title", "Unknown Session"),
                    "url": metadata.get("google_doc_url", ""),
                    "session_date": metadata.get("session_date"),
                    "places": metadata.get("places_mentioned", []),
                    "chunk_summary": metadata.get("chunk_summary", ""),
                }
            )

        elif content_type in ["character", "place", "item", "artifact", "race"]:
            base_source.update(
                {
                    "name": metadata.get("name", f"Unknown {content_type.title()}"),
                    "mentioned_in_sessions": metadata.get("mentioned_in_sessions", []),
                    "featured_in_sessions": metadata.get("featured_in_sessions", []),
                }
            )

            # Add type-specific fields
            if content_type == "character" and "race" in metadata:
                base_source["race"] = metadata["race"]
            elif content_type == "item" and "item_type" in metadata:
                base_source["item_type"] = metadata["item_type"]

        elif content_type == "custom":
            base_source.update(
                {
                    "title": metadata.get("title", "Custom Content"),
                    **{
                        k: v
                        for k, v in metadata.items()
                        if k not in ["title", "chunk_index"]
                    },
                }
            )

        return base_source

    def generate_response(
        self,
        query: str,
        similarity_threshold: float = None,
        content_types: List[str] = None,
        # include_legacy: bool = True,
    ) -> Dict[str, Any]:
        """
        Main RAG pipeline: search, build context, generate response

        Args:
            query: User's question
            similarity_threshold: Minimum similarity for chunk inclusion
            content_types: List of content types to search
            # include_legacy: Whether to include legacy GameLogChunk results

        Returns:
            Dict with response, sources, tokens_used, etc.
        """
        try:
            # Check cache first
            context_params = {
                "similarity_threshold": similarity_threshold,
                "content_types": content_types,
                # "include_legacy": include_legacy,
            }
            cached_response = self.check_query_cache(query, context_params)
            if cached_response:
                return {**cached_response, "from_cache": True}

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
                }
                return response_data

            # Build context for LLM
            context, sources = self.build_context(chunks)

            # Create system prompt with enhanced instructions
            system_prompt = """You are a knowledgeable D&D campaign assistant with access to detailed information from an ongoing campaign including session logs, characters, places, items, artifacts, races, associations, and other campaign elements.

Your role is to help players and the DM recall information, understand relationships, remember important details, and connect story elements across different aspects of the campaign.

Guidelines:
- Answer questions using the provided context from various sources
- When referencing game sessions, mention specific session titles/numbers and dates when available
- When discussing characters, places, items, etc., use their proper names and reference where they appeared
- Be conversational and engaging, like a helpful fellow player who has perfect recall
- If information spans multiple sources, weave them together naturally to tell a complete story
- If you can't find relevant information, say so clearly but suggest related topics that might help
- For entity questions (characters, places, items, artifacts, races, associations), focus on what actually happened or was described in the campaign
- Maintain the narrative tone of the campaign
- Always distinguish between different types of sources (session logs vs character descriptions vs place details, etc.)
- Do not make up information or editorialize.

The context below contains information from relevant campaign sources:"""

            # Generate response
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
            }

            # Cache the response
            self.cache_query_response(query, response_data, context_params)

            logger.info(
                f"Generated response for query: {query[:50]}... "
                f"(tokens: {tokens_used}, content_types: {content_types_found})"
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
        return ChatMessage.objects.create(
            session=session,
            message=message,
            response=response_data["response"],
            sources=response_data.get("sources", []),
            tokens_used=response_data.get("tokens_used", 0),
            similarity_threshold=response_data.get(
                "similarity_threshold", self.default_similarity_threshold
            ),
            content_types_searched=response_data.get("content_types_searched", []),
        )

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

        # # Legacy game log chunks
        # legacy_count = GameLogChunk.objects.count()
        # if legacy_count > 0:
        #     stats["game_log_legacy"] = legacy_count

        return stats
