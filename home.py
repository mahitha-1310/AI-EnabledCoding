import streamlit as st
from generation_pipeline import Pipeline
from utils import *
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
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    with st.container(height=450):
        for message in st.session_state.messages:
            st.chat_message(message['role']).markdown(message['content'])
        prompt = st.chat_input(CHATBOT_MESSAGE)
        if prompt and not prompt == "":
            # Add prompt to chat
            st.chat_message('user').markdown(prompt)
            st.session_state.messages.append({'role': 'user', 'content': prompt})

            clear_directories([PATH.editor_path, PATH.output_path])
            transfer(source=PATH.input_path, destination=PATH.editor_path)
            
            # Produce response
            with st.chat_message('assistant'):
                response = pipeline.run(
                    user_input=prompt,
                    user_id=user_id
                )
                st.write_stream(stream=stream(response=response, delay=0.01))
            
            clear_directory(PATH.input_path)
            transfer(source=PATH.editor_path, destination=PATH.output_path)

            st.session_state.messages.append({'role': 'assistant', 'content': response})
            st.rerun()

def codebase_download():
    disable = not os.listdir(PATH.output_path)
    text = "Nothing to Download" if disable else "Download Codebase"
    if st.button(text, disabled=disable, use_container_width=True):
        try:
            zip_data = create_zip(PATH.output_path)
            st.download_button(
                label="Click to Download ZIP",
                data=zip_data,
                file_name=f"{os.path.basename(PATH.output_path)}.zip",
                mime="application/zip",
                use_container_width=True
            )
            st.success("ZIP file ready for download!")
        except Exception as e:
            st.error(f"Error creating zip: {str(e)}")

def codebase_clear():
    disable = not os.listdir(PATH.editor_path) and not os.listdir(PATH.input_path)
    text = "Nothing to Clear" if disable else "Clear Codebase"
    if st.button(text, disabled=disable, use_container_width=True):
        try:
            clear_directory(PATH.workshop_path)
            st.success("Directory cleared successfully!")
            st.rerun()
        except Exception as e:
            st.error(f"Error clearing directory: {str(e)}")

def pipeline_customize(pipeline: Pipeline):
    if st.button("Model Settings...", use_container_width=True):
        customize_pipeline(pipeline=pipeline)

@st.dialog("Customize Pipeline")
def customize_pipeline(pipeline: Pipeline) -> None:
    """Allows user to control pipeline."""

    pc = pipeline.config
    vc = pipeline.validator.config

    def customize_chatbot():
        numargs = {"step":1.0, "min_value":1.0, "format":"%0f"}

        pc.display("summarize_after", "The amount of messages that will cause the LLM to summarize.", **numargs)
        pc.display("messages_to_keep", "The amount of messages that won't be summarized.", **numargs)
        pc.display("return_anyway_after", "The amount of attempts the LLM is allowed to have before a forced return.", **numargs)
        pc.display("retry_prompt", "Should the user be asked if they want to continue prompting?", override_type=bool)

    def customize_validator():

        vc.display("compiler", "Choose a compiler for the compilation step.", override_type=list)
        vc.display("build_tool", "Choose a build tool to use for the compilation step.", override_type=list)
        vc.display("static_analyzer", "Choose a code analyzer for static analysis step.", override_type=list)
        vc.display("flags", "Flags to use alongside the execution command.")
        vc.display("check_only", "Should the validator only check the code and make no formatting modifications?", override_type=bool)
        vc.display("style", "Formatting standard the format linter will use.", override_type=list)
    
    chat, valid = st.tabs(["Chatbot", "Validator"])

    with chat:
        customize_chatbot()
    with valid:
        customize_validator()
    

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

if __name__ == "__main__":

    pipeline = get_pipeline()
    user_id = generate_user_id()

    st.title("HASAIM")
    st.subheader("High Assurance System AI Modernization")
    edit_col, chat_col = st.columns([5, 3])

    with chat_col:
        cl, cm, cr = st.tabs(["Workspace", "Testing", "Files"])

        with cl:
            file_uploader(PATH.input_path, "Upload C Files")
        with cm:
            file_uploader(PATH.test_path, "Upload Unit Tests")
        with cr:
            codebase_download()
            codebase_clear()
            pipeline_customize(pipeline=pipeline)
    with edit_col:
        chatbot()