# <your_app>/management/commands/evaluate_chat.py

import os
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, LLMContextPrecisionWithoutReference
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_ollama import ChatOllama, OllamaEmbeddings

from langfuse import get_client

# Import your actual models — adjust the app name
from chats.models import Message  # <-- adjust import path
from rag.models import Document

# RAGAS still tries to touch OpenAI for some internal defaults. Fake key silences it.
from ragas import RunConfig

run_config = RunConfig(
    max_workers=3,       # Ollama cloud likely allows ~3-4 concurrent
    timeout=180,
)

os.environ["RAGAS_DO_NOT_TRACK"] = "true"
os.environ["RAGAS_ANALYTICS_ENABLED"] = "false"
os.environ["RAGAS_TELEMETRY_ENABLED"] = "false"
os.environ.setdefault("OPENAI_API_KEY", "sk-fake")


class Command(BaseCommand):
    help = "Run RAGAS evaluation on recent AI messages and push scores to Langfuse."

    def add_arguments(self, parser):
        parser.add_argument("--chat-id", type=str, default=None,
                            help="Evaluate only this chat. Omit to evaluate the N most recent chats.")
        parser.add_argument("--limit", type=int, default=20,
                            help="Max number of AI messages to evaluate (default 20).")
        parser.add_argument("--judge-model", type=str, default="llama3.2:3b",
                            help="Ollama model used as RAGAS judge.")
        parser.add_argument("--embed-model", type=str, default="nomic-embed-text",
                            help="Ollama model used for RAGAS embeddings.")
        parser.add_argument("--ollama-url", type=str, default="http://localhost:11434")
        parser.add_argument("--dry-run", action="store_true",
                            help="Build and print the dataset, but do not call RAGAS or Langfuse.")

    def handle(self, *args, **options):
        
        context_precision = LLMContextPrecisionWithoutReference()
        chat_id = options["chat_id"]
        limit = options["limit"]
        dry_run = options["dry_run"]

        # ---- 1. Fetch candidate AI messages ----
        qs = Message.objects.filter(sender="ai").exclude(retrieved_chunk_ids=[]).order_by("-created_at")
        if chat_id:
            qs = qs.filter(chat_id=chat_id)
        msgs = list(qs[:limit])

        if not msgs:
            raise CommandError("No AI messages with retrieved chunks found. Run some queries first.")

        self.stdout.write(self.style.NOTICE(f"Evaluating {len(msgs)} AI messages..."))

        # ---- 2. Build RAGAS dataset ----
        rows = {"user_input": [], "response": [], "retrieved_contexts": [], "reference": []}
        trace_ids = []

        for ai_msg in msgs:
            # Find the question that produced this answer:
            # The user message right before this AI message in the same chat.
            user_msg = (
                Message.objects
                .filter(chat=ai_msg.chat, sender="user", created_at__lt=ai_msg.created_at)
                .order_by("-created_at")
                .first()
            )
            if not user_msg:
                continue

            # Fetch the retrieved chunks by ID (fresh content from rag_document)
            chunk_ids = ai_msg.retrieved_chunk_ids or []
            docs = Document.objects.filter(id__in=chunk_ids)
            # Preserve order as stored (RagDocument filter doesn't preserve order)
            by_id = {d.id: d for d in docs}
            contexts = [by_id[cid].content for cid in chunk_ids if cid in by_id]

            if not contexts:
                self.stdout.write(self.style.WARNING(
                    f"Skipping msg {ai_msg.id}: no chunk content found for IDs {chunk_ids}"
                ))
                continue

            rows["user_input"].append(user_msg.text)
            rows["response"].append(ai_msg.text)
            rows["retrieved_contexts"].append(contexts)
            rows["reference"].append("")   # unused by the reference-free metrics below
            trace_ids.append(ai_msg.trace_id or "")

        if not rows["user_input"]:
            raise CommandError("Nothing to evaluate after filtering.")

        dataset = Dataset.from_dict(rows)
        self.stdout.write(self.style.SUCCESS(
            f"Dataset built: {len(rows['user_input'])} rows, "
            f"{len(trace_ids)} trace IDs captured."
        ))

        if dry_run:

            for i in range(min(3, len(rows["user_input"]))):
                self.stdout.write(f"\n{'='*60}")
                self.stdout.write(f"ROW {i}")
                self.stdout.write(f"Q: {rows['user_input'][i]}")
                self.stdout.write(f"A: {rows['response'][i][:200]}")
                self.stdout.write(f"Contexts: {len(rows['retrieved_contexts'][i])}")
                for j, c in enumerate(rows["retrieved_contexts"][i]):
                    self.stdout.write(f"  [{j}] len={len(c)} chars, preview: {c[:150]!r}")
            self.stdout.write(self.style.NOTICE("Dry run — printing dataset sample:"))
            self.stdout.write(str(dataset[0]))
            return

        # ---- 3. Wire RAGAS to local Ollama ----
        judge_llm = ChatOllama(model=options["judge_model"], base_url=options["ollama_url"])
        judge_emb = OllamaEmbeddings(model=options["embed_model"], base_url=options["ollama_url"])

        # ---- 4. Run RAGAS ----
        # Only reference-free metrics — avoids needing gold answers.
        result = evaluate(
            dataset=dataset,
            metrics=[faithfulness, answer_relevancy, context_precision],
            llm=LangchainLLMWrapper(judge_llm),
            embeddings=LangchainEmbeddingsWrapper(judge_emb),
            run_config=run_config,
        )

        df = result.to_pandas()
        self.stdout.write(f"DEBUG: df columns = {list(df.columns)}")
        self.stdout.write(self.style.SUCCESS("\nAggregate scores:"))
        for metric in ["faithfulness", "answer_relevancy", "llm_context_precision_without_reference"]:
            if metric in df.columns:
                self.stdout.write(f"  {metric}: {df[metric].mean():.4f}")


        self.stdout.write(self.style.NOTICE("\nPer-row breakdown:"))
        for i, row in df.iterrows():
            ui = rows["user_input"][i][:55].replace("\n", " ")
            cp = row.get("llm_context_precision_without_reference", float("nan"))
            fa = row.get("faithfulness", float("nan"))
            ar = row.get("answer_relevancy", float("nan"))
            self.stdout.write(f"  [{i:2d}] cp={cp:.3f}  fa={fa:.3f}  ar={ar:.3f}  Q: {ui!r}")
            
        # ---- 5. Push per-row scores back to Langfuse ----
        langfuse = get_client()
        pushed = 0

        for i, trace_id in enumerate(trace_ids):
            if not trace_id:
                continue
            row = df.iloc[i]
            metric_names = [m.name for m in [faithfulness, answer_relevancy, context_precision]]
            for metric_name in metric_names:
                if metric_name in df.columns and row[metric_name] == row[metric_name]:
                    langfuse.create_score(
                        trace_id=trace_id,
                        name=metric_name,
                        value=float(row[metric_name]),
                        data_type="NUMERIC",
                        comment="RAGAS eval (offline)",
                    )
            pushed += 1

        langfuse.flush()
        self.stdout.write(self.style.SUCCESS(f"Pushed scores for {pushed} traces to Langfuse."))