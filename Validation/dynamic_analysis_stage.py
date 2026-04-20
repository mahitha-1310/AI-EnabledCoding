import os
import subprocess
import json
from typing import List, Dict, Any

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

    def run(self, executable_path: str, flags: List[str] = None) -> Dict[str, Any]:
        """
        Run dynamic analysis on the executable.

        Args:
            executable_path: Path to the compiled executable.
            flags: Additional flags for the dynamic analysis tool.

        Returns:
            A dictionary containing the results of the dynamic analysis.
        """
        if not executable_path:
            return {"success": False, "error": "Executable path is None."}

        executable_path = os.path.abspath(executable_path)

        cmd = ["valgrind", executable_path] + (flags or [])

        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        result = {
            "cmd": " ".join(cmd),
            "success": proc.returncode == 0,
            "stdout": proc.stdout,
            "stderr": proc.stderr
        }

        self._write_logs(result)

        return result

    # ------------------------------------------------------------------------
    #     PRIVATE METHODS
    # ------------------------------------------------------------------------

    def _write_logs(self, result: Dict[str, Any]) -> None:
        """Write Valgrind output to log files"""

        os.makedirs(self.logs_dir, exist_ok=True)

        valgrind_path = os.path.join(self.logs_dir, "valgrind.log")
        summary_path = os.path.join(self.logs_dir, "summary.json")

        with open(valgrind_path, "w") as f:
            for key, value in result.items():
                value = value.replace(" ", "\n\t") if key == "cmd" else value
                f.write(f"{key}: {value}\n\n")

        with open(summary_path, "w") as f:
            json.dump(result, f, indent=4)
