from fastmcp import FastMCP
from pathlib import Path

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

if __name__ == "__main__":
    mcp.run(transport="sse", host="127.0.0.1", port=8000)