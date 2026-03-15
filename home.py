import streamlit as st
from pipeline import Pipeline, run
from utils import *
from dotenv import load_dotenv
import time
import os

CHATBOT_MESSAGE = "Please explain what you would like me to do!"

@st.cache_resource
def get_pipeline():
    return Pipeline()

def stream(response, delay: float):
    for word in response:#.strip():
        yield word + " "
        time.sleep(delay)

def chatbot():
    prompt = st.chat_input(CHATBOT_MESSAGE)
    if prompt and (not prompt.strip() == ""):
        # Add prompt to chat
        st.chat_message('user').markdown(prompt)
        st.session_state.messages.append({'role': 'user', 'content': prompt})

        clear_directories([pipeline.editor_path, pipeline.output_path])
        transfer(source=pipeline.input_path, destination=pipeline.editor_path)
        
        # Produce response
        with st.chat_message('assistant'):
            response = run(
                pipeline=pipeline,
                user_input=prompt,
                user_id=user_id
            )
            st.write_stream(stream=stream(response=response, delay=0.01))
        
        clear_directory(pipeline.input_path)
        transfer(source=pipeline.editor_path, destination=pipeline.output_path)

        st.session_state.messages.append({'role': 'assistant', 'content': response})
        st.rerun()

def chatbox():
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    with st.container(height=450):
        for message in st.session_state.messages:
            st.chat_message(message['role']).markdown(message['content'])
        chatbot()

def codebase_download():
    if st.button("Download Codebase", use_container_width=True):
        if os.path.exists(pipeline.output_path) and os.listdir(pipeline.output_path):
            try:
                zip_data = create_zip(pipeline.output_path)
                st.download_button(
                    label="Click to Download ZIP",
                    data=zip_data,
                    file_name=f"{os.path.basename(pipeline.output_path)}.zip",
                    mime="application/zip",
                    use_container_width=True
                )
                st.success("ZIP file ready for download!")
            except Exception as e:
                st.error(f"Error creating zip: {str(e)}")
        else:
            st.warning("No output to download.")

def codebase_clear():
    if st.button("Clear Codebase", use_container_width=True):
        if os.path.exists(pipeline.editor_path) and os.path.exists(pipeline.input_path):
            try:
                clear_directory(pipeline.editor_path)
                clear_directory(pipeline.input_path)
                clear_directory(pipeline.output_path)
                st.success("Directory cleared successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error clearing directory: {str(e)}")
        else:
            st.warning("Directory doesn't exist")

def file_uploader():
    uploaded_files = st.file_uploader(
        label="Upload Files",
        accept_multiple_files=True
    )
    for uploaded_file in uploaded_files:
        # Read the file data
        bytes_data = uploaded_file.read()
        
        # Save the file to pipeline.input_path
        file_path = os.path.join(pipeline.input_path, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(bytes_data)

if __name__ == '__main__':
    load_dotenv()
    
    pipeline = get_pipeline()
    user_id = generate_user_id()

    for path in [pipeline.input_path, pipeline.editor_path, pipeline.output_path]:
        os.makedirs(path, exist_ok=True)
        clear_directory(path)

    st.title("HASAIM")
    st.subheader("High Assurance System AI Modernization")

    chatbox()

    cl, cr = st.columns([3, 1])

    with cl:
        file_uploader()
    with cr:
        codebase_download()
        codebase_clear()