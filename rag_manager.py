from chromadb.api.models.Collection import Collection
from rag.vector_store import get_collection
from rag.embedder import embed_texts
from rag.git_loader_full import fetch_repo_files_all_branches
from rag.indexer import preprocess, chunk_lines

def embed_repo(collection: Collection, repo_url: str, batch_size: int = 64):

    # 1. Fetch all files across all branches
    items = fetch_repo_files_all_branches(
        repo_url,
        include_branches=None,   # None = all branches; or pass ["main", "dev"]
        max_files_per_branch=100,
        max_chars_per_file=50000,
    )

    # 2. Chunk each file into overlapping line windows
    docs, metas, ids = [], [], []
    for branch, path, content in items:
        clean = preprocess(content)
        for idx, (chunk, start, end) in enumerate(chunk_lines(clean, max_lines=120, overlap=20)):
            docs.append(chunk)
            metas.append({
                "repo_url": repo_url,
                "branch": branch,
                "file_path": path,
                "start_line": start,
                "end_line": end,
            })
            ids.append(f"{branch}:{path}:{idx}")

    # 3. Embed and upsert in batches
    for i in range(0, len(docs), batch_size):
        batch_docs  = docs[i:i+batch_size]
        batch_metas = metas[i:i+batch_size]
        batch_ids   = ids[i:i+batch_size]

        embeddings = embed_texts(batch_docs)
        collection.upsert(
            ids=batch_ids,
            documents=batch_docs,
            metadatas=batch_metas,
            embeddings=embeddings,
        )
        print(f"Upserted {i + len(batch_docs)}/{len(docs)} chunks")

    print(f"Done. {len(docs)} chunks indexed from {repo_url}")