# ramalama-mcp
Files to test local mcp for ramalama

the local mcp server list files on the desktop

# How to use

# Run MCP 
uv run mcp-test-server.py 
in one terminal tab

# Run Ramalama
uv run ramalama serve llama3.2 --network=bridge
note must run without --chat-template-file
in another terminal tab

# Run main
uv run agent.py
in a final terminal tab 