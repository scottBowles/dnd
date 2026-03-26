import base64
import json
import logging

from django.conf import settings
from django.http import StreamingHttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from gqlauth.core.middlewares import USER_OR_ERROR_KEY

from .models import ChatSession
from .services.RAGService import RAGService
from .source_models import create_sources

logger = logging.getLogger(__name__)


def _get_jwt_user(request):
    """
    Resolve the authenticated user from gqlauth's JWT middleware.

    gqlauth's django_jwt_middleware stores a UserOrError on the request but does
    NOT set request.user — that only happens inside JwtSchema for GraphQL views.
    This helper replicates that step for regular Django views.
    """
    user_or_error = getattr(request, USER_OR_ERROR_KEY, None)
    if user_or_error is not None and user_or_error.user.is_authenticated:
        return user_or_error.user
    return request.user


def _check_chat_permission(user) -> bool:
    """Check if a user has permission to send chat messages."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return (
        user.has_perm("rag_chat.can_send_chat_message")
        or user.groups.filter(name="RAG Chat Users").exists()
    )


def _resolve_session_id(raw_id) -> int:
    """Resolve a session ID from either a raw integer or a Relay global ID."""
    if isinstance(raw_id, int):
        return raw_id
    raw_id = str(raw_id)
    # Try parsing as plain integer first
    try:
        return int(raw_id)
    except ValueError:
        pass
    # Try decoding as Relay global ID (base64 "TypeName:id")
    try:
        decoded = base64.b64decode(raw_id).decode("utf-8")
        _, pk = decoded.rsplit(":", 1)
        return int(pk)
    except Exception:
        raise ValueError(f"Invalid session ID: {raw_id}")


def _sse_event(data: dict) -> str:
    """Format a dict as an SSE data event."""
    return f"data: {json.dumps(data)}\n\n"


@csrf_exempt
@require_POST
def chat_stream_view(request):
    """
    SSE endpoint for streaming RAG chat responses.

    Expects JSON body: {"session_id": <int>, "message": "<text>", "similarity_threshold": <float|null>}
    Authenticates via the JWT middleware (Authorization header).

    Returns a text/event-stream with:
      data: {"type": "token", "token": "..."}
      ...
      data: {"type": "done", "message_id": ..., "tokens_used": ..., "sources": {...}}
    Or on error:
      data: {"type": "error", "error": "..."}
    """
    user = _get_jwt_user(request)

    if not _check_chat_permission(user):
        return JsonResponse({"error": "Permission denied"}, status=403)

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    session_id = body.get("session_id")
    message = body.get("message", "").strip()
    similarity_threshold = body.get("similarity_threshold")

    if not session_id or not message:
        return JsonResponse(
            {"error": "session_id and message are required"}, status=400
        )

    try:
        pk = _resolve_session_id(session_id)
        session = ChatSession.objects.get(pk=pk)
    except (ValueError, ChatSession.DoesNotExist):
        return JsonResponse({"error": "Chat session not found"}, status=404)

    if session.user != user:
        return JsonResponse(
            {"error": "You can only send messages to your own chat sessions"},
            status=403,
        )

    # Select model based on staff status
    model = (
        settings.OPENAI_BEST_CHAT_MODEL
        if user.is_staff
        else settings.OPENAI_CHEAP_CHAT_MODEL
    )
    rag_service = RAGService(model=model)

    def event_stream():
        try:
            prepared = rag_service.prepare_context(
                query=message,
                similarity_threshold=similarity_threshold,
                session=session,
            )

            if prepared is None:
                no_context_response = "I couldn't find any relevant information for that question. Could you try rephrasing it or asking about something more specific?"
                # Save to DB even when no context found
                response_data = {
                    "response": no_context_response,
                    "sources": create_sources([]),
                    "tokens_used": 0,
                    "similarity_threshold": similarity_threshold
                    or rag_service.default_similarity_threshold,
                }
                saved_message = rag_service.save_chat_message(
                    session, message, response_data
                )
                yield _sse_event({"type": "token", "token": no_context_response})
                yield _sse_event(
                    {
                        "type": "done",
                        "message_id": saved_message.pk,
                        "tokens_used": 0,
                        "sources": response_data["sources"].to_json(),
                    }
                )
                return

            # Stream the LLM response
            full_response = []
            tokens_used = 0

            for chunk in rag_service.generate_response_stream(message, prepared):
                if chunk["type"] == "token":
                    full_response.append(chunk["token"])
                    yield _sse_event(chunk)
                elif chunk["type"] == "done":
                    tokens_used = chunk.get("tokens_used", 0)
                elif chunk["type"] == "error":
                    yield _sse_event(chunk)
                    return

            # Save the complete message to DB
            response_text = "".join(full_response)
            response_data = {
                "response": response_text,
                "sources": prepared.sources,
                "tokens_used": tokens_used,
                "similarity_threshold": prepared.similarity_threshold,
            }
            saved_message = rag_service.save_chat_message(
                session, message, response_data
            )

            yield _sse_event(
                {
                    "type": "done",
                    "message_id": saved_message.pk,
                    "tokens_used": tokens_used,
                    "sources": prepared.sources.to_json(),
                }
            )

        except Exception as e:
            logger.error(f"Streaming chat error: {str(e)}")
            yield _sse_event({"type": "error", "error": str(e)})

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"  # Prevent nginx/proxy buffering
    return response
