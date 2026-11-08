from sentence_transformers import SentenceTransformer

model_name = "sentence-transformers/all-MiniLM-L6-v2"
model = SentenceTransformer(model_name)


def embedding(raw_text):
    texts = [text["content"] for text in raw_text]
    if not texts:
        raise ValueError("No Markdown bullet sentences were found.")

    return model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=False,
    ).tolist()


def query_embedding(query):
    return model.encode(
        [query],
        normalize_embeddings=True,
        show_progress_bar=False,
    ).tolist()[0]
