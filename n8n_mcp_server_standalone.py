#!/usr/bin/env python3
"""
n8n MCP Server for Claude Desktop
Uses the MCP Python SDK to provide n8n workflow tools to Claude Desktop
"""

import asyncio
import os
import sys
import ssl
import json
from typing import Any
import aiohttp
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import MCP SDK
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# n8n configuration
N8N_BASE_URL = os.getenv("N8N_BASE_URL", "http://localhost:5678").rstrip("/")
N8N_API_KEY = os.getenv("N8N_API_KEY", "")
N8N_SKIP_SSL_VERIFY = os.getenv("N8N_SKIP_SSL_VERIFY", "false").lower() == "true"

# Create MCP server
app = Server("n8n-mcp-custom")


async def make_n8n_request(
    method: str,
    endpoint: str,
    data: dict = None
) -> dict[str, Any]:
    """Helper function to make requests to n8n API"""
    if not N8N_API_KEY:
        return {
            "error": "N8N_API_KEY not configured. Set environment variable N8N_API_KEY."
        }

    url = f"{N8N_BASE_URL}/api/v1/{endpoint}"
    headers = {
        "X-N8N-API-KEY": N8N_API_KEY,
        "Content-Type": "application/json"
    }

    # Configure SSL context
    ssl_context = None
    if N8N_SKIP_SSL_VERIFY:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

    try:
        connector = aiohttp.TCPConnector(ssl=ssl_context) if ssl_context else None
        async with aiohttp.ClientSession(connector=connector) as session:
            if method == "GET":
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        return {"error": f"HTTP {response.status}: {error_text}"}

            elif method == "POST":
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status in [200, 201]:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        return {"error": f"HTTP {response.status}: {error_text}"}

            elif method == "PATCH":
                async with session.patch(url, headers=headers, json=data) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        return {"error": f"HTTP {response.status}: {error_text}"}

            elif method == "DELETE":
                async with session.delete(url, headers=headers) as response:
                    if response.status in [200, 204]:
                        return {"success": True}
                    else:
                        error_text = await response.text()
                        return {"error": f"HTTP {response.status}: {error_text}"}

    except Exception as e:
        return {"error": f"Request failed: {str(e)}"}


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available n8n tools"""
    return [
        Tool(
            name="list_workflows",
            description="List all workflows in n8n. Returns workflow names, IDs, and active status.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_workflow",
            description="Get detailed information about a specific workflow by ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_id": {
                        "type": "string",
                        "description": "The ID of the workflow"
                    }
                },
                "required": ["workflow_id"]
            }
        ),
        Tool(
            name="execute_workflow",
            description="Execute a workflow by ID. Optionally pass input data as JSON string.",
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_id": {
                        "type": "string",
                        "description": "The ID of the workflow to execute"
                    },
                    "input_data": {
                        "type": "string",
                        "description": "Optional JSON string with input data for the workflow"
                    }
                },
                "required": ["workflow_id"]
            }
        ),
        Tool(
            name="get_execution",
            description="Get the status and result of a workflow execution by execution ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "execution_id": {
                        "type": "string",
                        "description": "The execution ID to check"
                    }
                },
                "required": ["execution_id"]
            }
        ),
        Tool(
            name="activate_workflow",
            description="Activate (enable) a workflow by ID so it can run automatically.",
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_id": {
                        "type": "string",
                        "description": "The ID of the workflow to activate"
                    }
                },
                "required": ["workflow_id"]
            }
        ),
        Tool(
            name="deactivate_workflow",
            description="Deactivate (disable) a workflow by ID to stop it from running automatically.",
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_id": {
                        "type": "string",
                        "description": "The ID of the workflow to deactivate"
                    }
                },
                "required": ["workflow_id"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls"""

    if name == "list_workflows":
        result = await make_n8n_request("GET", "workflows")

        if "error" in result:
            return [TextContent(type="text", text=f"Error: {result['error']}")]

        workflows = result.get("data", [])

        if not workflows:
            return [TextContent(type="text", text="No workflows found in n8n.")]

        workflow_list = []
        for wf in workflows:
            workflow_list.append(
                f"- {wf.get('name', 'Unnamed')} (ID: {wf.get('id')}) "
                f"[{'Active' if wf.get('active') else 'Inactive'}]"
            )

        response_text = f"Found {len(workflows)} workflow(s):\n" + "\n".join(workflow_list)
        return [TextContent(type="text", text=response_text)]

    elif name == "get_workflow":
        workflow_id = arguments.get("workflow_id")
        result = await make_n8n_request("GET", f"workflows/{workflow_id}")

        if "error" in result:
            return [TextContent(type="text", text=f"Error: {result['error']}")]

        # Handle both nested and flat response structures
        if "data" in result:
            wf = result.get("data", {})
        else:
            wf = result

        # Get nodes and connections
        nodes = wf.get('nodes', [])
        connections = wf.get('connections', {})

        info = [
            f"Workflow: {wf.get('name', 'Unnamed')}",
            f"ID: {wf.get('id')}",
            f"Status: {'Active' if wf.get('active') else 'Inactive'}",
            f"Nodes: {len(nodes)}",
            f"Connections: {len(connections)}",
        ]

        # Add node details if available
        if nodes:
            info.append(f"\nNodes in workflow:")
            for node in nodes:
                node_type = node.get('type', 'Unknown')
                node_name = node.get('name', 'Unnamed')
                info.append(f"  - {node_name} ({node_type})")

        if wf.get('tags'):
            info.append(f"\nTags: {', '.join([tag.get('name', '') for tag in wf.get('tags', [])])}")

        return [TextContent(type="text", text="\n".join(info))]

    elif name == "execute_workflow":
        workflow_id = arguments.get("workflow_id")
        input_data = arguments.get("input_data", "{}")

        # Parse input data
        try:
            data_payload = json.loads(input_data) if input_data else {}
        except json.JSONDecodeError:
            return [TextContent(type="text", text="Error: input_data must be valid JSON string")]

        result = await make_n8n_request(
            "POST",
            f"workflows/{workflow_id}/execute",
            data_payload
        )

        if "error" in result:
            return [TextContent(type="text", text=f"Error: {result['error']}")]

        execution_data = result.get("data", {})
        execution_id = execution_data.get("id", "unknown")
        finished = execution_data.get("finished", False)

        response_text = f"Workflow executed!\nExecution ID: {execution_id}\nStatus: {'Finished' if finished else 'Running'}"
        return [TextContent(type="text", text=response_text)]

    elif name == "get_execution":
        execution_id = arguments.get("execution_id")
        result = await make_n8n_request("GET", f"executions/{execution_id}")

        if "error" in result:
            return [TextContent(type="text", text=f"Error: {result['error']}")]

        execution = result.get("data", {})

        info = [
            f"Execution ID: {execution.get('id')}",
            f"Workflow: {execution.get('workflowData', {}).get('name', 'Unknown')}",
            f"Status: {'Finished' if execution.get('finished') else 'Running'}",
            f"Mode: {execution.get('mode', 'unknown')}",
        ]

        if execution.get("stoppedAt"):
            info.append(f"Stopped at: {execution.get('stoppedAt')}")

        return [TextContent(type="text", text="\n".join(info))]

    elif name == "activate_workflow":
        workflow_id = arguments.get("workflow_id")
        result = await make_n8n_request(
            "PATCH",
            f"workflows/{workflow_id}",
            {"active": True}
        )

        if "error" in result:
            return [TextContent(type="text", text=f"Error: {result['error']}")]

        return [TextContent(type="text", text=f"Workflow {workflow_id} activated successfully!")]

    elif name == "deactivate_workflow":
        workflow_id = arguments.get("workflow_id")
        result = await make_n8n_request(
            "PATCH",
            f"workflows/{workflow_id}",
            {"active": False}
        )

        if "error" in result:
            return [TextContent(type="text", text=f"Error: {result['error']}")]

        return [TextContent(type="text", text=f"Workflow {workflow_id} deactivated successfully!")]

    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())