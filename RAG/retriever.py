from typing import List, Dict, Any

from rag.vector_store import get_collection
from rag.embedder import embed_query

class RAGRetriever:
    def __init__(self) -> None:
        self.collection = get_collection()
    
    def retrieve(self, query: str, k: int) -> List[Dict[str, Any]]:
        q_emb = embed_query(query)

        results = self.collection.query(
            query_embeddings=[q_emb],
            n_results=k,
            include=["documents", "metadatas", "distances"]
        )

        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        retrieved: List[Dict[str, Any]] = []

        for doc, meta, dist in zip(docs, metas, distances):
            meta = meta or {}

            retrieved.append({
                "file_path": meta.get("file_path", "unknown_file"),
                "branch": meta.get("branch", "unknown_branch"),
                "start_line": meta.get("start_line", "?"),
                "end_line": meta.get("end_line", "?"),
                "repo_url": meta.get("repo_url", ""),
                "distance": dist,
                "document": doc
            })

        return retrieved