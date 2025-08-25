import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Dict, Iterable, List, Optional

from django.conf import settings
from django.db.models import QuerySet
from django.utils import timezone
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

from association.models import Association
from character.models import Character
from item.models import Artifact, Item
from nucleus.models import GameLog
from place.models import Place
from race.models import Race
from rag_chat.services.normalize_and_hybrid_rank_fuse import (
    ScoreSetElement,
    hybrid_rank_fuse,
    remove_results_more_than_stddev_below_mean,
    z_score_normalize,
)

from ..content_processors import get_processor
from ..embeddings import create_query_hash, get_embedding
from ..models import ChatMessage, ChatSession, ContentChunk, QueryCache
from ..source_models import (
    ArtifactSource,
    AssociationSource,
    CharacterSource,
    GameLogSource,
    ItemSource,
    PlaceSource,
    RaceSource,
    SourceUnion,
)
from ..utils import count_tokens
from .game_log_full_text_search import game_log_fts
from .trigram_entity_search import find_entities_by_trigram_similarity

logger = logging.getLogger(__name__)

# Initialize OpenAI client
openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)


@dataclass
class SemanticSearchResult:
    """Result from semantic search with proper typing"""

    chunk_text: str
    metadata: Dict[str, Any]
    similarity: float
    chunk_id: int
    content_type: str
    content_object: Association | Character | Place | Item | Artifact | Race | GameLog


class RAGService:
    def __init__(self, model: str = settings.OPENAI_CHEAP_CHAT_MODEL):
        self.model = model
        self.default_similarity_threshold = 0.1
        self.max_context_chunks = 8  # Increased to handle more diverse content
        self.token_limit: int = (
            120_000  # The model token limit with some room for system + user query + response
        )

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
            recent_context_text = (
                summary_resp.choices[0].message.content or ""
            ).strip()

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
        limit: Optional[int] = None,
        similarity_threshold: Optional[float] = None,
        content_types: Optional[List[str]] = None,
    ) -> List[SemanticSearchResult]:
        """
        Find relevant chunks using cosine similarity across different content types

        Args:
            query: Search query
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score
            content_types: List of content types to search (None = search all)

        Returns:
            List of SemanticSearchResult objects
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
                    SemanticSearchResult(
                        chunk_text=chunk.chunk_text,
                        metadata=chunk.metadata,
                        similarity=float(chunk.similarity),
                        chunk_id=chunk.pk,
                        content_type=chunk.content_type,
                        content_object=chunk.content_object,
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
        self, query: str, context_params: Optional[Dict[str, Any]] = None
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
        context_params: Optional[Dict[str, Any]] = None,
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

        else:
            return f"Content ({content_type}):\n{chunk_text}"

    def _build_source_info(
        self, metadata: Dict, similarity: float, chunk_id: int, content_type: str
    ):
        from ..source_models import (
            ArtifactSource,
            AssociationSource,
            CharacterSource,
            GameLogSource,
            ItemSource,
            PlaceSource,
            RaceSource,
        )

        if content_type == "game_log":
            return GameLogSource(
                type=content_type,
                chunk_id=chunk_id,
                similarity=similarity,
                chunk_index=metadata.get("chunk_index", 0),
                session_number=metadata.get("session_number"),
                title=metadata.get("title", "Unknown Session"),
                url=metadata.get("google_doc_url", ""),
                session_date=metadata.get("session_date"),
                places=metadata.get("places_set_in", []),
            )
        elif content_type == "character":
            return CharacterSource(
                type=content_type,
                chunk_id=chunk_id,
                similarity=similarity,
                chunk_index=metadata.get("chunk_index", 0),
                name=metadata.get("name", "Unknown Character"),
                mentioned_in_sessions=metadata.get("mentioned_in_sessions", []),
                race=metadata.get("race"),
            )
        elif content_type == "place":
            return PlaceSource(
                type=content_type,
                chunk_id=chunk_id,
                similarity=similarity,
                chunk_index=metadata.get("chunk_index", 0),
                name=metadata.get("name", "Unknown Place"),
                mentioned_in_sessions=metadata.get("mentioned_in_sessions", []),
            )
        elif content_type == "item":
            return ItemSource(
                type=content_type,
                chunk_id=chunk_id,
                similarity=similarity,
                chunk_index=metadata.get("chunk_index", 0),
                name=metadata.get("name", "Unknown Item"),
                mentioned_in_sessions=metadata.get("mentioned_in_sessions", []),
                item_type=metadata.get("item_type"),
            )
        elif content_type == "artifact":
            return ArtifactSource(
                type=content_type,
                chunk_id=chunk_id,
                similarity=similarity,
                chunk_index=metadata.get("chunk_index", 0),
                name=metadata.get("name", "Unknown Artifact"),
                mentioned_in_sessions=metadata.get("mentioned_in_sessions", []),
            )
        elif content_type == "race":
            return RaceSource(
                type=content_type,
                chunk_id=chunk_id,
                similarity=similarity,
                chunk_index=metadata.get("chunk_index", 0),
                name=metadata.get("name", "Unknown Race"),
                mentioned_in_sessions=metadata.get("mentioned_in_sessions", []),
            )
        elif content_type == "association":
            return AssociationSource(
                type=content_type,
                chunk_id=chunk_id,
                similarity=similarity,
                chunk_index=metadata.get("chunk_index", 0),
                name=metadata.get("name", "Unknown Association"),
                mentioned_in_sessions=metadata.get("mentioned_in_sessions", []),
            )
        else:
            raise ValueError(f"Unknown content_type: {content_type}")

    def generate_response(
        self,
        query: str,
        similarity_threshold: Optional[float] = None,
        content_types: Optional[List[str]] = None,
        session: Optional[ChatSession] = None,
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
        from .ConversationMemoryService import ConversationMemoryService

        try:
            ######### GET CONVERSATION HISTORY #########
            conversation_messages = (
                list(
                    ConversationMemoryService(
                        session, model=self.model
                    ).get_prompt_messages_str(query)
                )
                if session
                else []
            )

            query_with_history = (
                "\n".join(conversation_messages) + f"\n\nQuestion: {query}"
            )

            ######### GET ENTITIES FOR QUERY ENHANCEMENT #########

            trigram_results_for_query_enhancement = find_entities_by_trigram_similarity(
                query_with_history
            )
            trigram_entities_for_query_enhancement = [
                res.entity for res in trigram_results_for_query_enhancement
            ]
            semantic_search_results_for_query_enhancement = self.semantic_search(
                query_with_history,
                limit=self.max_context_chunks,
                similarity_threshold=similarity_threshold,
                content_types=[ct for ct in (content_types or []) if ct != "game_log"],
            )
            entity_ids_in_query_enhancement = set()
            entities_for_query = []
            for entity in trigram_entities_for_query_enhancement:
                if entity.pk not in entity_ids_in_query_enhancement:
                    entities_for_query.append(entity)
                    entity_ids_in_query_enhancement.add(entity.pk)
            for result in semantic_search_results_for_query_enhancement:
                if result.content_object.pk not in entity_ids_in_query_enhancement:
                    entities_for_query.append(result.content_object)
                    entity_ids_in_query_enhancement.add(result.content_object.pk)
            entities_formatted_for_query_enhancement = (
                "\n".join(
                    f"- **{e['name']}** ({e.__class__.__name__})\n  Aliases: {', '.join(e.get('aliases', [])) or 'none'})\n  {e['description']}"
                    for e in entities_for_query
                )
                or "No entities retrieved."
            )

            ######### ENHANCE QUERY #########
            system_prompt_for_query_enhancement = """You are a helpful assistant that rewrites user queries into enriched,
contextually clear forms suitable for retrieving information from narrative logs
and entity databases. 

- Always resolve vague references by grounding them in entity names and aliases.
- Incorporate relevant details from the conversation history and summary.
- Do not hallucinate: only use information provided.
- Output only the rewritten enriched query, nothing else."""
            user_prompt_for_query_enhancement = f"""
Conversation History:
{"\n".join(conversation_messages) if conversation_messages else "No prior conversation."}

Entities Retrieved:
{entities_formatted_for_query_enhancement}

Original User Query:
{query}

Task:
Rewrite the original query so that it is explicit, unambiguous, and makes
use of relevant entities, aliases, or prior context. Output only the enriched query.
"""
            enhancement_response = openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt_for_query_enhancement},
                    {"role": "user", "content": user_prompt_for_query_enhancement},
                ],
                temperature=0.0,
            )
            enhanced_search_query = (
                enhancement_response.choices[0].message.content or query
            ).strip()

            logger.info(f"Enhanced search query: {enhanced_search_query[:100]}...")

            ######### RETRIEVE LOGS AND ENTITIES USING ENHANCED QUERY #########

            trigram_results = find_entities_by_trigram_similarity(enhanced_search_query)
            entities_from_trigram = [res.entity for res in trigram_results]

            fts_results = game_log_fts(enhanced_search_query, limit=10)

            chunks = self.semantic_search(
                enhanced_search_query,
                limit=self.max_context_chunks,
                similarity_threshold=similarity_threshold,
                content_types=content_types,
            )

            if not chunks and not entities_from_trigram and not fts_results:
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

            semantic_log_chunks = [
                chunk for chunk in chunks if chunk.content_type == "game_log"
            ]
            semantic_entity_chunks = [
                chunk for chunk in chunks if chunk.content_type != "game_log"
            ]

            semantic_log_scores = [
                ScoreSetElement(chunk.content_object, chunk.similarity)
                for chunk in semantic_log_chunks
            ]
            semantic_entity_scores = [
                ScoreSetElement(chunk.content_object, chunk.similarity)
                for chunk in semantic_entity_chunks
            ]
            fts_scores = [
                ScoreSetElement(r, (len(fts_results) - idx) / len(fts_results) * 1.0)
                for idx, r in enumerate(fts_results)
            ]
            trigram_scores = [
                ScoreSetElement(r.entity, r.similarity) for r in trigram_results
            ]

            semantic_log_scores_normalized = z_score_normalize(semantic_log_scores)
            semantic_entity_scores_normalized = z_score_normalize(
                semantic_entity_scores
            )
            fts_scores_normalized = z_score_normalize(fts_scores)
            trigram_scores_normalized = z_score_normalize(trigram_scores)

            SEMANTIC_WEIGHT = 0.6
            FTS_WEIGHT = 0.3
            TRIGRAM_WEIGHT = 0.1

            all_fused_log_results = hybrid_rank_fuse(
                (semantic_log_scores_normalized, SEMANTIC_WEIGHT),
                (fts_scores_normalized, FTS_WEIGHT),
            )
            all_fused_entity_results = hybrid_rank_fuse(
                (semantic_entity_scores_normalized, SEMANTIC_WEIGHT),
                (trigram_scores_normalized, TRIGRAM_WEIGHT),
            )

            fused_log_results = remove_results_more_than_stddev_below_mean(
                all_fused_log_results
            )
            fused_entity_results = remove_results_more_than_stddev_below_mean(
                all_fused_entity_results
            )

            # Type assertions since we know the specific types from how we constructed the scores
            logs_to_include_candidates: list[GameLog] = [r.data for r in fused_log_results]  # type: ignore
            entities_to_include: list[Association | Character | Place | Item | Artifact | Race] = [r.data for r in fused_entity_results]  # type: ignore

            ######### BUILD CONTEXT FROM THE RESULTS #########

            # --- Entities formatted ---
            entity_text = (
                "\n".join(
                    f"- **{e.name}** ({e.__class__.__name__}; aliases: {', '.join(a.name for a in e.aliases.all()) or 'none'})\n  {e.description}"
                    for e in entities_to_include
                )
                or "No entities retrieved."
            )

            # --- Log summaries (all logs) ---
            summaries_text = "\n".join(
                f"Log {log.session_number} — {log.title}:\n{log.summary}"
                for log in GameLog.objects.all()
            )

            # --- Base sections ---
            sections = {
                "Conversation History": (
                    "\n".join(conversation_messages)
                    if conversation_messages
                    else "No prior conversation."
                ),
                "Retrieved Entities": entity_text,
                "Narrative Summaries of All Logs": summaries_text,
            }

            # --- Count base token usage ---
            assembled = ""
            for title, content in sections.items():
                assembled += f"=== {title} ===\n{content}\n\n"

            # --- Add full logs within budget ---
            logs_to_include = []
            tokens_added = count_tokens(assembled, model=self.model)
            for log in logs_to_include_candidates:
                candidate = f"Log {log.session_number} (Full) — {log.title}:\n{log.full_text}\n\n"
                cand_tokens = count_tokens(candidate, model=self.model)
                if tokens_added + cand_tokens > self.token_limit:
                    break
                logs_to_include.append(log)
                tokens_added += cand_tokens

            if logs_to_include:
                logs_text = "\n\n".join(
                    f"Log {log.session_number} (Full) — {log.title})\n{log.full_text}"
                    for log in sorted(logs_to_include, key=lambda l: l.session_number)
                )
                assembled += f"=== Full Logs (Retrieved Subset) ===\n{logs_text}\n\n"

            # # Build context for LLM
            # semantic_search_context = []
            # semantic_search_sources = []
            # if chunks:
            #     for chunk in chunks:
            #         # Build context entry based on content type
            #         context_entry = self._format_context_entry(
            #             chunk.chunk_text, chunk.metadata, chunk.content_type
            #         )
            #         semantic_search_context.append(context_entry)

            #         # Build source info as Pydantic model
            #         source = self._build_source_info(
            #             chunk.metadata,
            #             chunk.similarity,
            #             chunk.chunk_id,
            #             chunk.content_type,
            #         )
            #         semantic_search_sources.append(source)

            # # Construct the context and the sources list
            # # - Determine what objects to use
            # # - Do the source objects make sense for the new retrievals?
            # # - Do we use content_processors for the text we'll include?
            # trigram_context_parts = []
            # for trigram_result in trigram_results:
            #     entity = trigram_result.entity
            #     source = None

            #     processor = get_processor(
            #         entity.__class__.__name__.lower()
            #     )  # doesn't work for game_log but does for entities
            #     text = processor.extract_text(entity)

            #     context_part = f"{entity.__class__.__name__} - {entity.name}:\n{text}"
            #     trigram_context_parts.append(context_part)

            # fts_sources: list[GameLogSource] = []
            # fts_context_parts = []
            # for i, log in enumerate(fts_results):
            #     fts_sources.append(
            #         GameLogSource(
            #             # similarity=fts_result.similarity, # PROBABLY WANT TO ADD RANK (i) HERE, OR WE ADD A COMBINED SCORE
            #             session_number=log.session_number,
            #             title=log.title,
            #             url=log.url,
            #             session_date=log.game_date,
            #             places=log.places_set_in,
            #         )
            #     )
            #     processor = get_processor("game_log")
            #     text = processor.extract_text(log)
            #     context_part = (
            #         f"Game Log - {log.title} (Session {log.session_number}):\n{text}"
            #     )
            #     fts_context_parts.append(context_part)

            # semantic_scores = [
            #     ScoreSetElement(r.content_object, r.similarity) for r in chunks
            # ]
            # fts_scores = [
            #     ScoreSetElement(r, (len(fts_results) - idx) / len(fts_results) * 1.0)
            #     for idx, r in enumerate(fts_results)
            # ]
            # trigram_scores = [
            #     ScoreSetElement(r.entity, r.similarity) for r in trigram_results
            # ]

            # semantic_scores_normalized = z_score_normalize(semantic_scores)
            # fts_scores_normalized = z_score_normalize(fts_scores)
            # trigram_scores_normalized = z_score_normalize(trigram_scores)

            # SEMANTIC_WEIGHT = 0.6
            # FTS_WEIGHT = 0.3
            # TRIGRAM_WEIGHT = 0.1

            # fused_results = hybrid_rank_fuse(
            #     (semantic_scores_normalized, SEMANTIC_WEIGHT),
            #     (fts_scores_normalized, FTS_WEIGHT),
            #     (trigram_scores_normalized, TRIGRAM_WEIGHT),
            # )

            # # Sort by combined score, maybe separating by content type. We need the entity/log and not just the global_id and score.

            # context = "\n\n---\n\n".join(
            #     [*fts_context_parts, *trigram_context_parts, *semantic_search_context]
            # )

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

            messages: Iterable[ChatCompletionMessageParam] = [
                {"role": "system", "content": system_prompt},
                {"role": "assistant", "content": assembled},
                {"role": "user", "content": query},
            ]

            response = openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_completion_tokens=2000,
            )

            response_text = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else None

            # Determine what content types were actually found
            content_types_found = list(set(chunk.content_type for chunk in chunks))

            response_data = {
                "response": response_text,
                "sources": semantic_search_sources,
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
            # if not session:
            #     self.cache_query_response(query, response_data, context_params)

            logger.info(
                f"Generated response for query: {query[:50]}... "
                f"(query: {query[:50]}..., tokens: {tokens_used}, content_types: {content_types_found})"
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

    def create_chat_session(self, user, title: Optional[str] = None) -> ChatSession:
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
        from ..source_models import parse_source

        return [parse_source(s) for s in sources]

    def get_user_chat_sessions(
        self, user, limit: int = 10
    ) -> QuerySet[ChatSession, ChatSession]:
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
