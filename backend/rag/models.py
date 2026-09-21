from django.db import models
from django.forms.fields import CharField
from pgvector.django import VectorField

# Create your models here.

SENDER_ROLES = [
    ("ai", "AI Assistant"),
    ("user", "User"),
]


class Chats(models.Model):
    id = models.UUIDField(primary_key=True)
    title = models.CharField(max_length=225)
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(default=None)


class Message(models.Model):
    chat = models.ForeignKey(Chats, on_delete=models.CASCADE, related_name="messages")
    text = models.TextField()
    sender = models.CharField(choices=SENDER_ROLES, max_length=5, default="user")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


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
