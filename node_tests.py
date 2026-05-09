from langchain_core.messages import HumanMessage, ToolMessage
from unittest.mock import MagicMock, patch
from generation_pipeline import Pipeline
import inspect as insp
import tempfile, os, pytest

from tools import *

class TestGenerationPipelineInstance:
    def __init__(self):
        with patch("generation_pipeline.ChatOpenAI") as MockChatOpenAI:
            with patch.dict("os.environ", {
                "OPENAI_API_MODEL": "gpt-oss-120b",
                "OPENAI_API_BASE": "https://llm-api.arc.vt.edu/api/v1/",

                "TEMPERATURE": "0.3",
                "MODEL_TIMEOUT": "150"
            }):
                MockChatOpenAI.return_value.bind_tools.return_value = MagicMock()
                self.pipeline = Pipeline()
    
    def _msgcontent(self, result):
        return result["messages"][0].content
    
    def _mocktool(self, content):
        mock = MagicMock()
        mock.tool_calls = [content]
        return mock

    ### ROUTERS ###

    def grading_router_pass(self):
        with patch("generation_pipeline.grade", return_value=True):
            state = {"attempts_left": 2}

            assert self.pipeline.grading_router(state) == "pass"

    def grading_router_fail(self):
        with patch("generation_pipeline.grade", return_value=False):
            state = {"attempts_left": 2}

            assert self.pipeline.grading_router(state) == "fail"

    def grading_router_insufficient_no_attempts(self):
        with patch("generation_pipeline.grade", return_value=False):
            state = {"attempts_left": 0}

            assert self.pipeline.grading_router(state) == "insufficient"

    def post_converse_router_tools(self):
        msg = MagicMock()
        msg.tool_calls = [{"name": "read", "args": {"path": "workshop/input/test.py", "encoding": "utf-8"}, "id": "1"}]
        state = {"messages": [msg]}
        assert self.pipeline.post_converse_router(state) == "tools"

    def post_converse_router_validate(self):
        msg = MagicMock()
        msg.tool_calls = []
        state = {"messages": [msg]}
        assert self.pipeline.post_converse_router(state) == "validate"

    def summarization_router_summarize(self):
        state = {"messages": [MagicMock()] * 25}
        assert self.pipeline.summarization_router(state) == "summarize"

    def summarization_router_converse(self):
        state = {"messages": [MagicMock()] * 5}
        assert self.pipeline.summarization_router(state) == "converse"
    
    ### NODES ###

    def tool_node_success_read(self):

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("SOMEONE PLEASE REEEEAAAAADDDDDMMMMMMMMMMMMEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE")
            tmp_path = f.name

        msg = self._mocktool(
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
        parsed = eval(self._msgcontent(result))

        assert len(result["messages"]) == 1
        assert parsed["content"] == "SOMEONE PLEASE REEEEAAAAADDDDDMMMMMMMMMMMMEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE"
        assert parsed["encoding"] == "utf-8"
        assert parsed["path"] == tmp_path

        os.unlink(tmp_path)
    
    def tool_node_success_write(self):

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("")
            tmp_path = f.name

        msg = self._mocktool(
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
        parsed = eval(self._msgcontent(result))

        assert len(result["messages"]) == 1
        assert text == "hola cola ::))"
        assert parsed["mode"] == "overwrite"
        assert parsed["size"] > 0
        assert parsed["path"] == tmp_path

        os.unlink(tmp_path)
    
    def tool_node_success_remove(self):

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("byebye")
            tmp_path = f.name

        msg = self._mocktool(
            {
                "name": "remove",
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
        
        parsed = eval(self._msgcontent(result))

        assert parsed["path"] == tmp_path
        assert parsed["removed"]
        assert parsed["type"] == "file"
    
    def tool_node_remove_unknown_path(self):

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("byebye")

        with pytest.raises(FileNotFoundError):
            remove.invoke({"path": "idontexistlol.mp5", "recursive": False})

    def tool_node_unknown_tool(self):
        piss_on_porch = MagicMock()

        with patch("generation_pipeline.TOOLS", {"piss_on_porch": piss_on_porch}):
            msg = self._mocktool({
                "name": "pop",
                "args": {"path": "workshop/editor/test.py", "encoding": "utf-9"}, 
                "id": "exread"
            })
            result = self.pipeline.tool_node({"messages": [msg]})

        assert isinstance(result["messages"][0], ToolMessage)
        assert self._msgcontent(result) == "Error: tool 'pop' not found."

    def tool_node_tool_exception_write(self):
        mock_tool = MagicMock()
        mock_tool.invoke.side_effect = Exception("weird_tool_call")

        with patch("generation_pipeline.TOOLS", {"write": mock_tool}):
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
                    "id": "failed_write"
                }
            ]
            result = self.pipeline.tool_node({"messages": [msg]})

        assert "weird_tool_call" in self._msgcontent(result)

    def validate_node_initializes_attempts(self):
        with patch.object(self.pipeline.validator, 'run', return_value={"success": True}):
            state = {"attempts_left": None, "validations": []}
            result = self.pipeline.validate_node(state)
        assert result["attempts_left"] == self.pipeline.model_config["return_anyway_after"]-1

    def validate_node_decrements_attempts(self):
        with patch.object(self.pipeline.validator, 'run', return_value={"success": True}):
            state = {"attempts_left": 68, "validations": []}
            result = self.pipeline.validate_node(state)
        assert result["attempts_left"] == 67

    def validate_node_appends_results(self):
        with patch.object(self.pipeline.validator, 'run', return_value={"stage": "ok"}):
            state = {"attempts_left": 1, "validations": [{"prior": "run"}]}
            result = self.pipeline.validate_node(state)
        assert len(result["validations"]) == 2

    def converse_node_success(self):
        self.pipeline.model.invoke.return_value = MagicMock(content="Here is the code.")
        state = {"messages": [HumanMessage(content="Write a function the prints 'i miss your mom' 36 times.")], "summarized_messages": None}
        result = self.pipeline.converse_node(state)
        assert self._msgcontent(result) == "Here is the code."

    def sendback_node(self):
        with patch.object(self.pipeline, 'model') as mock_model:
            mock_model.invoke.return_value = MagicMock(content="Fix this issue.")
            state = {"validations": [{"lint": {"success": False}}]}
            result = self.pipeline.sendback_node(state)
        assert self._msgcontent(result) == "Fix this issue."

def main():

    tester = TestGenerationPipelineInstance()
    tests = []
    for test_name, test in insp.getmembers(tester, predicate=insp.ismethod):
        if not test_name.startswith('_'):
            tests.append((test_name, test))

    fails = 0
    for test_name, test in tests:
        try:
            test()
            print(f"[O] Test Passed: {test_name}")
        except Exception as e:
            print(f"[X] Test Failed: {test_name}\n    Reason: {e}")
            fails += 1
    
    if fails == 0:
        print("All tests passed! :D")
    elif fails == 1:
        print("1 issue remains.")
    else:
        print(f"{fails} issues remain.")

if __name__ == "__main__":
    main()