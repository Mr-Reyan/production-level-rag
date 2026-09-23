import logging
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view

from chats.models import Chats

logger = logging.getLogger(__name__)


@csrf_exempt
@api_view(["GET"])
def list_chats(request):
    """
    List all active chats ordered by latest creation.
    """
    try:
        chats = Chats.objects.filter(deleted_at__isnull=True).order_by("-created_at")
        data = [
            {
                "id": str(chat.id),
                "title": chat.title,
                "summary": chat.summary or "",
                "created_at": chat.created_at.isoformat() if chat.created_at else None,
                "message_count": chat.messages.count(),
            }
            for chat in chats
        ]
        return JsonResponse({"chats": data}, status=200)
    except Exception as e:
        logger.error(f"Error listing chats: {e}", exc_info=True)
        return JsonResponse({"error": f"Failed to list chats: {str(e)}"}, status=500)


@csrf_exempt
@api_view(["GET", "DELETE"])
def chat_detail(request, chat_id):
    """
    GET: Retrieve chat info, message history with sources, summary, and associated documents.
    DELETE: Soft-delete a chat.
    """
    chat = Chats.objects.filter(id=chat_id, deleted_at__isnull=True).first()
    if not chat:
        return JsonResponse({"error": "Chat not found"}, status=404)

    if request.method == "DELETE":
        try:
            chat.deleted_at = timezone.now()
            chat.save(update_fields=["deleted_at"])
            return JsonResponse(
                {"message": "Chat deleted successfully", "chat_id": str(chat.id)},
                status=200,
            )
        except Exception as e:
            return JsonResponse({"error": f"Failed to delete chat: {str(e)}"}, status=500)

    # GET: return chat details, messages, documents, and summary
    try:
        messages = [
            {
                "id": m.id,
                "sender": m.sender,
                "text": m.text,
                "sources": m.sources or [],
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in chat.messages.all().order_by("created_at")
        ]
        docs = list(
            chat.documents.values("source_id", "title").distinct()
        )
        return JsonResponse(
            {
                "chat": {
                    "id": str(chat.id),
                    "title": chat.title,
                    "summary": chat.summary or "",
                    "created_at": chat.created_at.isoformat() if chat.created_at else None,
                },
                "messages": messages,
                "documents": [
                    {"source_id": str(d["source_id"]), "title": d["title"]} for d in docs
                ],
            },
            status=200,
        )
    except Exception as e:
        logger.error(f"Error fetching chat detail: {e}", exc_info=True)
        return JsonResponse({"error": f"Failed to fetch chat details: {str(e)}"}, status=500)
