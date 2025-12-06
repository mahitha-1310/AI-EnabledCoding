import streamlit as st
from pipeline import *
from utils import *
from dotenv import load_dotenv

load_dotenv()
pipeline = CodebasePipeline()
user_id = generate_user_id()

input_path = os.getenv("INPUT_PATH")
editor_path = os.getenv("EDITOR_PATH")
output_path = os.getenv("OUTPUT_PATH")

for path in [input_path, editor_path, output_path]:
    os.makedirs(path, exist_ok=True)

if __name__ == '__main__':
    st.title("Code Modernizer")
    st.subheader("Boeing Group #2")

    if 'messages' not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        st.chat_message(message['role']).markdown(message['content'])

    uploaded_files = st.file_uploader(
        "Upload Code Files", 
        type=os.getenv("DEFAULT_EXTS"),
        accept_multiple_files=True
    )

    for uploaded_file in uploaded_files:
        # Read the file data
        bytes_data = uploaded_file.read()
        
        # Save the file to input_path
        file_path = os.path.join(os.getenv("EDITOR_PATH"), uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(bytes_data)

    prompt = st.chat_input("Please explain what you would like me to do!")

    if prompt and (not prompt.strip() == ""):
        
        # Add prompt to chat
        st.chat_message('user').markdown(prompt)
        st.session_state.messages.append({'role': 'user', 'content': prompt})

        # Bring any inputted code to editor
        transfer(input_path, editor_path)

        response = pipeline.run(
            user_input=prompt,
            user_id=user_id
        )

        # Bring edited code to output
        transfer(editor_path, output_path)
        
        # Produce response
        st.chat_message('assistant').markdown(response)
        st.session_state.messages.append({'role': 'assistant', 'content': response})
