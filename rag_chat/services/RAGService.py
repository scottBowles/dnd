import concurrent.futures
import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Dict, Generator, List, Optional

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import QuerySet
from openai import OpenAI
from pgvector.django import CosineDistance

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
from ..source_models import create_sources, parse_sources, bulk_resolve_sources
from ..utils import count_tokens
from .build_conversation_memory import build_conversation_memory
from .game_log_full_text_search import weighted_fts_search_logs
from .trigram_entity_search import trigram_entity_search
from .game_log_full_text_search import key_terms

logger = logging.getLogger(__name__)


class PipelineTimer:
    """Lightweight timer for profiling pipeline steps."""

    def __init__(self):
        self.steps: list[tuple[str, float]] = []
        self._start = time.perf_counter()

    @contextmanager
    def step(self, name: str):
        t0 = time.perf_counter()
        yield
        self.steps.append((name, time.perf_counter() - t0))

    def record(self, name: str, duration: float):
        """Record a pre-measured duration (e.g. from a timed closure)."""
        self.steps.append((name, duration))

    def summary(self):
        total = time.perf_counter() - self._start
        w = max((len(n) for n, _ in self.steps), default=20)
        lines = [
            "",
            f"{'─' * (w + 22)}",
            f"{'Step':<{w}}  {'Time':>7}  {'%':>5}",
            f"{'─' * (w + 22)}",
        ]
        for name, dur in self.steps:
            pct = (dur / total * 100) if total else 0
            lines.append(f"{name:<{w}}  {dur:>6.2f}s  {pct:>4.0f}%")
        lines.append(f"{'─' * (w + 22)}")
        lines.append(f"{'TOTAL':<{w}}  {total:>6.2f}s")
        lines.append("")
        msg = "\n".join(lines)
        print(msg)
        logger.info(msg)


def _timed(fn):
    """Call fn(), return (result, elapsed_seconds)."""
    t0 = time.perf_counter()
    result = fn()
    return result, time.perf_counter() - t0


# Map from content-type string keys (used throughout the pipeline) to model classes.
# ContentType.objects.get_for_model() uses Django's internal cache, so after the
# first call each model's ContentType is resolved without a DB query.
_CONTENT_TYPE_MODEL_MAP: dict[str, type] = {
    "gamelog": GameLog,
    "character": Character,
    "place": Place,
    "item": Item,
    "artifact": Artifact,
    "race": Race,
    "association": Association,
}

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


@dataclass
class PreparedContext:
    """All the pre-LLM pipeline output needed to generate a response."""

    system_prompt: str
    assembled_context: str
    sources: Any  # SourcesV1
    entities_to_include: List[Any]
    logs_included: List[GameLog]
    similarity_threshold: float
    used_session_context: bool


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

            queryset = ContentChunk.objects.annotate(
                similarity=1 - CosineDistance("embedding", query_embedding)
            ).filter(similarity__gte=similarity_threshold)

            # Filter by content types if specified
            if content_types:
                content_type_objects = [
                    ContentType.objects.get_for_model(model_cls)
                    for ct_str in content_types
                    if (model_cls := _CONTENT_TYPE_MODEL_MAP.get(ct_str))
                ]
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
        timer: PipelineTimer | None = None,
    ) -> str:
        ######### GET ENTITIES FOR QUERY ENHANCEMENT #########
        query_with_history = conversation_messages + f"\n\nQuestion: {query}"

        def _trigram_search():
            return trigram_entity_search(query)

        def _semantic_search():
            return self.semantic_search(
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

        def _past_message_sources():
            if not session:
                return []
            messages_sources = list(session.messages.values_list("sources", flat=True))
            all_sources = bulk_resolve_sources(messages_sources)
            return [s for s in all_sources if not isinstance(s, GameLog)]

        # Run all three entity-gathering operations concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            trigram_future = executor.submit(_timed, _trigram_search)
            semantic_future = executor.submit(_timed, _semantic_search)
            past_msg_future = executor.submit(_timed, _past_message_sources)

            trigram_results_for_query_enhancement, t_tri = trigram_future.result()
            semantic_search_results_for_query_enhancement, t_sem = (
                semantic_future.result()
            )
            entities_from_past_messages, t_past = past_msg_future.result()

        if timer:
            timer.record("  enh: trigram_search", t_tri)
            timer.record("  enh: semantic_search", t_sem)
            timer.record("  enh: past_msg_sources", t_past)

        trigram_entities_for_query_enhancement = [
            res.entity for res in trigram_results_for_query_enhancement
        ]
        entities_from_semantic_search = [
            result.content_object
            for result in semantic_search_results_for_query_enhancement
            if not isinstance(result.content_object, GameLog)
        ]

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
        with_llm = (
            timer.step("  enh: llm_rewrite")
            if timer
            else contextmanager(lambda: (yield))()
        )
        with with_llm:
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

        return enhanced_search_query

    def _get_logs_and_entities_for_query(
        self,
        query: str,
        similarity_threshold: Optional[float] = None,
        max_logs_to_include: int = 10,
        max_entities_to_include: int = 15,
        timer: PipelineTimer | None = None,
    ) -> tuple[
        List[GameLog], List[Association | Character | Place | Item | Artifact | Race]
    ]:
        SEMANTIC_WEIGHT = 0.6
        FTS_WEIGHT = 0.3
        TRIGRAM_WEIGHT = 0.1

        # Run the entity search operations in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            # Submit both entity searches simultaneously
            trigram_future = executor.submit(
                _timed, lambda: trigram_entity_search(query)
            )
            semantic_entity_future = executor.submit(
                _timed,
                lambda: self.semantic_search(
                    query,
                    self.max_context_chunks,
                    similarity_threshold,
                    ["character", "place", "item", "artifact", "race", "association"],
                ),
            )

            # Wait for results
            trigram_results, t_tri = trigram_future.result()
            semantic_entity_chunks, t_sem = semantic_entity_future.result()

        if timer:
            timer.record("  ret: entity_trigram", t_tri)
            timer.record("  ret: entity_semantic", t_sem)

        semantic_entity_scores = [
            ScoreSetElement(chunk.content_object, chunk.similarity)
            for chunk in semantic_entity_chunks
        ]
        trigram_scores = [
            ScoreSetElement(r.entity, r.similarity) for r in trigram_results
        ]

        with_entity_fusion = (
            timer.step("  ret: entity_fusion")
            if timer
            else contextmanager(lambda: (yield))()
        )
        with with_entity_fusion:
            semantic_entity_scores_normalized = z_score_normalize(
                semantic_entity_scores
            )
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
                _timed, lambda: weighted_fts_search_logs(query, entities_for_log_search)
            )

            enhanced_query_for_log_search = (
                self.build_enriched_text_for_semantic_search(
                    query,
                    entities_for_log_search,
                )
            )
            semantic_log_future = log_executor.submit(
                _timed,
                lambda: self.semantic_search(
                    enhanced_query_for_log_search,
                    self.max_context_chunks,
                    similarity_threshold,
                    ["gamelog"],
                ),
            )

            # Get log search results
            fts_results, t_fts = fts_future.result()
            semantic_log_chunks, t_sem_log = semantic_log_future.result()

        if timer:
            timer.record("  ret: log_fts", t_fts)
            timer.record("  ret: log_semantic", t_sem_log)

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

        with_log_fusion = (
            timer.step("  ret: log_fusion")
            if timer
            else contextmanager(lambda: (yield))()
        )
        with with_log_fusion:
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

    def _build_system_prompt(self, session: Optional[ChatSession] = None) -> str:
        """Build the system prompt for the LLM."""
        pc_name = (
            session.user.pc_name
            if session and session.user and session.user.pc_name
            else None
        )

        return f"""# D&D Bi-Solar Campaign Onboard Intelligence
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
- The Codex of Teresias is a key artifact that contains difficult-to-decipher prophecies about the gods, the Vardum, and the Branch of Teresias. It is currently in the possession of Bode Augur, who the group believes, with the Vardum, seeks to use it to construct a Solar Cannon, capable of destroying the gods.{f"""

## Current User Context
You are currently interfacing with {pc_name}.""" if pc_name else ""}

Your goal: Be the ultimate space fantasy campaign ship's computer that understands the unique dynamics of this multi-world setting. **Remember** to always respond in character as the ship's AI."""

    def prepare_context(
        self,
        query: str,
        similarity_threshold: Optional[float] = None,
        session: Optional[ChatSession] = None,
        max_logs_to_include: int = 10,
        max_entities_to_include: int = 15,
    ) -> Optional[PreparedContext]:
        """
        Run the full pre-LLM pipeline: conversation history, query enhancement,
        retrieval, context assembly, system prompt. Returns None if no relevant
        context is found.
        """
        timer = PipelineTimer()

        ######### GET CONVERSATION HISTORY #########
        with timer.step("conversation_history"):
            conversation_messages = (
                build_conversation_memory(session, query, model=self.model)
                if session
                else ""
            )

        ######### ENHANCE QUERY WITH CONTEXT #########
        with timer.step("query_enhancement"):
            enhanced_search_query = self._get_enhanced_query(
                query,
                conversation_messages=conversation_messages,
                session=session,
                similarity_threshold=similarity_threshold,
                timer=timer,
            )

        ######### RETRIEVE LOGS AND ENTITIES USING ENHANCED QUERY #########
        with timer.step("retrieval"):
            logs_to_include_candidates, entities_to_include = (
                self._get_logs_and_entities_for_query(
                    enhanced_search_query,
                    similarity_threshold=similarity_threshold,
                    max_logs_to_include=max_logs_to_include,
                    max_entities_to_include=max_entities_to_include,
                    timer=timer,
                )
            )

        if not logs_to_include_candidates and not entities_to_include:
            timer.summary()
            return None

        ######### BUILD CONTEXT FROM THE RESULTS #########
        with timer.step("assemble_context"):
            assembled_context, logs_included = self._assemble_context(
                conversation_messages=conversation_messages,
                entities_to_include=entities_to_include,
                logs_to_include_candidates=logs_to_include_candidates,
            )

        with timer.step("build_system_prompt"):
            system_prompt = self._build_system_prompt(session)
        sources = create_sources(entities_to_include + logs_included)

        timer.summary()

        return PreparedContext(
            system_prompt=system_prompt,
            assembled_context=assembled_context,
            sources=sources,
            entities_to_include=entities_to_include,
            logs_included=logs_included,
            similarity_threshold=similarity_threshold
            or self.default_similarity_threshold,
            used_session_context=session is not None,
        )

    def generate_response_stream(
        self,
        query: str,
        prepared_context: PreparedContext,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Stream the LLM response token-by-token. Yields dicts:
          {"type": "token", "token": "..."} for each content chunk
          {"type": "done", "tokens_used": N} on completion
          {"type": "error", "error": "..."} on failure
        """
        try:
            stream = openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": prepared_context.system_prompt},
                    {
                        "role": "assistant",
                        "content": prepared_context.assembled_context,
                    },
                    {"role": "user", "content": query},
                ],
                temperature=0.3,
                max_completion_tokens=2000,
                stream=True,
                stream_options={"include_usage": True},
            )

            tokens_used = None
            for chunk in stream:
                if chunk.usage:
                    tokens_used = chunk.usage.total_tokens

                if chunk.choices and chunk.choices[0].delta.content:
                    yield {"type": "token", "token": chunk.choices[0].delta.content}

            yield {"type": "done", "tokens_used": tokens_used}

        except Exception as e:
            logger.error(f"Streaming response failed: {str(e)}")
            yield {"type": "error", "error": str(e)}

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
        try:
            prepared = self.prepare_context(
                query=query,
                similarity_threshold=similarity_threshold,
                session=session,
                max_logs_to_include=max_logs_to_include,
                max_entities_to_include=max_entities_to_include,
            )

            if prepared is None:
                return {
                    "response": "I couldn't find any relevant information for that question. Could you try rephrasing it or asking about something more specific?",
                    "sources": create_sources([]),
                    "tokens_used": 0,
                    "similarity_threshold": similarity_threshold
                    or self.default_similarity_threshold,
                    "chunks_found": 0,
                    "used_session_context": session is not None,
                }

            t0 = time.perf_counter()
            response = openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": prepared.system_prompt},
                    {"role": "assistant", "content": prepared.assembled_context},
                    {"role": "user", "content": query},
                ],
                temperature=0.3,
                max_completion_tokens=2000,
            )

            llm_elapsed = time.perf_counter() - t0
            logger.info(f"LLM generation: {llm_elapsed:.2f}s")
            print(f"\nLLM generation: {llm_elapsed:.2f}s")

            response_text = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else None

            response_data = {
                "response": response_text,
                "sources": prepared.sources,
                "tokens_used": tokens_used,
                "similarity_threshold": prepared.similarity_threshold,
                "used_session_context": prepared.used_session_context,
            }

            logger.info(
                f"Generated response for query: {query[:50]}... "
                f"(tokens: {tokens_used})"
            )
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
