import os
from dotenv import load_dotenv
import cohere

load_dotenv()

api_key = os.getenv("CO_API_KEY")
if not api_key:
    raise RuntimeError("CO_API_KEY not found")

_co = cohere.Client(api_key)

def embed_documents(texts: list[str]) -> list[list[float]]:
    resp = _co.embed(
        texts=texts,
        model="embed-english-v3.0",
        input_type="search_document"
    )
    return resp.embeddings

def embed_query(text: str) -> list[float]:
    resp = _co.embed(
        texts=[text],
        model="embed-english-v3.0",
        input_type="search_query"
    )
    return resp.embeddings[0]