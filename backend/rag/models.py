from django.db import models
from pgvector.django import VectorField
# Create your models here.

class Document(models.Model):
    title = models.CharField(max_length=255)          # PDF filename
    content = models.TextField()                       # the chunk text
    embedding = VectorField(dimensions=768)
    source_id = models.UUIDField(db_index=True)        # groups chunks of same PDF
    chunk_index = models.IntegerField()                # position within PDF
    created_at = models.DateTimeField(auto_now_add=True)