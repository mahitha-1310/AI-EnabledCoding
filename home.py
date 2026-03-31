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

    def customize_chatbot():
        EID.discard()

        # Chatbot variables
        summarize_after     = pipeline.config.get("summarize_after")
        messages_to_keep    = pipeline.config.get("messages_to_keep")
        summarized          = summarize_after-messages_to_keep
        return_anyway_after = pipeline.config.get("return_anyway_after")
        retry_prompt        = pipeline.config.get("retry_prompt")

        st.markdown("#### Chatbot")
        st.markdown(f"Model: **{pipeline.get_model_name()}**, Context Window Size: **{summarize_after} Messages**")

        summarized = st.number_input(label="Messages to Summarize:", value=summarized, min_value=1, step=1, key=EID.get())
        messages_to_keep = st.number_input(label="Messages to Preserve:", value=messages_to_keep, min_value=0, step=1, key=EID.get())
        return_anyway_after = st.number_input(label="Stop attempting after this amount of attempts:", value=return_anyway_after, min_value=1, step=1, key=EID.get())
        retry_prompt = st.checkbox(label="Enable End-of-Attempts Prompt", value=retry_prompt, key=EID.get())
        st.text(f"If disabled, code will automatically be outputted after {return_anyway_after} attempts.")

        if st.button("Confirm"):

            pipeline.config.set({
                "messages_to_keep":     messages_to_keep,
                "summarize_after":      summarize_after,
                "return_anyway_after":  return_anyway_after,
                "retry_prompt":         retry_prompt
            })

    def customize_validator():
        EID.discard()

        # Validator variables
        compiler            = pipeline.validator.config.get("compiler")
        build_tool          = pipeline.validator.config.get("build_tool")
        static_analyzer     = pipeline.validator.config.get("static_analyzer")
        flags               = pipeline.validator.config.get("flags")
        allow_modify        = not pipeline.validator.config.get("check_only")
        style               = pipeline.validator.config.get("style")

        st.markdown("#### Validator")

        compiler = st.selectbox("Compiler", ["clang"], key=EID.get())
        build_tool = st.selectbox("Build Tool", [None], key=EID.get())
        static_analyzer = st.selectbox("Static Analyzer", ["clang-tidy"], key=EID.get())
        flags = st.text_input("Enter execution flags here...", key=EID.get())
        style = st.selectbox("Formatting Style", ["LLVM"], key=EID.get())
        allow_modify = st.checkbox("Formatter Can Modify Code", allow_modify, key=EID.get())

        if st.button("Confirm"):

            pipeline.validator.config.set({
                "compiler":         compiler, # "clang",
                "build_tool":       build_tool, # None,
                "static_analyzer":  static_analyzer, # "clang-tidy",
                "flags":            flags, # [],
                "check_only":       not allow_modify, # True,
                "style":            style, # "LLVM"
            })
    
    chat, valid = st.tabs(["Customize Chatbot", "Customize Validator"])

    with chat:
        customize_chatbot()
    with valid:
        customize_validator()
    
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