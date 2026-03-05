import os, json
from dotenv import load_dotenv
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from Validation.validation_pipeline import ValidationPipeline
from langgraph.graph.message import add_messages
from typing import Annotated

from tools import *
from utils import *

SYSTEM_PROMPT    = os.path.join("prompt", "system_prompt.md")
STRUCTURE_PROMPT = os.path.join("prompt", "structure_prompt.md")

class State(TypedDict):
        messages: Annotated[list[BaseMessage], add_messages]
        structure: Dict[str, Any]

class Pipeline():
    def __init__(self):
        
        self.input_path = os.getenv("INPUT_PATH")
        self.editor_path = os.getenv("EDITOR_PATH")
        self.output_path = os.getenv("OUTPUT_PATH")

        model_name = os.getenv("OPENAI_API_MODEL")
        model_tools = list(TOOLS.values())
        self.model = ChatOpenAI(model=model_name).bind_tools(model_tools)

        self.system_message = read_path(SYSTEM_PROMPT)
        self.structure_message = read_path(STRUCTURE_PROMPT)

        self.validator = ValidationPipeline(output_dir=self.output_path, source_dir=self.editor_path)

        self.graph = self.build(MemorySaver())
        print(graph.get_graph().draw_ascii())

    ### ROUTERS ###

    def grading_router(self, state: State):
        return "pass" if grade(output_path=self.output_path) else "fail"

    def post_converse_router(self, state: State):
        message = state["messages"][-1]
        if message.tool_calls:
            return "tools"
        return "validate"
    
    ###############
    
    ### NODES ###

    def tool_node(self, state: State):
        message = state["messages"][-1]
        tool_messages = []

        for tool_call in message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_call_id = tool_call["id"]

            tool_fn = TOOLS.get(tool_name)
            if tool_fn is None:
                result = f"Error: tool '{tool_name}' not found."
            else:
                try:
                    result = tool_fn.invoke(tool_args)
                except Exception as e:
                    result = f"Error: {e}"

            tool_messages.append(ToolMessage(
                content=str(result),
                tool_call_id=tool_call_id
            ))

        return {"messages": [tool_messages] + state["messages"]}

    def update_node(self, state: State):
        project_structure = list_dir(self.editor_path)
        tool_message = str.format(
            self.structure_message,
            directory_tree=json.dumps(project_structure["structure"], indent=4)
        )
        if not isinstance(existing_messages, list):
            existing_messages = [existing_messages]
        return {"structure": project_structure, "messages": [SystemMessage(content=tool_message)] + state["messages"]}

    def validate_node(self, state: State):
        results = self.validator.run()
        print(results)
        return state
    
    def sendback_node(self, state: State):
        return state

    def converse_node(self, state: State):
        # message_count = len(state["messages"])

        # start = time.monotonic()
        response = self.model.invoke([SystemMessage(content=self.system_message)] + state["messages"])
        # elapsed = time.monotonic() - start

        # tool_calls = getattr(response, "tool_calls", [])
        # if tool_calls:
        #     tool_names = [tc.get("name", "unknown") for tc in tool_calls]
        #     logger.info("[CONVERSE] LLM responded in %.2fs — requesting tool(s): %s", elapsed, tool_names)
        # else:
        #     preview = (response.content or "")[:120].replace("\n", " ")
        #     logger.info("[CONVERSE] LLM responded in %.2fs — content: \"%s%s\"",
        #                 elapsed, preview, "..." if len(response.content or "") > 120 else "")

        return {"messages": [response]}

    #############

    def build(self, checkpointer):
        graph_builder = StateGraph(State)

        # NODES

        # LLM's thinking node
        graph_builder.add_node("converse", self.converse_node)
        # Update the LLM's mental representation of the codebase structure
        graph_builder.add_node("update", self.update_node)
        # Provide LLM tools
        graph_builder.add_node("tools", self.tool_node)
        # Once request is handled, validate
        graph_builder.add_node("validate", self.validate_node)
        # Handle validation pipeline failure
        graph_builder.add_node("sendback", self.sendback_node)

        # EDGES

        # Entry
        graph_builder.add_edge(START, "update")
        # Update-reflect pattern
        graph_builder.add_edge("update", "converse")
        graph_builder.add_conditional_edges("converse", self.post_converse_router, {"tools": "tools", "validate": "validate"})
        graph_builder.add_edge("tools", "update")
        # Once LLM thinks code is ready, it can send to validation pipeline
        graph_builder.add_conditional_edges("validate", self.grading_router, {"pass": END, "fail": "converse"})

        return graph_builder.compile(checkpointer=checkpointer)

    def init(self):
        global graph
        graph = self.build(MemorySaver())
        print(graph.get_graph().draw_ascii())
        # logger.debug("[BUILD] Graph structure:\n%s", graph.get_graph().draw_ascii())

def run(self, user_input: str, user_id: str):

    global graph

    if not graph:
        self.init()

    response = graph.invoke(
        {"messages": [HumanMessage(content=user_input)]},
        {"configurable": {"thread_id": user_id}}
    )

    return response['messages'][-1].content