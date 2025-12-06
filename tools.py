import base64
from typing import Dict, Any
from utils import *

def read(path: str, encoding: str = "utf-8") -> Dict[str, Any]:
    """
    Read content from a file.
    
    Args:
        path: The file path to read
        encoding: Encoding format (utf-8, ascii, base64)
        
    Returns:
        Dictionary containing the content and metadata
    """
    file_path = getpath(path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    if not file_path.is_file():
        raise ValueError(f"Path is not a file: {path}")
    
    # Read the file
    if encoding == "base64":
        with open(file_path, "rb") as f:
            content = base64.b64encode(f.read()).decode('ascii')
    else:
        with open(file_path, "r", encoding=encoding) as f:
            content = f.read()
    
    stat = file_path.stat()
    
    return {
        "path": str(file_path),
        "content": content,
        "encoding": encoding,
        "size": stat.st_size
    }


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
    file_path = getpath(path)
    
    # Create parent directories if requested
    if create_directories:
        file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Determine write mode
    write_mode = "a" if mode == "append" else "w"
    
    # Write the file
    with open(file_path, write_mode, encoding=encoding) as f:
        f.write(content)
    
    stat = file_path.stat()
    
    return {
        "path": str(file_path),
        "size": stat.st_size,
        "mode": mode
    }


def remove(path: str, recursive: bool = False) -> Dict[str, Any]:
    """
    Remove or delete a file or directory.
    
    Args:
        path: The file or directory path to remove
        recursive: Recursively remove directories
        
    Returns:
        Dictionary with operation result
    """
    file_path = getpath(path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"Path not found: {path}")
    
    if file_path.is_file():
        file_path.unlink()
        return {"path": str(file_path), "removed": True, "type": "file"}
    
    elif file_path.is_dir():
        if recursive:
            import shutil
            shutil.rmtree(file_path)
        else:
            file_path.rmdir()  # Only removes empty directories
        return {"path": str(file_path), "removed": True, "type": "directory"}
    
    else:
        raise ValueError(f"Unknown path type: {path}")


def find(directory: str, pattern: str = "*", recursive: bool = True, max_results: int = 100) -> Dict[str, Any]:
    """
    Search for files matching specified criteria.
    
    Args:
        directory: The directory to search within
        pattern: Search pattern (supports wildcards)
        recursive: Search recursively through subdirectories
        max_results: Maximum number of results to return
        
    Returns:
        Dictionary containing list of matching files
    """
    dir_path = getpath(directory)
    
    if not dir_path.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")
    
    if not dir_path.is_dir():
        raise ValueError(f"Path is not a directory: {directory}")
    
    # Search for files
    if recursive:
        search_pattern = f"**/{pattern}"
    else:
        search_pattern = pattern
    
    matches = []
    for file_path in dir_path.glob(search_pattern):
        if len(matches) >= max_results:
            break
        
        if file_path.is_file():
            stat = file_path.stat()
            matches.append({
                "path": str(file_path),
                "name": file_path.name,
                "size": stat.st_size,
                "modified": stat.st_mtime
            })
    
    return {
        "directory": str(dir_path),
        "pattern": pattern,
        "matches": matches,
        "count": len(matches)
    }

TOOLS = {
    "read": read,
    "write": write,
    "remove": remove,
    "find": find
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
    },
    {
        "type": "function",
        "function": {
            "name": "find",
            "description": "Search for files matching specified criteria.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {"type": "string"},
                    "pattern": {"type": "string", "default": "*"},
                    "recursive": {"type": "boolean", "default": True},
                    "max_results": {"type": "integer", "default": 100}
                },
                "required": ["directory"]
            }
        }
    }
]