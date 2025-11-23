import os
import subprocess
import json
from typing import List, Dict, Any

class CompilationStage:
    """Class to run the compilation stage of the validation pipeline"""

    def __init__(self, output_dir: str):
        """
        Initialize the compilation stage with where to write stage's output
        (This refers to where to write root from which to write `.o` files 
        and executables)
        """
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

        self.logs_dir = os.path.join(self.output_dir, "logs/")
        os.makedirs(self.logs_dir, exist_ok=True)

    def run(
        self, 
        source_files: List[str], 
        header_files: List[str], 
        build_tool: str = None
    ) -> Dict[str, Any]:
        """
        Run the compilation stage of validation pipeline

        Returns:
            A dictionary mapping relevant outputs to the contents/states of the
            outputs, including: 
                - success/failure of stage
                - generated errors/warnings
                - stdout/stderr
                - any misc. artifacts
        """
        # CASE 1: No build tool provided
        if not build_tool:
            results = self.run_manual_compile(
                source_files=source_files,
                compiler="clang"
            )

        # CASE 2: Build tool provided
        # NOT IMPLEMENTED IN THIS SPRINT
        else:
            # self.run_via_build_tool()
            results = {"error": "build tool functionality not yet supported"}

        # Log results to files in `logs/` subdirectory
        self.write_logs(results)

        return results

    def run_manual_compile(
        self, 
        source_files: List[str], 
        compiler: str = "clang", 
        flags: List[str] = None
    ) -> Dict[str, Any]:
        """
        Manually compile each `.c` source file into a `.o` object file.
        Then, manually link each object file to generate an executable.

        Args:
            source_files: list of `.c` source code files
        
        Returns:
            TODO
        """
        if flags is None:
            flags = []
          
        results = {
            "file_outputs": {},
            "link_output": {},
            "executable_path": None
        }

        # Container to store all SUCCESSFULLY COMPILED object files
        object_files = []
        
        # ====================== STEP 1 ======================
        # Compile each source (`.c`) file into an object (`.o`) file
        for src in source_files:
            # Extract only the filename from `.c` file's full path
            obj_basename = os.path.splitext(os.path.basename(src))[0]
            # Add `.o` extension
            obj_name = obj_basename + ".o"
            obj = os.path.join(self.output_dir, obj_name)
            cmd = [compiler, "-c", src] + flags + ["-o", obj]

            # Use Python subprocess module to run command, capture
            # return code and stdout/stderr streams
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )

            success = proc.returncode == 0
            results["file_outputs"][src] = {
                "cmd": ' '.join(cmd),         # to store command ran
                "success": success,          # to store success/fail per file
                "stdout": proc.stdout,       # to capture stdout per file
                "stderr": proc.stderr,       # to capture stderr per file
                "object_file": obj if success else None
            }

            if success:
                object_files.append(obj)

        # ====================== STEP 2 ======================
        # If any compilation failed, abort linking stage
        if len(object_files) < len(source_files):
            results["link_output"]["success"] = False
            return results
        
        # ====================== STEP 3 ======================
        # Attempt linking all object files 
        executable_path = os.path.join(self.output_dir, "a.out")
        cmd = [compiler] + object_files + ["-o", executable_path]

        # Run command to attempt linking all object files
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )

        results["link_output"]["success"] = proc.returncode == 0
        results["link_output"]["stdout"] = proc.stdout
        results["link_output"]["stderr"] = proc.stderr

        if results["link_output"]["success"]:
            results["executable_path"] = executable_path
          
        return results
    
    def write_logs(self, results: Dict[str, Any]) -> None:
        """
        Write compilation and linking results to the `logs/` subdirectory

        Args:
            results: a dictionary containing pertinent information gathered
                     from an attempt to compile and link `.c` files
        """

        # ====================== STEP 1 ======================
        # Write per-file compile logs
        for src, file_results in results["file_outputs"].items():
            base = os.path.splitext(os.path.basename(src))[0]
            log_path = os.path.join(self.logs_dir, f"compile_{base}.log")

            with open(log_path, "w") as f:
                for artifact, content in file_results.items():
                    f.write(f"{artifact}: " + f"{content}\n\n")
            
        # ====================== STEP 2 ======================
        # Write linker log
        link_log_path = os.path.join(self.logs_dir, "link.log")
        
        with open(link_log_path, "w") as f:
            for artifact, content in results["link_output"].items():
                f.write(f"{artifact}: " + f"{content}\n\n")
        
        # ====================== STEP 3 ======================
        # Write a summary JSON dump log
        summary_path = os.path.join(self.logs_dir, "summary.json")

        with open(summary_path, "w") as f:
            json.dump(results, f, indent=4)