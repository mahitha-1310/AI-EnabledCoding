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

def download(path, downloadable_name:str):
    disable = only_folders(path)
    text = f"No {downloadable_name} to Download" if disable else f"Download {downloadable_name}"
    st.download_button(
        label=text,
        data=create_zip(project_path(path)),
        file_name=f"{os.path.basename(path)}.zip",
        mime="application/zip",
        use_container_width=True,
        disabled=disable
    )

def codebase_clear(user_paths):
    disable = only_folders(project_path(user_paths.workshop_path))
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
                                   help="Runs clang-tidy on each source file using the project's compile_commands.json.")
        use_cppcheck = st.checkbox("cppcheck",   value="cppcheck"   in current, key="static_analyzer_cppcheck",
                                   help="Runs cppcheck on the whole project at once.")
        selected = [a for a, on in [("clang-tidy", use_clang), ("cppcheck", use_cppcheck)] if on]
        if selected:
            vc["static_analyzer"]["default"] = selected
        else:
            vc["static_analyzer"]["default"] = ["clang-tidy"]
            st.warning("At least one analyzer must be selected. Defaulting to clang-tidy.")
        st.caption("Choose one or both analyzers for the static analysis step.")

        with st.expander("More Info on Static Analyzers"):
            st.markdown(
                "- **clang-tidy**: A Clang-based C/C++ linter tool that diagnoses typical programming errors, "
                "like style violations, interface misuse, or bugs that can be deduced via static analysis. "
                "It uses the compile_commands.json file to understand how each source file is compiled, "
                "allowing it to provide precise diagnostics."
                )
            st.markdown(
                "- **cppcheck**: A static analysis tool for C/C++ code that detects various types of bugs and issues, "
                "such as memory leaks, null pointer dereferences, and unused functions. Unlike clang-tidy, "
                "cppcheck analyzes the entire codebase at once and does not require compile_commands.json, "
                "making it easier to set up but potentially less precise in its diagnostics."
                )
            
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

        vc.display(
            "command_line_args", 
            help="Command-line arguments passed to the compiled executable when run under Valgrind. Leave blank if the program takes no arguments.", 
            placeholder="e.g. --input <filename>.txt --verbose --count 10"
            )

        with st.expander("More Info on Valgrind Tools"):
            st.markdown(
                "- **memcheck**: The most commonly used Valgrind tool, memcheck detects memory-related errors such as out-of-bounds "
                "accesses, use of uninitialized memory, and memory leaks. It provides detailed reports to help identify and fix memory "
                "issues in C/C++ programs."
            )
            st.markdown(
                "- **helgrind**: Helgrind is a Valgrind tool designed to detect threading errors in C/C++ programs that use POSIX threads. "
                "It identifies issues such as race conditions, deadlocks, and misuse of synchronization primitives, helping developers ensure "
                "thread safety in their applications."
            )
            st.markdown(
                "- **massif**: Massif is a Valgrind tool that profiles heap memory usage over time. It helps developers understand how their "
                "program allocates and deallocates memory, identify memory usage peaks, and optimize memory consumption by providing detailed "
                "snapshots of heap usage at different points during execution."
            )
            st.markdown(
                "- **callgrind**: Callgrind is a Valgrind tool that profiles call graphs and cache/branch prediction behavior in C/C++ programs. "
                "It helps developers analyze the performance of their code by providing insights into function call frequencies, call paths, "
                "and cache usage, enabling them to optimize critical sections of their code for better performance."
            )

        st.divider()

        st.markdown("**Formatting**")
        vc.display("check_only", override_type=bool, help="When enabled, clang-format checks formatting but makes no changes to source files. Disable to have clang-format automatically reformat the code.")
        vc.display("style", override_type=list, help="The clang-format style guide used to check or reformat the code.")

        with st.expander("More Info on Formatting Options"):
            st.markdown(
                "- **check_only**: When enabled, the formatting stage will run clang-format in a mode where it checks the formatting of the code "
                "without making any changes. If any formatting issues are detected, the stage will be marked as FAILED. When disabled, clang-format "
                "will automatically reformat the code according to the specified style, and the stage will be marked as OK if the formatting is successful."
            )
            st.markdown(
                "- **style**: This option specifies the clang-format style guide to use when checking or reformatting the code. "
                "Clang-format supports a variety of predefined styles (e.g., Google, LLVM, Mozilla) as well as a 'file' option that uses a "
                ".clang-format configuration file in the project directory. Choosing an appropriate style can help ensure consistent code formatting "
                "across the project."
            )
    
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
    state_key = f"uploaded_{label.replace(' ', '_')}"
    if state_key not in st.session_state:
        st.session_state[state_key] = []

    uploaded_files = st.file_uploader(
        label=label,
        accept_multiple_files=True,
    )

    if not uploaded_files:
        return

    uploaded_files = uploaded_files if isinstance(uploaded_files, list) else [uploaded_files]

    new_names = {f.name for f in uploaded_files}

    removed = set(st.session_state[state_key]) - new_names
    for fname in removed:
        try:
            os.remove(os.path.join(path, fname))
        except Exception as e:
            st.error(f"Failed to delete removed file '{fname}': {e}")

    for uploaded_file in uploaded_files:
        name = uploaded_file.name
        ext = os.path.splitext(name)[1].lower()

        if ext not in _ALLOWED_EXTENSIONS and name not in _ALLOWED_FILENAMES:
            st.warning(
                f"'{name}' was skipped: Only .c/.h source files and Makefiles are supported."
            )
            continue

        try:
            os.makedirs(path, exist_ok=True)
            file_path = os.path.join(path, name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
        except Exception as e:
            st.error(f"Failed to upload '{name}': {str(e)}")
            continue
    st.session_state[state_key] = list(new_names)

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
            pipeline_customize(pipeline=pipeline)
            code_col, logs_col = st.columns(2)
            with code_col:
                download(user_paths.output_path, "Codebase")
            with logs_col:
                download(user_paths.testing_path, "Logs")
            codebase_clear(user_paths)
    with edit_col:
        chatbot()