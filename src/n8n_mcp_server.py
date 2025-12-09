"""
MCP Server for n8n Integration
Provides tools to interact with n8n workflow automation platform
"""

from claude_agent_sdk import tool, create_sdk_mcp_server
from typing import Any
import aiohttp
import os
import json
import ssl
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# n8n configuration - can be set via environment variables
N8N_BASE_URL = os.getenv("N8N_BASE_URL", "http://localhost:5678").rstrip("/")
N8N_API_KEY = os.getenv("N8N_API_KEY", "")
N8N_SKIP_SSL_VERIFY = os.getenv("N8N_SKIP_SSL_VERIFY", "false").lower() == "true"


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


@tool(
    "list_workflows",
    "List all workflows in n8n. Returns workflow names, IDs, and active status.",
    {}
)
async def list_workflows(args: dict[str, Any]) -> dict[str, Any]:
    """List all n8n workflows"""
    try:
        result = await make_n8n_request("GET", "workflows")

        if "error" in result:
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error: {result['error']}"
                }],
                "is_error": True
            }

        workflows = result.get("data", [])

        if not workflows:
            return {
                "content": [{
                    "type": "text",
                    "text": "No workflows found in n8n."
                }]
            }

        # Format workflow list
        workflow_list = []
        for wf in workflows:
            workflow_list.append(
                f"- {wf.get('name', 'Unnamed')} (ID: {wf.get('id')}) "
                f"[{'Active' if wf.get('active') else 'Inactive'}]"
            )

        response_text = f"Found {len(workflows)} workflow(s):\n" + "\n".join(workflow_list)

        return {
            "content": [{
                "type": "text",
                "text": response_text
            }]
        }

    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": f"Failed to list workflows: {str(e)}"
            }],
            "is_error": True
        }


@tool(
    "get_workflow",
    "Get detailed information about a specific workflow by ID.",
    {"workflow_id": str}
)
async def get_workflow(args: dict[str, Any]) -> dict[str, Any]:
    """Get details of a specific workflow"""
    try:
        workflow_id = args["workflow_id"]
        result = await make_n8n_request("GET", f"workflows/{workflow_id}")

        if "error" in result:
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error: {result['error']}"
                }],
                "is_error": True
            }

        wf = result.get("data", {})
        info = [
            f"Workflow: {wf.get('name', 'Unnamed')}",
            f"ID: {wf.get('id')}",
            f"Status: {'Active' if wf.get('active') else 'Inactive'}",
            f"Nodes: {len(wf.get('nodes', []))}",
            f"Connections: {len(wf.get('connections', {}))}",
        ]

        if wf.get('tags'):
            info.append(f"Tags: {', '.join([tag.get('name', '') for tag in wf.get('tags', [])])}")

        return {
            "content": [{
                "type": "text",
                "text": "\n".join(info)
            }]
        }

    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": f"Failed to get workflow: {str(e)}"
            }],
            "is_error": True
        }


@tool(
    "execute_workflow",
    "Execute a workflow by ID. Optionally pass input data as JSON string.",
    {"workflow_id": str, "input_data": str}
)
async def execute_workflow(args: dict[str, Any]) -> dict[str, Any]:
    """Execute a workflow"""
    try:
        workflow_id = args["workflow_id"]

        # Parse input data if provided
        data_payload = {}
        if args.get("input_data"):
            try:
                data_payload = json.loads(args["input_data"])
            except json.JSONDecodeError:
                return {
                    "content": [{
                        "type": "text",
                        "text": "Error: input_data must be valid JSON string"
                    }],
                    "is_error": True
                }

        result = await make_n8n_request(
            "POST",
            f"workflows/{workflow_id}/execute",
            data_payload
        )

        if "error" in result:
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error: {result['error']}"
                }],
                "is_error": True
            }

        execution_data = result.get("data", {})
        execution_id = execution_data.get("id", "unknown")
        finished = execution_data.get("finished", False)

        response_text = f"Workflow executed!\nExecution ID: {execution_id}\nStatus: {'Finished' if finished else 'Running'}"

        return {
            "content": [{
                "type": "text",
                "text": response_text
            }]
        }

    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": f"Failed to execute workflow: {str(e)}"
            }],
            "is_error": True
        }


@tool(
    "get_execution",
    "Get the status and result of a workflow execution by execution ID.",
    {"execution_id": str}
)
async def get_execution(args: dict[str, Any]) -> dict[str, Any]:
    """Get execution status"""
    try:
        execution_id = args["execution_id"]
        result = await make_n8n_request("GET", f"executions/{execution_id}")

        if "error" in result:
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error: {result['error']}"
                }],
                "is_error": True
            }

        execution = result.get("data", {})

        info = [
            f"Execution ID: {execution.get('id')}",
            f"Workflow: {execution.get('workflowData', {}).get('name', 'Unknown')}",
            f"Status: {'Finished' if execution.get('finished') else 'Running'}",
            f"Mode: {execution.get('mode', 'unknown')}",
        ]

        if execution.get("stoppedAt"):
            info.append(f"Stopped at: {execution.get('stoppedAt')}")

        return {
            "content": [{
                "type": "text",
                "text": "\n".join(info)
            }]
        }

    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": f"Failed to get execution: {str(e)}"
            }],
            "is_error": True
        }


@tool(
    "activate_workflow",
    "Activate (enable) a workflow by ID so it can run automatically.",
    {"workflow_id": str}
)
async def activate_workflow(args: dict[str, Any]) -> dict[str, Any]:
    """Activate a workflow"""
    try:
        workflow_id = args["workflow_id"]
        result = await make_n8n_request(
            "PATCH",
            f"workflows/{workflow_id}",
            {"active": True}
        )

        if "error" in result:
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error: {result['error']}"
                }],
                "is_error": True
            }

        return {
            "content": [{
                "type": "text",
                "text": f"Workflow {workflow_id} activated successfully!"
            }]
        }

    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": f"Failed to activate workflow: {str(e)}"
            }],
            "is_error": True
        }


@tool(
    "deactivate_workflow",
    "Deactivate (disable) a workflow by ID to stop it from running automatically.",
    {"workflow_id": str}
)
async def deactivate_workflow(args: dict[str, Any]) -> dict[str, Any]:
    """Deactivate a workflow"""
    try:
        workflow_id = args["workflow_id"]
        result = await make_n8n_request(
            "PATCH",
            f"workflows/{workflow_id}",
            {"active": False}
        )

        if "error" in result:
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error: {result['error']}"
                }],
                "is_error": True
            }

        return {
            "content": [{
                "type": "text",
                "text": f"Workflow {workflow_id} deactivated successfully!"
            }]
        }

    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": f"Failed to deactivate workflow: {str(e)}"
            }],
            "is_error": True
        }


# Create the n8n MCP server
n8n_server = create_sdk_mcp_server(
    name="n8n",
    version="1.0.0",
    tools=[
        list_workflows,
        get_workflow,
        execute_workflow,
        get_execution,
        activate_workflow,
        deactivate_workflow
    ]
)


# Export the server for use in other modules
__all__ = ["n8n_server"]
