from typing import List, Dict, Any

class CompilationStage:
    """Class to run the compilation stage of the validation pipeline"""

    def __init__(self, output_dir: str):
        """
        Initialize the compilation stage with where to write stage's output
        """
        self.output_dir = output_dir

    def run(self, source_files: List[str], header_files: List[str], build_tool: str = None) -> Dict[str, Any]:
        """
        Run the compilation stage of validation pipeline

        Returns:
            bb
        """
        # CASE 1: No build tool provided
        if not build_tool:
            self.run_manual_compile(source_files)

        # CASE 2: Build tool provided
        else:
            # self.run_via_build_tool()
            pass
