import os, json
from typing_extensions import TypedDict
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from openai import APITimeoutError
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from Validation.validation_pipeline import ValidationPipeline
from langgraph.graph.message import add_messages
from typing import Annotated
from config import HasaimConfiguration
from rag.rag_orchestrator import RAGRetriever
from rag_manager import embed_repo
import traceback as tb

from tools import *
from utils import *

_shared_checkpointer = None

def _get_checkpointer():
    global _shared_checkpointer
    if _shared_checkpointer is None:
        _shared_checkpointer = MemorySaver()
    return _shared_checkpointer

class State(TypedDict):
    rag_url: str
    rag_contents: str
    messages: Annotated[list[BaseMessage], add_messages]
    summaries: list[BaseMessage]
    structure: Dict[str, Any]
    validations: list[Dict[str, Any]]
    attempts_left: int

class Pipeline():
    def __init__(self, user_id: str = None):
        self.user_id = user_id


        # Config init
        self.model_config = HasaimConfiguration({
            "summarize_after": 20,
            "messages_to_keep": 10,
            "return_anyway_after": 3,
            "retry_prompt": True,
            "temperature": 0.3,
            "timeout": 120
        })
        self.rag_config = HasaimConfiguration({
            "repository_url": "https://github.com/TheAlgorithms/C",
            "retrieval_chunks": 6,
            "batch_size": 64
        })
        

        # Model init
        self._model_name = os.getenv("OPENAI_API_MODEL")
        model_tools = list(TOOLS.values())
        self.model = ChatOpenAI(
            model=self._model_name,
            base_url=os.getenv("OPENAI_API_BASE"),
            max_retries=10
        ).bind_tools(model_tools)

        # Path init
        self.paths = get_user_paths(user_id)
        # Pipeline init
        self.graph = self._build(_get_checkpointer())
        print(self.graph.get_graph().draw_ascii())
        # Validation init
        self.validator = ValidationPipeline(
            output_dir=project_path(self.paths.testing_path),
            source_dir=project_path(self.paths.editor_path)
        )
        # RAG init
        self.rag = RAGRetriever()
        self._embedded_url: str | None = None

    ### ROUTERS ###

    def grading_router(self, state: State):
        if grade(output_path=project_path(self.paths.testing_path)):
            return "pass"

        attempts_left = state.get("attempts_left", 0)

        if not self.model_config.get("retry_prompt") or attempts_left == 0:
            print("[WARNING]: Code is not guaranteed to be functional.")
            return "insufficient"

        return "fail"

    def post_converse_router(self, state: State):
        message = state["messages"][-1]
        if message.tool_calls:
            return "tools"
        return "validate"
    
    def summarization_router(self, state: State):
        return "summarize" if len(state["messages"]) > self.model_config.get("summarize_after") else "converse"


    ###############
    
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
                    tb.print_exc()

            tool_messages.append(ToolMessage(
                content=str(result),
                tool_call_id=tool_call_id
            ))

        return {"messages": tool_messages}

    def update_node(self, state: State):
        url = self.rag_config.get("repository_url")
        if url and url != self._embedded_url:
            embed_repo(self.rag.collection, url, self.rag_config.get("batch_size"))
            self._embedded_url = url

        print("[Pipeline] Updating project structure...")
        project_structure = list_dir(self.paths.editor_path)
        tool_message = str.format(
            self.paths.structure_message,
            directory_tree=json.dumps(project_structure["structure"], indent=4)
        )

        trimmed = state["messages"][-self.model_config.get("summarize_after"):]

        new_state = {"structure": project_structure, "messages": trimmed + [SystemMessage(content=tool_message)]}

        if url:
            new_state["rag_url"] = url

        return new_state

    def validate_node(self, state: State):
        print("[Pipeline] Running validation pipeline...")

        attempts_left = state.get("attempts_left")
        if attempts_left is None:
            attempts_left = self.model_config.get("return_anyway_after") - 1
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

        summarize = messages[:-self.model_config.get("messages_to_keep")]
        preserve  = messages[-self.model_config.get("messages_to_keep"):]

        history = "\n".join(
            f"{msg.__class__.__name__}: {msg.content}"
            for msg in summarize
            if msg.content and not isinstance(msg, SystemMessage)
        )

        summary = self.model.invoke([HumanMessage(content=get_global_prompts().summarization_message.format(history=history))])

        summary_message = SystemMessage(
            content=f"[Conversation summary so far]: {summary.content}"
        )

        return {"summaries": [summary_message] + preserve}

    def sendback_node(self, state: State):
        print("[Pipeline] Sending validation feedback back to model...")
        
        summary_json = json.dumps(state.get("validations", [{}])[-1])

        response = self.model.invoke([HumanMessage(content=get_global_prompts().feedback_message.format(summary=summary_json))])

        return {"messages": [SystemMessage(content=response.content)]}

    def converse_node(self, state: State):
        print("[Pipeline] Model is generating a response...")

        try:
            self.model.bind(temperature=self.model_config.get("temperature"), timeout=self.model_config.get("timeout"))
        except Exception:
            tb.print_exc()

        state_updates = {}
        response = None
        
        try:
            history = state.get("summarized_messages") or state["messages"]

            rag_data = ""
            if state.get("rag_url") is not None:
                last_human = next(
                    (msg for msg in reversed(history) if isinstance(msg, HumanMessage) and msg.content),
                    None
                )
                if last_human:
                    new_data = self.rag.retrieve(last_human.content, self.rag_config.get("retrieval_chunks"))
                    rag_data = self.rag.build_context(new_data)
                    state_updates["rag_contents"] = rag_data
            else:
                state_updates["rag_contents"] = None
            
            response = self.model.invoke(
                [SystemMessage(content=get_global_prompts().system_message.replace("{RAGDATA}", rag_data))] + history
            )
        except APITimeoutError:
            print("[Pipeline] WARNING: Model request timed out.")
            response = AIMessage(content="[Error: the model timed out and could not produce a response. Please try again.]")
        except Exception as e:
            print(f"[Pipeline] ERROR: Failed to generate response: {e}")
            tb.print_exc()
            response = AIMessage(content=f"[Error: Failed to generate response: {str(e)}]")
        
        if response is None:
            response = AIMessage(content="[Error: No response generated. Please try again.]")

        state_updates["messages"] = [response]
        return state_updates

    #############
    
    def _reflect(self, response):
        last = response['messages'][-1]
        response_text = ""
        validations = response.get("validations", [])
        
        if last.content:
            response_text = last.content
        else:
            if validations:
                v = validations[-1]
                lines = ["The model produced no text response. Validation summary:"]
                for stage, result in v.items():
                    if isinstance(result, dict):
                        ok = result.get("overall_success", result.get("success", "?"))
                        lines.append(f"  {stage}: {'OK' if ok else 'FAILED'}")
                response_text = "\n".join(lines)
            else:
                response_text = "No response generated."
        
        attempts_left = response.get("attempts_left", 0)
        
        last_validation_failed = len(validations) > 0 and not grade(output_path=project_path(self.paths.testing_path))
        needs_retry_prompt = (
            self.model_config.get("retry_prompt") and
            attempts_left > 0 and
            last_validation_failed
        )
        
        metadata = {
            "attempts_left": attempts_left,
            "needs_retry_prompt": needs_retry_prompt,
            "validations_count": len(validations)
        }

        return response_text, metadata

    def _build(self, checkpointer):
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
        return self._reflect(
            self.graph.invoke(
                {"messages": [HumanMessage(content=user_input)]},
                {"configurable": {"thread_id": user_id}}
            )
        )
