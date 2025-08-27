import asyncio
from agents import Agent, Runner, OpenAIChatCompletionsModel, AsyncOpenAI
from agents.mcp import MCPServerSse
from agents.run_context import RunContextWrapper

from agents import set_tracing_disabled

set_tracing_disabled(True)

async def main():
    # Wrap a run context (required for server calls)
    run_context = RunContextWrapper(context=None)

    # Use async context manager to connect to MCP server
    async with MCPServerSse(params={"url": "http://127.0.0.1:8000/sse"}) as mcp_server:

        model = OpenAIChatCompletionsModel(
            model="llama3.2",
            openai_client=AsyncOpenAI(
                base_url="http://localhost:8080/v1",
                api_key=""
            )
        )

        # Create the Agent
        agent = Agent(
            name="Assistant",
            instructions="Use the tools to achieve the task",
            mcp_servers=[mcp_server],
            model=model
        )

        # List available tools (optional, for debugging)
        tools = await mcp_server.list_tools(run_context, agent)
        print("Tools available from MCP server:")
        for tool in tools:
            print("-", tool.name)

        # Run the Agent
        result = await Runner.run(agent, "How many files do I have on my Desktop and what are the file names?", max_turns=100)
        print("Agent output:", result.final_output)

asyncio.run(main())