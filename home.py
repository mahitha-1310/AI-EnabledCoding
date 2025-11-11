import streamlit as st
from pipeline import *
from dotenv import load_dotenv

load_dotenv()
pipeline = CodebasePipeline()

st.title("Boeing 2")

if 'messages' not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    st.chat_message(message['role']).markdown(message['content'])

uploaded_files = st.file_uploader(
    "Multiple Image Uploader", 
    type=DEFAULT_EXTS, 
    help="Upload code files", 
    accept_multiple_files=True
)
details = st.button("Check Details", key=420)
for uploaded_file in uploaded_files:
    if details:
        if uploaded_file is not None:
            bytes_data = uploaded_file.read()
            st.write("file_name:", uploaded_file.name)
        else:
            st.write("No Image File is Uploaded")
            break

prompt = st.chat_input("Please explain what you would like me to do!")

if prompt and (not prompt.strip() == ""):
    st.chat_message('user').markdown(prompt)
    st.session_state.messages.append({'role':'user', 'content':prompt})
    response = pipeline.run(
        input_path=os.getenv("INPUT_PATH"),
        output_path=os.getenv("OUTPUT_PATH"),
        instruction=prompt
    )
    st.chat_message('assistant').markdown(response)
    st.session_state.messages.append({'role':'assistant', 'content':response})
