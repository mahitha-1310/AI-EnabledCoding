import streamlit as st
from pipeline import Pipeline
from utils import *
from dotenv import load_dotenv
import time
import os

CHATBOT_MESSAGE = "What to do, what to do..."

@st.cache_resource
def get_pipeline():
    return Pipeline()

def stream(response, delay: float):
    for word in response:#.strip():
        yield word
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
            response = pipeline.run(
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
    disable = not os.listdir(pipeline.output_path)
    text = "Nothing to Download" if disable else "Download Codebase"
    if st.button(text, disabled=disable, use_container_width=True):
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

def codebase_clear():
    disable = not os.listdir(pipeline.editor_path) and not os.listdir(pipeline.input_path)
    text = "Nothing to Clear" if disable else "Clear Codebase"
    if st.button(text, disabled=disable, use_container_width=True):
        try:
            clear_directory(pipeline.editor_path)
            clear_directory(pipeline.input_path)
            clear_directory(pipeline.output_path)
            st.success("Directory cleared successfully!")
            st.rerun()
        except Exception as e:
            st.error(f"Error clearing directory: {str(e)}")

def pipeline_customize():
    if st.button("Model Settings...", use_container_width=True):
        customize_pipeline(pipeline=pipeline)

@st.dialog("Customize Pipeline")
def customize_pipeline(pipeline: Pipeline) -> None:
    """Allows user to control pipeline."""

    st.markdown(f"Model: **{pipeline.get_model_name()}**, Context Window Size: **{pipeline.summarize_after} Messages**")

    summarized = st.number_input(label="Messages to Summarize:", value=pipeline.summarize_after-pipeline.messages_to_keep, min_value=1, step=1, key=67)
    preseved = st.number_input(label="Messages to Preserve:", value=pipeline.messages_to_keep, min_value=0, step=1, key=69)
    return_anyway_after = st.number_input(label="Stop attempting after this amount of attempts:", value=pipeline.return_anyway_after, min_value=1, step=1, key=42)
    retry_prompt = st.checkbox(label="Enable End-of-Attempts Prompt", value=pipeline.retry_prompt)
    st.text(f"If disabled, code will automatically be outputted after {return_anyway_after} attempts.")

    if st.button("Confirm"):
        pipeline.messages_to_keep = preseved
        pipeline.summarize_after = preseved + summarized
        pipeline.return_anyway_after = return_anyway_after
        pipeline.retry_prompt = retry_prompt
        st.rerun()
    

def file_uploader(path: str, label: str):
    uploaded_files = st.file_uploader(
        label=label,
        accept_multiple_files=True
    )
    for uploaded_file in uploaded_files:
        # Read the file data
        bytes_data = uploaded_file.read()
        
        # Save the file to pipeline.input_path
        file_path = os.path.join(path, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(bytes_data)

if __name__ == '__main__':
    load_dotenv()
    
    pipeline = get_pipeline()
    user_id = generate_user_id()

    for path in [pipeline.input_path, pipeline.editor_path, pipeline.output_path]:
        os.makedirs(path, exist_ok=True)

    st.title("HASAIM")
    st.subheader("High Assurance System AI Modernization")
    edit_col, chat_col = st.columns([5, 3])

    with chat_col:
        cl, cm, cr = st.tabs(["Workspace", "Testing", "Files"])

        with cl:
            file_uploader(pipeline.input_path, "Upload C Files")
        with cm:
            file_uploader(pipeline.test_path, "Upload Unit Tests")
        with cr:
            codebase_download()
            codebase_clear()
            pipeline_customize()
    with edit_col:
        chatbox()