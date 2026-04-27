from langchain_core.messages import HumanMessage, ToolMessage
from unittest.mock import MagicMock, patch
from generation_pipeline import Pipeline
from openai import APITimeoutError
from tools import *
import tempfile, os, pytest

class TestGenerationPipelineInstance:
    def __init__(self):
        self.pipeline = Pipeline()
    
    # Helper functions (NOT TESTS):
    
    def content(self, result):
        return result["messages"][0].content
    
    def mocktool(content):
        mock = MagicMock()
        mock.tool_calls = [content]
        return mock

    ### ROUTERS ###

    # Grading Router

    def test_grading_router_pass(self):
        state = {"attempts_left": 2}
        assert self.pipeline.grading_router(state) == "pass"

    def test_grading_router_fail(self):
        state = {"attempts_left": 2}
        assert self.pipeline.grading_router(state) == "fail"

    def test_grading_router_insufficient_no_attempts(self):
        state = {"attempts_left": 0}
        assert self.pipeline.grading_router(state) == "insufficient"

    def test_grading_router_insufficient_retry_disabled(self):
        self.pipeline.config["retry_prompt"] = False
        state = {"attempts_left": 2}
        assert self.pipeline.grading_router(state) == "insufficient"

    # Post Converse Router

    def test_post_converse_router_tools(self):
        msg = MagicMock()
        msg.tool_calls = [{"name": "read", "args": {"path": "workshop/input/test.py", "encoding": "utf-8"}, "id": "1"}]
        state = {"messages": [msg]}
        assert self.pipeline.post_converse_router(state) == "tools"

    def test_post_converse_router_validate(self):
        msg = MagicMock()
        msg.tool_calls = []
        state = {"messages": [msg]}
        assert self.pipeline.post_converse_router(state) == "validate"

    # Summarization Router

    def test_summarization_router_summarize(self):
        state = {"messages": [MagicMock()] * 25}  # > summarize_after (20)
        assert self.pipeline.summarization_router(state) == "summarize"

    def test_summarization_router_converse(self):
        state = {"messages": [MagicMock()] * 5}
        assert self.pipeline.summarization_router(state) == "converse"
    
    ### NODES ###

    # Tool Node

    def test_tool_node_success_read(self):

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("SOMEONE PLEASE REEEEAAAAADDDDDMMMMMMMMMMMMEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE")
            tmp_path = f.name

        try:
            msg = self.mocktool(
                {
                    "name": "read",
                    "args": {
                        "path": tmp_path, 
                        "encoding": "utf-8"
                    },
                    "id": "read_succ"
                }
            )
            state = {"messages": [msg]}

            with patch("generation_pipeline.TOOLS", {"read": read}):
                result = self.pipeline.tool_node(state)
            parsed = eval(self.content(result))

            assert len(result["messages"]) == 1
            assert parsed["content"] == "hello world"
            assert parsed["encoding"] == "utf-8"
            assert parsed["path"] == tmp_path

        finally:
            os.unlink(tmp_path)
    
    def test_tool_node_success_write(self):

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("")
            tmp_path = f.name

        try:
            msg = self.mocktool(
                {
                    "name": "write",
                    "args": {
                        "path": tmp_path, 
                        "content": "hola cola ::))", 
                        "encoding": "utf-8", 
                        "mode": "overwrite", 
                        "create_directories": False
                    },
                    "id": "write_succ"
                }
            )
            state = {"messages": [msg]}

            with patch("generation_pipeline.TOOLS", {"write": write}):
                result = self.pipeline.tool_node(state)
            
            with open(tmp_path, 'r') as res:
                text = res.read()
            parsed = eval(self.content(result))

            assert len(result["messages"]) == 1
            assert text == "hola cola ::))"
            assert parsed["mode"] == "overwrite"
            assert parsed["size"] > 0
            assert parsed["path"] == tmp_path

        finally:
            os.unlink(tmp_path)
    
    def test_tool_node_success_remove(self):

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("byebye")
            tmp_path = f.name

        try:
            msg = self.mocktool(
                {
                    "name": "write",
                    "args": {
                        "path": tmp_path, 
                        "recursive": False
                    },
                    "id": "remove_succ"
                }
            )
            state = {"messages": [msg]}

            with patch("generation_pipeline.TOOLS", {"remove": remove}):
                result = self.pipeline.tool_node(state)
            
            parsed = eval(self.content(result))

            assert parsed["path"] == tmp_path
            assert parsed["removed"]
            assert parsed["type"] == "file"

        finally:
            os.unlink(tmp_path)
    
    def test_tool_node_remove_unknown_path(self):

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("byebye")
            tmp_path = f.name

        try:
            msg = self.mocktool(
                {
                    "name": "remove",
                    "args": {
                        "path": "idontexistlol.mp5", 
                        "recursive": False
                    },
                    "id": "remove_unkpth"
                }
            )
            state = {"messages": [msg]}

            with pytest.raises(FileNotFoundError):
                remove.invoke(state)

        finally:
            os.unlink(tmp_path)

    def test_tool_node_unknown_tool(self):
        piss_on_porch = MagicMock()
        exp = ToolMessage(
            content=str(result),
            tool_call_id="piss_on_porch"
        )

        with patch("generation_self.pipeline.TOOLS", {"piss_on_porch": piss_on_porch}):
            msg = self.mocktool({
                "name": "pop",
                "args": {"path": "workshop/editor/test.py", "encoding": "utf-9"}, 
                "id": "exread"
            })
            result = self.pipeline.tool_node({"messages": [msg]})

        assert isinstance(self.content(result), ToolMessage)
        assert self.content(result)["content"] == "Error: tool 'piss_on_porch' not found."

    def test_tool_node_tool_exception_write(self):
        mock_tool = MagicMock()
        mock_tool.invoke.side_effect = RuntimeError("runtime_error")

        with patch("generation_self.pipeline.TOOLS", {"bad_tool": mock_tool}):
            msg = MagicMock()
            msg.tool_calls = [
                {
                    "name": "write",
                    "args": {
                    "path": "workshop/editor/test.py", 
                    "content": 420, 
                    "encoding": "utf-8", 
                    "mode": "overwrite", 
                    "create_directories": False
                    }, 
                    "id": "exwrite"
                }
            ]
            result = self.pipeline.tool_node({"messages": [msg]})

        assert "runtime_error" in self.content(result)

    # Validate Node

    def test_validate_node_initializes_attempts(self):
        self.pipeline.validator.run.return_value = {"success": True}
        state = {"attempts_left": None, "validations": []}
        result = self.pipeline.validate_node(state)
        assert result["attempts_left"] == self.pipeline.config["return_anyway_after"]

    def test_validate_node_decrements_attempts(self):
        self.pipeline.validator.run.return_value = {"success": True}
        state = {"attempts_left": 2, "validations": []}
        result = self.pipeline.validate_node(state)
        assert result["attempts_left"] == 1

    def test_validate_node_appends_results(self):
        self.pipeline.validator.run.return_value = {"stage": "ok"}
        state = {"attempts_left": 1, "validations": [{"prior": "run"}]}
        result = self.pipeline.validate_node(state)
        assert len(result["validations"]) == 2

    # Converse Node

    def test_converse_node_success(self):
        self.pipeline.model.invoke.return_value = MagicMock(content="Here is the code.")
        state = {"messages": [HumanMessage(content="Write a function")], "summarized_messages": None}
        result = self.pipeline.converse_node(state)
        assert self.content(result) == "Here is the code."

    def test_converse_node_timeout(self):
        self.pipeline.model.invoke.side_effect = APITimeoutError(request=MagicMock())
        state = {"messages": [HumanMessage(content="Do something")], "summarized_messages": None}
        result = self.pipeline.converse_node(state)
        assert "timed out" in self.content(result)

    # Sendback Node

    def test_sendback_node(self):
        self.pipeline.model.invoke.return_value = MagicMock(content="Fix this issue.")
        state = {"validations": [{"lint": {"success": False}}]}
        result = self.pipeline.sendback_node(state)
        assert self.content(result) == "Fix this issue."