import base64
from langchain_core.tools import tool
from typing import Dict, Any
from utils import *
import logging

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
    logging.info(f"[READ] Starting read operation")
    logging.info(f"[READ] Path: {path}")
    logging.info(f"[READ] Encoding: {encoding}")
    
    file_path = getpath(path)
    logging.info(f"[READ] Resolved path: {file_path}")
    
    if not file_path.exists():
        logging.error(f"[READ] File not found: {path}")
        raise FileNotFoundError(f"File not found: {path}")
    
    if not file_path.is_file():
        logging.error(f"[READ] Path is not a file: {path}")
        raise ValueError(f"Path is not a file: {path}")
    
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
    
    logging.info(f"[READ] Successfully read file, size: {stat.st_size} bytes")
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
    logging.info(f"[WRITE] Starting write operation")
    logging.info(f"[WRITE] Path: {path}")
    logging.info(f"[WRITE] Content length: {len(content)} characters")
    logging.info(f"[WRITE] Encoding: {encoding}")
    logging.info(f"[WRITE] Mode: {mode}")
    logging.info(f"[WRITE] Create directories: {create_directories}")
    
    file_path = getpath(path)
    logging.info(f"[WRITE] Resolved path: {file_path}")
    logging.info(f"[WRITE] Absolute path: {file_path.absolute()}")
    logging.info(f"[WRITE] Parent directory: {file_path.parent}")
    logging.info(f"[WRITE] Parent exists: {file_path.parent.exists()}")
    
    # Create parent directories if requested
    if create_directories:
        logging.info(f"[WRITE] Creating parent directories...")
        file_path.parent.mkdir(parents=True, exist_ok=True)
        logging.info(f"[WRITE] Parent directories created/verified")
    
    # Check if parent directory exists
    if not file_path.parent.exists():
        error_msg = f"Parent directory does not exist: {file_path.parent}"
        logging.error(f"[WRITE] {error_msg}")
        raise FileNotFoundError(error_msg)
    
    # Determine write mode
    write_mode = "a" if mode == "append" else "w"
    logging.info(f"[WRITE] File open mode: {write_mode}")
    
    try:
        # Write the file
        logging.info(f"[WRITE] Opening file for writing...")
        logging.info(f"[CONTENT]\n{content}")
        with open(file_path, write_mode, encoding=encoding) as f:
            f.write(content)
        logging.info(f"[WRITE] Content written successfully")
    except Exception as e:
        logging.error(f"[WRITE] Failed to write file: {type(e).__name__}: {str(e)}")
        raise
    
    # Verify the file was created/modified
    if not file_path.exists():
        error_msg = "File does not exist after write operation"
        logging.error(f"[WRITE] {error_msg}")
        raise RuntimeError(error_msg)
    
    stat = file_path.stat()
    logging.info(f"[WRITE] File size after write: {stat.st_size} bytes")
    
    result = {
        "path": str(file_path),
        "size": stat.st_size,
        "mode": mode
    }
    
    logging.info(f"[WRITE] Write operation completed successfully")
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
    logging.info(f"[REMOVE] Starting remove operation")
    logging.info(f"[REMOVE] Path: {path}")
    logging.info(f"[REMOVE] Recursive: {recursive}")
    
    file_path = getpath(path)
    logging.info(f"[REMOVE] Resolved path: {file_path}")
    
    if not file_path.exists():
        logging.error(f"[REMOVE] Path not found: {path}")
        raise FileNotFoundError(f"Path not found: {path}")
    
    if file_path.is_file():
        logging.info(f"[REMOVE] Removing file...")
        file_path.unlink()
        logging.info(f"[REMOVE] File removed successfully")
        return {"path": str(file_path), "removed": True, "type": "file"}
    
    elif file_path.is_dir():
        if recursive:
            logging.info(f"[REMOVE] Removing directory recursively...")
            import shutil
            shutil.rmtree(file_path)
            logging.info(f"[REMOVE] Directory removed recursively")
        else:
            logging.info(f"[REMOVE] Removing empty directory...")
            file_path.rmdir()  # Only removes empty directories
            logging.info(f"[REMOVE] Empty directory removed")
        return {"path": str(file_path), "removed": True, "type": "directory"}
    
    else:
        logging.error(f"[REMOVE] Unknown path type: {path}")
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