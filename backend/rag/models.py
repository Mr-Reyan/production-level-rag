from django.db import models
from pgvector.django import VectorField
from chats.models import Chats


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

    class Meta:
        db_table = "rag_document"

    def __str__(self):
        return f"{self.title} - Chunk {self.chunk_index}"
