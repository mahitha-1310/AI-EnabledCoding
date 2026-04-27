import json
from collections import Counter
from git_loader_full import fetch_repo_files_all_branches

# Reuse the chunking logic if it's in indexer.py; otherwise keep this local
def preprocess(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()

def chunk_lines(text: str, max_lines: int = 120, overlap: int = 20):
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

def main():
    repo_url = input("Repo URL: ").strip()
    prefix = input("Optional path prefix (press Enter for none): ").strip()
    include_prefixes = [prefix] if prefix else None

    items = fetch_repo_files_all_branches(
        repo_url,
        include_branches=None,
        include_prefixes=None,
        max_files_per_branch=50,
        max_chars_per_file=50000,
    )


    if not items:
        print("No files fetched.")
        return

    manifest_path = "index_manifest.jsonl"
    per_file = Counter()
    sizes = []
    total_chunks = 0

    with open(manifest_path, "w", encoding="utf-8") as f:
        for branch, path, content in items:
            clean = preprocess(content)
            chunks = chunk_lines(clean)
            per_file[path] += len(chunks)

            for idx, (chunk, sline, eline) in enumerate(chunks):
                rec = {
                    "repo_url": repo_url,
                    "branch": branch,
                    "file_path": path,
                    "chunk_index": idx,
                    "start_line": sline,
                    "end_line": eline,
                    "char_len": len(chunk),
                }
                f.write(json.dumps(rec) + "\n")
                total_chunks += 1
                sizes.append(len(chunk))

    print("\n✅ Chunking Report")
    print("Files fetched:", len(items))
    print("Total chunks:", total_chunks)
    print("Avg chunk chars:", round(sum(sizes)/max(1,len(sizes)), 1))
    print("Min chunk chars:", min(sizes) if sizes else 0)
    print("Max chunk chars:", max(sizes) if sizes else 0)

    print("\nTop 5 files by chunk count:")
    for p, c in per_file.most_common(5):
        print(f"  {c:>4}  {p}")

    print(f"\n✅ Manifest written: {manifest_path}")

if __name__ == "__main__":
    main()
