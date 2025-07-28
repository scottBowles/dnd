from django.conf import settings
import strawberry
import strawberry_django
from strawberry import auto, relay
from typing import List, Optional
from strawberry_django.relay import DjangoListConnection
from . import models, services
from nucleus.types.user import User as UserType

# Relay node types for each model


@strawberry_django.type(models.ChatSession)
class ChatSessionType(relay.Node):
    user: UserType
    title: auto
    created_at: auto
    updated_at: auto
    messages: List["ChatMessageType"]

    @strawberry.field
    def messages(self) -> List["ChatMessageType"]:
        return self.messages.all().order_by("created_at")


@strawberry_django.type(models.ChatMessage)
class ChatMessageType(relay.Node):
    session: "ChatSessionType"
    message: auto
    response: auto
    sources: auto
    tokens_used: auto
    similarity_threshold: auto
    created_at: auto


@strawberry_django.type(models.QueryCache)
class QueryCacheType(relay.Node):
    query_hash: auto
    query_text: auto
    response_data: auto
    tokens_saved: auto
    hit_count: auto
    expires_at: auto
    created_at: auto


# Input types for mutations


@strawberry.input
class StartChatSessionInput:
    title: Optional[str] = None


@strawberry.input
class SendChatMessageInput:
    session_id: relay.GlobalID
    message: str
    similarity_threshold: Optional[float] = None


# Output type for chat message mutation


@strawberry.type
class SendChatMessagePayload:
    message: ChatMessageType
    session: ChatSessionType


# Query and Mutation classes


@strawberry.type
class RAGQuery:
    chat_sessions: DjangoListConnection[ChatSessionType] = (
        strawberry_django.connection()
    )
    chat_messages: DjangoListConnection[ChatMessageType] = (
        strawberry_django.connection()
    )


@strawberry.type
class RAGMutation:
    @strawberry.mutation
    def start_chat_session(self, info, input: StartChatSessionInput) -> ChatSessionType:
        user = info.context.request.user
        rag_service = services.RAGService()
        session = rag_service.create_chat_session(user, title=input.title)
        return session

    @strawberry.mutation
    def send_chat_message(
        self, info, input: SendChatMessageInput
    ) -> SendChatMessagePayload:
        user = info.context.request.user
        if not user.is_authenticated:
            raise Exception("User must be authenticated to send messages.")
        if user.is_staff:
            model = settings.OPENAI_BEST_CHAT_MODEL
        else:
            model = settings.OPENAI_CHEAP_CHAT_MODEL
        rag_service = services.RAGService(model=model)
        session = input.session_id.resolve_node_sync(
            info, ensure_type=models.ChatSession
        )
        response_data = rag_service.generate_response(
            input.message, similarity_threshold=input.similarity_threshold
        )
        message = rag_service.save_chat_message(session, input.message, response_data)
        return SendChatMessagePayload(message=message, session=session)
