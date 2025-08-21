from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from pgvector.django import HnswIndex, VectorField


class ContentChunk(models.Model):
    """
    Stores text chunks from various content sources with their embeddings for semantic search
    """

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        limit_choices_to={
            "app_label__in": [
                "character",
                "place",
                "item",
                "race",
                "association",
                "nucleus",
            ],
            "model__in": [
                "character",
                "place",
                "item",
                "artifact",
                "race",
                "association",
                "gamelog",
            ],
        },
        help_text="Content type for the generic foreign key",
    )
    object_id = models.PositiveBigIntegerField(
        help_text="ID of the source object (primary key of the related model)",
    )
    content_object = GenericForeignKey("content_type", "object_id")
    chunk_text = models.TextField(help_text="The actual text content of this chunk")
    chunk_index = models.IntegerField(
        default=0,
        help_text="Order of this chunk within the source content (0 for single chunks)",
    )
    embedding = VectorField(
        dimensions=1536, help_text="OpenAI text-embedding-3-small vector"
    )
    metadata = models.JSONField(
        default=dict,
        help_text="Content-specific metadata: titles, URLs, relationships, dates, etc.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["content_type"]),
            models.Index(fields=["object_id"]),
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["chunk_index"]),
            # HNSW vector index for cosine similarity search
            HnswIndex(
                name="embedding_hnsw_idx",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]
        unique_together = ["content_type", "object_id", "chunk_index"]
        ordering = ["content_type", "object_id", "chunk_index"]

    def __str__(self):
        title = self.metadata.get("title", self.object_id)
        content_type_name = self.content_type.model if self.content_type else "Unknown"
        if self.chunk_index > 0:
            return f"{content_type_name.title()}: {title} - Chunk {self.chunk_index}"
        return f"{content_type_name.title()}: {title}"


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
    conversation_summary = models.TextField(
        default="",
        help_text="Running summary of all messages outside the sliding token window",
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
    content_types_searched = models.JSONField(
        default=list, help_text="List of content types that were searched"
    )
    included_in_summary = models.BooleanField(
        default=False,
        help_text="Whether this message has been included in the conversation summary",
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
