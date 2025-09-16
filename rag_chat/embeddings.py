import hashlib
import re
from typing import Any, Dict, List, Optional

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


def create_query_hash(
    query: str, context_params: Optional[Dict[str, Any]] = None
) -> str:
    """
    Create a hash for caching query results
    """
    content = query.lower().strip()
    if context_params:
        content += str(sorted(context_params.items()))

    return hashlib.sha256(content.encode()).hexdigest()
