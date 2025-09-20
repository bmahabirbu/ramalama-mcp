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

@mcp.tool(description="Get the current working directory")
def get_current_directory() -> str:
    return str(Path.cwd())

@mcp.tool(description="Get system information including OS and Python version")
def get_system_info() -> str:
    info = [
        f"Operating System: {platform.system()} {platform.release()}",
        f"Python Version: {platform.python_version()}",
        f"Machine: {platform.machine()}",
        f"Processor: {platform.processor()}",
        f"Current User: {os.getenv('USER', 'Unknown')}"
    ]
    return "\n".join(info)

@mcp.tool(description="Get a person's favorite food given the name of a person")
def get_favorite_food(name: str) -> str:
    return f"{name}'s favorite food is pizza"
    
if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=8000)