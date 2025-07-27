import hashlib
import re
from typing import Any, Dict, List

from django.conf import settings
from openai import OpenAI

# Initialize OpenAI client

openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)


def get_embedding(text: str) -> List[float]:
    """
    Get embedding using OpenAI's cheapest embedding model
    """
    try:
        response = openai_client.embeddings.create(
            model=settings.OPENAI_EMBEDDINGS_MODEL,
            input=text.strip(),
        )
        return response.data[0].embedding
    except Exception as e:
        raise Exception(f"Failed to get embedding: {str(e)}")


def chunk_document(text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
    """
    Split document into overlapping chunks for better context preservation

    Args:
        text: The full document text
        chunk_size: Target number of words per chunk
        overlap: Number of words to overlap between chunks

    Returns:
        List of text chunks
    """
    if not text or not text.strip():
        return []

    # Clean up the text
    text = clean_text(text)
    words = text.split()

    if len(words) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(words):
        # Calculate initial end position
        end = min(start + chunk_size, len(words))
        chunk_words = words[start:end]
        chunk_text = " ".join(chunk_words)

        # If this isn't the last chunk, try to end on a sentence boundary
        if end < len(words) and not chunk_text.endswith((".", "!", "?")):
            # Look for the last sentence boundary in the chunk
            last_sentence_end = max(
                chunk_text.rfind("."), chunk_text.rfind("!"), chunk_text.rfind("?")
            )

            # Only cut at sentence boundary if it's not too early (keeps chunk reasonably sized)
            if last_sentence_end > len(chunk_text) * 0.6:
                chunk_text = chunk_text[: last_sentence_end + 1]
                # Recalculate actual end position in words
                actual_words = chunk_text.split()
                end = start + len(actual_words)

        chunks.append(chunk_text.strip())

        # Check if we've processed all words
        if end >= len(words):
            break

        # Move start position with overlap, ensuring we don't go backwards
        next_start = max(start + 1, end - overlap)
        start = next_start

    return [chunk for chunk in chunks if chunk.strip()]


def clean_text(text: str) -> str:
    """
    Clean up text for better embedding quality
    """
    if not text:
        return ""

    # Remove excessive whitespace
    text = re.sub(r"\s+", " ", text)

    # Remove very long sequences of the same character (artifacts)
    text = re.sub(r"(.)\1{10,}", r"\1", text)

    # Basic cleanup
    text = text.strip()

    return text


def generate_chunk_summary(chunk_text: str, max_length: int = 150) -> str:
    """
    Generate a brief summary of a text chunk
    For now, just takes the first few sentences, but could be enhanced with LLM
    """
    if not chunk_text:
        return ""

    sentences = re.split(r"[.!?]+", chunk_text)
    summary_parts = []
    current_length = 0

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        if current_length + len(sentence) > max_length and summary_parts:
            break

        summary_parts.append(sentence)
        current_length += len(sentence)

    summary = ". ".join(summary_parts)
    if summary and not summary.endswith((".", "!", "?")):
        summary += "..."

    return summary


def create_query_hash(query: str, context_params: Dict[str, Any] = None) -> str:
    """
    Create a hash for caching query results
    """
    content = query.lower().strip()
    if context_params:
        content += str(sorted(context_params.items()))

    return hashlib.sha256(content.encode()).hexdigest()


def build_chunk_metadata(
    game_log, chunk_text: str, chunk_index: int, total_chunks: int
) -> Dict[str, Any]:
    """
    Build essential metadata for a game log chunk (kept concise for efficiency)
    """
    metadata = {
        "session_number": game_log.session_number,
        "session_title": game_log.title,
        "session_date": game_log.game_date.isoformat() if game_log.game_date else None,
        "chunk_index": chunk_index,
        "total_chunks": total_chunks,
        "google_doc_url": game_log.url,
    }

    # Add brief summary only if it's reasonably short
    if game_log.brief and len(game_log.brief) < 200:
        metadata["brief_summary"] = game_log.brief

    # Add places but limit to avoid excessive length
    try:
        places = [place.name for place in game_log.places_set_in.all()]
        if places:
            metadata["places_mentioned"] = places[:5]  # Limit to 5 places max
    except:
        pass

    # Add chunk summary only if the chunk is long enough to warrant it
    if len(chunk_text) > 400:
        metadata["chunk_summary"] = generate_chunk_summary(chunk_text, max_length=100)

    return metadata
