# Change this query to ask a different question.
query = "What is the approval process for purchasing a new software tool?"

import json
from pathlib import Path
from embedding import embedding, query_embedding, model_name
from rag import setup_vector_db, retrieve_documents, generation_model

folder = Path(__file__).parent
documents_raw = sorted((folder / "documents").glob("*.md"))
# documents_raw = [folder / "documents" / "injected_20_percent.md"]
# documents_raw = [folder / "documents" / "injected_40_percent.md"]
top_k = 5
answer_model = "llama3.2:3b"
output_file = folder / "baseline_result.json"


def aggregate_documents(files):
    chunked_data = []

    for document in files:
        with open(document, "r", encoding="utf-8") as file:
            content = file.read()

        metadata = {}
        if content.startswith("---\n"):
            _, header, content = content.split("---", 2)
            for line in header.strip().splitlines():
                key, value = line.split(":", 1)
                metadata[key.strip()] = value.strip()

        sentence_number = 0
        for line in content.splitlines():
            line = line.strip()

            # Each Markdown bullet is one chunk.
            if line.startswith("- "):
                sentence_number += 1
                chunked_data.append({
                    "source": document.name,
                    "sentence_number": sentence_number,
                    "content": line[2:].strip(),
                    "source_type": metadata.get("source_type", "wiki"),
                    "sender": metadata.get("sender", "synthetic"),
                    "role": metadata.get("role", "employee"),
                    "department": metadata.get("department", "general"),
                    "timestamp": metadata.get("timestamp", "2026-10-01T09:00:00Z"),
                    "trust_level": metadata.get("trust_level", "unknown"),
                    "access_level": metadata.get("access_level", "internal"),
                })

    return chunked_data


# Run the RAG pipeline in order.
result = aggregate_documents(documents_raw)
embedding_data = embedding(result)
collection = setup_vector_db(result, embedding_data)
query_vector = query_embedding(query)
retrieved_data = retrieve_documents(collection, query_vector, top_k)

print("Query:", query)
print("Indexed sentences:", len(result))

sources = []
for index, content in enumerate(retrieved_data["documents"][0]):
    metadata = retrieved_data["metadatas"][0][index]
    distance = retrieved_data["distances"][0][index]

    print(f"\n[{index + 1}] {metadata['source']}, sentence {metadata['sentence_number']}")
    print("Cosine distance:", round(distance, 3))
    print(content)

    sources.append({
        "id": retrieved_data["ids"][0][index],
        "text": content,
        "metadata": metadata,
        "distance": distance,
    })

answer = generation_model(query, retrieved_data, answer_model)
print("\nAnswer:\n", answer)

with open(output_file, "w", encoding="utf-8") as file:
    json.dump({
        "variant": "baseline",
        "question": query,
        "settings": {
            "embedding_model": model_name,
            "generation_model": answer_model,
            "top_k": top_k,
            "documents": [str(document.resolve()) for document in documents_raw],
        },
        "sources": sources,
        "answer": answer,
    }, file, indent=2)
