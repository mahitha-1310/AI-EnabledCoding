from pathlib import Path
from typing import Any, Dict
from graders import ANALYSIS
from dotenv import load_dotenv
import streamlit as st, zipfile, shutil, json, uuid, io, os

_STREAM_KEYS = {"stdout", "stderr"}

def fmt_field(key: str, value: Any) -> str:
    """Format a single log field for human-readable .log files.

    - cmd:    each argument on its own indented line
    - stdout/stderr: content on next line, wrapped in --- dividers
    - other:  key: value on one line
    """
    value = str(value) if not isinstance(value, str) else value
    if key == "cmd":
        args = "  " + "\n  ".join(value.split())
        return f"cmd:\n{args}\n\n"
    elif key in _STREAM_KEYS:
        content = value.strip()
        body = f"\n{'-'*60}\n{content}\n{'-'*60}\n" if content else "\n(empty)\n"
        return f"{key}:{body}\n"
    else:
        return f"{key}: {value}\n\n"

def assert_exists(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Path not found: {path}")

def assert_dir(path: Path) -> None:
    assert_exists(path)
    if not path.is_dir():
        raise ValueError(f"Path is not a directory: {path}")

def assert_file(path: Path) -> None:
    assert_exists(path)
    if not path.is_file():
        raise ValueError(f"Path is not a file: {path}")

def only_folders(path: str) -> bool:
    return os.path.exists(path) and all(os.path.isdir(os.path.join(path, item)) for item in os.listdir(path))

def read_path(file_path: str) -> str:
    """Read and return the text content of a file, resolved relative to the project root."""
    path = Path(file_path)
    if not path.is_absolute():
        path = Path(__file__).parent / path
    assert_exists(path)
    return path.read_text(encoding="utf-8")

def project_path(path: str) -> Path:
    """Resolve a path relative to the project root (directory containing utils.py).
    
    Use this for INPUT_PATH, OUTPUT_PATH, and other env vars that are siblings
    of EDITOR_PATH, not children of it.
    """
    p = Path(path)
    if p.is_absolute():
        return p
    return Path(__file__).parent / p

class _PathData:
    def __init__(self, user_id: str = None):
        self.summary_path = os.path.join("logs", "summary.json")
        self.prompts_path = "prompts"
        self.workshop_path = "workshop"
        
        if user_id:
            user_session_path = os.path.join("sessions", user_id)
        else:
            user_session_path = self.workshop_path

        self.input_path =   os.path.join(user_session_path, "input")
        self.test_path =    os.path.join(user_session_path, "test")
        self.editor_path =  os.path.join(user_session_path, "editor")
        self.testing_path = os.path.join(user_session_path, "testing")
        self.output_path =  os.path.join(user_session_path, "output")
        self.result_path =  os.path.join(user_session_path, "result")

        for path in [
            self.input_path, self.test_path, self.editor_path,
            self.testing_path, self.output_path, self.result_path
        ]:
            os.makedirs(project_path(path), exist_ok=True)

        SYSTEM_PROMPT =        os.path.join(self.prompts_path, "system_prompt.md")
        FEEDBACK_PROMPT =      os.path.join(self.prompts_path, "feedback_prompt.md")
        STRUCTURE_PROMPT =     os.path.join(self.prompts_path, "structure_prompt.md")
        SUMMARIZATION_PROMPT = os.path.join(self.prompts_path, "summarization_prompt.md")

        # Prompts
        self.system_message = read_path(SYSTEM_PROMPT)
        self.feedback_message = read_path(FEEDBACK_PROMPT)
        self.structure_message = read_path(STRUCTURE_PROMPT)
        self.summarization_message = read_path(SUMMARIZATION_PROMPT)
    
    def make_dir(self, envvar: str):
        if not os.getenv(envvar):
            load_dotenv()
        path = os.getenv(envvar)
        os.makedirs(path, exist_ok=True)
        return path

def get_user_paths(user_id: str = None) -> _PathData:
    """Get or create path data for a specific user session."""
    if user_id is None:
        return _PathData()
    return _PathData(user_id)

def get_global_prompts() -> _PathData:
    global _global_prompts
    if _global_prompts is None:
        _global_prompts = _PathData()
    return _global_prompts

_global_prompts = None

def get_path(path: str) -> Path:
    """Resolve a path relative to the EDITOR_PATH environment variable.

    If the path is already absolute, return it directly without prepending
    EDITOR_PATH — handles cases where INPUT_PATH / OUTPUT_PATH are full paths.
    """
    requested_path = Path(path)

    if requested_path.is_absolute():
        return requested_path

    tail = get_global_prompts().editor_path
    if tail is None:
        raise ValueError("`EDITOR_PATH` is not set. Please provide a valid directory path.")

    base_path = Path(tail)

    if requested_path.parts and requested_path.parts[0] == base_path.name:
        requested_path = Path(*requested_path.parts[1:])

    return base_path / requested_path

def _copy_recursive(src: Path, dst: Path, patterns: list[str]) -> None:
    try:
        dst.mkdir(parents=True, exist_ok=True)
        with os.scandir(src) as entries:
            for entry in entries:
                src_item = Path(entry.path)
                dst_item = dst / entry.name

                if any(src_item.match(pattern) for pattern in patterns):
                    continue

                try:
                    if entry.is_dir(follow_symlinks=False):
                        _copy_recursive(src_item, dst_item)
                    elif entry.is_file(follow_symlinks=False):
                        shutil.copy2(src_item, dst_item)
                except Exception as e:
                    print(f"Warning: Failed to copy {src_item.name}: {e}")
                    continue
    except Exception as e:
        print(f"Error creating directory {dst}: {e}")
        raise

def transfer(source: str, destination: str) -> None:
    """
    Recursively copy *source* directory into *destination*, honouring
    comma-separated glob patterns in the IGNORE environment variable.
    
    Raises:
        FileNotFoundError: If source directory doesn't exist
        Exception: If copy operation fails
    """
    src_path = project_path(source)
    dst_path = project_path(destination)

    assert_dir(src_path)

    ignore_raw = os.getenv("IGNORE", "")
    patterns = [p.strip() for p in ignore_raw.split(",") if p.strip()]

    try:
        _copy_recursive(src_path, dst_path, patterns)
    except Exception as e:
        print(f"Transfer failed from {source} to {destination}: {e}")
        raise

def write_files(file_list: list[str], target_dir: str) -> None:
    """Copy a flat list of files into *target_dir* using transfer primitives."""
    dst = project_path(target_dir)
    dst.mkdir(parents=True, exist_ok=True)
    for file_path in file_list:
        src = Path(file_path)
        if src.is_file():
            shutil.copy2(src, dst)

def clear_directory(directory: str) -> bool:
    """Remove all contents of *directory* without deleting the directory itself.
    
    Returns True if successful, False otherwise. Handles errors gracefully.
    """
    path = Path(directory)
    if not path.exists():
        return False
    
    try:
        for item in path.iterdir():
            try:
                if item.is_file() or item.is_symlink():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            except Exception as e:
                print(f"Failed to delete {item}: {e}")
                continue
        return True
    except Exception as e:
        print(f"Error clearing directory {directory}: {e}")
        return False

def clear_directories(directories: list[str]) -> Dict[str, bool]:
    """Clear multiple directories, returning a success map."""
    return {d: clear_directory(d) for d in directories}

def build_tree(path: Path, max_depth: int | None, current_depth: int = 0) -> list:
    """Recursively build a directory tree structure."""
    items = []
    if max_depth is not None and current_depth >= max_depth:
        return items

    try:
        for item in sorted(path.iterdir()):
            stat = item.stat()
            entry = {
                "name": item.name,
                "path": str(item),
                "type": "directory" if item.is_dir() else "file",
            }
            if item.is_file():
                entry["size"] = stat.st_size
                entry["modified"] = stat.st_mtime
            elif item.is_dir():
                entry["children"] = build_tree(item, max_depth, current_depth + 1)
            items.append(entry)
    except PermissionError:
        items.append({"error": "PermissionError"})

    return items


def list_dir(directory: str, max_depth: int | None = None) -> Dict[str, Any]:
    """
    List all files and directories in a directory structure.

    Args:
        directory: The directory to list
        max_depth: Maximum depth to traverse (None for unlimited)

    Returns:
        Dictionary containing the directory structure
    """
    dir_path = project_path(directory)
    assert_dir(dir_path)

    return {
        "directory": str(dir_path),
        "structure": build_tree(path=dir_path, max_depth=max_depth),
    }

def grade(output_path: Path) -> bool:
    if not isinstance(output_path, Path):
        output_path = Path(output_path)
    assert_exists(output_path)

    try:
        for stage, functions in ANALYSIS.items():
            path = output_path / "logs" / stage / "summary.json"
            with open(path, "r", encoding="utf-8") as file:
                success = functions["function"](json.load(file))
                if not success:
                    accept_program = False
                    if "message" in functions:
                        accept_program = functions["fail_case"](functions["message"])
                    else:
                        accept_program = functions["fail_case"](None)

                    if not accept_program:
                        return False
    except Exception as e:
        print(f"{type(e)}: {e.__traceback__}")
        print("An internal grader failure has occurred. DO NOT assume code product meets standards!")

    return True

def create_zip(directory: str) -> io.BytesIO:
    """Create an in-memory zip from a directory's contents."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for root, _dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, directory)
                zip_file.write(file_path, arcname)
    zip_buffer.seek(0)
    return zip_buffer

def generate_user_id() -> str:
    """Return a stable user ID, persisted in Streamlit session state and URL params."""
    if "user_id" not in st.session_state:
        if "uid" in st.query_params:
            st.session_state.user_id = st.query_params["uid"]
        else:
            new_id = str(uuid.uuid4())
            st.session_state.user_id = new_id
            st.query_params["uid"] = new_id
    return st.session_state.user_id