from pathlib import Path
from typing import Any, Dict
from graders import ANALYSIS
import streamlit as st
import shutil
import uuid
import zipfile
import io
import json
import os

SUMMARY_PATH = os.path.join("logs", "summary.json")

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

def get_path(path: str) -> Path:
    """Resolve a path relative to the EDITOR_PATH environment variable."""
    tail = os.getenv("EDITOR_PATH")
    if tail is None:
        raise ValueError("`EDITOR_PATH` is not set. Please provide a valid directory path.")

    base_path = Path(tail)
    requested_path = Path(path)

    if requested_path.parts and requested_path.parts[0] == base_path.name:
        requested_path = Path(*requested_path.parts[1:])

    return base_path / requested_path

def read_path(file_path: str) -> str:
    """Read and return the text content of a file."""
    path = get_path(file_path)
    assert_exists(path)
    return path.read_text(encoding="utf-8")

def transfer(source: str, destination: str) -> None:
    """
    Recursively copy *source* directory into *destination*, honouring
    comma-separated glob patterns in the IGNORE environment variable.
    """
    src_path = get_path(source)
    dst_path = get_path(destination)

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
    dst = get_path(target_dir)
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
    dir_path = get_path(directory)
    assert_dir(dir_path)

    return {
        "directory": str(dir_path),
        "structure": build_tree(path=dir_path, max_depth=max_depth),
    }

def grade(output_path: Path) -> bool:
    assert_exists(output_path)

    try:
        for stage, functions in ANALYSIS.items():
            path = output_path / stage / SUMMARY_PATH
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