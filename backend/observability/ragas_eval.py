from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_ollama import ChatOllama, OllamaEmbeddings
from datasets import Dataset
import os
os.environ["OPENAI_API_KEY"] = "sk-fake"
judge_llm = ChatOllama(model='llama3.2:3b', base_url="http://localhost:11434")
judge_embeddings = OllamaEmbeddings(model="nomic-embed-text", base_url="http://localhost:11434")
ragas_llm = LangchainLLMWrapper(judge_llm)
ragas_embeddings = LangchainEmbeddingsWrapper(judge_embeddings)

eval_data = {
    "user_input": ["What is the purpose of Life?"],
    "response": ["The purpose of life is a philosophical question..."],
    "retrieved_contexts": [["Life is a characteristic...", "Philosophy asks..."]],
    "reference": ["The purpose of life is subjective."] # Optional, but needed for recall/accuracy metrics
}

eval_dataset = Dataset.from_dict(eval_data)

result = evaluate(
    dataset=eval_dataset,
    metrics=[
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall,
    ],
    llm=ragas_llm,
    embeddings=ragas_embeddings,
)

print(result)
print(f"Answer Relevancy: {result['answer_relevancy']}")
print(f"Context Precision: {result['context_precision']}")
print(f"Context Recall: {result['context_recall']}")
print(f"Faithfulness: {result['faithfulness']}")