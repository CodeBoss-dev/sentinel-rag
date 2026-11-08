import chromadb
import requests
from pathlib import Path
from embedding import model_name

chroma_client = chromadb.PersistentClient(
    path=str(Path(__file__).parent / "chroma_db")
)
ollama_url = "http://localhost:11434/api/generate"


def setup_vector_db(result, embedding_data):
    collection = chroma_client.get_or_create_collection(
        name="baseline-" + model_name.replace("/", "-"),
        embedding_function=None,
        configuration={"hnsw": {"space": "cosine"}},
    )

    ids = ["id" + str(index) for index in range(len(result))]
    metadatas = []
    for data in result:
        metadata = data.copy()
        metadata.pop("content")
        metadatas.append(metadata)

    collection.upsert(
        ids=ids,
        embeddings=embedding_data,
        documents=[data["content"] for data in result],
        metadatas=metadatas,
    )

    # Remove leftover chunks when fewer documents are selected.
    old_ids = collection.get(include=[])["ids"]
    unused_ids = [item_id for item_id in old_ids if item_id not in ids]
    if unused_ids:
        collection.delete(ids=unused_ids)

    return collection


def retrieve_documents(collection, query_vector, top_k=5):
    if top_k < 1:
        raise ValueError("top_k must be at least 1.")

    return collection.query(
        query_embeddings=[query_vector],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )


def generation_model(query, provided_answer, model_name="llama3.2:3b"):
    context_parts = []
    for index, content in enumerate(provided_answer["documents"][0]):
        metadata = provided_answer["metadatas"][0][index]
        context_parts.append(
            f"[{index + 1}] {metadata['source']} "
            f"(sentence {metadata['sentence_number']})\n{content}"
        )
    context = "\n\n".join(context_parts)

    prompt = (
        "Answer the employee question using the company context below. "
        "Cite supporting context numbers such as [1]. "
        "If the context does not contain the answer, say so.\n\n"
        f"Company context:\n{context}\n\nEmployee question: {query}\nAnswer:"
    )

    response = requests.post(
        ollama_url,
        json={
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0, "seed": 42},
        },
        timeout=180,
    )
    response.raise_for_status()
    return response.json()["response"]
