import hashlib
from vector_store import get_collection
from embedder import embed_documents
from git_loader_full import fetch_repo_files_all_branches

def _hash(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", errors="ignore")).hexdigest()[:16]

def preprocess(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # collapse excessive blank lines
    while "\n\n\n\n" in text:
        text = text.replace("\n\n\n\n", "\n\n\n")
    return text.strip()

def chunk_lines(text: str, max_lines: int = 80, overlap: int = 10):
    lines = text.splitlines()
    out = []
    i = 0
    n = len(lines)
    while i < n:
        start = i
        end = min(i + max_lines, n)
        chunk = "\n".join(lines[start:end]).strip()
        if chunk:
            out.append((chunk, start + 1, end))
        i = end - overlap
        if i < 0: i = 0
        if end == n: break
    return out

def index_repo(repo_url: str, max_files_per_branch: int = 20):
    collection = get_collection()

    items = fetch_repo_files_all_branches(
        repo_url,
        max_files_per_branch=max_files_per_branch,
        max_chars_per_file=50000,
    )

    docs, metas, ids = [], [], []
    for branch, path, content in items:
        clean = preprocess(content)
        for idx, (chunk, sline, eline) in enumerate(chunk_lines(clean)):
            h = _hash(chunk)
            doc_id = f"{_hash(repo_url)}:{branch}:{path}:{idx}:{h}"
            ids.append(doc_id)
            docs.append(chunk)
            metas.append({
                "repo_url": repo_url,
                "branch": branch,
                "file_path": path,
                "start_line": sline,
                "end_line": eline,
            })

    # embed + upsert in batches
    batch = 24
    added = 0
    for i in range(0, len(docs), batch):
        d = docs[i:i+batch]
        m = metas[i:i+batch]
        _ids = ids[i:i+batch]
        embs = embed_documents(d)
        collection.upsert(ids=_ids, documents=d, metadatas=m, embeddings=embs)
        added += len(d)

    return {"files_seen": len(items), "chunks_added": added}
