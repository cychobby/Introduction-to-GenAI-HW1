import json
import os
import subprocess
import sys
from typing import Dict, Any, List
from duckduckgo_search import DDGS

# Tool definitions for OpenAI function calling
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Perform mathematical calculations and solve equations",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression to evaluate (e.g., '2 + 3 * 4', 'sqrt(16)', 'sin(30)')"
                    }
                },
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the internet for current information and news",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query to look up on the internet"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 3)",
                        "default": 3
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_code",
            "description": "Execute Python code in a safe environment and return the output",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python code to execute"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Execution timeout in seconds (default: 10)",
                        "default": 10
                    }
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "file_operations",
            "description": "Perform basic file operations (read, write, list directory)",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["read", "write", "list"],
                        "description": "Operation to perform"
                    },
                    "path": {
                        "type": "string",
                        "description": "File or directory path"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write (only for write operation)"
                    }
                },
                "required": ["operation", "path"]
            }
        }
    }
]

class ToolExecutor:
    def __init__(self):
        self.safe_paths = ["/tmp", "/home/daddywu/Python區/GenAI_class"]  # Define safe paths

    def calculator(self, expression: str) -> str:
        """Safe calculator function"""
        try:
            # Use eval with restricted globals/locals for safety
            import types
            import math

            # Create a safe builtins module
            safe_builtins = types.ModuleType('safe_builtins')
            safe_builtins.__dict__.update({
                'abs': abs,
                'round': round,
                'min': min,
                'max': max,
                'sum': sum,
                'len': len,
                'range': range,
                'int': int,
                'float': float,
                'str': str,
                'bool': bool,
                'complex': complex,
            })

            allowed_names = {
                '__builtins__': safe_builtins,
                'math': math,
            }

            result = eval(expression, allowed_names)
            return f"Result: {result}"
        except Exception as e:
            return f"Error calculating '{expression}': {str(e)}"

    def web_search(self, query: str, max_results: int = 3) -> str:
        """Web search using DuckDuckGo"""
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
                if not results:
                    return f"No search results found for: {query}"

                output = f"Search results for '{query}':\n\n"
                for i, result in enumerate(results, 1):
                    output += f"{i}. {result['title']}\n"
                    output += f"   {result['body']}\n"
                    output += f"   URL: {result['href']}\n\n"

                return output
        except Exception as e:
            return f"Error searching web: {str(e)}"

    def execute_code(self, code: str, timeout: int = 10) -> str:
        """Execute Python code safely"""
        try:
            # Use subprocess with timeout for safety
            result = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd="/tmp"  # Safe directory
            )

            output = ""
            if result.stdout:
                output += f"Output:\n{result.stdout}"
            if result.stderr:
                output += f"Errors:\n{result.stderr}"

            return output or "Code executed successfully (no output)"
        except subprocess.TimeoutExpired:
            return f"Code execution timed out after {timeout} seconds"
        except Exception as e:
            return f"Error executing code: {str(e)}"

    def file_operations(self, operation: str, path: str, content: str = "") -> str:
        """Safe file operations"""
        try:
            # Security check: ensure path is within safe directories
            abs_path = os.path.abspath(path)
            if not any(abs_path.startswith(safe) for safe in self.safe_paths):
                return f"Error: Access denied to path {path}"

            if operation == "read":
                if not os.path.isfile(path):
                    return f"Error: File {path} does not exist"
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read()

            elif operation == "write":
                # Ensure directory exists
                os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return f"File {path} written successfully"

            elif operation == "list":
                if not os.path.isdir(path):
                    return f"Error: Directory {path} does not exist"
                items = os.listdir(path)
                return "\n".join(items)

            else:
                return f"Error: Unknown operation {operation}"

        except Exception as e:
            return f"Error in file operation: {str(e)}"

    def process_tool_call(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        """Process a tool call and return the result"""
        if not hasattr(self, tool_name):
            return f"Error: Tool '{tool_name}' not found"

        try:
            method = getattr(self, tool_name)
            return method(**tool_args)
        except Exception as e:
            return f"Error executing tool '{tool_name}': {str(e)}"

def get_tools_for_api() -> List[Dict]:
    """Return tools list for API calls"""
    return TOOLS #</content>
#<parameter name="filePath">/home/daddywu/Python區/GenAI_class/tools.py