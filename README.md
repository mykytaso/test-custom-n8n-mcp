# n8n MCP Server

A Model Context Protocol (MCP) server for integrating Claude with n8n workflow automation platform.

## Overview

This MCP server allows Claude to interact with your n8n instance, enabling:
- Listing workflows
- Getting workflow details
- Executing workflows
- Checking execution status
- Activating/deactivating workflows

## Prerequisites

- Python 3.13+
- n8n instance running (local or remote)
- n8n API key

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure n8n connection:
```bash
cp .env.example .env
# Edit .env and add your n8n API key
```

## Getting n8n API Key

1. Open your n8n instance (e.g., http://localhost:5678)
2. Go to **Settings** → **API**
3. Generate or copy your API key
4. Add it to your `.env` file

## Usage

### Basic Example

```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
from src.n8n_mcp_server import n8n_server
import asyncio
from dotenv import load_dotenv

load_dotenv()

async def main():
    options = ClaudeAgentOptions(
        mcp_servers={"n8n": n8n_server},
        allowed_tools=[
            "mcp__n8n__list_workflows",
            "mcp__n8n__execute_workflow",
            # ... other tools
        ]
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query("Show me all workflows in n8n")
        async for message in client.receive_response():
            print(message)

asyncio.run(main())
```

### Run Example Script

```bash
python example_usage.py
```

## Available Tools

### 1. `list_workflows`
Lists all workflows in your n8n instance.

**Example query:** "Show me all my n8n workflows"

### 2. `get_workflow`
Get detailed information about a specific workflow.

**Parameters:**
- `workflow_id` (string): The ID of the workflow

**Example query:** "Get details of workflow with ID '5'"

### 3. `execute_workflow`
Execute a workflow by ID.

**Parameters:**
- `workflow_id` (string): The ID of the workflow
- `input_data` (string, optional): JSON string with input data

**Example queries:**
- "Execute workflow with ID '3'"
- "Run workflow 5 with input data {'name': 'test'}"

### 4. `get_execution`
Get the status and result of a workflow execution.

**Parameters:**
- `execution_id` (string): The execution ID

**Example query:** "Check the status of execution '12345'"

### 5. `activate_workflow`
Activate a workflow to enable automatic execution.

**Parameters:**
- `workflow_id` (string): The ID of the workflow

**Example query:** "Activate workflow with ID '2'"

### 6. `deactivate_workflow`
Deactivate a workflow to disable automatic execution.

**Parameters:**
- `workflow_id` (string): The ID of the workflow

**Example query:** "Deactivate workflow 7"

## Configuration

Environment variables (set in `.env`):

- `N8N_BASE_URL`: n8n instance URL (default: `http://localhost:5678`)
- `N8N_API_KEY`: Your n8n API key (required)

## Project Structure

```
TestMCP/
├── src/
│   └── n8n_mcp_server.py    # Main MCP server implementation
├── example_usage.py          # Example usage script
├── requirements.txt          # Python dependencies
├── .env.example             # Example environment configuration
└── README.md                # This file
```

## Troubleshooting

### "N8N_API_KEY not configured"
Make sure you have created a `.env` file with your n8n API key:
```
N8N_API_KEY=your_actual_api_key_here
```

### Connection errors
- Verify n8n is running: Check if you can access n8n UI
- Check the `N8N_BASE_URL` in your `.env` file
- Ensure your API key is valid

### Workflow not found
- Verify the workflow ID exists in your n8n instance
- Check if you have permissions to access the workflow

## n8n API Documentation

For more information about the n8n API:
https://docs.n8n.io/api/

## License

MIT
