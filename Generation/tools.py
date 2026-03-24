import base64
import shutil
from langchain_core.tools import tool
from typing import Dict, Any
from Generation.utils import *

@tool
def read(path: str, encoding: str = "utf-8") -> Dict[str, Any]:
    """
    Read content from a file.
    
    Args:
        path: The file path to read
        encoding: Encoding format (utf-8, ascii, base64)
        
    Returns:
        Dictionary containing the content and metadata
    """
    
    file_path = get_path(path)
    
    assert_exists(file_path)
    assert_file(file_path)
    
    # Read the file
    if encoding == "base64":
        with open(file_path, "rb") as f:
            content = base64.b64encode(f.read()).decode('ascii')
    else:
        with open(file_path, "r", encoding=encoding) as f:
            content = f.read()
    
    stat = file_path.stat()
    
    result = {
        "path": str(file_path),
        "content": content,
        "encoding": encoding,
        "size": stat.st_size
    }
    
    return result

@tool
def write(path: str, content: str, encoding: str = "utf-8", mode: str = "overwrite", create_directories: bool = False) -> Dict[str, Any]:
    """
    Write or update content to a file.
    
    Args:
        path: The file path to write to
        content: The content to write
        encoding: Encoding format (utf-8, ascii)
        mode: Write mode (overwrite, append)
        create_directories: Create parent directories if needed
        
    Returns:
        Dictionary with operation result
    """
    
    file_path = get_path(path)
    
    # Create parent directories if requested
    if create_directories:
        file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Check if parent directory exists
    assert_exists(file_path.parent)
    
    # Determine write mode
    write_mode = "a" if mode == "append" else "w"
    
    try:
        # Write the file
        with open(file_path, write_mode, encoding=encoding) as f:
            f.write(content)
    except Exception as e:
        raise
    
    # Verify the file was created/modified
    assert_exists(file_path)
    
    stat = file_path.stat()
    
    result = {
        "path": str(file_path),
        "size": stat.st_size,
        "mode": mode
    }
    
    return result

@tool
def remove(path: str, recursive: bool = False) -> Dict[str, Any]:
    """
    Remove or delete a file or directory.
    
    Args:
        path: The file or directory path to remove
        recursive: Recursively remove directories
        
    Returns:
        Dictionary with operation result
    """
    
    file_path = get_path(path)
    assert_exists(file_path)
    
    if file_path.is_file():
        file_path.unlink()
        return {"path": str(file_path), "removed": True, "type": "file"}
    
    elif file_path.is_dir():
        if recursive:
            shutil.rmtree(file_path)
        else:
            file_path.rmdir()  # Only removes empty directories
        return {"path": str(file_path), "removed": True, "type": "directory"}
    
    else:
        raise ValueError(f"Unknown path type: {path}")


TOOLS = {
    "read": read,
    "write": write,
    "remove": remove
}

SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "read",
            "description": "Read content from a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The file path to read."
                    },
                    "encoding": {
                        "type": "string",
                        "enum": ["utf-8", "ascii", "base64"],
                        "default": "utf-8"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write",
            "description": "Write or update content to a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                    "encoding": {
                        "type": "string",
                        "enum": ["utf-8", "ascii"],
                        "default": "utf-8"
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["overwrite", "append"],
                        "default": "overwrite"
                    },
                    "create_directories": {
                        "type": "boolean",
                        "default": False
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "remove",
            "description": "Remove or delete a file or directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "recursive": {"type": "boolean", "default": False}
                },
                "required": ["path"]
            }
        }
    }
]