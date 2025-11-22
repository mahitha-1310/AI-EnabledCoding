import os
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from openai import OpenAI
from dotenv import load_dotenv
import logging

DEFAULT_EXTS = ['.py', '.js', '.java', '.cpp', '.c', '.ts', '.jsx', '.tsx']
DEFAULT_DIRS = {'node_modules', '.git', '__pycache__', 'venv', '.venv', 'dist', 'build'}

BEGIN_DELIMITER = '~~~```'
END_DELIMITER = '```~~~'

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
        load_dotenv()
        self.client = OpenAI(
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE")
        )
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
            formatted.append(f"{file_path}\n{BEGIN_DELIMITER}\n{content}\n{END_DELIMITER}")
        
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
        in_code_block = False
        
        for line in lines:
            # Start code block
            if line.strip().startswith(BEGIN_DELIMITER):
                in_code_block = True
                continue
            
            # End code block
            elif line.strip().startswith(END_DELIMITER):
                # Save the current file
                if current_file and current_content:
                    codebase[current_file] = '\n'.join(current_content)
                    current_file = None
                    current_content = []
                in_code_block = False
                continue 
            
            # If we're in a code block, collect the content
            if in_code_block:
                current_content.append(line)
            
            # If we see a potential filename (before code block starts)
            elif not in_code_block and line.strip() and not line.strip().startswith(BEGIN_DELIMITER):
                # Check if next lines might contain a code block
                # This could be a filename
                if current_file is None and len(line.strip()) > 0:
                    # Look ahead to see if this is followed by a code delimiter
                    # For now, collect as potential filename
                    potential_file = line.strip()
                    # Check if it looks like a file path
                    if '.' in potential_file or '/' in potential_file:
                        current_file = potential_file
                    else:
                        text_response_lines.append(line)
                else:
                    text_response_lines.append(line)
        
        # Save last file if exists
        if current_file and current_content:
            codebase[current_file] = '\n'.join(current_content)
        
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
    
    def chat(self, message: str) -> Tuple[str, Optional[Dict[str, str]]]:
        """
        Send a message in the ongoing conversation.
        
        Args:
            message: Your message/instruction
            
        Returns:
            Tuple of (text_response, codebase_dict)
        """
        
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": message
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
        text_response, modified_codebase = self.parse_codebase_response(llm_response)
        if modified_codebase:
            self.current_codebase = modified_codebase
        return text_response, modified_codebase
    
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

        prompt = f"""{instruction}

IMPORTANT: If you make any code changes, you MUST return the complete modified codebase.

Format your response as follows:
1. First, provide a brief summary of changes
2. If you are about to make a file, give it an appropriate and relevant filename and extension like so: `<filename>.<extension>`
3. Then, provide each modified file in this EXACT format:

`<filename>.<extension>`
~~~```
<entire file contents here>
```~~~

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
            print(return_code)
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
    
    def run(self, instruction: str, user_id: str, input_path: str, output_path: str, extensions: List[str] = None) -> str:
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

        logging.basicConfig(
            filename='llm_queries.log',
            level=logging.INFO,
            format='%(asctime)s - %(message)s'
        )

        logging.info(f"User: {user_id} | Query: {instruction}")

        if input_path is None:
            raise ValueError("input_path cannot be None. Please provide a valid directory path.")
        if output_path is None:
            raise ValueError("output_path cannot be None. Please provide a valid directory path.")
        if BEGIN_DELIMITER == '':
            raise ValueError("Begining delimiter cannot be empty.")
        if END_DELIMITER == '':
            raise ValueError("Ending delimiter cannot be empty.")

        print("Collecting codebase...")
        input_codebase = self.collect_codebase(input_path, extensions)
        print(f"Found {len(input_codebase)} files.")
        
        print("\nProcessing with LLM...")
        text_response, output_codebase = self.process_with_llm(
            input_codebase, instruction
        )
        
        # sz = 50
        # print("\n" + "="*sz)
        # print("LLM Response:")
        # print("-"*sz)
        # print(text_response)
        # print("="*sz + "\n")
        
        print(output_codebase)
        if output_codebase:
            # If code output is requested:
            print(f"Received {len(output_codebase)} files from LLM.")
            print("\nWriting output...")
            self.write_codebase(output_codebase, output_path)
            print("\nPipeline complete!")
        
        return text_response