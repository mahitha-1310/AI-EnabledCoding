import os
import subprocess
import json
from typing import List, Dict, Any

class StaticAnalysisStage:
    """Class to run the static analysis stage of the validation pipeline"""

    def __init__(self, output_dir: str, project_root: str):
        """
        Initialize the static analysis stage with where to write stage's output
        (this refers to root from which to write captured static analysis outputs),
        as well as project root where source files are found.

        Args:
            output_dir: Path to directory to which this stage will write all generated artifacts
                        and/or log files (may be existing directory or nonexisting, in which case
                        a new directory will be created at the specified path)
            project_root: Path to project directory (where all source code/header files will be
                          found)
            
            (NOTE: these may or may not be a relative path; if relative, this initializer normalizes
            the relative path to be an absolute path)
        """
        self.project_root = os.path.abspath(project_root)

        self.output_dir = os.path.abspath(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)

        self.logs_dir = os.path.join(self.output_dir, "logs/")
        os.makedirs(self.logs_dir, exist_ok=True)

    # ------------------------------------------------------------------------
    #     PUBLIC METHODS 
    # ------------------------------------------------------------------------

    def run(
        self,
        source_files: List[str],
        compile_commands: str,
        static_analyzer:str = "clang-tidy"
    ):
        """
        Runs the static analysis stage of the validation pipeline

        Args:
            source_files: List of paths to source code (`.c`) files. May
                          be relative or absolute paths.
            compile_commands: A path to the `compile_commands.json` file needed by clang-tidy
            static_analyzer: Which static analyzer to use (default clang-tidy)
        
        NOTE: Eventually, cppcheck will also be implemented as an option
        """
        
        results = self._run_static_analysis(
            source_files=source_files,
            compile_commands=compile_commands,
            static_analyzer=static_analyzer
        )

        self._write_logs(results)

        return results

    # ------------------------------------------------------------------------
    #     PRIVATE HELPERS 
    # ------------------------------------------------------------------------

    def _run_static_analysis(
        self,
        source_files: List[str],
        compile_commands: str,
        static_analyzer: str = "clang-tidy"
    ) -> Dict[str, Any]:
        """
        Invokes the static analyzer on each source file.

        Returns:
            {
                "file_outputs": {
                    src_path: {
                        "cmd": "...",
                        "success": bool,
                        "stdout": "...",
                        "stderr": "...",
                    }
                },
                "overall_success": bool
            }
        """

        file_outputs: Dict[str, Any] = {}
        all_success = True

        # clang-tidy must be pointed to the build directory containing compile_commands.json
        build_dir = os.path.abspath(compile_commands)

        for src in source_files:
            src_abs = os.path.abspath(src)

            cmd = [
                static_analyzer,
                src_abs,
                "-p", build_dir
            ]

            try:
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True
                )
                success = proc.returncode == 0
                stdout = proc.stdout
                stderr = proc.stderr
            except FileNotFoundError:
                success = False
                all_success = False
                file_outputs[src_abs] = {
                    "cmd": ' '.join(cmd),
                    "success": False,
                    "stdout": "",
                    "stderr": (
                        f"Error: '{static_analyzer}' was not found."
                    )
                }
                continue

            if not success:
                all_success = False

            file_outputs[src_abs] = {
                "cmd": ' '.join(cmd),
                "success": success,
                "stdout": stdout,
                "stderr": stderr
            }

        return {
            "file_outputs": file_outputs,
            "overall_success": all_success
        }

    def _write_logs(self, results: Dict[str, Any]):
        """Write per-file logs + summary JSON."""

        os.makedirs(self.logs_dir, exist_ok=True)

        # Write per-file logs
        for src, file_result in results["file_outputs"].items():
            base = os.path.splitext(os.path.basename(src))[0]
            log_path = os.path.join(self.logs_dir, f"static_{base}.log")

            with open(log_path, "w") as f:
                for key, value in file_result.items():
                    # Reformat command field for prettier log printing
                    value = value.replace(" ", "\n\t") if key == "cmd" else value
                    f.write(f"{key}: {value}\n\n")

        # Write summary JSON
        summary_path = os.path.join(self.logs_dir, "summary.json")
        with open(summary_path, "w") as f:
            json.dump(results, f, indent=4)