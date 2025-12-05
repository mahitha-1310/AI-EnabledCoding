import os
from pathlib import Path
import uuid
import streamlit as st

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