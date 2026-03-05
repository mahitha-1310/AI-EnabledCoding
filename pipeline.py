import os, json
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

SYSTEM_PROMPT = os.path.join("prompt", "system_prompt.md")
FEEDBACK_PROMPT = os.path.join("prompt", "feedback_prompt.md")
STRUCTURE_PROMPT = os.path.join("prompt", "structure_prompt.md")
SUMMARIZATION_PROMPT = os.path.join("prompt", "summarization_prompt.md")

SUMMARIZE_AFTER = 20  # summarize when message count exceeds this
MESSAGES_TO_KEEP = 10 # how many recent messages to keep after summarizing

class State(TypedDict):
        messages: Annotated[list[BaseMessage], add_messages]
        structure: Dict[str, Any]
        success: list[Dict[str, Any]]

class Pipeline():
    def __init__(self):
        
        self.input_path = os.getenv("INPUT_PATH")
        self.editor_path = os.getenv("EDITOR_PATH")
        self.output_path = os.getenv("OUTPUT_PATH")

        model_name = os.getenv("OPENAI_API_MODEL")
        model_tools = list(TOOLS.values())
        self.model = ChatOpenAI(model=model_name).bind_tools(model_tools)

        self.system_message = read_path(SYSTEM_PROMPT)
        self.feedback_message = read_path(FEEDBACK_PROMPT)
        self.structure_message = read_path(STRUCTURE_PROMPT)
        self.summarization_message = read_path(SUMMARIZATION_PROMPT)

        self.validator = ValidationPipeline(output_dir=self.output_path, source_dir=self.editor_path)

        self.graph = self.build(MemorySaver())
        print(self.graph.get_graph().draw_ascii())

    ### ROUTERS ###

    def grading_router(self, state: State):
        return "pass" if grade(output_path=self.output_path) else "fail"

    def post_converse_router(self, state: State):
        message = state["messages"][-1]
        if message.tool_calls:
            return "tools"
        return "validate"
    
    def summarization_router(self, state: State):
        return "summarize" if len(state["messages"]) > SUMMARIZE_AFTER else "converse"


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
        return state["success"].append(results)
    
    def summarize_node(self, state: State):
        messages = state["messages"]

        summarize = messages[:-MESSAGES_TO_KEEP]
        preserve  = messages[-MESSAGES_TO_KEEP:]

        history = "\n".join(f"{msg.__class__.__name__}: {msg.content}" for msg in summarize if msg.content)

        summary = self.model.invoke(HumanMessage(content=self.summarization_message.format(history=history)))

        summary_message = SystemMessage(
            content=f"[Conversation summary so far]: {summary.content}"
        )
    
        return [summary_message] + preserve
    
    def sendback_node(self, state: State):
        return state

    def converse_node(self, state: State):
        response = self.model.invoke([SystemMessage(content=self.system_message)] + state["messages"])
        return {"messages": [response]}

    #############

    def build(self, checkpointer):
        graph_builder = StateGraph(State)

        # NODES

        # Update the LLM's mental representation of the codebase structure
        graph_builder.add_node("update", self.update_node)
        # If message history gets too long, summarize
        graph_builder.add_node("summarize", self.summarize_node)
        # LLM's thinking node
        graph_builder.add_node("converse", self.converse_node)
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
        graph_builder.add_edge("summarize", "converse")
        graph_builder.add_conditional_edges("update", self.summarization_router, {"summarize": "summarize", "converse": "converse"})
        graph_builder.add_conditional_edges("sendback", self.summarization_router, {"summarize": "summarize", "converse": "converse"})

        graph_builder.add_conditional_edges("converse", self.post_converse_router, {"tools": "tools", "validate": "validate"})
        graph_builder.add_edge("tools", "update")
        # Once LLM thinks code is ready, it can send to validation pipeline
        graph_builder.add_conditional_edges("validate", self.grading_router, {"pass": END, "fail": "sendback"})

        return graph_builder.compile(checkpointer=checkpointer)

def run(pipeline: Pipeline, user_input: str, user_id: str):

    if not pipeline.graph:
        pipeline.build(MemorySaver())

    response = pipeline.graph.invoke(
        {"messages": [HumanMessage(content=user_input)]},
        {"configurable": {"thread_id": user_id}}
    )

    return response['messages'][-1].content