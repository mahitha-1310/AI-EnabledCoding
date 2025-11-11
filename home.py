import streamlit as st
from pipeline import *
from dotenv import load_dotenv

load_dotenv()
pipeline = CodebasePipeline()

input_path = os.getenv("INPUT_PATH")
output_path = os.getenv("OUTPUT_PATH")
os.makedirs(input_path, exist_ok=True)
os.makedirs(output_path, exist_ok=True)

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
        input_path=os.getenv("INPUT_PATH"),
        output_path=os.getenv("OUTPUT_PATH"),
        instruction=prompt
    )
    st.chat_message('assistant').markdown(response)
    st.session_state.messages.append({'role':'assistant', 'content':response})
