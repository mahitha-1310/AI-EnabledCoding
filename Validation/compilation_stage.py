import os
import re
import subprocess
import json
from typing import List, Dict, Any, Optional

MAKE_COMMAND = ["bear", "--", "make"]
MAKEFILE_ALIASES = ["Makefile", "makefile", "GNUmakefile"]

class CompilationStage:
    """Class to run the compilation stage of the validation pipeline"""

    def __init__(self, logs_dir: str, artifacts_dir: str, project_root: str):
        """
        Initialize the compilation stage with where to write stage's output (logs and artifacts),
        as well as the project root (where source code would be found).

        Args:
            logs_dir: Path to directory to which this stage will write all generated log files
            artifacts_dir: Path to directory to which this stage will write all generated artifacts
                           (`.o` files, executables, etc.)
            project_root: Path to project directory (where all source code/header files will be
                          found)

            (NOTE: these may or may not be a relative path; if relative, this initializer normalizes
            the relative path to be an absolute path)
        """
        self.project_root = os.path.abspath(project_root)

        # Create `logs/compilation/` subdirectory
        self.logs_dir = os.path.abspath(logs_dir)
        os.makedirs(self.logs_dir, exist_ok=True)

        # Create `artifacts/compilation/` subdirectory
        self.artifacts_dir = os.path.abspath(artifacts_dir)
        os.makedirs(self.artifacts_dir, exist_ok=True)

    # ------------------------------------------------------------------------
    #     PUBLIC METHODS
    # ------------------------------------------------------------------------

    def run(self) -> Dict[str, Any]:
        """
        Run the compilation stage of validation pipeline. This stage requires
        the presence of a `Makefile` in the project root directory.

        Returns:
            A dictionary mapping relevant outputs to the contents/states of the
            outputs, including:
                - success/failure of stage
                - generated errors/warnings
                - stdout/stderr
                - any misc. artifacts
        """
        if not self._makefile_exists():
            return {
                "make_output": {
                    "cmd": ' '.join(MAKE_COMMAND),
                    "success": False,
                    "stdout": "",
                    "stderr": "No Makefile found in project root."
                },
                "compile_commands_path": None,
                "executable_path": None,
                "error_type": "missing_makefile",
                "error_detail": (
                    "No Makefile was found in the project root directory. "
                    "Please upload a Makefile alongside your source files."
                )
            }

        # Run `make` build tool
        results = self._run_make_build()

        # Write logs to disk
        self._write_logs(results)

        return results

    # ------------------------------------------------------------------------
    #     PRIVATE HELPERS
    # ------------------------------------------------------------------------

    def _run_make_build(self) -> Dict[str, Any]:
        """
        Run `bear -- make` in the project root directory, capture stdout/stderr, and return results.

        Returns:
            A dictionary with:
                - "make_output": results of the `bear -- make` command (success, stdout, stderr).
                - "compile_commands_path": path to the generated `compile_commands.json` file,
                                           or None if `make` failed or did not generate a
                                           `compile_commands.json` file.
                - "executable_path": path to the generated executable, or None if `make` failed
                                     or did not generate an executable.
        """
        try:
            proc = subprocess.run(
                MAKE_COMMAND,
                cwd=self.project_root,
                capture_output=True,
                text=True
            )

            # Attempt to find generated `compile_commands.json` file
            compile_commands_path = os.path.join(self.project_root, "compile_commands.json")
            if not os.path.isfile(compile_commands_path):
                compile_commands_path = None

            # Attempt to find generated executable (if any)
            executable_path = None
            for file in os.listdir(self.project_root):
                full_path = os.path.join(self.project_root, file)
                if os.access(full_path, os.X_OK) and not os.path.isdir(full_path):
                    executable_path = full_path
                    break

            result = {
                "make_output": {
                    "cmd": ' '.join(MAKE_COMMAND),
                    "success": proc.returncode == 0,
                    "stdout": proc.stdout,
                    "stderr": proc.stderr
                },
                "compile_commands_path": compile_commands_path,
                "executable_path": executable_path
            }

            # If make failed, check whether the cause is an unsupported compiler
            if proc.returncode != 0:
                bad_compiler = self._detect_unsupported_compiler(proc.stderr)
                if bad_compiler:
                    result["error_type"] = "unsupported_compiler"
                    result["error_detail"] = (
                        f"The Makefile invokes '{bad_compiler}', which is not installed. "
                        f"Supported compilers are: clang, gcc."
                    )

            return result

        except Exception as e:
            print(f"Error running make: {e}")
            return {
                "make_output": {
                    "cmd": ' '.join(MAKE_COMMAND),
                    "success": False,
                    "stdout": "",
                    "stderr": str(e)
                },
                "compile_commands_path": None,
                "executable_path": None
            }

    def _write_logs(self, results: Dict[str, Any]) -> None:
        """
        Write compilation results to the `logs/` subdirectory.

        Args:
            results: a dictionary containing pertinent information gathered
                     from an attempt to compile via make
        """
        if "make_output" not in results:
            raise ValueError("Results dictionary is missing required key: 'make_output'.")

        os.makedirs(self.logs_dir, exist_ok=True)

        # ====================== STEP 1 ======================
        # Write `make` command output log
        make_log_path = os.path.join(self.logs_dir, "make_output.log")
        with open(make_log_path, "w") as f:
            for key, value in results["make_output"].items():
                f.write(f"{key}: {value}\n\n")
            f.write(f"compile_commands_path: {results['compile_commands_path']}\n\n")
            f.write(f"executable_path: {results['executable_path']}\n\n")

        # ====================== STEP 2 ======================
        # Write a summary JSON dump log
        summary_path = os.path.join(self.logs_dir, "summary.json")
        with open(summary_path, "w") as f:
            json.dump(results, f, indent=4)

    def _detect_unsupported_compiler(self, stderr: str) -> Optional[str]:
        """
        Scan make stderr for patterns that indicate a missing/unsupported compiler binary.

        Returns the offending binary name if one is found, otherwise None.
        """
        patterns = [
            # make: <name>: No such file or directory
            r"make(?:\[\d+\])?: (\S+): No such file or directory",
            # /bin/sh: 1: <name>: not found
            r"/\S+sh: \d+: (\S+): not found",
            # bash/sh: <name>: command not found
            r"(?:bash|sh): (\S+): command not found",
        ]
        for pattern in patterns:
            match = re.search(pattern, stderr)
            if match:
                return match.group(1)
        return None

    def _makefile_exists(self) -> bool:
        """
        Checks whether a Makefile exists in the project root.

        Returns: True if a Makefile is present, False otherwise.
        """
        for name in MAKEFILE_ALIASES:
            if os.path.isfile(os.path.join(self.project_root, name)):
                return True
        return False