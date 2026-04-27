import time
from vector_store import get_collection
from embedder import embed_texts
from git_loader_full import fetch_repo_files_all_branches
from indexer import preprocess, chunk_lines

def batched(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i+n]

def main():
    repo_url = input("Repo URL: ").strip()
    col = get_collection()

    items = fetch_repo_files_all_branches(
        repo_url,
        include_branches=None,
        max_files_per_branch=10,
        max_chars_per_file=20000,
    )
    if not items:
        print("No files fetched.")
        return

    # Build chunk list
    docs, metas, ids = [], [], []
    for branch, path, content in items:
        clean = preprocess(content)
        for idx, (chunk, s, e) in enumerate(chunk_lines(clean, max_lines=120, overlap=20)):
            docs.append(chunk)
            metas.append({"repo_url": repo_url, "branch": branch, "file_path": path, "start_line": s, "end_line": e})
            ids.append(f"bench:{branch}:{path}:{idx}")

    print(f"\nChunks prepared: {len(docs)}")

    # Benchmark embedding + upsert
    batch_size = 64
    t0 = time.time()
    total = 0

    for d_batch, m_batch, id_batch in zip(batched(docs, batch_size), batched(metas, batch_size), batched(ids, batch_size)):
        t1 = time.time()
        embs = embed_texts(d_batch)
        t2 = time.time()

        col.upsert(ids=id_batch, documents=d_batch, metadatas=m_batch, embeddings=embs)
        t3 = time.time()

        print(f"Batch {total//batch_size + 1:>2}: embed={t2-t1:.2f}s  upsert={t3-t2:.2f}s  size={len(d_batch)}")
        total += len(d_batch)

    t_end = time.time()
    print("\n✅ Embedding benchmark complete")
    print("Total chunks embedded:", total)
    print("Total time (s):", round(t_end - t0, 2))

    # quick sanity query
    q = "entry point"
    q_emb = embed_texts([q])[0]
    res = col.query(query_embeddings=[q_emb], n_results=3, where={"repo_url": repo_url}, include=["metadatas","distances"])
    print("\nTop hits:")
    for meta, dist in zip(res["metadatas"][0], res["distances"][0]):
        print(dist, meta["file_path"], f'{meta.get("start_line")}-{meta.get("end_line")}')

if __name__ == "__main__":
    main()
