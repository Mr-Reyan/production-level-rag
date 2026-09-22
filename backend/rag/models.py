import uuid
from django.db import models
from pgvector.django import VectorField

# Create your models here.

SENDER_ROLES = [
    ("ai", "AI Assistant"),
    ("user", "User"),
]


class Chats(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, default="Untitled Chat")
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True, default=None)

    def __str__(self):
        return f"{self.title} ({self.id})"




class Message(models.Model):
    chat = models.ForeignKey(Chats, on_delete=models.CASCADE, related_name="messages")
    text = models.TextField()
    sender = models.CharField(choices=SENDER_ROLES, max_length=5, default="user")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"[{self.sender}] {self.text[:30]}"


class Document(models.Model):
    chat = models.ForeignKey(
        Chats, on_delete=models.CASCADE, null=True, related_name="documents"
    )
    title = models.CharField(max_length=255)
    content = models.TextField()
    embedding = VectorField(dimensions=1024)
    source_id = models.UUIDField(db_index=True)
    chunk_index = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - Chunk {self.chunk_index}"

