from openai import OpenAI
from django.conf import settings
from typing import List, Dict, Any, Tuple
from .models import GameLogChunk, ChatSession, ChatMessage, QueryCache
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
        self.max_context_chunks = 5

    def semantic_search(
        self, query: str, limit: int = None, similarity_threshold: float = None
    ) -> List[Tuple]:
        """
        Find relevant chunks using cosine similarity

        Returns:
            List of tuples: (chunk_text, metadata, similarity_score, chunk_id)
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

            chunks = (
                GameLogChunk.objects.select_related("game_log")
                .annotate(similarity=1 - CosineDistance("embedding", query_embedding))
                .filter(similarity__gte=similarity_threshold)
                .order_by("-similarity")[:limit]
            )

            results = []
            for chunk in chunks:
                results.append(
                    (
                        chunk.chunk_text,
                        chunk.metadata,
                        float(chunk.similarity),
                        chunk.id,
                    )
                )

            logger.info(
                f"Semantic search found {len(results)} relevant chunks for query: {query[:50]}..."
            )
            return results

        except Exception as e:
            logger.error(f"Semantic search failed: {str(e)}")
            return []

    def check_query_cache(
        self, query: str, context_params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
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

        Returns:
            Tuple of (context_string, sources_list)
        """
        if not chunks:
            return "", []

        context_parts = []
        sources = []

        for chunk_text, metadata, similarity, chunk_id in chunks:
            # Build context entry
            session_info = f"Session {metadata.get('session_number', 'Unknown')}"
            if metadata.get("session_title"):
                session_info = f"'{metadata['session_title']}'"

            if metadata.get("session_date"):
                date_str = metadata["session_date"][:10]  # Just the date part
                session_info += f" (played {date_str})"

            context_entry = f"From {session_info}:\n{chunk_text}"
            context_parts.append(context_entry)

            # Build source info
            source = {
                "type": "session",
                "chunk_id": chunk_id,
                "session_number": metadata.get("session_number"),
                "title": metadata.get("session_title", "Unknown Session"),
                "url": metadata.get("google_doc_url", ""),
                "similarity": similarity,
                "session_date": metadata.get("session_date"),
                "places": metadata.get("places_mentioned", []),
                "chunk_summary": metadata.get("chunk_summary", ""),
            }
            sources.append(source)

        context = "\n\n---\n\n".join(context_parts)
        return context, sources

    def generate_response(
        self, query: str, similarity_threshold: float = None
    ) -> Dict[str, Any]:
        """
        Main RAG pipeline: search, build context, generate response

        Args:
            query: User's question
            similarity_threshold: Minimum similarity for chunk inclusion

        Returns:
            Dict with response, sources, tokens_used, etc.
        """
        try:
            # Check cache first
            context_params = {"similarity_threshold": similarity_threshold}
            cached_response = self.check_query_cache(query, context_params)
            if cached_response:
                return {**cached_response, "from_cache": True}

            # Perform semantic search
            chunks = self.semantic_search(
                query,
                limit=self.max_context_chunks,
                similarity_threshold=similarity_threshold,
            )

            if not chunks:
                response_data = {
                    "response": "I couldn't find any relevant information in the game logs for that question. Could you try rephrasing it or asking about something more specific?",
                    "sources": [],
                    "tokens_used": 0,
                    "similarity_threshold": similarity_threshold
                    or self.default_similarity_threshold,
                    "chunks_found": 0,
                }
                return response_data

            # Build context for LLM
            context, sources = self.build_context(chunks)

            # Create system prompt
            system_prompt = """You are a knowledgeable D&D campaign assistant with access to detailed session logs from an ongoing campaign. 

Your role is to help players and the DM recall what happened in past sessions, understand character relationships, remember important plot points, and connect story elements.

Guidelines:
- Answer questions using the provided session context
- Always mention specific session titles/numbers when referencing events
- Be conversational and engaging, like a helpful fellow player
- If information from multiple sessions is relevant, weave them together naturally
- If you can't find relevant information, say so clearly
- For character or location questions, focus on what actually happened in the sessions
- Maintain the narrative tone and excitement of the campaign

The context below contains excerpts from relevant game sessions:"""

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
                max_tokens=1000,
            )

            response_text = response.choices[0].message.content
            tokens_used = response.usage.total_tokens

            response_data = {
                "response": response_text,
                "sources": sources,
                "tokens_used": tokens_used,
                "similarity_threshold": similarity_threshold
                or self.default_similarity_threshold,
                "chunks_found": len(chunks),
                "from_cache": False,
            }

            # Cache the response
            self.cache_query_response(query, response_data, context_params)

            logger.info(
                f"Generated response for query: {query[:50]}... (tokens: {tokens_used})"
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
        )

    def get_user_chat_sessions(self, user, limit: int = 10) -> List[ChatSession]:
        """
        Get recent chat sessions for a user
        """
        return ChatSession.objects.filter(user=user).order_by("-updated_at")[:limit]
