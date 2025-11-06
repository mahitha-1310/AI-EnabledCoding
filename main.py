# import streamlit as st
from codebase_pipeline import *
from dotenv import load_dotenv

load_dotenv()

# st.title("do you think chickehns hav dreams")

def run():
    # Initialize pipeline
    pipeline = CodebasePipeline(model=os.getenv("OPENAI_API_MODEL"))
    
    print("Please explain what you would like me to do.")

    while(True):
        prompt = input("\n> ")

        pipeline.run(
            input_path=os.getenv("INPUT_PATH"),
            output_path=os.getenv("OUTPUT_PATH"),
            instruction=prompt
        )

    # EXAMPLES

    # Example 1: Simple passthrough
    # pipeline.run(
    #     input_path="./my_project",
    #     output_path="./output_project",
    #     instruction="Return this codebase exactly as provided."
    #     extensions=['.py']
    # )
    
    # Example 2: Add documentation
    # pipeline.run(
    #     input_path="./my_project",
    #     output_path="./documented_project",
    #     instruction="Add docstrings to all functions that don't have them.",
    #     extensions=['.py']
    # )
    
    # Example 3: Refactor code
    # pipeline.run(
    #     input_path="./my_project",
    #     output_path="./refactored_project",
    #     instruction="Refactor the code to improve readability and follow PEP 8 standards.",
    #     extensions=['.py']
    # )

if __name__ == "__main__":
    run()