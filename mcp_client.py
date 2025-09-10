#!/usr/bin/env python3
"""
Pure Python MCP client for FastMCP servers using streamable HTTP transport.

This client successfully connects to FastMCP servers and can:
- Initialize MCP sessions
- List available tools
- Call tools with parameters
- Handle Server-Sent Events (SSE) responses

The key insight is that FastMCP requires:
1. Accept header: "application/json, text/event-stream"
2. Proper MCP session initialization with notifications/initialized
3. SSE response parsing for streamable HTTP transport
"""

import requests
import json
from typing import Dict, Any, Optional

class PureMCPClient:
    """A pure Python MCP client that works with FastMCP servers."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session_id = None
        self.request_id = 0
        
    def _get_next_request_id(self) -> int:
        """Get the next request ID for JSON-RPC messages."""
        self.request_id += 1
        return self.request_id
    
    def _send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send a JSON-RPC request via HTTP POST."""
        
        message = {
            "jsonrpc": "2.0",
            "id": self._get_next_request_id(),
            "method": method,
            "params": params or {}
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"  # Key requirement for FastMCP
        }
        
        # Add session ID header if we have one
        if self.session_id:
            headers["mcp-session-id"] = self.session_id
            
        response = self.session.post(
            self.base_url,
            headers=headers,
            json=message
        )
        
        # Extract session ID from response headers if present
        if "mcp-session-id" in response.headers:
            self.session_id = response.headers["mcp-session-id"]
            
        if response.status_code != 200:
            print(f"Error response: {response.status_code}")
            print(f"Response headers: {response.headers}")
            print(f"Response body: {response.text}")
            response.raise_for_status()
            
        # Check if response is SSE format
        if response.headers.get('content-type') == 'text/event-stream':
            return self._parse_sse_response(response.text)
        else:
            return response.json()
    
    def _parse_sse_response(self, sse_text: str) -> Dict[str, Any]:
        """Parse Server-Sent Events response to extract JSON data."""
        lines = sse_text.strip().split('\n')
        
        for line in lines:
            if line.startswith('data: '):
                json_data = line[6:]  # Remove 'data: ' prefix
                try:
                    return json.loads(json_data)
                except json.JSONDecodeError as e:
                    print(f"Failed to parse JSON from SSE data: {json_data}")
                    raise e
        
        print(f"No data found in SSE response: {sse_text}")
        return {}
    
    def _send_notification(self, method: str, params: Optional[Dict[str, Any]] = None):
        """Send a JSON-RPC notification (no response expected)."""
        message = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {}
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        
        if self.session_id:
            headers["mcp-session-id"] = self.session_id
            
        response = self.session.post(
            self.base_url,
            headers=headers,
            json=message
        )
        
        # Notifications don't expect responses, but check for errors
        if response.status_code not in [200, 202]:  # 202 is acceptable for notifications
            print(f"Notification error: {response.status_code} - {response.text}")
        
        return response
    
    def initialize(self) -> Dict[str, Any]:
        """Initialize the MCP session."""
        result = self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "roots": {"listChanged": True},
                "sampling": {}
            },
            "clientInfo": {
                "name": "pure-python-client",
                "version": "1.0.0"
            }
        })
        
        # Send initialized notification as required by MCP protocol
        self._send_notification("notifications/initialized")
        
        return result
    
    def list_tools(self) -> Dict[str, Any]:
        """List available tools."""
        return self._send_request("tools/list", {})
    
    def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Call a tool."""
        return self._send_request("tools/call", {
            "name": name,
            "arguments": arguments or {}
        })
    
    def list_resources(self) -> Dict[str, Any]:
        """List available resources."""
        return self._send_request("resources/list", {})
    
    def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a resource by URI."""
        return self._send_request("resources/read", {
            "uri": uri
        })
    
    def list_prompts(self) -> Dict[str, Any]:
        """List available prompts."""
        return self._send_request("prompts/list", {})
    
    def get_prompt(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get a prompt by name."""
        return self._send_request("prompts/get", {
            "name": name,
            "arguments": arguments or {}
        })
    
    def close(self):
        """Close the session."""
        if self.session:
            self.session.close()

def main():
    """Demo of the simple MCP client."""
    import sys
    
    # Allow URL to be passed as command line argument
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000/mcp"
    
    client = PureMCPClient(url)
    
    try:
        print("🔌 Initializing MCP session...")
        init_result = client.initialize()
        print(f"✅ Connected to: {init_result['result']['serverInfo']['name']}")
        print(f"📋 Protocol version: {init_result['result']['protocolVersion']}")
        
        print("\n🔧 Listing available tools...")
        tools_result = client.list_tools()
        tools = tools_result['result']['tools']
        print(f"📊 Found {len(tools)} tool(s):")
        
        if not tools:
            print("  No tools available on this server.")
            return
            
        for i, tool in enumerate(tools, 1):
            print(f"  {i}. {tool['name']}: {tool['description']}")
            # Show input schema if available
            if 'inputSchema' in tool and tool['inputSchema'].get('properties'):
                props = tool['inputSchema']['properties']
                if props:
                    print(f"     Parameters: {', '.join(props.keys())}")
        
        # Demo: Call the first tool
        if tools:
            first_tool = tools[0]
            tool_name = first_tool['name']
            
            print(f"\n🚀 Calling tool: {tool_name}...")
            call_result = client.call_tool(tool_name, {})
            
            if 'error' in call_result:
                print(f"❌ Tool call failed: {call_result['error']['message']}")
            elif call_result['result']['isError']:
                print("❌ Tool execution failed")
                if 'content' in call_result['result']:
                    error_content = call_result['result']['content'][0].get('text', 'Unknown error')
                    print(f"   Error: {error_content}")
            else:
                print("✅ Tool executed successfully:")
                if 'content' in call_result['result']:
                    content = call_result['result']['content'][0]['text']
                    print(f"📁 Result:\n{content}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()
        print("\n🔌 Connection closed")

if __name__ == "__main__":
    main()
