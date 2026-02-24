import os
import subprocess
import json
from typing import List, Dict, Any

class FormattingStage:
    """Class to run the formatting stage of the validation pipeline using clang-format."""

    def __init__(self, output_dir: str):
        """
        Initialize formatting stage with output directory for artifacts/logs.
        """

        self.output_dir = os.path.abspath(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)

        self.logs_dir = os.path.join(self.output_dir, "logs/")
        os.makedirs(self.logs_dir, exist_ok=True)

        self.formatted_dir = os.path.join(self.output_dir, "formatted_files/")
        os.makedirs(self.formatted_dir, exist_ok=True)

    # ------------------------------------------------------------------------
    # PUBLIC METHODS
    # ------------------------------------------------------------------------

    def run(
        self,
        source_files: List[str],
        check_only: bool = True,
        style: str = "LLVM"
    ) -> Dict[str, Any]:
        """
        Run clang-format on provided source files.

        Args:
            source_files: List of .c/.h/.cpp files
            check_only: If True, do not modify files (fail if misformatted)
            style: clang-format style (LLVM, Google, etc.)

        Returns:
            Dict containing results
        """

        if not source_files:
            raise ValueError("No source files provided to FormattingStage")

        results = []

        for file_path in source_files:
            file_path = os.path.abspath(file_path)

            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Source file not found: {file_path}")

            if check_only:
                # Check formatting without modifying file
                cmd = [
                    "clang-format",
                    "--dry-run",
                    "--Werror",
                    f"--style={style}",
                    file_path
                ]
            else:
                # Output formatted code to stdout
                cmd = [
                    "clang-format",
                    f"--style={style}",
                    file_path
                ]

            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )

            formatted_output_path = None

            # If not check-only, save formatted file output
            if not check_only and proc.returncode == 0:
                filename = os.path.basename(file_path)
                formatted_output_path = os.path.join(self.formatted_dir, filename)

                with open(formatted_output_path, "w") as f:
                    f.write(proc.stdout)

            result = {
                "cmd": " ".join(cmd),
                "success": proc.returncode == 0,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "formatted_output": formatted_output_path
            }

            results.append(result)

        summary = {
            "stage": "formatting",
            "overall_success": all(r["success"] for r in results),
            "files_processed": len(results),
            "results": results
        }

        self.write_logs(summary)
        return summary

    # ------------------------------------------------------------------------
    # PRIVATE METHODS
    # ------------------------------------------------------------------------

    def write_logs(self, result: Dict[str, Any]) -> None:
        """Write formatting output to log files."""

        log_path = os.path.join(self.logs_dir, "clang_format.log")
        summary_path = os.path.join(self.logs_dir, "summary.json")

        with open(log_path, "w") as f:
            json.dump(result, f, indent=4)

        with open(summary_path, "w") as f:
            json.dump(result, f, indent=4)