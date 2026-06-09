# Jules MCP Server

A dockerized remote MCP server for the Google Jules API. It allows ChatGPT (or any MCP client) to connect to the Jules API via HTTP/SSE.

## Features

- Built with FastAPI and FastMCP.
- Connects to `https://jules.googleapis.com/v1alpha` (configurable via `JULES_API_BASE`).
- Pass-through authentication: forwards `X-Goog-Api-Key` to the Jules API securely.
- Exposes all Jules MCP tools.
- Dockerized for easy deployment.

## Build

```bash
docker build -t jules-mcp-server .
```

## Run

```bash
docker run --rm -p 8000:8000 jules-mcp-server
```

## ChatGPT Setup

To configure this as a custom MCP server in ChatGPT:

1. **Name**: `Jules MCP`
2. **Server URL**: Try `https://your-domain.example.com/mcp` first. If ChatGPT rejects that endpoint or your transport requires SSE, use the fallback: `https://your-domain.example.com/sse/`
3. **Authentication**:
   - **Type**: API key / access token
   - **Header schema**: custom header
   - **Header name**: `X-Goog-Api-Key`
   - **Header value**: (Your Jules API key from Jules settings)
