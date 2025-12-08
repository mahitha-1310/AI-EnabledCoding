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


def list(directory: str, recursive: bool = True, max_depth: int = None) -> Dict[str, Any]:
    """
    List all files and directories in a directory structure.
    
    Args:
        directory: The directory to list
        recursive: List recursively through subdirectories
        max_depth: Maximum depth to traverse (None for unlimited)
        
    Returns:
        Dictionary containing the directory structure
    """
    dir_path = getpath(directory)
    
    if not dir_path.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")
    
    if not dir_path.is_dir():
        raise ValueError(f"Path is not a directory: {directory}")
    
    def build_tree(path, current_depth=0):
        """Recursively build directory tree structure"""
        items = []
        
        # Check depth limit
        if max_depth is not None and current_depth >= max_depth:
            return items
        
        try:
            for item in sorted(path.iterdir()):
                stat = item.stat()
                entry = {
                    "name": item.name,
                    "path": str(item),
                    "type": "directory" if item.is_dir() else "file",
                }
                
                if item.is_file():
                    entry["size"] = stat.st_size
                    entry["modified"] = stat.st_mtime
                elif item.is_dir() and recursive:
                    entry["children"] = build_tree(item, current_depth + 1)
                
                items.append(entry)
        except PermissionError:
            # Skip directories we don't have permission to read
            pass
        
        return items
    
    structure = build_tree(dir_path)
    
    return {
        "directory": str(dir_path),
        "recursive": recursive,
        "structure": structure
    }


TOOLS = {
    "read": read,
    "write": write,
    "remove": remove,
    "list": list
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
            "name": "list",
            "description": "List all files and directories in a directory structure.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "The directory to list."
                    },
                    "recursive": {
                        "type": "boolean",
                        "default": True,
                        "description": "List recursively through subdirectories."
                    },
                    "max_depth": {
                        "type": "integer",
                        "default": None,
                        "description": "Maximum depth to traverse (None for unlimited)."
                    }
                },
                "required": ["directory"]
            }
        }
    }
]