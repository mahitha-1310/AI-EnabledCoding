import os
from pathlib import Path
from typing import List, Dict
from openai import OpenAI

DEFAULT_EXTS = ['.py', '.js', '.java', '.cpp', '.c', '.ts', '.jsx', '.tsx']
DEFAULT_DIRS = {'node_modules', '.git', '__pycache__', 'venv', '.venv', 'dist', 'build'}

TEMPERATURE = 0.7
SYSTEM_PROMPT = """
You are a helpful coding assistant. Return code in the exact format requested.
"""

class CodebasePipeline:
    """Pipeline for processing codebases through an LLM."""
    
    def __init__(self, api_key: str = None, model: str = os.getenv("OPENAI_API_MODEL")):
        """
        Initialize the pipeline.
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Model to use (default: gpt-4)
        """
        self.client = OpenAI(api_key = api_key or os.getenv("OPENAI_API_KEY"))
        self.model = model
        
    def collect_codebase(self, root_path: str, extensions: List[str] = None) -> Dict[str, str]:
        """
        Collect all code files from a directory.
        
        Args:
            root_path: Root directory to scan
            extensions: List of file extensions to include (e.g., ['.py', '.js'])
        
        Returns:
            Dictionary mapping file paths to their contents
        """
        # Use default extensions if none provided
        if extensions is None:
            extensions = DEFAULT_EXTS
        
        # Initialize empty dictionary to store file paths and contents
        codebase = {}
        root = Path(root_path)
        
        # Iterate through each file extension
        for ext in extensions:
            # Recursively find all files with this extension
            for file_path in root.rglob(f"*{ext}"):
                # Check if file should be included (not in excluded directories)
                if self._should_include(file_path):
                    try:
                        # Get path relative to root for cleaner file names
                        relative_path = file_path.relative_to(root)
                        # Read file contents and store in dictionary
                        with open(file_path, 'r', encoding='utf-8') as f:
                            codebase[str(relative_path)] = f.read()
                        
                    except Exception as e:
                        # Log errors but continue processing other files
                        print(f"Error reading {file_path}: {e}")
        
        return codebase
    
    def _should_include(self, file_path: Path) -> bool:
        """Check if a file should be included (exclude common directories)."""
        # Define directories that should be excluded from processing
        exclude_dirs = DEFAULT_DIRS
        # Return False if any excluded directory appears in the file path
        return not any(excluded in file_path.parts for excluded in exclude_dirs)
    
    def format_codebase(self, codebase: Dict[str, str]) -> str:
        """
        Format codebase dictionary into a string for the LLM.
        
        Args:
            codebase: Dictionary of file paths to contents
            
        Returns:
            Formatted string representation
        """
        # Initialize list to collect formatted file entries
        formatted = []

        # Iterate through each file in the codebase
        for file_path, content in codebase.items():
            # Format each file with clear delimiters and its content
            formatted.append(f"=== {file_path} ===\n{content}\n")
        
        # Join all files with newlines into a single string
        return "\n".join(formatted)
    
    def parse_codebase_response(self, response: str) -> Dict[str, str]:
        """
        Parse LLM response back into codebase dictionary.
        
        Args:
            response: LLM response containing formatted codebase
            
        Returns:
            Dictionary mapping file paths to contents
        """
        codebase = {}
        current_file = None
        current_content = []
        
        for line in response.split('\n'):
            if line.startswith('=== ') and line.endswith(' ==='):
                # Save previous file if exists
                if current_file:
                    codebase[current_file] = '\n'.join(current_content).strip()
                
                # Start new file
                current_file = line[4:-4].strip()
                current_content = []
            
            elif current_file:
                current_content.append(line)
        
        # Save last file
        if current_file:
            codebase[current_file] = '\n'.join(current_content).strip()
        
        return codebase
    
    def process_with_llm(self, codebase: Dict[str, str], instruction: str) -> Dict[str, str]:
        """
        Send codebase to LLM with instructions and get modified codebase back.
        
        Args:
            codebase: Dictionary of file paths to contents
            instruction: What to ask the LLM to do with the codebase
            
        Returns:
            Modified codebase dictionary
        """
        formatted_codebase = self.format_codebase(codebase)
        
        prompt = f"""{instruction}

Please return the entire codebase in the same format, with each file clearly marked:

=== path/to/file.ext ===
<file contents>

Here is the codebase:

{formatted_codebase}"""
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=TEMPERATURE
        )
        
        llm_response = response.choices[0].message.content
        return self.parse_codebase_response(llm_response)
    
    def write_codebase(self, codebase: Dict[str, str], output_path: str):
        """
        Write codebase dictionary to disk.
        
        Args:
            codebase: Dictionary of file paths to contents
            output_path: Root directory to write files to
        """
        output_root = Path(output_path)
        output_root.mkdir(parents=True, exist_ok=True)
        
        for file_path, content in codebase.items():
            full_path = output_root / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Written: {full_path}")
    
    def run(self, input_path: str, output_path: str, instruction: str, extensions: List[str] = None):
        """
        Run the complete pipeline.
        
        Args:
            input_path: Path to input codebase
            output_path: Path to write output codebase
            instruction: Instructions for the LLM
            extensions: File extensions to include
        """
        print("Step 1: Collecting codebase...")
        codebase = self.collect_codebase(input_path)
        print(f"Found {len(codebase)} files.")
        
        print("\nStep 2: Processing with LLM...")
        modified_codebase = self.process_with_llm(codebase, instruction)
        print(f"Received {len(modified_codebase)} files from LLM.")
        
        print("\nStep 3: Writing output...")
        self.write_codebase(modified_codebase, output_path)
        print("\nPipeline complete!")