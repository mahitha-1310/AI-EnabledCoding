import os
import subprocess
import json
from typing import List, Dict, Any
from utils import fmt_field

class StaticAnalysisStage:
    """Class to run the static analysis stage of the validation pipeline"""

    def __init__(self, logs_dir: str, artifacts_dir: str, project_root: str):
        """
        Initialize the static analysis stage with where to write stage's output
        (this refers to root from which to write captured static analysis outputs),
        as well as project root where source files are found.

        Args:
            logs_dir: Path to directory to which this stage will write all generated log files
            artifacts_dir: Path to directory to which this stage will write all generated artifacts
            project_root: Path to project directory (where all source code/header files will be
                          found)

            (NOTE: these may or may not be a relative path; if relative, this initializer normalizes
            the relative path to be an absolute path)
        """
        self.project_root = os.path.abspath(project_root)

        # Create `logs/static_analysis/` subdirectory
        self.logs_dir = os.path.abspath(logs_dir)
        os.makedirs(self.logs_dir, exist_ok=True)

        # Create `artifacts/static_analysis/` subdirectory
        self.artifacts_dir = os.path.abspath(artifacts_dir)
        os.makedirs(self.artifacts_dir, exist_ok=True)

    # ------------------------------------------------------------------------
    #     PUBLIC METHODS
    # ------------------------------------------------------------------------

    def run(
        self,
        source_files: List[str],
        compile_commands: str,
        static_analyzers: List[str] = None
    ):
        """
        Runs the static analysis stage of the validation pipeline.

        Args:
            source_files: List of paths to source code (`.c`) files. May
                          be relative or absolute paths.
            compile_commands: A path to the directory containing `compile_commands.json`
                              (used by clang-tidy).
            static_analyzers: List of analyzers to run. Supported values: "clang-tidy",
                              "cppcheck". Defaults to ["clang-tidy"].
        """
        if not static_analyzers:
            static_analyzers = ["clang-tidy"]

        results = self._run_static_analysis(
            source_files=source_files,
            compile_commands=compile_commands,
            static_analyzers=static_analyzers
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
        static_analyzers: List[str]
    ) -> Dict[str, Any]:
        """
        Invokes each requested static analyzer on every source file.

        Returns:
            {
                "<analyzer>": {
                    "file_outputs": {
                        src_path: {
                            "cmd": "...",
                            "success": bool,
                            "stdout": "...",
                            "stderr": "...",
                        }
                    },
                    "overall_success": bool
                },
                ...
                "overall_success": bool   # True only if every analyzer passed
            }
        """
        build_dir = os.path.abspath(compile_commands)
        analyzer_results: Dict[str, Any] = {}

        for analyzer in static_analyzers:
            if analyzer == "cppcheck":
                # cppcheck is most accurate when it sees the whole project at once.
                # Run it once using compile_commands.json so cross-file usage is visible.
                analyzer_results[analyzer] = self._run_cppcheck_project(build_dir)
            else:
                # Per-file analysis (clang-tidy)
                file_outputs: Dict[str, Any] = {}
                all_success = True

                for src in source_files:
                    src_abs = os.path.abspath(src)
                    cmd = self._build_cmd(analyzer, src_abs, build_dir)

                    try:
                        proc = subprocess.run(cmd, capture_output=True, text=True)
                        success = proc.returncode == 0
                        stdout = proc.stdout
                        stderr = proc.stderr
                    except FileNotFoundError:
                        all_success = False
                        file_outputs[src_abs] = {
                            "cmd": ' '.join(cmd),
                            "success": False,
                            "stdout": "",
                            "stderr": f"Error: '{analyzer}' was not found."
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

                analyzer_results[analyzer] = {
                    "file_outputs": file_outputs,
                    "overall_success": all_success
                }

        overall = all(r["overall_success"] for r in analyzer_results.values())
        return {**analyzer_results, "overall_success": overall}

    def _run_cppcheck_project(self, build_dir: str) -> Dict[str, Any]:
        """
        Run cppcheck once on the whole project using compile_commands.json.
        Stores the result under the key "project" in file_outputs so the
        rest of the result structure (and graders) remain unchanged.
        """
        compile_commands_path = os.path.join(build_dir, "compile_commands.json")
        cmd = [
            "cppcheck",
            "--enable=warning,style,performance,portability",  # exclude 'information' — cppcheck self-diagnostics, not code findings
            f"--project={compile_commands_path}",
        ]

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True)
            # Only hard-fail on 'error' severity; warnings/style/performance/portability
            # are logged but treated as passing.
            success = not any(
                ": error:" in line
                for line in proc.stderr.splitlines()
            )
            return {
                "file_outputs": {
                    "project": {
                        "cmd": ' '.join(cmd),
                        "success": success,
                        "stdout": proc.stdout,
                        "stderr": proc.stderr,
                    }
                },
                "overall_success": success
            }
        except FileNotFoundError:
            return {
                "file_outputs": {
                    "project": {
                        "cmd": ' '.join(cmd),
                        "success": False,
                        "stdout": "",
                        "stderr": "Error: 'cppcheck' was not found.",
                    }
                },
                "overall_success": False
            }

    def _build_cmd(self, static_analyzer: str, src_abs: str, build_dir: str) -> List[str]:
        """
        Build the per-file command for the given static analyzer.
        Only used for clang-tidy, which runs per-file.
        cppcheck uses _run_cppcheck_project instead.
        """
        if static_analyzer == "clang-tidy":
            return ["clang-tidy", src_abs, "-p", build_dir]
        else:
            raise ValueError(f"Unsupported static analyzer: '{static_analyzer}'")

    def _write_logs(self, results: Dict[str, Any]):
        """Write per-analyzer per-file logs + summary JSON."""

        os.makedirs(self.logs_dir, exist_ok=True)

        for key, value in results.items():
            if key == "overall_success":
                continue

            # Each remaining key is an analyzer name
            analyzer = key
            analyzer_dir = os.path.join(self.logs_dir, analyzer)
            os.makedirs(analyzer_dir, exist_ok=True)

            for src, file_result in value["file_outputs"].items():
                base = os.path.splitext(os.path.basename(src))[0] or src
                log_path = os.path.join(analyzer_dir, f"static_{base}.log")

                with open(log_path, "w") as f:
                    for k, v in file_result.items():
                        f.write(fmt_field(k, v))

        # Write summary JSON
        summary_path = os.path.join(self.logs_dir, "summary.json")
        with open(summary_path, "w") as f:
            json.dump(results, f, indent=4)
