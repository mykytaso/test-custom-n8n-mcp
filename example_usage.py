"""
Example usage of the n8n MCP server with Claude Agent SDK
"""

from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
from src.n8n_mcp_server import n8n_server
import asyncio
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


async def main():
    """Example queries to test the n8n MCP server"""

    # Configure Claude with the n8n MCP server
    options = ClaudeAgentOptions(
        mcp_servers={"n8n": n8n_server},
        allowed_tools=[
            "mcp__n8n__list_workflows",
            "mcp__n8n__get_workflow",
            "mcp__n8n__execute_workflow",
            "mcp__n8n__get_execution",
            "mcp__n8n__activate_workflow",
            "mcp__n8n__deactivate_workflow"
        ]
    )

    async with ClaudeSDKClient(options=options) as client:
        print("=== Example 1: List all workflows ===")
        await client.query("Show me all the workflows in n8n")
        async for message in client.receive_response():
            print(message)
        print()

        print("=== Example 2: Get specific workflow details ===")
        await client.query("Get the details of workflow with ID '1'")
        async for message in client.receive_response():
            print(message)
        print()

        print("=== Example 3: Execute a workflow ===")
        await client.query("Execute the workflow with ID '1'")
        async for message in client.receive_response():
            print(message)
        print()

        print("=== Example 4: Complex query ===")
        await client.query(
            "List all my n8n workflows and tell me which ones are active. "
            "Then execute the first active workflow you find."
        )
        async for message in client.receive_response():
            print(message)


if __name__ == "__main__":
    print("Starting n8n MCP server example...")
    print("Make sure you have:")
    print("1. n8n running (default: http://localhost:5678)")
    print("2. N8N_API_KEY set in .env file")
    print()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}")
