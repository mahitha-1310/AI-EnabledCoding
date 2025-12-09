import os
import subprocess
import json
from typing import List, Dict, Any

DEFAULT_FLAGS = [
    "-std=c11",
    "-Wall",
    "-Wextra"
]

class CompilationStage:
    """Class to run the compilation stage of the validation pipeline"""

    def __init__(self, output_dir: str, project_root: str):
        """
        Initialize the compilation stage with where to write stage's output (this refers 
        to root from which to write `.o` files and executables), as well as the project root
        (where source code would be found)

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

        # For now, log directory is always nested inside compilation directory
        # ====================================================================
        # In the future, I'd like to make this a third parameter such that the user can
        #   specify where they would like logs to be written
        self.logs_dir = os.path.join(self.output_dir, "logs/")
        os.makedirs(self.logs_dir, exist_ok=True)

    def run(
        self, 
        source_files: List[str], 
        header_files: List[str], 
        include_dirs: List[str],
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
                include_dirs=include_dirs,
                compiler="clang"
            )

        # CASE 2: Build tool provided
        # NOT IMPLEMENTED IN THIS SPRINT
        else:
            # self.run_via_build_tool()
            results = {"error": "user-defined build tool functionality not yet supported"}

        # Log results to files in `logs/` subdirectory
        self._write_logs(results)

        # Generate `compile_commands.json` file for next stage (static analysis)
        if results["executable_path"] != None:
            self._generate_compile_commands(results)

        return results

    def run_manual_compile(
        self, 
        source_files: List[str], 
        include_dirs: List[str],
        compiler: str = "clang", 
        flags: List[str] = None
    ) -> Dict[str, Any]:
        """
        Manually compile each `.c` source file into a `.o` object file.
        Then, manually link each object file to generate an executable.

        Args:
            source_files: Paths to `.c` source files.
            include_dirs: List of all include directories in this project
            compiler: C compiler to invoke (default: clang).
            flags: Optional list of user-defined, additional compiler flags.
        
        Returns:
            A dictionary with:
                - "file_outputs": per-file compile results (success, stdout, 
                  stderr, object file path, and command used).
                - "link_output": results of the linking step 
                  (success, stdout, stderr).
                - "executable_path": path to the generated executable, or None 
                  if linking failed or was skipped.
        """
        if flags is None:
            flags = []
        full_flags = DEFAULT_FLAGS + flags

        # ====================== STEP 1 ======================
        # Compile each source (`.c`) file into an object (`.o`) file
        compile_results = self._compile_source_files(
            source_files=source_files,
            include_dirs=include_dirs,
            compiler=compiler,
            flags=full_flags
        )

        object_files = compile_results["object_files"]
        file_outputs = compile_results["file_outputs"]
          
        results = {
            "file_outputs": file_outputs,
            "link_output": {},
            "executable_path": None
        }

        # Generate 

        # Attempt to generate a `compile_commands.json` file for all successfully
        # compiled source files
        self._generate_compile_commands(results)

        # ====================== STEP 2 ======================
        # If any compilation failed, abort linking stage
        if len(object_files) < len(source_files):
            results["link_output"]["success"] = False
            return results
        
        # ====================== STEP 3 ======================
        link_result = self._link_object_files(
            object_files=object_files,
            compiler=compiler
        )
        results["link_output"] = link_result["link_output"]
        results["executable_path"] = link_result["executable_path"]
          
        return results

    
    # --- PRIVATE HELPERS ----------------------------------------------------

    def _compile_source_files(
        self,
        source_files: List[str],
        include_dirs: List[str],
        compiler: str = "clang",
        flags: List[str] = None
    ) -> Dict[str, Any]:
        """
        Compile each source file into a `.o` object file

        Returns:
            {
                "object_files": [...], (list of object file names)
                "file_outputs": {
                    src_path: { cmd, success, stdout, stderr, object_file }
                }
            }
        """ 
        if flags is None:
            flags = []
        
        include_flags = [f"-I{d}" for d in include_dirs]

        file_outputs = {}
        object_files = []

        # Compile each source (`.c`) file into an object (`.o`) file
        for src in source_files:
            # Ensure `src` is an absolute path
            src = os.path.abspath(src)

            # Extract only the filename from `.c` file's full path
            obj_basename = os.path.splitext(os.path.basename(src))[0]

            # Add `.o` extension
            obj_name = obj_basename + ".o"
            obj = os.path.join(self.output_dir, obj_name)
            cmd = [compiler, "-c", src] + flags + include_flags + ["-o", obj]

            # Use Python subprocess module to run command, capture
            # return code and stdout/stderr streams
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )

            success = proc.returncode == 0

            file_outputs[src] = {
                "cmd": ' '.join(cmd),        # to store command ran
                "success": success,          # to store success/fail per file
                "stdout": proc.stdout,       # to capture stdout per file
                "stderr": proc.stderr,       # to capture stderr per file
                "object_file": obj if success else None
            }

            if success:
                object_files.append(obj)

        return {
            "object_files": object_files,
            "file_outputs": file_outputs
        }
        
    def _link_object_files(
        self,
        object_files: List[str],
        compiler: str = "clang"
    ) -> Dict[str, Any]:
        """
        Attempt to generate executable by linking all generated object files

        Returns: 
            {
                "link_output": { cmd, success, stdout, stderr },
                "executable_path": str (or None if executable not generated)
            }
        """
        # Attempt linking all object files 
        executable_path = os.path.join(self.output_dir, "a.out")
        cmd = [compiler] + object_files + ["-o", executable_path]

        # Run command to attempt linking all object files
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )

        return {
            "link_output": {
                "cmd": ' '.join(cmd),
                "success": proc.returncode == 0,
                "stdout": proc.stdout,
                "stderr": proc.stderr
            },
            "executable_path": executable_path if proc.returncode == 0 else None
        }
    
    def _write_logs(self, results: Dict[str, Any]) -> None:
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

    def _generate_compile_commands(self, results: Dict[str, Any]):
        """
        Generates the necessary `compile_commands.json` file in order for static 
        analysis (via clang-tidy) to be performed.
        
        Each successfully compiled source file gets an entry consisting of:
            - directory: absolute path to the project root (note that this is NOT
                         the `compilation/` folder)
            - file: absolute path to the `.c` file
            - command: the exact command used to compile this file
        
        Args:
            results: a dictionary containing pertinent information gathered
                     from an attempt to compile and link `.c` files
        """
        compile_db = []

        # Generate an entry for each successfully compiled `.c` file
        for src_path, file_result in results["file_outputs"].items():
            if not file_result["success"]:
                continue
             
            entry = {
                "directory": self.project_root,
                "file": os.path.abspath(src_path),
                "command": file_result["cmd"]
            }

            compile_db.append(entry)

        out_path = os.path.join(self.output_dir, "compile_commands.json")
        with open(out_path, "w") as f:
            json.dump(compile_db, f, indent=4)