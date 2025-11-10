import streamlit as st
from codebase_pipeline import *
from dotenv import load_dotenv

load_dotenv()
pipeline = CodebasePipeline()

st.title("Boeing 2")

if 'messages' not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    st.chat_message(message['role']).markdown(message['content'])

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
