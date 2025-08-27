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

# Sample output
bmahabir@bmahabir-mac ramalama-mcp % uv run agent.py     
Tools available from MCP server:
- list_desktop_files
Agent output: It looks like there are 18 files on your desktop. The file names are:

1. cat.jpeg
2. .DS_Store
3. Screenshot 2025-08-26 at 11.49.32 AM.png
4. Screenshot 2025-05-06 at 2.01.29 PM.png
5. load-image.txt
6. Screenshot 2025-08-26 at 11.48.02 AM.png
7. localized
8. pd.sh
9. big.pdf
10. podbook.tar
11. test.pdf
12. pd.txt
13. crt
14. test.md
15. discord.txt
16. podman-desktop-nice-tests.txt
bmahabir@bmahabir-mac ramalama-mcp % 