import contextvars
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Context variable to hold the X-Goog-Api-Key
# Default to None, so we know if it was not provided
jules_api_key_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("jules_api_key", default=None)

def get_api_key() -> str | None:
    """Retrieve the current Jules API key from the context."""
    return jules_api_key_var.get()

class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Allow /health endpoint to pass without auth
        if request.url.path == "/health":
            return await call_next(request)

        # Extract the key from headers
        # ChatGPT sends X-Goog-Api-Key
        api_key = request.headers.get("X-Goog-Api-Key")

        if not api_key:
            # We return a structured JSON response to conform with tool expectations
            # if they directly hit MCP endpoints and need auth checking at HTTP level.
            # However, for MCP endpoints, missing auth should fail before reaching tools.
            # We fail with structured auth error as requested.
            return JSONResponse(
                status_code=401,
                content={
                    "ok": False,
                    "status": 401,
                    "error": "Unauthorized",
                    "details": {
                        "message": "Missing X-Goog-Api-Key header"
                    }
                }
            )

        # Set context variable for this request
        token = jules_api_key_var.set(api_key)
        try:
            response = await call_next(request)
            return response
        finally:
            jules_api_key_var.reset(token)
