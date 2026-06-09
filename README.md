# Jules MCP Server

A dockerized remote MCP server for the Google Jules API. It allows ChatGPT (or any MCP client) to connect to the Jules API via HTTP/SSE.

## Features

- Built with FastAPI and FastMCP.
- Connects to `https://jules.googleapis.com/v1alpha` (configurable via `JULES_API_BASE`).
- Pass-through authentication: forwards `X-Goog-Api-Key` to the Jules API securely.
- Exposes all Jules MCP tools.
- Dockerized for easy deployment.

## Deployment

This app is primarily designed to be deployed using Google Cloud Run with native Python buildpacks.

### Google Cloud Run (Source Deploy)

1. Ensure the Google Cloud SDK is authenticated.
2. From the repository root, deploy directly to Cloud Run:

```bash
gcloud run deploy jules-mcp-server \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars JULES_API_BASE=https://jules.googleapis.com/v1alpha
```

**Google Cloud Console Settings**:
- **Build type**: Google Cloud buildpacks / native runtime
- **Build context directory**: `/`
- **Entrypoint**: Can be left empty because `Procfile` is present. Otherwise: `uvicorn jules_mcp_server.main:app --host 0.0.0.0 --port $PORT`

### Docker Build (Optional)

Alternatively, you can build and run using Docker:

```bash
docker build -t jules-mcp-server .
docker run --rm -p 8080:8080 jules-mcp-server
```

## Verification & ChatGPT Setup

You can manually verify that your server is running by pinging the health endpoint:
```bash
curl https://SERVICE_URL/health
```

To configure this as a custom MCP server in ChatGPT:

1. **Name**: `Jules MCP`
2. **Server URL**: `https://SERVICE_URL/mcp` (If SSE endpoints are needed, the base application exports standard paths natively at `/sse` and `/messages`)
3. **Authentication**:
   - **Type**: API key / access token
   - **Header schema**: custom header
   - **Header name**: `X-Goog-Api-Key`
   - **Header value**: (Your Jules API key from Jules settings)
