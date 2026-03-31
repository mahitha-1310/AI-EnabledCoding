from pathlib import Path
from typing import Any, Dict
from graders import ANALYSIS
from dotenv import load_dotenv
import streamlit as st
import zipfile
import shutil
import random
import json
import uuid
import io
import os

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
    def __init__(self):
        # Paths
        self.summary_path = os.path.join("logs", "summary.json")
        self.workshop_path = "workshop"
        self.prompts_path = "prompts"

        self.input_path =   os.path.join(self.workshop_path, "input")
        self.test_path =    os.path.join(self.workshop_path, "test")  
        self.editor_path =  os.path.join(self.workshop_path, "editor")
        self.testing_path = os.path.join(self.workshop_path, "testing")
        self.output_path =  os.path.join(self.workshop_path, "output")
        self.result_path =  os.path.join(self.workshop_path, "result")

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

PATH = _PathData()

class ElementIDManager():
    def __init__(self, minimum, maximum):
        self.element_ids = set()
        self.min = minimum
        self.max = maximum

    def get(self) -> int:
        length = len(self.element_ids)
        while length == len(self.element_ids):
            self.element_ids.add(random.randint(self.min, self.max))
        return self.element_ids[-1]

EID = ElementIDManager(1, 32767)

def get_path(path: str) -> Path:
    """Resolve a path relative to the EDITOR_PATH environment variable.

    If the path is already absolute, return it directly without prepending
    EDITOR_PATH — handles cases where INPUT_PATH / OUTPUT_PATH are full paths.
    """
    requested_path = Path(path)

    if requested_path.is_absolute():
        return requested_path

    tail = PATH.editor_path
    if tail is None:
        raise ValueError("`EDITOR_PATH` is not set. Please provide a valid directory path.")

    base_path = Path(tail)

    if requested_path.parts and requested_path.parts[0] == base_path.name:
        requested_path = Path(*requested_path.parts[1:])

    return base_path / requested_path

def transfer(source: str, destination: str) -> None:
    """
    Recursively copy *source* directory into *destination*, honouring
    comma-separated glob patterns in the IGNORE environment variable.
    """
    src_path = project_path(source)
    dst_path = project_path(destination)

    assert_dir(src_path)

    ignore_raw = os.getenv("IGNORE", "")
    patterns = [p.strip() for p in ignore_raw.split(",") if p.strip()]

    def _copy_recursive(src: Path, dst: Path) -> None:
        dst.mkdir(parents=True, exist_ok=True)
        with os.scandir(src) as entries:
            for entry in entries:
                src_item = Path(entry.path)
                dst_item = dst / entry.name

                if any(src_item.match(pattern) for pattern in patterns):
                    print(f"Excluded: {src_item.relative_to(src_path)}")
                    continue

                if entry.is_dir(follow_symlinks=False):
                    _copy_recursive(src_item, dst_item)
                elif entry.is_file(follow_symlinks=False):
                    shutil.copy2(src_item, dst_item)

    _copy_recursive(src_path, dst_path)

def write_files(file_list: list[str], target_dir: str) -> None:
    """Copy a flat list of files into *target_dir* using transfer primitives."""
    dst = project_path(target_dir)
    dst.mkdir(parents=True, exist_ok=True)
    for file_path in file_list:
        src = Path(file_path)
        if src.is_file():
            shutil.copy2(src, dst)

def clear_directory(directory: str) -> bool:
    """Remove all contents of *directory* without deleting the directory itself."""
    path = Path(directory)
    if not path.exists():
        return False
    for item in path.iterdir():
        if item.is_file() or item.is_symlink():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)
    return True

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
    if output_path is not Path:
        output_path = Path(output_path)
    assert_exists(output_path)

    try:
        for stage, functions in ANALYSIS.items():
            path = output_path / stage / PATH.summary_path
            with open(path, "r", encoding="utf-8") as file:
                success = functions["function"].invoke(json.load(file))
                if not success:
                    accept_program = False
                    if "message" in functions:
                        accept_program = functions["fail_case"].invoke(functions["message"])
                    else:
                        accept_program = functions["fail_case"].invoke()

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

@st.dialog("LLM Attempt Limit Reached")
def request_retry(num_attempts: int) -> bool:
    """Ask user if they should continue with prompting the llm."""

    st.write("How would you like to proceed?")
    choice = st.radio(
        label="Select an option:",
        options=[
            "Stop Attempting", 
            "Attempt One More Time", 
            f"Attempt {num_attempts} More Times"
        ],
        index=0 # Default selection: Stop Attempting
    )
    
    if st.button("Confirm", disabled=choice is None):
        st.session_state.confirmed_choice = choice
        st.rerun()
    
    if choice == "Attempt One More Time":
        return 1
    elif choice == f"Attempt {num_attempts} More Times":
        return num_attempts
    else:
        return 0