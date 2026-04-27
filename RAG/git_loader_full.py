import os
import base64
import requests
from typing import List, Tuple, Dict, Optional

CODE_EXTENSIONS = (
    ".c", ".h", ".py", ".js", ".ts", ".java", ".cpp", ".c", ".cs", ".go", ".rs", ".ipynb",
    ".cob", ".cbl", ".cpy",
    ".f", ".for", ".f90", ".f95", ".f03", ".f08",
    ".adb", ".ads",
    ".vhd", ".vhdl",
    ".v", ".sv",
    ".m", ".slx", ".mdl"
)

IGNORE_PATH_PARTS = (".git/", "node_modules/", "dist/", "build/", ".venv/", "__pycache__/")

def _parse_owner_repo(repo_url: str) -> str:
    repo_url = repo_url.strip().rstrip("/").replace(".git", "")
    if "github.com/" not in repo_url:
        raise ValueError("Not a valid GitHub repo URL.")
    return repo_url.split("github.com/")[1]  # owner/repo

def _headers() -> Dict[str, str]:
    tok = (os.getenv("GITHUB_TOKEN") or "").strip()
    h = {"Accept": "application/vnd.github+json"}

    # Attach only if token looks valid; otherwise don't send auth at all.
    if tok.startswith(("ghp_", "github_pat_")):
        h["Authorization"] = f"Bearer {tok}"

    return h


def list_branches(repo_url: str) -> List[str]:
    owner_repo = _parse_owner_repo(repo_url)
    url = f"https://api.github.com/repos/{owner_repo}/branches?per_page=100"
    r = requests.get(url, headers=_headers(), timeout=30)
    r.raise_for_status()
    print("branches status:", r.status_code, r.text[:120])
    return [b["name"] for b in r.json()]

def get_default_branch(repo_url: str) -> str:
    owner_repo = _parse_owner_repo(repo_url)
    url = f"https://api.github.com/repos/{owner_repo}"
    r = requests.get(url, headers=_headers(), timeout=30)
    r.raise_for_status()
    return r.json().get("default_branch", "main")


def list_tree_paths(repo_url: str, branch: str) -> List[str]:
    """
    Uses git trees API with recursive=1 (fast) to get all file paths.
    """
    owner_repo = _parse_owner_repo(repo_url)

    # Get branch SHA
    b_url = f"https://api.github.com/repos/{owner_repo}/branches/{branch}"
    b = requests.get(b_url, headers=_headers(), timeout=30)
    b.raise_for_status()
    sha = b.json()["commit"]["commit"]["tree"]["sha"]

    # Get recursive tree
    t_url = f"https://api.github.com/repos/{owner_repo}/git/trees/{sha}?recursive=1"
    t = requests.get(t_url, headers=_headers(), timeout=60)
    t.raise_for_status()

    paths = []
    for item in t.json().get("tree", []):
        if item.get("type") != "blob":
            continue
        p = item.get("path", "")
        if any(part in p for part in IGNORE_PATH_PARTS):
            continue
        if p.lower().endswith(CODE_EXTENSIONS):
            paths.append(p)
    return paths

def fetch_file_content(repo_url: str, branch: str, path: str, max_chars: int = 50000) -> Optional[str]:
    owner_repo = _parse_owner_repo(repo_url)
    c_url = f"https://api.github.com/repos/{owner_repo}/contents/{path}?ref={branch}"
    r = requests.get(c_url, headers=_headers(), timeout=30)

    if r.status_code != 200:
        return None

    data = r.json()
    if data.get("encoding") == "base64":
        raw = base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
    else:
        # fallback
        raw = requests.get(data.get("download_url"), headers=_headers(), timeout=30).text

    return raw[:max_chars]

def fetch_repo_files_all_branches(
    repo_url: str,
    max_files_per_branch: int = 500,
    max_chars_per_file: int = 50000,
    include_branches: Optional[List[str]] = None,
    include_prefixes: Optional[List[str]] = None, 
) -> List[Tuple[str, str, str]]:
    """
    Returns list of (branch, path, content)

    """
    
    # ✅ If user didn't specify branches, use repo default branch
    if not include_branches:
        include_branches = [get_default_branch(repo_url)]

    branches = list_branches(repo_url)
    branches = [b for b in branches if b in include_branches]

    # ✅ Fallback: if filtering removed everything, fall back to default branch
    if not branches:
        branches = [get_default_branch(repo_url)]
    
    branches = list_branches(repo_url)
    if include_branches:
        branches = [b for b in branches if b in include_branches]

    results: List[Tuple[str, str, str]] = []

    for branch in branches:
        paths = list_tree_paths(repo_url, branch)

        if include_prefixes:
            paths = [p for p in paths if any(p.startswith(pref) for pref in include_prefixes)]

        paths = paths[:max_files_per_branch]

        for p in paths:
            c = fetch_file_content(repo_url, branch, p, max_chars=max_chars_per_file)
            if c and c.strip():
                results.append((branch, p, c))

    return results
