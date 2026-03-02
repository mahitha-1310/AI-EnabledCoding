import os
from pathlib import Path
import shutil
from typing import Any, Dict
import uuid
import streamlit as st
import zipfile
import io
import json

SUMMARY_PATH = os.path.join("logs", "summary.json")

def grade(output_path: str):

    if not output_path.exists():
        raise FileNotFoundError(f"Path not found: {output_path}")

    from graders import ANALYSIS

    try:
        for stage, functions in ANALYSIS.items():
            path = os.path.join(output_path, stage, SUMMARY_PATH)
            with open(path, 'r', encoding='utf-8') as file:
                success = functions["function"].invoke(json.load(file))
                if not success:
                    accept_program = False
                    if "message" in functions.keys():
                        accept_program = functions["fail_case"].invoke(functions["message"])
                    else:
                        accept_program = functions["fail_case"].invoke()

                    if not accept_program:
                        return False
    except Exception as e:
        print(f"{type(e)}: {e.with_traceback()}")
        print("An internal grader failure as occured. DO NOT assume code product meets standards!")
    
    return True

def build_tree(path, max_depth, current_depth=0):
        """Recursively build directory tree structure"""
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
                    entry["children"] = build_tree(item, current_depth + 1)

                items.append(entry)
        except PermissionError as e:
            entry = {
                "error": "PermissionError"
            }

        return items

def list_dir(directory: str, max_depth: int = None) -> Dict[str, Any]:
    """
    List all files and directories in a directory structure.

    Args:
        directory: The directory to list
        max_depth: Maximum depth to traverse (None for unlimited)

    Returns:
        Dictionary containing the directory structure
    """

    dir_path = getpath(directory)

    if not dir_path.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")

    if not dir_path.is_dir():
        raise ValueError(f"Path is not a directory: {directory}")

    structure = build_tree(path=dir_path, max_depth=max_depth)

    return {
        "directory": str(dir_path),
        "structure": structure
    }

def create_zip(directory):
    """Create a zip file from directory contents"""
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, directory)
                zip_file.write(file_path, arcname)
    
    zip_buffer.seek(0)
    return zip_buffer

def clear_directory(directory):
    """Remove all contents from directory"""
    if os.path.exists(directory):
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            if os.path.isfile(item_path) or os.path.islink(item_path):
                os.unlink(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
        return True
    return False

def clear_directories(directories: list[str]):
    sucesses = {}
    for directory in directories:
        sucesses[directory] = clear_directory(directory=directory)
    return sucesses

def read_path(file_path):
    """Read system prompt using pathlib."""
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"System prompt file not found: {file_path}")
    
    return path.read_text(encoding='utf-8')

def transfer(source:str, destination:str):
    src_path = Path(source)
    dst_path = Path(destination)
    
    def should_exclude(file_path: Path):
        ignore_raw = os.getenv("IGNORE", "")
        patterns = [p.strip() for p in ignore_raw.split(",") if p.strip()]
        return any(file_path.match(pattern) for pattern in patterns)

    
    def copy_directory_recursive(src, dst):
        """Recursively copy directory using os.scandir()."""
        # Create destination directory if it doesn't exist
        os.makedirs(dst, exist_ok=True)
        
        # Scan the source directory
        with os.scandir(src) as entries:
            for entry in entries:
                src_item = Path(entry.path)
                dst_item = dst / entry.name
                
                # Check if should be excluded
                if should_exclude(src_item):
                    print(f"Excluded: {src_item.relative_to(src_path)}")
                    continue
                
                if entry.is_dir(follow_symlinks=False):
                    # Recursively copy subdirectory
                    copy_directory_recursive(src_item, dst_item)
                elif entry.is_file(follow_symlinks=False):
                    # Copy file with metadata
                    shutil.copy2(src_item, dst_item)
    
    copy_directory_recursive(src_path, dst_path)

def generate_user_id():
    # Try to get from session state first
    if 'user_id' not in st.session_state:
        # Check if returning user (via query params)
        if 'uid' in st.query_params:
            st.session_state.user_id = st.query_params['uid']
        else:
            # New user - generate ID
            new_id = str(uuid.uuid4())
            st.session_state.user_id = new_id
            # Optionally set in URL (persists across page refreshes)
            st.query_params['uid'] = new_id
    
    return st.session_state.user_id

def getpath(path: str): 
    tail = os.getenv("EDITOR_PATH")
    
    if tail is None:
        raise ValueError("`tail` cannot be None. Please provide a valid directory path.")
    
    # Convert both to Path objects
    base_path = Path(tail)
    requested_path = Path(path)
    
    # If the requested path starts with the base path name, strip it
    # E.g., if EDITOR_PATH is "sandbox" and path is "sandbox/test3.c"
    # then we want just "test3.c"
    if requested_path.parts and requested_path.parts[0] == base_path.name:
        # Remove the first part of the path
        relative_path = Path(*requested_path.parts[1:])
        return base_path / relative_path
    
    # Otherwise, just combine normally
    return base_path / requested_path