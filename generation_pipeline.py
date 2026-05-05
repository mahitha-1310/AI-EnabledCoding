import os, json
import streamlit as st
from typing_extensions import TypedDict
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from Validation.validation_pipeline import ValidationPipeline
from langgraph.graph.message import add_messages
from typing import Annotated
from config import HasaimConfiguration
from rag.retriever import RAGRetriever

from tools import *
from utils import *

class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    summaries: list[BaseMessage]
    structure: Dict[str, Any]
    validations: list[Dict[str, Any]]
    attempts_left: int

class Pipeline():
    def __init__(self):

        # Model init
        self.config = HasaimConfiguration({
            "summarize_after": 20,
            "messages_to_keep": 10,
            "return_anyway_after": 3,
            "retrieval_chunks": 6,
            "retry_prompt": True
        })

        self._model_name = os.getenv("OPENAI_API_MODEL")
        model_temperature = float(os.getenv("TEMPERATURE"))
        model_tools = list(TOOLS.values())
        self.model = ChatOpenAI(
            model=self._model_name,
            temperature=model_temperature,
            base_url=os.getenv("OPENAI_API_BASE"),
            timeout=int(os.getenv("MODEL_TIMEOUT")),
            max_retries=0
        ).bind_tools(model_tools)

        # Pipeline init
        self.graph = self.build(MemorySaver())
        # print(self.graph.get_graph().draw_ascii())
        # Validation init
        self.validator = ValidationPipeline(output_dir=PATH.testing_path, source_dir=PATH.editor_path)
        # RAG init
        self.rag = RAGRetriever()

    ### ROUTERS ###

    def grading_router(self, state: State):
        if grade(output_path=PATH.testing_path):
            return "pass"

        attempts_left = state.get("attempts_left", 0)

        if attempts_left == 0:
            if self.config["retry_prompt"]:
                st.session_state.pending_retry = True
                st.session_state.pending_retry_count = self.config["return_anyway_after"]
            else:
                print("[WARNING]: Code is not guaranteed to be functional.")
            return "insufficient"

        return "fail"

    def post_converse_router(self, state: State):
        message = state["messages"][-1]
        if message.tool_calls:
            return "tools"
        return "validate"
    
    def summarization_router(self, state: State):
        return "summarize" if len(state["messages"]) > self.config["summarize_after"] else "converse"

    ### NODES ###

    def tool_node(self, state: State):
        message = state["messages"][-1]
        tool_messages = []

        for tool_call in message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_call_id = tool_call["id"]

            print(f"[Pipeline] Executing tool: {tool_name}")

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

        return {"messages": tool_messages}

    def update_node(self, state: State):
        print("[Pipeline] Updating project structure...")
        project_structure = list_dir(PATH.editor_path)
        tool_message = str.format(
            PATH.structure_message,
            directory_tree=json.dumps(project_structure["structure"], indent=4)
        )

        trimmed = state["messages"][-self.config["summarize_after"]:]

        return {"structure": project_structure, "messages": trimmed + [SystemMessage(content=tool_message)]}

    def validate_node(self, state: State):
        print("[Pipeline] Running validation pipeline...")

        attempts_left = state.get("attempts_left")

        if attempts_left is None:
            attempts_left = self.config["return_anyway_after"] - 1
        else:
            attempts_left -= 1

        results = self.validator.run()

        return {
            "attempts_left": attempts_left,
            "validations": state.get("validations", []) + [results]
        }

    def summarize_node(self, state: State):
        print("[Pipeline] Summarizing conversation history...")
        messages = state["messages"]

        summarize = messages[:-self.config["messages_to_keep"]]
        preserve  = messages[-self.config["messages_to_keep"]:]

        history = "\n".join(
            f"{msg.__class__.__name__}: {parse_content(msg.content)}"
            for msg in summarize
            if msg.content and not isinstance(msg, SystemMessage)
        )

        summary = self.model.invoke([HumanMessage(content=PATH.summarization_message.format(history=history))])

        summary_message = SystemMessage(
            content=f"[Conversation summary so far]: {summary.content}"
        )

        return {"summaries": [summary_message] + preserve}

    def sendback_node(self, state: State):
        print("[Pipeline] Sending validation feedback back to model...")
        summary_json = json.dumps(state.get("validations", [{}])[-1])

        response = self.model.invoke([HumanMessage(content=PATH.feedback_message.format(summary=summary_json))])

        return {"messages": [SystemMessage(content=response.content)]}

    def converse_node(self, state: State):
        print("[Pipeline] Model is generating a response...")
        try:
            messages = state.get("summarized_messages") or state["messages"]
            text = "\n".join(parse_content(msg.content) for msg in messages)
            num_chunks = self.config.get("retrieval_chunks")
            rag_data = self.rag.retrieve(query=text, k=num_chunks) if num_chunks > 0 else {}
            rag_context = json.dumps(rag_data, indent=2) if rag_data else ""
            response = self.model.invoke([SystemMessage(content=PATH.system_message.replace("{rag_context}", rag_context))] + messages)
        except Exception as e:
            print(e)
            response = AIMessage(content=e)
        return {"messages": [response]}

    ### INITIALIZATION ###

    def get_model_name(self):
        return self._model_name

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
        graph_builder.add_edge("sendback", "converse")

        graph_builder.add_conditional_edges("converse", self.post_converse_router, {"tools": "tools", "validate": "validate"})
        graph_builder.add_edge("tools", "update")
        # Once LLM thinks code is ready, it can send to validation pipeline
        graph_builder.add_conditional_edges("validate", self.grading_router, {"pass": END, "fail": "sendback", "insufficient": END})

        return graph_builder.compile(checkpointer=checkpointer)

    def run(self, user_input: str, user_id: str):
        if not self.graph:
            self.build(MemorySaver())

        response = self.graph.invoke(
            {"messages": [HumanMessage(content=user_input)]},
            {"configurable": {"thread_id": user_id}}
        )

        return self._get_llm_response(response)

    def resume(self, user_id: str, extra_attempts: int) -> str:
        if not self.graph:
            self.build(MemorySaver())

        response = self.graph.invoke(
            {"attempts_left": extra_attempts},
            {"configurable": {"thread_id": user_id}}
        )

        return self._get_llm_response(response)

    def _get_llm_response(self, response: dict) -> str:

        resp = response['messages'][-1]
        if resp.content:
            return resp.content

        validations = response.get("validations", [])
        if validations:
            v = validations[-1]
            lines = ["(The model produced no text response. Validation summary:"]
            for stage, result in v.items():
                if isinstance(result, dict):
                    ok = result.get("overall_success", result.get("success", "?"))
                    lines.append(f"  {stage}: {'OK' if ok else 'FAILED'}")
            return "\n".join(lines)

        return "No response generated."