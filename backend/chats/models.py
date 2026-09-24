from sqlalchemy import true
import uuid
from django.db import models

SENDER_ROLES = [
    ("ai", "AI Assistant"),
    ("user", "User"),
]


class Chats(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, default="Untitled Chat")
    summary = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True, default=None)

    class Meta:
        db_table = "rag_chats"

    def __str__(self):
        return f"{self.title} ({self.id})"


class Message(models.Model):
    chat = models.ForeignKey(Chats, on_delete=models.CASCADE, related_name="messages")
    text = models.TextField()
    retrieved_chunk_ids = models.JSONField(default=list, blank=True)
    trace_id = models.CharField(max_length=64, blank=True, default="")
    sender = models.CharField(choices=SENDER_ROLES, max_length=5, default="user")
    sources = models.JSONField(null=True, blank=True, default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "rag_message"
        ordering = ["created_at"]

    def __str__(self):
        return f"[{self.sender}] {self.text[:30]}"
