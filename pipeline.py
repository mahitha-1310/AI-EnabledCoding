import os
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from openai import OpenAI
from openai import AuthenticationError
from dotenv import load_dotenv

load_dotenv()

DEFAULT_EXTS = ['.c'] # ['.py', '.js', '.java', '.cpp', '.c', '.ts', '.jsx', '.tsx']
DEFAULT_DIRS = {'node_modules', '.git', '__pycache__', 'venv', '.venv', 'dist', 'build'}

TEMPERATURE = 0.7
SYSTEM_PROMPT = """
You are a helpful coding assistant. Return code in the exact format requested.
"""

class CodebasePipeline:
    """Pipeline for processing codebases through an LLM with conversation memory."""
    
    def __init__(self, api_key: str = None, model: str = None):
        """
        Initialize the pipeline.
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Model to use (defaults to OPENAI_API_MODEL env var)
        """
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = model or os.getenv("OPENAI_API_MODEL")
        self.conversation_history = []
        self.current_codebase = {}
        
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
    
    def parse_codebase_response(self, response: str) -> Tuple[str, Dict[str, str]]:
        """
        Parse LLM response to extract both text response and codebase.
        
        Args:
            response: LLM response containing optional text and formatted codebase
            
        Returns:
            Tuple of (text_response, codebase_dict)
        """
        lines = response.split('\n')
        codebase = {}
        current_file = None
        current_content = []
        text_response_lines = []
        in_codebase = False
        
        for line in lines:
            if line.startswith('=== ') and line.endswith(' ==='):
                in_codebase = True
                # Save previous file if exists
                if current_file:
                    codebase[current_file] = '\n'.join(current_content).strip()
                
                # Start new file
                current_file = line[4:-4].strip()
                current_content = []
            
            elif current_file:
                current_content.append(line)
            
            elif not in_codebase:
                # Collect lines before codebase starts
                text_response_lines.append(line)
        
        # Save last file
        if current_file:
            codebase[current_file] = '\n'.join(current_content).strip()
        
        text_response = '\n'.join(text_response_lines).strip()
        return text_response, codebase
    
    def load_codebase(self, root_path: str, extensions: List[str] = None):
        """
        Load a codebase into the conversation context.
        
        Args:
            root_path: Root directory to scan
            extensions: File extensions to include
        """
        print("Loading codebase into context...")
        self.current_codebase = self.collect_codebase(root_path, extensions)
        print(f"Loaded {len(self.current_codebase)} files.")
        
        # Add codebase to conversation history
        formatted_codebase = self.format_codebase(self.current_codebase)
        self.conversation_history.append({
            "role": "user",
            "content": f"Here is the codebase I'm working with:\n\n{formatted_codebase}"
        })
        self.conversation_history.append({
            "role": "assistant",
            "content": "I've reviewed the codebase. How can I help you with it?"
        })
    
    def chat(self, message: str, return_code: bool = False) -> Tuple[str, Optional[Dict[str, str]]]:
        """
        Send a message in the ongoing conversation.
        
        Args:
            message: Your message/instruction
            return_code: Whether to expect and parse code in the response
            
        Returns:
            Tuple of (text_response, optional_codebase_dict)
        """
        # Build the prompt
        if return_code:
            full_message = f"""{message}

Please provide:
1. A summary or explanation of the changes
2. The entire modified codebase with each file clearly marked:

=== path/to/file.ext ===
<file contents>"""
        else:
            full_message = message
        
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": full_message
        })
        
        # Make API call with full conversation history
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                *self.conversation_history
            ],
            temperature=TEMPERATURE
        )
        
        llm_response = response.choices[0].message.content
        
        # Add assistant response to history
        self.conversation_history.append({
            "role": "assistant",
            "content": llm_response
        })
        
        # Parse response
        if return_code:
            text_response, modified_codebase = self.parse_codebase_response(llm_response)
            if modified_codebase:
                self.current_codebase = modified_codebase
            return text_response, modified_codebase
        else:
            return llm_response, None
    
    def reset_conversation(self):
        """Clear conversation history and current codebase."""
        self.conversation_history = []
        self.current_codebase = {}
        print("Conversation history cleared.")
    
    def process_with_llm(self, codebase: Dict[str, str], instruction: str, 
                        return_code: bool = True) -> Tuple[str, Dict[str, str]]:
        """
        Send codebase to LLM with instructions (single-shot, no conversation).
        
        Args:
            codebase: Dictionary of file paths to contents
            instruction: What to ask the LLM to do with the codebase
            return_code: Whether to request modified code back (default: True)
            
        Returns:
            Tuple of (text_response, modified_codebase_dict)
        """
        formatted_codebase = self.format_codebase(codebase)
        
######## SYSTEM PROMPT ########

        if return_code:
            prompt = f"""{instruction}

Please provide:
1. A summary or explanation of the changes you're making
2. The entire modified codebase in the same format, with each file clearly marked:

=== path/to/file.ext ===
<file contents>

Here is the codebase:

{formatted_codebase}"""

        else:
            prompt = f"""{instruction}

Here is the codebase:

{formatted_codebase}"""
        
###############################

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=TEMPERATURE
        )
        
        llm_response = response.choices[0].message.content
        
        if return_code:
            text_response, modified_codebase = self.parse_codebase_response(llm_response)
            return text_response, modified_codebase
        else:
            return llm_response, {}
    
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
    
    def save_current_codebase(self, output_path: str):
        """Save the current codebase in context to disk."""
        if not self.current_codebase:
            print("No codebase loaded in context.")
            return
        self.write_codebase(self.current_codebase, output_path)
    
    def run(self, input_path: str, output_path: str, instruction: str, 
            extensions: List[str] = None, return_code: bool = True) -> str:
        """
        Run the complete pipeline (single-shot, no conversation).
        
        Args:
            input_path: Path to input codebase
            output_path: Path to write output codebase
            instruction: Instructions for the LLM
            extensions: File extensions to include
            return_code: Whether to request and write modified code
            
        Returns:
            Text response from the LLM
        """
        if input_path is None:
            raise ValueError("input_path cannot be None. Please provide a valid directory path.")
        if output_path is None:
            raise ValueError("output_path cannot be None. Please provide a valid directory path.")

        try:
            print("Step 1: Collecting codebase...")
            codebase = self.collect_codebase(input_path, extensions)
            print(f"Found {len(codebase)} files.")
            
            print("\nStep 2: Processing with LLM...")
            text_response, modified_codebase = self.process_with_llm(
                codebase, instruction, return_code
            )
            
            print("\n" + "="*50)
            print("LLM Response:")
            print("="*50)
            print(text_response)
            print("="*50 + "\n")
            
            if return_code and modified_codebase:
                # If code output is requested:
                print(f"Received {len(modified_codebase)} files from LLM.")
                print("\nStep 3: Writing output...")
                self.write_codebase(modified_codebase, output_path)
                print("\nPipeline complete!")
            else:
                # If no code output is requested:
                print("\nPipeline complete!")
        except AuthenticationError as e:
            text_response = "No OpenAI API Key was provided."
        
        return text_response