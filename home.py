import streamlit as st
from pipeline import *
from dotenv import load_dotenv
import streamlit as st
import uuid

def get_or_create_user_id():
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

load_dotenv()
pipeline = CodebasePipeline()

input_path = os.getenv("INPUT_PATH")
output_path = os.getenv("OUTPUT_PATH")
os.makedirs(input_path, exist_ok=True)
os.makedirs(output_path, exist_ok=True)

user_id = get_or_create_user_id()

if __name__ == '__main__':
    st.title("Code Modernizer")
    st.subheader("Boeing Group #2")

    if 'messages' not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        st.chat_message(message['role']).markdown(message['content'])

    uploaded_files = st.file_uploader(
        "Upload Code Files", 
        type=DEFAULT_EXTS,
        accept_multiple_files=True
    )

    for uploaded_file in uploaded_files:
        # Read the file data
        bytes_data = uploaded_file.read()
        
        # Save the file to input_path
        file_path = os.path.join(input_path, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(bytes_data)

    prompt = st.chat_input("Please explain what you would like me to do!")

    if prompt and (not prompt.strip() == ""):
        st.chat_message('user').markdown(prompt)
        st.session_state.messages.append({'role':'user', 'content':prompt})
        response = pipeline.run(
            instruction=prompt,
            user_id=user_id,
            input_path=os.getenv("INPUT_PATH"),
            output_path=os.getenv("OUTPUT_PATH")
        )
        st.chat_message('assistant').markdown(response)
        st.session_state.messages.append({'role':'assistant', 'content':response})
