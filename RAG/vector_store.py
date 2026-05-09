import os
import chromadb
from chromadb.config import Settings

def get_collection():
    mode = os.getenv("CHROMA_MODE", "local").lower()
    name = os.getenv("CHROMA_COLLECTION", "boeingagent_kb")

    if mode == "server":
        host = os.getenv("CHROMA_HOST", "localhost")
        port = int(os.getenv("CHROMA_PORT", "8000"))
        client = chromadb.HttpClient(host=host, port=port)
    else:
        chroma_dir = os.getenv("CHROMA_DIR", ".chroma")
        client = chromadb.PersistentClient(
            path=chroma_dir,
            settings=Settings(anonymized_telemetry=False),
        )

    return client.get_or_create_collection(name=name)
    