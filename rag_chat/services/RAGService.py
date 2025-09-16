import concurrent.futures
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.db.models import QuerySet
from openai import OpenAI

from association.models import Association
from character.models import Character
from item.models import Artifact, Item
from nucleus.models import GameLog, Entity, Alias
from nucleus.utils import dedupe_model_instances
from place.models import Place
from race.models import Race
from rag_chat.services.normalize_and_hybrid_rank_fuse import (
    ScoreSetElement,
    hybrid_rank_fuse,
    remove_results_more_than_stddev_below_mean,
    z_score_normalize,
)

from ..content_processors import get_processor
from ..embeddings import get_embedding
from ..models import ChatMessage, ChatSession, ContentChunk
from ..source_models import create_sources, parse_sources
from ..utils import count_tokens
from .game_log_full_text_search import weighted_fts_search_logs
from .trigram_entity_search import trigram_entity_search
from .game_log_full_text_search import key_terms

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
            from django.contrib.contenttypes.models import ContentType
            from pgvector.django import CosineDistance

            queryset = ContentChunk.objects.annotate(
                similarity=1 - CosineDistance("embedding", query_embedding)
            ).filter(similarity__gte=similarity_threshold)

            # Filter by content types if specified
            if content_types:
                # Convert string content types to ContentType instances
                content_type_objects = []
                for content_type_str in content_types:
                    if content_type_str == "gamelog":
                        content_type_obj = ContentType.objects.get(
                            app_label="nucleus", model="gamelog"
                        )
                    elif content_type_str == "character":
                        content_type_obj = ContentType.objects.get(
                            app_label="character", model="character"
                        )
                    elif content_type_str == "place":
                        content_type_obj = ContentType.objects.get(
                            app_label="place", model="place"
                        )
                    elif content_type_str == "item":
                        content_type_obj = ContentType.objects.get(
                            app_label="item", model="item"
                        )
                    elif content_type_str == "artifact":
                        content_type_obj = ContentType.objects.get(
                            app_label="item", model="artifact"
                        )
                    elif content_type_str == "race":
                        content_type_obj = ContentType.objects.get(
                            app_label="race", model="race"
                        )
                    elif content_type_str == "association":
                        content_type_obj = ContentType.objects.get(
                            app_label="association", model="association"
                        )
                    else:
                        continue
                    content_type_objects.append(content_type_obj)

                if content_type_objects:
                    queryset = queryset.filter(content_type__in=content_type_objects)

            chunks = queryset.order_by("-similarity")[:limit]

            results = []
            for chunk in chunks:
                # Get the string representation of content type for backwards compatibility
                content_type_str = (
                    chunk.content_type.model if chunk.content_type else "unknown"
                )

                # The similarity is added by the annotation, so we access it directly
                similarity_score = getattr(chunk, "similarity", 0.0)

                # Ensure content_object exists before adding to results
                if chunk.content_object:
                    results.append(
                        SemanticSearchResult(
                            chunk_text=chunk.chunk_text,
                            metadata=chunk.metadata,
                            similarity=float(similarity_score),
                            chunk_id=chunk.pk,
                            content_type=content_type_str,
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

    def build_enriched_text_for_semantic_search(
        self,
        raw_query: str,
        entities: list[Entity],
        alias_cap=2,
        keyterm_cap=5,
        max_chars=512,
    ):
        lines = [raw_query.strip(), "Entities:"]
        for e in entities:
            # Work with local copies to avoid modifying the original lists
            current_aliases = list(e.aliases.all()[:alias_cap])
            current_terms = key_terms(e.description)[:keyterm_cap]

            # Build the initial entity line
            def build_entity_line(
                aliases_list: list[Alias], terms_list: list[str]
            ) -> str:
                alias_str = (
                    ("aka: " + ", ".join(str(a) for a in aliases_list) + "; ")
                    if aliases_list
                    else ""
                )
                separator = "; " if aliases_list and terms_list else ""
                terms_str = (
                    ("about: " + ", ".join(terms_list) + "; ") if terms_list else ""
                )
                return f"- {e.name} ({alias_str}{separator}{terms_str})"

            entity_line = build_entity_line(current_aliases, current_terms)
            lines.append(entity_line)

            current_text = "\n".join(lines)
            if len(current_text) > max_chars:
                # Back off: trim terms first, then aliases, then drop this entity entirely

                # Step 1: Trim terms one by one
                while current_terms and len("\n".join(lines)) > max_chars:
                    current_terms = current_terms[:-1]
                    lines[-1] = build_entity_line(current_aliases, current_terms)

                # Step 2: Trim aliases one by one if still too long
                while current_aliases and len("\n".join(lines)) > max_chars:
                    current_aliases = current_aliases[:-1]
                    lines[-1] = build_entity_line(current_aliases, current_terms)

                # Step 3: If still too long, drop this entity entirely
                if len("\n".join(lines)) > max_chars:
                    lines.pop()  # Remove this entity block
                    break  # Stop processing more entities

        return "\n".join(lines)[:max_chars]

    def _get_enhanced_query(
        self,
        query: str,
        conversation_messages: str,
        session: ChatSession | None,
        similarity_threshold: float | None,
    ) -> str:
        ######### GET ENTITIES FOR QUERY ENHANCEMENT #########
        query_with_history = conversation_messages + f"\n\nQuestion: {query}"

        trigram_results_for_query_enhancement = trigram_entity_search(query)
        trigram_entities_for_query_enhancement = [
            res.entity for res in trigram_results_for_query_enhancement
        ]
        print("got trigram entities for query enhancement")
        semantic_search_results_for_query_enhancement = self.semantic_search(
            query_with_history,
            limit=self.max_context_chunks,
            similarity_threshold=similarity_threshold,
            content_types=[
                "character",
                "place",
                "item",
                "artifact",
                "race",
                "association",
            ],
        )
        entities_from_semantic_search = [
            result.content_object
            for result in semantic_search_results_for_query_enhancement
            if not isinstance(result.content_object, GameLog)
        ]
        print("got entities from semantic search for query enhancement")
        entities_from_past_messages = [
            source
            for message in session.messages.all()
            for source in parse_sources(message.sources).sources
            if not isinstance(source, GameLog)
        ]
        print("got entities from past messages for query enhancement")

        entities_for_query = dedupe_model_instances(
            [
                *trigram_entities_for_query_enhancement,
                *entities_from_semantic_search,
                *entities_from_past_messages,
            ]
        )

        entities_formatted_for_query_enhancement = (
            "\n".join(
                [
                    f"- **{e.name}** ({e.__class__.__name__})\n  Aliases: {', '.join({alias.name for alias in e.aliases.all()}) or 'none'})\n  {e.description}"
                    for e in entities_for_query
                ]
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
{conversation_messages if conversation_messages else "No prior conversation."}

Entities Retrieved:
{entities_formatted_for_query_enhancement}

Original User Query:
{query}

Task:
Rewrite the original query so that it is explicit, unambiguous, and makes
use of relevant entities, aliases, or prior context. Output only the enriched query.
"""
        # Use a cheaper, faster model for query enhancement since it's a simpler rewriting task
        enhancement_model = settings.OPENAI_CHEAP_CHAT_MODEL
        enhancement_response = openai_client.chat.completions.create(
            model=enhancement_model,
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
        print(f"Enhanced search query: {enhanced_search_query}")

        return enhanced_search_query

    def _get_logs_and_entities_for_query(
        self,
        query: str,
        similarity_threshold: Optional[float] = None,
        max_logs_to_include: int = 10,
        max_entities_to_include: int = 15,
    ) -> tuple[
        List[GameLog], List[Association | Character | Place | Item | Artifact | Race]
    ]:
        SEMANTIC_WEIGHT = 0.6
        FTS_WEIGHT = 0.3
        TRIGRAM_WEIGHT = 0.1

        # Run the entity search operations in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            # Submit both entity searches simultaneously
            trigram_future = executor.submit(trigram_entity_search, query)

            semantic_entity_future = executor.submit(
                self.semantic_search,
                query,
                self.max_context_chunks,
                similarity_threshold,
                ["character", "place", "item", "artifact", "race", "association"],
            )

            # Wait for results
            trigram_results = trigram_future.result()
            semantic_entity_chunks = semantic_entity_future.result()

        print("got trigram and semantic entity results")

        semantic_entity_scores = [
            ScoreSetElement(chunk.content_object, chunk.similarity)
            for chunk in semantic_entity_chunks
        ]
        trigram_scores = [
            ScoreSetElement(r.entity, r.similarity) for r in trigram_results
        ]

        semantic_entity_scores_normalized = z_score_normalize(semantic_entity_scores)
        trigram_scores_normalized = z_score_normalize(trigram_scores)

        all_fused_entity_results = hybrid_rank_fuse(
            (semantic_entity_scores_normalized, SEMANTIC_WEIGHT),
            (trigram_scores_normalized, TRIGRAM_WEIGHT),
        )
        fused_entity_results = remove_results_more_than_stddev_below_mean(
            all_fused_entity_results
        )

        # Now run log searches in parallel
        entities_for_log_search: list[Entity] = [
            r.data for r in fused_entity_results if not isinstance(r.data, GameLog)
        ]

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as log_executor:
            fts_future = log_executor.submit(
                weighted_fts_search_logs, query, entities_for_log_search
            )

            enhanced_query_for_log_search = (
                self.build_enriched_text_for_semantic_search(
                    query,
                    entities_for_log_search,
                )
            )
            semantic_log_future = log_executor.submit(
                self.semantic_search,
                enhanced_query_for_log_search,
                self.max_context_chunks,
                similarity_threshold,
                ["gamelog"],
            )

            # Get log search results
            fts_results = fts_future.result()
            semantic_log_chunks = semantic_log_future.result()

        print("got fts and semantic log results")

        if not semantic_log_chunks and not fused_entity_results and not fts_results:
            return [], []

        semantic_log_scores = [
            ScoreSetElement(chunk.content_object, chunk.similarity)
            for chunk in semantic_log_chunks
        ]
        fts_scores = (
            [
                ScoreSetElement(r, (len(fts_results) - idx) / len(fts_results) * 1.0)
                for idx, r in enumerate(fts_results)
            ]
            if fts_results.count() > 0
            else []
        )

        semantic_log_scores_normalized = z_score_normalize(semantic_log_scores)
        fts_scores_normalized = z_score_normalize(fts_scores)

        all_fused_log_results = hybrid_rank_fuse(
            (semantic_log_scores_normalized, SEMANTIC_WEIGHT),
            (fts_scores_normalized, FTS_WEIGHT),
        )

        fused_log_results = remove_results_more_than_stddev_below_mean(
            all_fused_log_results
        )

        # Type assertions since we know the specific types from how we constructed the scores
        logs_to_include_candidates: list[GameLog] = [r.data for r in fused_log_results]  # type: ignore
        entities_to_include: list[Association | Character | Place | Item | Artifact | Race] = [r.data for r in fused_entity_results]  # type: ignore

        return (
            logs_to_include_candidates[:max_logs_to_include],
            entities_to_include[:max_entities_to_include],
        )

    def _assemble_context(
        self,
        conversation_messages: str,
        entities_to_include: List[
            Association | Character | Place | Item | Artifact | Race
        ],
        logs_to_include_candidates: List[GameLog],
    ) -> tuple[str, List[GameLog]]:

        # --- Entities formatted ---
        entity_text = (
            "\n".join([get_processor(e).format_for_llm(e) for e in entities_to_include])
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
                conversation_messages
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
        content_processor = get_processor("gamelog")
        logs_to_include: list[GameLog] = []
        tokens_added = count_tokens(assembled, model=self.model)
        for log in logs_to_include_candidates:
            candidate = (
                f"Log {log.session_number} (Full) — {log.title}:\n{log.full_text}\n\n"
            )
            cand_tokens = count_tokens(candidate, model=self.model)
            if tokens_added + cand_tokens > self.token_limit:
                break
            logs_to_include.append(log)
            tokens_added += cand_tokens

        if logs_to_include:
            logs_text = "\n\n".join(
                [
                    content_processor.format_for_llm(log)
                    for log in sorted(logs_to_include, key=lambda l: l.session_number)
                ]
            )
            assembled += f"=== Full Logs (Retrieved Subset) ===\n{logs_text}\n\n"

        return assembled, logs_to_include

    def generate_response(
        self,
        query: str,
        similarity_threshold: Optional[float] = None,
        session: Optional[ChatSession] = None,
        max_logs_to_include: int = 10,
        max_entities_to_include: int = 15,
    ) -> Dict[str, Any]:
        """
        Main RAG pipeline: search, build context, generate response

        Args:
            query: User's question
            similarity_threshold: Minimum similarity for chunk inclusion
            session: Optional chat session for building contextual search queries and conversation memory

        Returns:
            Dict with response, sources, tokens_used, etc.
        """
        from .ConversationMemoryService import ConversationMemoryService

        print("START")
        try:
            ######### GET CONVERSATION HISTORY #########
            conversation_messages = (
                ConversationMemoryService(
                    session, model=self.model
                ).get_prompt_messages_str(query)
                if session
                else ""
            )
            print("got conversation messages")

            ######### ENHANCE QUERY WITH CONTEXT #########
            enhanced_search_query = self._get_enhanced_query(
                query,
                conversation_messages=conversation_messages,
                session=session,
                similarity_threshold=similarity_threshold,
            )

            ######### RETRIEVE LOGS AND ENTITIES USING ENHANCED QUERY #########
            logs_to_include_candidates, entities_to_include = (
                self._get_logs_and_entities_for_query(
                    enhanced_search_query,
                    similarity_threshold=similarity_threshold,
                    max_logs_to_include=max_logs_to_include,
                    max_entities_to_include=max_entities_to_include,
                )
            )

            if not logs_to_include_candidates and not entities_to_include:
                response_data = {
                    "response": "I couldn't find any relevant information for that question. Could you try rephrasing it or asking about something more specific?",
                    "sources": create_sources([]),
                    "tokens_used": 0,
                    "similarity_threshold": similarity_threshold
                    or self.default_similarity_threshold,
                    "chunks_found": 0,
                    "used_session_context": session is not None,
                }
                return response_data

            ######### BUILD CONTEXT FROM THE RESULTS #########

            assembled_context, logs_included = self._assemble_context(
                conversation_messages=conversation_messages,
                entities_to_include=entities_to_include,
                logs_to_include_candidates=logs_to_include_candidates,
            )

            print("Assembled context")

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

            # Get PC name for context if available
            pc_name = (
                session.user.pc_name
                if session and session.user and session.user.pc_name
                else None
            )

            system_prompt = f"""# D&D Bi-Solar Campaign Onboard Intelligence
You are the ship's computer for a D&D homebrew campaign set in a bi-solar system with multiple planets connected by spaceship travel. You have access to embeddings containing game logs, places, characters, items, artifacts, associations, and races from this space fantasy setting.

## Core Rules
1. **Always prioritize campaign-specific information** from your knowledge base over standard D&D lore
2. **Never contradict established campaign facts** - maintain absolute consistency with the homebrew setting
3. **Use hierarchical location context**: Pay attention to place types and their parent locations (planet > region > district > location)
4. **For questions**: Search thoroughly across all planets/locations and provide contextual answers that consider interplanetary relationships
5. **For creative requests**: Blend fantasy and sci-fi elements authentically while respecting established world-building

## Response Guidelines
- Speak in character as the ship's AI—be formal, precise, and slightly clinical in tone, as an agent deeply familiar with this unique bi-solar campaign.
- Do not break character. Never speak about "the campaign" or "the game"—always refer to the setting, locations, characters, and events as real within this universe.
- While game logs are notes, treat them as historical records of actual events, as though they were recorded in the ship's databanks.
- You have access to summaries of all of the logs, and the full text of logs possibly relevant to the query. Be sure to keep them straight. If two logs are separated by time, know that the events in them also happened at different times.
- You are given as much context as deemed possibly useful. Use your judgment to determine what is relevant.
- Blend fantasy terminology with appropriate space/planetary concepts.
- When discussing locations, consider which planet/system they're on and how that affects context.
- For creative content, ensure new elements fit both the fantasy magic system and space setting.
- If you lack campaign-specific information, say so rather than defaulting to standard D&D assumptions.

## Handling Future-Oriented Questions
When users ask about predictions, future events, or "what might happen next":
1. Prioritize the most recent game logs and current character/entity states
2. Look for unresolved plot threads, character goals, and brewing conflicts
3. Consider logical consequences of recent player actions
4. Use historical context to inform possibilities, but weight recent developments heavily

## Campaign Basics
- The campaign is set in a bi-solar system with two suns and multiple planets
- The campaign revolves around a group called The Branch of Teresias. There have been other Branches of Teresias before, but this is the latest one. The players and their characters are part of this Branch, and are as follows:
    - Bruno, played by Mike—an elf who was with the group at the start and was revealed to be this generation's Teresias
    - Hrothulf, played by Michael aka MJ
    - Izar, played by Noel
    - Carlos/Ego, played by Scott—a slaad who goes by various names at different times
    - Dorinda, played by Joel
    - Darnit, played by Wes
- The primary objective of the Branch of Teresias is to free the gods from their imprisonment by the Vardum. The Vardum seek to control the gods.
- The Codex of Teresias is a key artifact that contains difficult-to-decipher prophecies about the gods, the Vardum, and the Branch of Teresias. It is currently in the possession of Bode Augur, who the group believes, with the Vardum, seeks to use it to construct a Solar Cannon, capable of destroying the gods.{f'''

## Current User Context
You are currently interfacing with {pc_name}.''' if pc_name else ""}

Your goal: Be the ultimate space fantasy campaign ship's computer that understands the unique dynamics of this multi-world setting. **Remember** to also respond in character as the ship's AI."""

            print("getting response from openai")

            response = openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "assistant", "content": assembled_context},
                    {"role": "user", "content": query},
                ],
                temperature=0.3,
                max_completion_tokens=2000,
            )

            print("got response from openai")

            response_text = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else None
            sources = create_sources(entities_to_include + logs_included)

            print("assembling response data")

            response_data = {
                "response": response_text,
                "sources": sources,
                "tokens_used": tokens_used,
                "similarity_threshold": similarity_threshold
                or self.default_similarity_threshold,
                "used_session_context": session is not None,
            }

            logger.info(
                f"Generated response for query: {query[:50]}... "
                f"(query: {query[:50]}..., tokens: {tokens_used}"
            )
            print("generated response")
            return response_data

        except Exception as e:
            logger.error(f"Failed to generate response: {str(e)}")
            return {
                "response": f"I encountered an error while processing your question: {str(e)}",
                "sources": create_sources([]),
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
        sources = response_data.get("sources")
        sources_json = sources.to_json()

        return ChatMessage.objects.create(
            session=session,
            message=message,
            response=response_data["response"],
            sources=sources_json,
            tokens_used=response_data.get("tokens_used", 0),
            similarity_threshold=response_data.get(
                "similarity_threshold", self.default_similarity_threshold
            ),
        )

    def get_user_chat_sessions(
        self, user, limit: int = 10
    ) -> QuerySet[ChatSession, ChatSession]:
        """
        Get recent chat sessions for a user
        """
        return ChatSession.objects.filter(user=user).order_by("-updated_at")[:limit]
