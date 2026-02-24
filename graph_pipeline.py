import os, json, logging, time
from dotenv import load_dotenv
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
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

logger = logging.basicConfig(
    filename='llm_queries.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
graph = None
model = os.getenv("OPENAI_API_MODEL")
logger.debug("[INIT] Loading tools and binding to model: %s", model)
llm_tools = list(TOOLS.values())
llm = ChatOpenAI(model=model).bind_tools(llm_tools)
logger.debug("[INIT] Bound %d tool(s) to LLM: %s", len(llm_tools), [t.name for t in llm_tools])
system_message = SystemMessage(content=read_path("prompt/system_prompt.md"))
structure_message = read_path("prompt/structure_prompt.md")
# validator = ValidationPipeline(output_dir=output_path, source_dir=editor_path)

class State(TypedDict):
    messages: list[BaseMessage]
    structure: Dict[str, Any]

# Nodes

def validate(state: State):
    pass # Pass codebase to validation pipeline

def determine_quality(state: State):
    # Understand if code met validation standards
    return END # PLACEHOLDER

def execute_tools(state: State):
    message = state["messages"][-1]
    tool_messages = []

    for tool_call in message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_call_id = tool_call["id"]

        logger.info("[EXECUTE_TOOLS] Executing tool: %s with args: %s", tool_name, tool_args)

        tool_fn = TOOLS.get(tool_name)
        if tool_fn is None:
            logger.warning("[EXECUTE_TOOLS] Tool not found: %s", tool_name)
            result = f"Error: tool '{tool_name}' not found."
        else:
            try:
                result = tool_fn.invoke(tool_args)
            except Exception as e:
                logger.error("[EXECUTE_TOOLS] Tool '%s' raised an error: %s", tool_name, e)
                result = f"Error: {e}"

        tool_messages.append(ToolMessage(
            content=str(result),
            tool_call_id=tool_call_id
        ))

    return {"messages": tool_messages}

def update(state: State):
    logger.debug("[UPDATE] Scanning editor directory: %s", editor_path)
    project_structure = list_dir(editor_path)
    item_count = len(project_structure.get("structure", []))
    logger.info("[UPDATE] Directory snapshot refreshed (%d top-level items)", item_count)
    tool_message = str.format(
        structure_message,
        directory_tree=json.dumps(project_structure["structure"], indent=4)
    )
    existing_messages = state["messages"]
    if not isinstance(existing_messages, list):
        existing_messages = [existing_messages]
    return {"structure": project_structure, "messages": [SystemMessage(content=tool_message)] + existing_messages}

def list_dir(directory: str, max_depth: int = None) -> Dict[str, Any]:
    """
    List all files and directories in a directory structure.

    Args:
        directory: The directory to list
        max_depth: Maximum depth to traverse (None for unlimited)

    Returns:
        Dictionary containing the directory structure
    """
    depth_label = max_depth if max_depth is not None else "unlimited"
    logger.debug("[LIST] Listing '%s' (max_depth=%s)", directory, depth_label)

    dir_path = getpath(directory)

    if not dir_path.exists():
        logger.error("[LIST] Directory not found: %s", directory)
        raise FileNotFoundError(f"Directory not found: {directory}")

    if not dir_path.is_dir():
        logger.error("[LIST] Path is not a directory: %s", directory)
        raise ValueError(f"Path is not a directory: {directory}")

    def build_tree(path, current_depth=0):
        """Recursively build directory tree structure"""
        items = []

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
            logger.warning("[LIST] Permission denied, skipping: %s", path)

        return items

    structure = build_tree(dir_path)
    logger.debug("[LIST] Found %d top-level items under '%s'", len(structure), dir_path)

    return {
        "directory": str(dir_path),
        "structure": structure
    }

def route_converse(state: State):
    message = state["messages"][-1]
    if message.tool_calls:
        return "tools"
    return "validate"

def converse(state: State):
    message_count = len(state["messages"])
    logger.debug("[CONVERSE] Invoking LLM with %d message(s) in state", message_count)

    start = time.monotonic()
    response = llm.invoke([system_message] + state["messages"])
    elapsed = time.monotonic() - start

    tool_calls = getattr(response, "tool_calls", [])
    if tool_calls:
        tool_names = [tc.get("name", "unknown") for tc in tool_calls]
        logger.info("[CONVERSE] LLM responded in %.2fs — requesting tool(s): %s", elapsed, tool_names)
    else:
        preview = (response.content or "")[:120].replace("\n", " ")
        logger.info("[CONVERSE] LLM responded in %.2fs — content: \"%s%s\"",
                    elapsed, preview, "..." if len(response.content or "") > 120 else "")

    return {"messages": [response]}

def build(chkptr):
    graph_builder = StateGraph(State)

    # NODES

    # LLM's thinking node
    graph_builder.add_node("converse", converse)
    # Update the LLM's mental representation of the codebase structure
    graph_builder.add_node("update", update)
    # Provide LLM tools
    graph_builder.add_node("tools", execute_tools)
    # Once request is handled, validate
    graph_builder.add_node("validate", validate)
    # Handle validation pipeline failure
    # graph_builder.add_node("sendback", sendback)

    # EDGES

    # Entry
    graph_builder.add_edge(START, "update")
    # Update-reflect pattern
    graph_builder.add_edge("update", "converse")
    graph_builder.add_conditional_edges("converse", route_converse)  # tools or validate
    graph_builder.add_edge("tools", "update")                        # loop back
    graph_builder.add_conditional_edges("validate", determine_quality)  # uncomment when ready
    # Once LLM thinks code is ready, it can send to validation pipeline
    # graph_builder.add_conditional_edges("validate", determine_grade)
    # Failure handling
    # graph_builder.add_edge("sendback", "converse")

    return graph_builder.compile(interrupt_after=["converse"], checkpointer=chkptr)

def init():
    logger.info("[BUILD] Constructing graph")
    global graph
    graph = build(MemorySaver())
    logger.info("[BUILD] Graph compiled successfully")
    print(graph.get_graph().draw_ascii())
    # logger.debug("[BUILD] Graph structure:\n%s", graph.get_graph().draw_ascii())

def run(user_input: str, user_id: str):
    logger.info("[RUN] ── New pipeline run ── user=%s", user_id)
    logger.debug("[RUN] Query: %s", user_input)

    global graph

    if not graph:
        logger.info("[RUN] No existing graph found — building now")
        init()
    else:
        logger.debug("[RUN] Reusing existing graph instance")

    # Run the graph
    logger.debug("[RUN] Invoking graph (thread_id=%s)", user_id)
    start = time.monotonic()
    response = graph.invoke(
        {"messages": [HumanMessage(content=user_input)]},
        {"configurable": {"thread_id": user_id}}
    )
    elapsed = time.monotonic() - start
    logger.info("[RUN] Graph invocation complete in %.2fs", elapsed)

    # Bring edited code to output
    # TODO: remove when validation pipeline is ready!
    logger.debug("[RUN] Transferring output from '%s' to '%s'", editor_path, output_path)
    transfer(editor_path, output_path)
    logger.info("[RUN] Output transfer complete")

    return response['messages'][-1].content