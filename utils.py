import os
from pathlib import Path
import shutil
import uuid
import streamlit as st
from pathlib import Path

def read_system_prompt(file_path):
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