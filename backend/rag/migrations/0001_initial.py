import django.db.models.deletion
import pgvector.django.vector
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("chats", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql="CREATE EXTENSION IF NOT EXISTS vector;",
            reverse_sql="DROP EXTENSION IF EXISTS vector;",
        ),
        migrations.CreateModel(
            name="Document",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=255)),
                ("content", models.TextField()),
                ("embedding", pgvector.django.vector.VectorField(dimensions=1024)),
                ("source_id", models.UUIDField(db_index=True)),
                ("chunk_index", models.IntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "chat",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="documents",
                        to="chats.chats",
                    ),
                ),
            ],
            options={
                "db_table": "rag_document",
            },
        ),
        migrations.RunSQL(
            sql="""
            CREATE OR REPLACE FUNCTION public.match_documents(query_embedding vector, match_count integer)
             RETURNS TABLE(id bigint, content text, source_id uuid, similarity double precision)
             LANGUAGE sql
             STABLE
            AS $function$
              select id, content, source_id, 1 - (embedding <=> query_embedding) as similarity
              from rag_document
              order by embedding <=> query_embedding
              limit match_count;
            $function$;
            """,
            reverse_sql="DROP FUNCTION IF EXISTS public.match_documents(vector, integer);",
        ),
    ]
