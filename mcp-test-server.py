from fastmcp import FastMCP
from pathlib import Path
import platform
import os

mcp = FastMCP("desktop_file_lister")


@mcp.tool(description="Lists all files and folders on the Desktop with their names")
def list_desktop_files() -> str:
    desktop = Path.home() / "Desktop"
    if not desktop.exists():
        return "Desktop folder not found."

    # Collect file/folder names
    items = [f.name for f in desktop.iterdir()]
    if not items:
        return "Desktop is empty."

    return "\n".join(items)

@mcp.tool(description="Get current working directory")
def get_current_directory() -> str:
    """Returns the current working directory."""
    return str(Path.cwd())

@mcp.tool(description="Get system information including OS and Python version")
def get_system_info() -> str:
    """Returns basic system information."""
    info = [
        f"Operating System: {platform.system()} {platform.release()}",
        f"Python Version: {platform.python_version()}",
        f"Machine: {platform.machine()}",
        f"Processor: {platform.processor()}",
        f"Current User: {os.getenv('USER', 'Unknown')}"
    ]
    return "\n".join(info)

@mcp.tool(description="List environment variables starting with a prefix")
def list_env_vars(prefix: str = "PATH") -> str:
    """Lists environment variables that start with the given prefix."""
    matching_vars = []
    for key, value in os.environ.items():
        if key.startswith(prefix.upper()):
            # Truncate long values
            display_value = value[:100] + "..." if len(value) > 100 else value
            matching_vars.append(f"{key}={display_value}")
    
    if not matching_vars:
        return f"No environment variables found starting with '{prefix}'"
    
    return "\n".join(matching_vars)

    
if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=8000)