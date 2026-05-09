import requests
from typing import List, Tuple

# Supported code extensions( can be extended later)
CODE_EXTENSIONS = (
    ".py", ".js", ".ts", ".java", ".cpp", ".c", ".cs", ".go", ".rs", ".ipynb",
    ".cob", ".cbl", ".cpy",                  # COBOL
    ".f", ".for", ".f90", ".f95", ".f03", ".f08",  # FORTRAN
    ".adb", ".ads",                          # Ada
    ".vhd", ".vhdl",                         # VHDL
    ".v", ".sv",                             # Verilog/SystemVerilog
    ".m", ".slx", ".mdl"                     # MATLAB / Simulink
)


def _to_api_url(repo_url: str) -> str:
    
    # Convert GitHub repo URL to API URL for content listing.

    if repo_url.endswith("/"):
        repo_url = repo_url[:-1]
    repo_url = repo_url.replace(".git", "")
    if "github.com/" not in repo_url:
        raise ValueError("This is not a valid GitHub repository URL.")
    owner_repo = repo_url.split("github.com/")[1]
    return f"https://api.github.com/repos/{owner_repo}/contents"


def fetch_repo_files(repo_url: str, max_files: int = 20, max_chars_per_file: int = 8000) -> List[Tuple[str, str]]:
    # Fetch up to `max_files` code files from the repo's root directory.
    # Supports both modern and high-assurance system languages.
    # Returns a list of (filename, content).

    api_url = _to_api_url(repo_url)
    resp = requests.get(api_url)

    if resp.status_code != 200:
        raise RuntimeError(f"GitHub API error {resp.status_code}: {resp.text}")

    items = resp.json()
    files = []

    for item in items:
        if item.get("type") == "file":
            name = item["name"]
            # Filter by all supported extensions
            if name.lower().endswith(CODE_EXTENSIONS):
                download_url = item["download_url"]
                file_resp = requests.get(download_url)
                if file_resp.status_code == 200:
                    content = file_resp.text[:max_chars_per_file]
                    files.append((name, content))
                    if len(files) >= max_files:
                        break
    return files

