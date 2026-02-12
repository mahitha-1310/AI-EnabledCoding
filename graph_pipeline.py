import os, getpass
from typing_extensions import TypedDict
from typing import Literal, List
# from IPython.display import Image, display
from Validation.validation_pipeline import ValidationPipeline
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.prebuilt import tools_condition, ToolNode
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from tools import *
from utils import *

def _set_env(var: str):
    if not os.environ.get(var):
        os.environ[var] = getpass.getpass(f"{var}: ")

_set_env("OPENAI_API_KEY")
_set_env("OPENAI_API_BASE")
_set_env("OPENAI_API_MODEL")

input_path = os.getenv("INPUT_PATH")
editor_path = os.getenv("EDITOR_PATH")
output_path = os.getenv("OUTPUT_PATH")

model=os.getenv("OPENAI_API_MODEL")
llm_tools = list(TOOLS.values())
llm = ChatOpenAI(model=model).bind_tools(llm_tools)
system_message = SystemMessage(content=read_path("prompt/system_prompt.md"))
validator = ValidationPipeline(output_dir=output_path, source_dir=editor_path)

class CodebaseState(TypedDict):
    messages: str
    structure: List[str]
    encoding: str

# Nodes

def validate(state: CodebaseState):
    pass # Pass codebase to validation pipeline

def sendback(state: CodebaseState):
    pass # Understand why code did not meet validation standards

def pick_tool(state: CodebaseState):
    message = state["messages"][-1]

    if len(message.tool_calls) > 0:
        tool_call = message.tool_calls[0]['args']['update_type']
        if tool_call == "validate":
            return "validate"
        elif tool_call in llm_tools:
            return tool_call
    
    return "update"

def determine_grade(state: CodebaseState):
    # Does the code meet the validation standards?
    if(True): # End of graph
        return END
    else: # Hand back to LLM
        return "sendback"

def converse(state: CodebaseState):
    return {"messages": [llm.invoke([system_message] + state["messages"])]}


def build():
    # Create the state graph
    workflow = StateGraph(CodebaseState)

    # LLM's thinking node
    workflow.add_node("converse", converse)
    # Update the LLM's mental representation of the codebase structure
    workflow.add_node("update", list_dir)
    # Provide LLM tools
    workflow.add_node("tools", ToolNode(llm_tools))
    # Once request is handled, validate
    # workflow.add_node("validate", validate)
    # Handle validation pipeline failure
    # workflow.add_node("sendback", sendback)

    # Entry
    workflow.add_edge(START, "update")
    # Update-reflect pattern
    workflow.add_edge("update", "converse")
    workflow.add_conditional_edges("converse", tools_condition)
    # One LLM thinks code is ready, it can send to validation pipeline
    # workflow.add_conditional_edges("validate", determine_grade)
    # Failure handling
    # workflow.add_edge("sendback", "converse")
    
    return workflow

def run():
    # Give memory to Graph
    memory = MemorySaver()

    # Run the graph
    build().compile(interrupt_before="converse", checkpointer=memory)
