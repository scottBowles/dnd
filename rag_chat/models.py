from django.conf import settings
from django.db import models
from pgvector.django import HnswIndex, VectorField


class GameLogChunk(models.Model):
    """
    Stores text chunks from game logs with their embeddings for semantic search
    """

    game_log = models.ForeignKey(
        "nucleus.GameLog",  # Adjust this import path based on your GameLog location
        on_delete=models.CASCADE,
        related_name="chunks",
    )
    chunk_text = models.TextField(help_text="The actual text content of this chunk")
    chunk_index = models.IntegerField(
        help_text="Order of this chunk within the game log"
    )
    embedding = VectorField(
        dimensions=1536, help_text="OpenAI text-embedding-3-small vector"
    )
    metadata = models.JSONField(
        default=dict,
        help_text="Additional context: session info, characters, places, etc.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["game_log"]),
            models.Index(fields=["chunk_index"]),
            # HNSW vector index for cosine similarity search
            HnswIndex(
                name="chunk_embedding_hnsw_idx",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]
        unique_together = ["game_log", "chunk_index"]
        ordering = ["game_log", "chunk_index"]

    def __str__(self):
        return f"{self.game_log.title} - Chunk {self.chunk_index}"


class ChatSession(models.Model):
    """
    Represents a chat conversation with the RAG bot
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_sessions"
    )
    title = models.CharField(
        max_length=200, blank=True, help_text="Auto-generated from first message"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.user.username} - {self.title or 'Chat Session'}"

    def save(self, *args, **kwargs):
        # Auto-generate title from first message if not set
        if not self.title and self.pk:
            first_message = self.messages.first()
            if first_message:
                self.title = first_message.message[:50] + (
                    "..." if len(first_message.message) > 50 else ""
                )
        super().save(*args, **kwargs)


class ChatMessage(models.Model):
    """
    Individual messages within a chat session
    """

    session = models.ForeignKey(
        ChatSession, on_delete=models.CASCADE, related_name="messages"
    )
    message = models.TextField(help_text="User's question/message")
    response = models.TextField(help_text="RAG bot's response")
    sources = models.JSONField(
        default=list, help_text="Citations and source links used in the response"
    )
    tokens_used = models.IntegerField(default=0, help_text="OpenAI API tokens consumed")
    similarity_threshold = models.FloatField(
        default=0.7, help_text="Minimum similarity score used for this query"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.session} - {self.message[:50]}..."


class QueryCache(models.Model):
    """
    Cache expensive RAG queries to reduce API costs
    """

    query_hash = models.CharField(max_length=64, unique=True, db_index=True)
    query_text = models.TextField(help_text="Original query for debugging")
    response_data = models.JSONField(help_text="Cached response, sources, etc.")
    tokens_saved = models.IntegerField(default=0)
    hit_count = models.IntegerField(
        default=0, help_text="How many times this cache was used"
    )
    expires_at = models.DateTimeField(help_text="When this cache entry expires")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Cache: {self.query_text[:50]}... (hits: {self.hit_count})"
