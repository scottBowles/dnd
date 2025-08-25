from django import forms
from django.apps import apps
from django.contrib import admin
from django.db.models import Count
from django.shortcuts import render
from django.urls import path

from rag_chat.content_processors import CONTENT_PROCESSORS
from rag_chat.services import RAGService

from . import models


@admin.register(models.ContentChunk)
class ContentChunkAdmin(admin.ModelAdmin):
    def search_content_view(self, request):

        results = None
        form = self.SearchForm(request.GET or None)
        if form.is_valid():
            rag_service = RAGService()
            results = rag_service.semantic_search(
                query=form.cleaned_data["query"],
                limit=form.cleaned_data.get("limit") or 10,
                similarity_threshold=form.cleaned_data.get("similarity_threshold"),
                content_types=form.cleaned_data.get("content_types") or None,
            )
        context = dict(
            self.admin_site.each_context(request),
            form=form,
            results=results,
        )
        return render(request, "admin/rag_chat/search_content.html", context)

    list_display = (
        "id",
        "content_type",
        "object_id",
        "chunk_index",
        "created_at",
        "updated_at",
    )
    list_filter = ("content_type", "created_at", "updated_at")
    search_fields = ("chunk_text", "object_id")

    actions = ["process_selected_chunks"]

    def process_selected_chunks(self, request, queryset):
        from rag_chat.tasks import process_content

        count = 0
        for chunk in queryset:
            process_content.delay(
                content_type=chunk.content_type,
                object_id=chunk.object_id,
                force_reprocess=True,
            )
            count += 1
        self.message_user(request, f"Queued processing for {count} selected chunks.")

    process_selected_chunks.short_description = "Process selected content chunks"

    # Add custom URLs for stats, types, and search
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "content-stats/",
                self.admin_site.admin_view(self.content_stats_view),
                name="rag_chat_content_stats",
            ),
            path(
                "available-content-types/",
                self.admin_site.admin_view(self.available_content_types_view),
                name="rag_chat_available_content_types",
            ),
            path(
                "search-content/",
                self.admin_site.admin_view(self.search_content_view),
                name="rag_chat_search_content",
            ),
        ]
        return custom_urls + urls

    def content_stats_view(self, request):
        # Model mapping for getting object counts
        model_map = {
            "gamelog": ("nucleus", "GameLog"),
            "character": ("character", "Character"),
            "place": ("place", "Place"),
            "item": ("item", "Item"),
            "artifact": ("item", "Artifact"),
            "race": ("race", "Race"),
            "association": ("association", "Association"),
        }
        chunk_stats = dict(
            models.ContentChunk.objects.values("content_type")
            .annotate(count=Count("id"))
            .values_list("content_type", "count")
        )
        stats = []
        for content_type, (app_label, model_name) in model_map.items():
            try:
                model = apps.get_model(app_label, model_name)
                object_count = model.objects.count()
                processed_count = (
                    models.ContentChunk.objects.filter(content_type=content_type)
                    .values("object_id")
                    .distinct()
                    .count()
                )
                stats.append(
                    {
                        "content_type": content_type,
                        "chunk_count": chunk_stats.get(content_type, 0),
                        "object_count": object_count,
                        "processed_count": processed_count,
                    }
                )
            except Exception:
                continue
        # Add custom content stats
        custom_chunk_count = chunk_stats.get("custom", 0)
        if custom_chunk_count > 0:
            custom_object_count = (
                models.ContentChunk.objects.filter(content_type="custom")
                .values("object_id")
                .distinct()
                .count()
            )
            stats.append(
                {
                    "content_type": "custom",
                    "chunk_count": custom_chunk_count,
                    "object_count": custom_object_count,
                    "processed_count": custom_object_count,
                }
            )
        context = dict(
            self.admin_site.each_context(request),
            stats=stats,
        )
        return render(request, "admin/rag_chat/content_stats.html", context)

    def available_content_types_view(self, request):
        content_types = list(CONTENT_PROCESSORS.keys())
        context = dict(
            self.admin_site.each_context(request),
            content_types=content_types,
        )
        return render(request, "admin/rag_chat/available_content_types.html", context)

    class SearchForm(forms.Form):
        query = forms.CharField(required=True, label="Search Query")
        content_types = forms.MultipleChoiceField(
            required=False,
            choices=[(k, k) for k in CONTENT_PROCESSORS.keys()],
            widget=forms.CheckboxSelectMultiple,
        )
        similarity_threshold = forms.FloatField(
            required=False, label="Similarity Threshold"
        )
        limit = forms.IntegerField(required=False, label="Limit", initial=10)


@admin.register(models.QueryCache)
class QueryCacheAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "query_hash",
        "query_text",
        "tokens_saved",
        "hit_count",
        "expires_at",
        "created_at",
    )
    search_fields = ("query_text", "query_hash")


@admin.register(models.ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "title", "created_at", "updated_at")
    search_fields = ("title", "user__username")


@admin.register(models.ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "message", "created_at")
    search_fields = ("message", "session__title", "session__user__username")
