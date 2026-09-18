from django.db import migrations

CREATE_MATCH_DOCUMENTS_SQL = """
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
"""

DROP_MATCH_DOCUMENTS_SQL = """
DROP FUNCTION IF EXISTS public.match_documents(vector, integer);
"""

class Migration(migrations.Migration):
    dependencies = [
        ("rag", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql=CREATE_MATCH_DOCUMENTS_SQL,
            reverse_sql=DROP_MATCH_DOCUMENTS_SQL,
        )
    ]
