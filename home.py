import streamlit as st
from generation_pipeline import Pipeline
from utils import *
import time
import os

st.set_page_config(layout="wide", page_title="HASAIM")

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
    with st.container():
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
            response = None
            try:
                with st.chat_message('assistant'):
                    with st.spinner("Working on it... (check terminal for live progress)", show_time=True):
                        response = pipeline.run(
                            user_input=prompt,
                            user_id=user_id
                        )
                    st.write_stream(stream=stream(response=response, delay=0.005))
            except Exception as e:
                st.error(f"Pipeline error: {e}")
            finally:
                clear_directory(PATH.input_path)
                transfer(source=PATH.editor_path, destination=PATH.output_path)
                transfer(source=PATH.testing_path, destination=PATH.output_path)

            if response:
                st.session_state.messages.append({'role': 'assistant', 'content': response})
            st.rerun()

def codebase_download():
    if not os.path.exists(PATH.output_path):
        os.makedirs(PATH.output_path, exist_ok=True)
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

        st.markdown("**Static Analyzers**")
        current = vc.list_items("static_analyzer")
        use_clang    = st.checkbox("clang-tidy", value="clang-tidy" in current, key="static_analyzer_clang_tidy",
                                   help="Runs clang-tidy on each source file using the project's compile_commands.json. Catches style violations, bug-prone patterns, and modernization opportunities.")
        use_cppcheck = st.checkbox("cppcheck",   value="cppcheck"   in current, key="static_analyzer_cppcheck",
                                   help="Runs cppcheck on the whole project at once. Detects undefined behavior, memory issues, and style problems. Complements clang-tidy with different heuristics.")
        selected = [a for a, on in [("clang-tidy", use_clang), ("cppcheck", use_cppcheck)] if on]
        if selected:
            vc["static_analyzer"]["default"] = selected
        else:
            vc["static_analyzer"]["default"] = ["clang-tidy"]
            st.warning("At least one analyzer must be selected. Defaulting to clang-tidy.")
        st.caption("Choose one or both analyzers for the static analysis step.")

        st.divider()

        st.markdown("**Dynamic Analysis**")
        current_tools = vc.list_items("tool")
        use_memcheck   = st.checkbox("memcheck",   value="memcheck"   in current_tools, key="valgrind_memcheck",
                                     help="Detects memory errors and leaks. The most commonly used Valgrind tool.")
        use_helgrind   = st.checkbox("helgrind",   value="helgrind"   in current_tools, key="valgrind_helgrind",
                                     help="Detects threading errors such as race conditions and misuse of POSIX pthreads.")
        use_massif     = st.checkbox("massif",     value="massif"     in current_tools, key="valgrind_massif",
                                     help="Profiles heap memory usage over time.")
        use_callgrind  = st.checkbox("callgrind",  value="callgrind"  in current_tools, key="valgrind_callgrind",
                                     help="Profiles call graphs and cache/branch prediction behavior.")
        selected_tools = [t for t, on in [("memcheck", use_memcheck), ("helgrind", use_helgrind),
                                          ("massif", use_massif), ("callgrind", use_callgrind)] if on]
        if selected_tools:
            vc["tool"]["default"] = selected_tools
        else:
            vc["tool"]["default"] = ["memcheck"]
            st.warning("At least one Valgrind tool must be selected. Defaulting to memcheck.")
        st.caption("Choose one or more Valgrind tools to run during dynamic analysis.")

        vc.display("program_args", help="Command-line arguments passed to the compiled executable when run under Valgrind. Leave blank if the program takes no arguments.", placeholder="e.g. --input file.txt --verbose")

        st.divider()

        st.markdown("**Formatting**")
        vc.display("check_only", override_type=bool, help="When enabled, clang-format checks formatting but makes no changes to source files. Disable to have clang-format automatically reformat the code.")
        vc.display("style", override_type=list, help="The clang-format style guide used to check or reformat the code. LLVM and Google are the most commonly used for C projects.")
    
    chat, valid = st.tabs(["Chatbot", "Validator"])

    with chat:
        customize_chatbot()
    with valid:
        customize_validator()
    

_ALLOWED_EXTENSIONS = {".c", ".h"}
_ALLOWED_FILENAMES  = {"Makefile", "makefile", "GNUmakefile"}

def file_uploader(path: str, label: str):
    uploaded_files = st.file_uploader(
        label=label,
        accept_multiple_files=True
    )
    for uploaded_file in uploaded_files:
        name = uploaded_file.name
        ext  = os.path.splitext(name)[1].lower()

        if ext not in _ALLOWED_EXTENSIONS and name not in _ALLOWED_FILENAMES:
            st.warning(
                f"'{name}' was skipped: only .c/.h source files and Makefiles are supported."
            )
            continue

        # Read the file data
        bytes_data = uploaded_file.read()

        # Save the file to pipeline.input_path
        file_path = os.path.join(path, name)
        os.makedirs(path, exist_ok=True)  # creates the dir if it doesn't exist
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

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