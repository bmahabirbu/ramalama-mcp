#!/usr/bin/env python3
from mcp_client import PureMCPClient
from typing import Dict, Any, Optional, List
import requests
import json

class LLMAgent:
    """An LLM-powered agent that can make multiple tool calls to accomplish tasks."""
    
    def __init__(self, clients: List[PureMCPClient], llm_base_url: str = "http://localhost:8080"):
        self.clients = clients if isinstance(clients, list) else [clients]
        self.llm_base_url = llm_base_url.rstrip('/')
        self.available_tools = []
        self.tool_to_client = {} 
        self.llm_available = False
        
    def test_llm_connection(self) -> bool:
        """Test if LLM server is available."""
        try:
            response = requests.get(f"{self.llm_base_url}/v1/models", timeout=5)
            self.llm_available = response.status_code == 200
            return self.llm_available
        except:
            self.llm_available = False
            return False
    
    def initialize(self):
        """Initialize the agent and get available tools from all clients."""
        # Test LLM connection first
        llm_status = self.test_llm_connection()
        print(f"🧠 LLM server ({'✅ Available' if llm_status else '❌ Unavailable'}) at {self.llm_base_url}")
        
        all_init_results = []
        self.available_tools = []
        self.tool_to_client = {}
        
        for i, client in enumerate(self.clients):
            try:
                print(f"🔌 Connecting to server {i+1}/{len(self.clients)}...")
                init_result = client.initialize()
                all_init_results.append(init_result)
                
                server_name = init_result['result']['serverInfo']['name']
                print(f"✅ Connected to: {server_name}")
                
                # Get tools from this server
                tools_result = client.list_tools()
                server_tools = tools_result['result']['tools']
                
                # Add server info to each tool and track which client provides it
                for tool in server_tools:
                    tool_name = tool['name']
                    # Handle name conflicts by prefixing with server name
                    if tool_name in self.tool_to_client:
                        original_name = tool_name
                        tool_name = f"{server_name}_{original_name}"
                        tool['name'] = tool_name
                        print(f"⚠️  Tool name conflict: '{original_name}' renamed to '{tool_name}'")
                    
                    tool['server'] = server_name
                    self.tool_to_client[tool_name] = client
                    self.available_tools.append(tool)
                
                print(f"📊 Found {len(server_tools)} tool(s) from {server_name}")
                
            except Exception as e:
                print(f"❌ Failed to connect to server {i+1}: {e}")
                continue
        
        if not self.available_tools:
            raise Exception("No tools available from any server")
            
        print(f"🎯 Total tools available: {len(self.available_tools)}")
        return all_init_results, self.available_tools
    
    def _call_llm(self, messages: List[Dict[str, str]]) -> str:
        """Call the LLM with the given messages."""
        if not self.llm_available:
            return ""
            
        try:
            response = requests.post(
                f"{self.llm_base_url}/v1/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer dummy"
                },
                json={
                    "messages": messages,
                    "stream": True
                },
                timeout=30
            )
            response.raise_for_status()
            
            # Handle streaming response
            content = ""
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data_str = line[6:]  # Remove 'data: ' prefix
                        if data_str.strip() == '[DONE]':
                            break
                        try:
                            data = json.loads(data_str)
                            if 'choices' in data and len(data['choices']) > 0:
                                delta = data['choices'][0].get('delta', {})
                                if 'content' in delta and delta['content'] is not None:
                                    content += delta['content']
                        except json.JSONDecodeError:
                            continue
            
            return content.strip()
        except Exception as e:
            print(f"⚠️  LLM call failed: {e}")
            self.llm_available = False  # Mark as unavailable after failure
            return ""
    
    def run_task(self, task: str, max_turns: int = 5) -> Dict[str, Any]:
        """Run a task with multiple tool calls if needed."""
        print(f"🎯 Task: {task}")
        
        if not self.llm_available:
            print("❌ LLM is required for this agent but is not available. Please ensure LLM server is running.")
            return {
                'task': task,
                'turns': 0,
                'results': [],
                'final_result': None,
                'error': 'LLM not available'
            }
        
        results = []
        turn = 0
        
        while turn < max_turns:
            turn += 1
            print(f"\n--- Turn {turn} ---")
            
            # LLM-powered tool selection
            selected_tool = self._select_tool(task, results)
            
            if not selected_tool:
                print("No suitable tool found for this task.")
                break
                
            print(f"🔧 Using tool: {selected_tool['name']}")
            
            # Call the tool using the appropriate client
            try:
                client = self.tool_to_client[selected_tool['name']]
                result = client.call_tool(selected_tool['name'], {})
                
                if 'error' in result:
                    print(f"❌ Tool call failed: {result['error']['message']}")
                    results.append({
                        'turn': turn,
                        'tool': selected_tool['name'],
                        'success': False,
                        'error': result['error']['message']
                    })
                elif result['result']['isError']:
                    print("❌ Tool execution failed")
                    results.append({
                        'turn': turn,
                        'tool': selected_tool['name'],
                        'success': False,
                        'error': 'Tool execution failed'
                    })
                else:
                    content = result['result']['content'][0]['text']
                    print(f"✅ Tool result: {content}")
                    
                    results.append({
                        'turn': turn,
                        'tool': selected_tool['name'],
                        'success': True,
                        'content': content
                    })
                    
                    # LLM-powered task completion check
                    if self._is_task_complete(task, results):
                        print(f"✅ Task completed after {turn} turn(s)")
                        break
                        
            except Exception as e:
                print(f"❌ Error calling tool: {e}")
                results.append({
                    'turn': turn,
                    'tool': selected_tool['name'],
                    'success': False,
                    'error': str(e)
                })
        
        return {
            'task': task,
            'turns': turn,
            'results': results,
            'final_result': results[-1] if results else None
        }
    
    def _select_tool(self, task: str, previous_results: List[Dict]) -> Optional[Dict]:
        """LLM-powered tool selection."""
        if not self.available_tools:
            return None
        
        return self._select_tool_with_llm(task, previous_results)
    
    def _select_tool_with_llm(self, task: str, previous_results: List[Dict]) -> Optional[Dict]:
        """LLM-powered tool selection."""
        tools_context = "Available tools:\n"
        for i, tool in enumerate(self.available_tools, 1):
            server_info = f" (from {tool['server']})" if 'server' in tool else ""
            tools_context += f"{i}. {tool['name']}: {tool['description']}{server_info}\n"
        
        messages = [
            {
                "role": "system",
                "content": """You are a helpful assistant that selects the best tool for a given task.

Analyze the task and the available tools, then respond with ONLY the exact name of the most appropriate tool.

Consider:
- What the user is trying to accomplish
- Which tool's description best matches the task requirements
- Which tool is most likely to provide the needed information or perform the required action"""
            },
            {
                "role": "user",
                "content": f"""Task: {task}

{tools_context}

Which tool should I use to complete this task? Respond with ONLY the tool name."""
            }
        ]
        
        response = self._call_llm(messages)
        
        # Find the tool by name
        for tool in self.available_tools:
            if tool['name'].lower() == response.lower().strip():
                return tool
        
        # If LLM failed, return first tool as last resort
        return self.available_tools[0] if self.available_tools else None
    
    def _is_task_complete(self, task: str, results: List[Dict]) -> bool:
        """LLM-powered task completion check."""
        if not results or not any(r['success'] for r in results):
            return False
            
        return self._is_task_complete_with_llm(task, results)
    
    def _is_task_complete_with_llm(self, task: str, results: List[Dict]) -> bool:
        """LLM-powered task completion check."""
        if not results or not any(r['success'] for r in results):
            return False
        
        # Get the latest successful result
        last_success = None
        for result in reversed(results):
            if result['success']:
                last_success = result
                break
        
        if not last_success:
            return False
        
        messages = [
            {
                "role": "system",
                "content": """You are a helpful assistant that determines if a task has been completed successfully.

Analyze the original task and the tool result, then respond with ONLY "YES" if the task is complete or "NO" if more work is needed.

Be practical about what's achievable:
- If the task asks for a count and you can count items from the result, that's complete
- If the task asks to identify file types but the tool only lists names, you can still make reasonable inferences from extensions
- If the task asks "how many" and you see a list, you can count it - that answers the question
- Don't expect perfect information if the available tools have limitations

Focus on whether the core question can be answered from the available data."""
            },
            {
                "role": "user",
                "content": f"""Task: {task}

Tool result:
{last_success['content']}

Can the core question be answered from this result, even if not perfectly? Answer ONLY with YES or NO."""
            }
        ]
        
        response = self._call_llm(messages)
        print(f"🤔 LLM completion response: '{response}'")
        
        return response and response.upper().strip() == "YES"
    
    def analyze_results(self, task: str, results: List[Dict]) -> str:
        """LLM-powered result analysis and formatting."""
        if not results or not any(r['success'] for r in results):
            return "❌ Task could not be completed successfully."
        
        # Get the last successful result
        last_success = None
        for result in reversed(results):
            if result['success']:
                last_success = result
                break
        
        if not last_success:
            return "❌ No successful results found."
        
        content = last_success['content']
        
        messages = [
            {
                "role": "system",
                "content": """You are a helpful assistant that formats and presents information clearly.

Your job is to:
1. Understand what the user originally requested
2. Analyze the raw tool output 
3. Present the information in a clear, well-organized way
4. Answer the original request directly and completely

Use appropriate formatting and structure, to make the response engaging and easy to read.
Focus on directly answering what was asked."""
            },
            {
                "role": "user",
                "content": f"""Original request: {task}

Raw tool output:
{content}

Please provide a clear, well-formatted response that directly answers the original request."""
            }
        ]
        
        response = self._call_llm(messages)
        return response or f"✅ Result:\n{content}"

def main():
    """Demo of the MCP agent."""
    import sys
    
    # Parse command line arguments
    urls = ["http://127.0.0.1:8000/mcp","http://127.0.0.1:8001/mcp"]
    task = "what are my environment variables?"
    
    if len(sys.argv) > 1:
        # Support multiple URLs separated by commas
        url_arg = sys.argv[1]
        if ',' in url_arg:
            urls = [url.strip() for url in url_arg.split(',')]
        else:
            urls = [url_arg]
    
    if len(sys.argv) > 2:
        task = sys.argv[2]
    
    # Create clients for each URL
    clients = []
    for url in urls:
        try:
            clients.append(PureMCPClient(url))
        except Exception as e:
            print(f"❌ Failed to create client for {url}: {e}")
    
    if not clients:
        print("❌ No valid clients created")
        return
    
    agent = LLMAgent(clients, "http://localhost:8080")
    
    try:
        print("🤖 Initializing MCP agent...")
        init_results, tools = agent.initialize()
        
        # Show summary of all connected servers
        server_names = [result['result']['serverInfo']['name'] for result in init_results]
        print(f"✅ Connected to {len(server_names)} server(s): {', '.join(server_names)}")
        print(f"📊 Found {len(tools)} tool(s): {', '.join(tool['name'] for tool in tools)}")
        
        # Run the task
        result = agent.run_task(task, max_turns=5)
        
        print(f"\n🎉 Final Summary:")
        print(f"Task: {result['task']}")
        print(f"Turns taken: {result['turns']}")
        
        # Analyze and present results
        analysis = agent.analyze_results(task, result['results'])
        print(f"\n{analysis}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        for client in agent.clients:
            client.close()
        print("\n🔌 All connections closed")

if __name__ == "__main__":
    main()
