import os
import subprocess
import json
from typing import List, Dict, Any

class DynamicAnalysisStage:
    """Class to run the dynamic analysis stage of the validation pipeline"""

    def __init__(self, output_dir: str):
        """
        Initialize the dynamic analysis stage with where to write stage's output (this refers 
        to root from which to write tool output).

        Args:
            output_dir: Path to directory to which this stage will write all generated artifacts
                        and/or log files (may be existing directory or nonexisting, in which case
                        a new directory will be created at the specified path)
                
            (NOTE: these may or may not be a relative path; if relative, this initializer normalizes
            the relative path to be an absolute path)
        """
        self.output_dir = os.path.abspath(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)

        self.logs_dir = os.path.join(self.output_dir, "logs/")
        os.makedirs(self.logs_dir, exist_ok=True)

    # ------------------------------------------------------------------------
    #     PUBLIC METHODS 
    # ------------------------------------------------------------------------

    def run(
        self, 
        executable_path: str,
        flags: List
    ) -> Dict[str, Any]:
        
        executable_path = os.path.abspath(executable_path)
        if not os.path.exists(executable_path):
            raise FileNotFoundError(f"Executable not found: {executable_path}")
        


        cmd = [
            "valgrind",
            *flags,
            executable_path
        ]

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )

        result = {
            "cmd": ' '.join(cmd),
            "success": proc.returncode == 0,
            "stdout": proc.stdout,
            "stderr": proc.stderr
        }

        self.write_logs(result)

        return result
    
    # ------------------------------------------------------------------------
    #     PRIVATE METHODS
    # ------------------------------------------------------------------------

    def write_logs(self, result: Dict[str, Any]) -> None:
        """Write Valgrind output to log files"""

        valgrind_path = os.path.join(self.logs_dir, "valgrind.log")
        print(f"valgrind_path: {valgrind_path}")
        summary_path = os.path.join(self.logs_dir, "summary.json")
        print(f"summary_path: {summary_path}")

        with open(valgrind_path, "w") as f:
            for key, value in result.items():
                # Reformat command field for prettier log printing
                value = value.replace(" ", "\n\t") if key == "cmd" else value
                f.write(f"{key}: {value}\n\n")

        with open(summary_path, "w") as f:
            json.dump(result, f, indent=4)