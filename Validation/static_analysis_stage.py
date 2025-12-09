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
        """
        self.project_root = project_root

        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

        self.logs_dir = os.path.join(self.output_dir, "logs/")
        os.makedirs(self.logs_dir, exist_ok=True)

    def run(
        self,
        source_files: List[str],
        
    ):
        pass