import os, json
from dotenv import load_dotenv
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.prebuilt import tools_condition, ToolNode
from langgraph.graph import StateGraph, START
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from tools import *
from utils import *

# def _set_env(var: str):
#     if not os.environ.get(var):
#         os.environ[var] = getpass.getpass(f"{var}: ")

# _set_env("OPENAI_API_KEY")
# _set_env("OPENAI_API_BASE")
# _set_env("OPENAI_API_MODEL")

load_dotenv()

input_path = os.getenv("INPUT_PATH")
editor_path = os.getenv("EDITOR_PATH")
output_path = os.getenv("OUTPUT_PATH")

graph = None
model=os.getenv("OPENAI_API_MODEL")
llm_tools = list(TOOLS.values())
llm = ChatOpenAI(model=model).bind_tools(llm_tools)
system_message = SystemMessage(content=read_path("prompt/system_prompt.md"))
# validator = ValidationPipeline(output_dir=output_path, source_dir=editor_path)

class State(TypedDict):
    messages: list[BaseMessage]
    structure: Dict[str, Any]

# Nodes

# def validate(state: State):
#     pass # Pass codebase to validation pipeline

# def sendback(state: State):
#     pass # Understand why code did not meet validation standards

def pick_tool(state: State):
    message = state["messages"][-1]

    if len(message.tool_calls) > 0:
        tool_call = message.tool_calls[0]['args']['update_type']
        if tool_call == "validate":
            return "validate"
        elif tool_call in llm_tools:
            return tool_call
    
    return "update"

def update(state: State):
    project_structure = list_dir(editor_path)
    tool_message = str.format(
        read_path("prompt/structure_prompt.md"), 
        directory_tree=json.dumps(project_structure, indent=4)
    )
    return {"structure": project_structure, "messages": [SystemMessage(content=tool_message)]}

def list_dir(directory: str, max_depth: int = None) -> Dict[str, Any]:
    """
    List all files and directories in a directory structure.
    
    Args:
        directory: The directory to list
        max_depth: Maximum depth to traverse (None for unlimited)
        
    Returns:
        Dictionary containing the directory structure
    """
    logging.info(f"[LIST] Starting list operation")
    logging.info(f"[LIST] Directory: {directory}")
    logging.info(f"[LIST] Max depth: {max_depth}")
    
    dir_path = getpath(directory)
    logging.info(f"[LIST] Resolved path: {dir_path}")
    
    if not dir_path.exists():
        logging.error(f"[LIST] Directory not found: {directory}")
        raise FileNotFoundError(f"Directory not found: {directory}")
    
    if not dir_path.is_dir():
        logging.error(f"[LIST] Path is not a directory: {directory}")
        raise ValueError(f"Path is not a directory: {directory}")
    
    def build_tree(path, current_depth=0):
        """Recursively build directory tree structure"""
        items = []
        
        # Check depth limit
        if max_depth is not None and current_depth >= max_depth:
            return items
        
        try:
            for item in sorted(path.iterdir()):
                stat = item.stat()
                entry = {
                    "name": item.name,
                    "path": str(item),
                    "type": "directory" if item.is_dir() else "file",
                }
                
                if item.is_file():
                    entry["size"] = stat.st_size
                    entry["modified"] = stat.st_mtime
                elif item.is_dir():
                    entry["children"] = build_tree(item, current_depth + 1)
                
                items.append(entry)
        except PermissionError:
            # Skip directories we don't have permission to read
            logging.warning(f"[LIST] Permission denied for: {path}")
            pass
        
        return items
    
    structure = build_tree(dir_path)
    logging.info(f"[LIST] Found {len(structure)} items in directory")
    
    result = {
        "directory": str(dir_path),
        "structure": structure
    }
    
    logging.info(f"[LIST] List operation completed successfully")
    return result

# def determine_grade(state: State):
#     # Does the code meet the validation standards?
#     if(True): # End of graph
#         return END
#     else: # Hand back to LLM
#         return "sendback"

def converse(state: State):
    return {"messages": [llm.invoke([system_message] + state["messages"])]}

def build(chkptr):
    graph_builder = StateGraph(State)

    # NODES

    # LLM's thinking node
    graph_builder.add_node("converse", converse)
    # Update the LLM's mental representation of the codebase structure
    graph_builder.add_node("update", update)
    # Provide LLM tools
    graph_builder.add_node("tools", ToolNode(llm_tools))
    # Once request is handled, validate
    # graph_builder.add_node("validate", validate)
    # Handle validation pipeline failure
    # graph_builder.add_node("sendback", sendback)

    # EDGES

    # Entry
    graph_builder.add_edge(START, "update")
    # Update-reflect pattern
    graph_builder.add_edge("update", "converse")
    graph_builder.add_conditional_edges("converse", tools_condition)
    graph_builder.add_edge("tools", "update")
    # One LLM thinks code is ready, it can send to validation pipeline
    # graph_builder.add_conditional_edges("validate", determine_grade)
    # Failure handling
    # graph_builder.add_edge("sendback", "converse")
    
    return graph_builder.compile(interrupt_after=["converse"], checkpointer=chkptr)

def run(user_input: str, user_id: str):

    logging.info(f"NEW PIPELINE RUN")
    logging.info(f"[USER] {user_id}")
    logging.info(f"[QUERY] {user_input}")

    global graph

    if not graph:
        graph = build(MemorySaver())
        print(graph.get_graph().draw_ascii())

    # Run the graph
    response = graph.invoke(
        {"messages": HumanMessage(content=user_input)},
        {"configurable": {"thread_id": user_id}}
    )

    # Bring edited code to output
    # TODO: remove when validation pipeline is ready!
    transfer(editor_path, output_path)

    return response