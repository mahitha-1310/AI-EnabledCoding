from generation_pipeline import Pipeline
from dotenv import load_dotenv
from utils import *
import streamlit as st
import traceback as tb
import time, os

load_dotenv()

st.set_page_config(layout="wide", page_title="HASAIM")

CHATBOT_MESSAGE = "What to do, what to do..."
HEIGHT = 550

@st.cache_resource
def get_pipeline(user_id: str = None):
    """Get a pipeline instance.
    
    Note: The pipeline is created once per session. If user_id is None,
    it will use default paths. For proper session isolation, user_id should
    be provided.
    """
    return Pipeline(user_id=user_id)

def stream(response, delay: float):
    for word in response:
        yield word
        time.sleep(delay)

@st.dialog("LLM Attempt Limit Reached")
def request_retry(num_attempts: int) -> int:
    """Ask user if they should continue with prompting the llm.
    
    Returns:
        Number of additional attempts to allow (0, 1, or num_attempts)
    """

    if "retry_dialog_choice" not in st.session_state:
        st.session_state.retry_dialog_choice = None
    
    st.write("How would you like to proceed?")
    choice = st.radio(
        label="Select an option:",
        options=[
            "Stop Attempting", 
            "Attempt One More Time", 
            f"Attempt {num_attempts} More Times"
        ],
        index=0,
        key="retry_radio"
    )
    
    if st.button("Confirm", disabled=choice is None, key="retry_confirm"):
        st.session_state.retry_dialog_choice = choice
        st.rerun()
    
    if st.session_state.retry_dialog_choice:
        confirmed_choice = st.session_state.retry_dialog_choice
        st.session_state.retry_dialog_choice = None
        
        if confirmed_choice == "Attempt One More Time":
            return 1
        elif confirmed_choice == f"Attempt {num_attempts} More Times":
            return num_attempts
        else:
            return 0
    
    return 0

def chatbot():
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    user_paths = get_user_paths(user_id)
    
    with st.container(height=HEIGHT):
        for message in st.session_state.messages:
            st.chat_message(message['role']).markdown(message['content'])
        
        prompt = st.chat_input(CHATBOT_MESSAGE, key="chat_input")
        
        if prompt and not prompt == "":
            st.chat_message('user').markdown(prompt)
            st.session_state.messages.append({'role': 'user', 'content': prompt})

            try:
                clear_directories([user_paths.editor_path, user_paths.output_path])
                transfer(source=user_paths.input_path, destination=user_paths.editor_path)
                
                response = None
                metadata = None
                try:
                    with st.chat_message('assistant'):
                        with st.spinner("Working on it... (check terminal for live progress)", show_time=True):
                            response, metadata = pipeline.run(
                                user_input=prompt,
                                user_id=user_id
                            )
                        st.write_stream(stream=stream(response=response, delay=0.005))
                except Exception as e:
                    error_msg = f"An error was encountered: {str(e)}"
                    st.error(error_msg)
                    print(tb.format_exc())
                    response = error_msg
                    metadata = {"needs_retry_prompt": False, "attempts_left": 0}
                
                try:
                    clear_directory(user_paths.input_path)
                    transfer(source=user_paths.editor_path, destination=user_paths.output_path)
                    transfer(source=user_paths.testing_path, destination=user_paths.output_path)
                except Exception as cleanup_error:
                    print(f"Error during cleanup: {cleanup_error}")
                    st.warning("Some files may not have been properly transferred.")

                if response:
                    st.session_state.messages.append({'role': 'assistant', 'content': response})
                
                if metadata and metadata.get("needs_retry_prompt"):
                    attempts_left = metadata.get("attempts_left", 0)
                    retry_choice = request_retry(attempts_left)
                    
                    if retry_choice > 0:
                        st.info(f"Retrying with {retry_choice} additional attempt(s)...")
                        st.success(f"Please enter your request again to retry.")
                    else:
                        # User chose to stop
                        st.warning("Retry stopped as requested.")
                
                st.rerun()
                
            except Exception as e:
                import traceback
                st.error(f"Critical error: {str(e)}")
                print(f"Critical error traceback: {traceback.format_exc()}")

def codebase_download(user_paths):
    disable = only_folders(user_paths.output_path)
    text = "Nothing to Download" if disable else "Download Codebase"
    st.download_button(
        label=text,
        data=create_zip(project_path(user_paths.output_path)),
        file_name=f"{os.path.basename(user_paths.output_path)}.zip",
        mime="application/zip",
        use_container_width=True,
        disabled=disable
    )

def codebase_clear(user_paths):
    disable = only_folders(project_path(user_paths.editor_path)) and only_folders(project_path(user_paths.input_path))
    text = "Nothing to Clear" if disable else "Clear Codebase"
    if st.button(text, disabled=disable, use_container_width=True):
        try:
            user_session_path = os.path.join(user_paths.workshop_path, "sessions", user_id)
            if os.path.exists(user_session_path):
                shutil.rmtree(user_session_path)
            st.success("Your workspace cleared successfully!")
            st.rerun()
        except Exception as e:
            st.error(f"Error clearing directory: {str(e)}")

def pipeline_customize(pipeline: Pipeline):
    if st.button("Model Settings...", use_container_width=True):
        customize_pipeline(pipeline=pipeline)

@st.dialog("Customize Pipeline")
def customize_pipeline(pipeline: Pipeline) -> None:
    """Allows user to control pipeline."""

    rc = pipeline.rag_config
    mc = pipeline.model_config
    vc = pipeline.validator.config

    def customize_rag():
        ragargs = {"step":1.0, "min_value":0.0, "format":"%0f"}
        rc.display("repository_url", "The repository link to extract files from. RAG will not be used if this is blank.")
        rc.display("retrieval_chunks", "The amount of RAG chunks that will be used in genrating a response. Set to 0 to disable.", **ragargs)

    def customize_chatbot():
        numargs = {"step":1.0, "min_value":1.0, "format":"%0f"}
        temprange = {"step":0.001, "min_value":0.0, "max_value":2.0, "format":"%0f"}

        mc.display("summarize_after", "The amount of messages that will cause the LLM to summarize.", **numargs)
        mc.display("messages_to_keep", "The amount of messages that won't be summarized.", **numargs)
        mc.display("return_anyway_after", "The amount of attempts the LLM is allowed to have before a forced return.", **numargs)
        mc.display("retry_prompt", "Should the user be asked if they want to continue prompting?", override_type=bool)
        mc.display("temperature", "How deterministic the model should be.\n0.0 - Deterministic, 2.0 - Creative", **temprange)
        mc.display("timeout", "Amount of seconds the client will wait for a response from the OpenAI API before terminating the connection.")

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
    
    rag, chat, valid = st.tabs(["RAG", "Chatbot", "Validator"])

    with rag:
        customize_rag()
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
    
    if not uploaded_files:
        return
    
    for uploaded_file in uploaded_files:
        name = uploaded_file.name
        ext  = os.path.splitext(name)[1].lower()

        if ext not in _ALLOWED_EXTENSIONS and name not in _ALLOWED_FILENAMES:
            st.warning(
                f"'{name}' was skipped: Only .c/.h source files and Makefiles are supported."
            )
            continue

        try:
            file_path = os.path.join(path, name)
            os.makedirs(path, exist_ok=True)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
        except Exception as e:
            st.error(f"Failed to upload '{name}': {str(e)}")
            continue

if __name__ == "__main__":

    user_id = generate_user_id()
    pipeline = get_pipeline(user_id=user_id)
    user_paths = get_user_paths(user_id)

    st.title("HASAIM")
    st.subheader("High Assurance System AI Modernization")
    edit_col, chat_col = st.columns([5, 3])

    with chat_col:
        cl, cm, cr = st.tabs(["Workspace", "Testing", "Files"])

        with cl:
            file_uploader(project_path(user_paths.input_path), "Upload C Files")
        with cm:
            file_uploader(project_path(user_paths.test_path), "Upload Unit Tests")
        with cr:
            codebase_download(user_paths)
            codebase_clear(user_paths)
            pipeline_customize(pipeline=pipeline)
    with edit_col:
        chatbot()