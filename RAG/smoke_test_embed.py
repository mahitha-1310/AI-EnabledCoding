import os
from vector_store import get_collection
from embedder import embed_documents, embed_query
from git_loader_full import fetch_repo_files_all_branches

def main():
    repo_url = input("Paste GitHub repo URL: ").strip()

    # small for first test
    items = fetch_repo_files_all_branches(
        repo_url,
        include_branches=None,
        max_files_per_branch=3,
        max_chars_per_file=4000,
    )

    if not items:
        print("No files fetched.")
        return

    branch, path, content = items[0]
    text = content[:800]  # tiny sample just to see embeddings output

    # 1) embeddings output
    emb = embed_documents([text])[0]
    print("\n✅ Embedding generated")
    print("Vector length:", len(emb))
    print("First 8 values:", emb[:8])

    # 2) store into Chroma
    col = get_collection()
    doc_id = f"smoke:{branch}:{path}"
    col.upsert(
        ids=[doc_id],
        documents=[text],
        metadatas=[{"repo_url": repo_url, "branch": branch, "file_path": path}],
        embeddings=[emb],
    )
    print("\n✅ Upserted 1 chunk into Chroma:", doc_id)

    # 3) query Chroma
    q = "main entry point"  # sample query
    q_emb = embed_query([q])
    res = col.query(query_embeddings=[q_emb], n_results=1, include=["documents", "metadatas", "distances"])
    print("\n✅ Query result")
    print("Distance:", res["distances"][0][0])
    print("Meta:", res["metadatas"][0][0])
    print("Doc preview:", res["documents"][0][0][:200])

if __name__ == "__main__":
    main()
