import os
import subprocess
import json
from typing import List, Dict, Any
from utils import fmt_field

class DynamicAnalysisStage:
    """Class to run the dynamic analysis stage of the validation pipeline"""

    def __init__(self, logs_dir: str):
        """
        Initialize the dynamic analysis stage with where to write stage's output (this refers
        to root from which to write tool output).

        Args:
            logs_dir: Path to directory to which this stage will write all generated log files
                      (may be existing directory or nonexisting, in which case
                      a new directory will be created at the specified path)

            (NOTE: these may or may not be a relative path; if relative, this initializer normalizes
            the relative path to be an absolute path)
        """
        self.logs_dir = os.path.abspath(logs_dir)
        os.makedirs(self.logs_dir, exist_ok=True)

    # ------------------------------------------------------------------------
    #     PUBLIC METHODS
    # ------------------------------------------------------------------------

    def run(self, executable_path: str, tools: List[str] = None, flags: List[str] = None) -> Dict[str, Any]:
        """
        Run one or more Valgrind tools on the executable.

        Args:
            executable_path: Path to the compiled executable.
            tools: Valgrind tools to run. Supported: memcheck, helgrind, massif, callgrind.
                   Defaults to ["memcheck"].
            flags: Command-line arguments passed to the executable.

        Returns:
            {
                "<tool>": { "cmd": "...", "success": bool, "stdout": "...", "stderr": "..." },
                ...
                "overall_success": bool   # True only if every tool passed
            }
        """
        if not executable_path:
            return {"overall_success": False, "error": "Executable path is None."}

        if not tools:
            tools = ["memcheck"]

        executable_path = os.path.abspath(executable_path)
        tool_results: Dict[str, Any] = {}

        for tool in tools:
            cmd = ["valgrind", f"--tool={tool}", executable_path] + (flags or [])
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            tool_results[tool] = {
                "cmd": " ".join(cmd),
                "success": proc.returncode == 0,
                "stdout": proc.stdout,
                "stderr": proc.stderr
            }

        overall = all(r["success"] for r in tool_results.values())
        results = {**tool_results, "overall_success": overall}

        self._write_logs(results)

        return results

    # ------------------------------------------------------------------------
    #     PRIVATE METHODS
    # ------------------------------------------------------------------------

    def _write_logs(self, result: Dict[str, Any]) -> None:
        """Write Valgrind output to per-tool log files"""

        os.makedirs(self.logs_dir, exist_ok=True)

        for key, value in result.items():
            if key == "overall_success":
                continue

            tool_dir = os.path.join(self.logs_dir, key)
            os.makedirs(tool_dir, exist_ok=True)

            valgrind_path = os.path.join(tool_dir, "valgrind.log")
            with open(valgrind_path, "w") as f:
                for field, field_val in value.items():
                    f.write(fmt_field(field, field_val))

        summary_path = os.path.join(self.logs_dir, "summary.json")
        with open(summary_path, "w") as f:
            json.dump(result, f, indent=4)
