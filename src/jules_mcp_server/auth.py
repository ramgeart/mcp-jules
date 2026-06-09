import contextvars
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Scope, Receive, Send

# Context variable to hold the X-Goog-Api-Key
# Default to None, so we know if it was not provided
jules_api_key_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("jules_api_key", default=None)

def get_api_key() -> str | None:
    """Retrieve the current Jules API key from the context."""
    return jules_api_key_var.get()

class APIKeyMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "lifespan":
            await self.app(scope, receive, send)
            return

        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Allow /health endpoint to pass without auth
        if scope.get("path") == "/health":
            await self.app(scope, receive, send)
            return

        # Extract the key from headers
        api_key = None
        headers = scope.get("headers", [])
        for key, value in headers:
            if key.lower() == b"x-goog-api-key":
                api_key = value.decode("utf-8", errors="ignore")
                break

        if not api_key:
            response = JSONResponse(
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
            await response(scope, receive, send)
            return

        # Set context variable for this request
        token = jules_api_key_var.set(api_key)
        try:
            await self.app(scope, receive, send)
        finally:
            jules_api_key_var.reset(token)
