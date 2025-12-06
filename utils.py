import os
from pathlib import Path
import shutil
import uuid
import streamlit as st

def transfer(source:str, destination:str):
    src_path = Path(source)
    dst_path = Path(destination)
    
    def should_exclude(file_path):
        """Check if file matches any exclude pattern."""
        return any(file_path.match(pattern) for pattern in os.getenv("IGNORE"))
    
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

def getpath(path:str): 
    tail = os.getenv("EDITOR_PATH")

    if tail is None:
        raise ValueError("input_path cannot be None. Please provide a valid directory path.")

    return Path(tail, path)