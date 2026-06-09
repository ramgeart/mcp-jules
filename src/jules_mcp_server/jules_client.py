import os
import httpx
import json
import asyncio
from typing import Any, Dict, Optional
from .auth import get_api_key

import time

# Default API base for Jules
JULES_API_BASE = os.environ.get("JULES_API_BASE", "https://jules.googleapis.com/v1alpha")

# Shared client to reuse connections and avoid socket exhaustion
_client = httpx.AsyncClient(timeout=60.0)

def validate_resource_name(name: str) -> str:
    """Validate and clean up resource names before making a request."""
    if not isinstance(name, str):
        raise ValueError("Resource name must be a string")

    name = name.strip()
    if not name:
        raise ValueError("Resource name cannot be empty")

    # Strip leading slash
    if name.startswith("/"):
        name = name[1:]

    if ".." in name:
        raise ValueError("Invalid resource name: contains '..'")

    if "?" in name or "#" in name or "\\" in name or "//" in name:
        raise ValueError("Invalid resource name: contains illegal characters")

    if name.startswith("http://") or name.startswith("https://"):
        raise ValueError("Invalid resource name: looks like a full URL")

    return name

def validate_source_name(name: str) -> str:
    name = validate_resource_name(name)
    if not name.startswith("sources/"):
        raise ValueError("Source name must start with 'sources/'")
    return name

def validate_session_name(name: str) -> str:
    name = validate_resource_name(name)
    if not name.startswith("sessions/"):
        raise ValueError("Session name must start with 'sessions/'")
    return name

def validate_activity_name(name: str) -> str:
    name = validate_resource_name(name)
    if not name.startswith("sessions/") or "/activities/" not in name:
        raise ValueError("Activity name must match 'sessions/.../activities/...'")
    return name

def build_url(resource_name: str) -> str:
    """Construct full Jules URL from a resource name."""
    clean_name = validate_resource_name(resource_name)
    base = JULES_API_BASE.rstrip("/")
    return f"{base}/{clean_name}"

def redact_secrets(data: Any) -> Any:
    """Recursively search for and redact sensitive information from dicts and lists."""
    if isinstance(data, dict):
        redacted_dict = {}
        for k, v in data.items():
            key_lower = k.lower()
            if any(secret_term in key_lower for secret_term in ['token', 'secret', 'auth', 'key', 'cookie']):
                redacted_dict[k] = "***REDACTED***"
            elif k == "X-Goog-Api-Key" or k == "Authorization":
                redacted_dict[k] = "***REDACTED***"
            else:
                redacted_dict[k] = redact_secrets(v)
        return redacted_dict
    elif isinstance(data, list):
        return [redact_secrets(item) for item in data]
    elif isinstance(data, str):
        # A simple check for strings that might accidentally contain key names followed by secrets
        if "X-Goog-Api-Key" in data or "Authorization" in data:
            return "***REDACTED_STRING***"
        return data
    else:
        return data

def format_error(status_code: int, error_message: str, details: Any = None) -> Dict[str, Any]:
    """Format structured errors according to specification."""
    # Redact secrets from error details before returning
    safe_details = redact_secrets(details or {})
    return {
        "ok": False,
        "status": status_code,
        "error": error_message,
        "details": safe_details
    }

async def make_jules_request(
    method: str,
    resource_name: str,
    params: Optional[Dict[str, Any]] = None,
    json_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Make an HTTP request to the Jules API."""
    api_key = get_api_key()
    if not api_key:
        return format_error(401, "Unauthorized", {"message": "Missing API key in context"})

    try:
        url = build_url(resource_name)
    except ValueError as e:
        return format_error(400, "Bad Request", {"message": str(e)})

    headers = {
        "X-Goog-Api-Key": api_key,
        "Content-Type": "application/json"
    }

    try:
        response = await _client.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json=json_data
        )

        if response.status_code >= 400:
            try:
                error_data = response.json()
            except ValueError:
                error_data = {"raw_text": response.text}

            return format_error(
                response.status_code,
                "Jules API Error",
                error_data
            )

        try:
            data = response.json()
        except ValueError:
            data = {}

        # We also redact successful tool responses just in case
        return {
            "ok": True,
            "data": redact_secrets(data)
        }

    except httpx.RequestError as e:
        return format_error(500, "Internal Server Error", {"message": f"HTTP request failed: {type(e).__name__}"})
    except Exception as e:
        return format_error(500, "Internal Server Error", {"message": f"Unexpected error: {type(e).__name__}"})

# ---------------------------------------------------------
# Tool Helpers
# ---------------------------------------------------------

async def list_sources() -> Dict[str, Any]:
    return await make_jules_request("GET", "sources")

async def get_source(name: str) -> Dict[str, Any]:
    try:
        return await make_jules_request("GET", validate_source_name(name))
    except ValueError as e:
        return format_error(400, "Bad Request", {"message": str(e)})

async def create_session(
    source: str,
    starting_branch: str,
    prompt: str,
    title: str = "",
    require_plan_approval: bool = True,
    automation_mode: Optional[str] = None
) -> Dict[str, Any]:

    try:
        clean_source = validate_source_name(source)
    except ValueError as e:
        return format_error(400, "Bad Request", {"message": str(e)})

    payload = {
        "sourceContext": {
            "source": clean_source,
            "githubRepoContext": {
                "startingBranch": starting_branch
            }
        },
        "prompt": prompt,
        "requirePlanApproval": require_plan_approval
    }

    if title:
        payload["title"] = title

    if automation_mode:
        payload["automationMode"] = automation_mode

    return await make_jules_request("POST", "sessions", json_data=payload)

async def list_sessions(page_size: int = 50, page_token: str = "") -> Dict[str, Any]:
    params = {"pageSize": page_size}
    if page_token:
        params["pageToken"] = page_token
    return await make_jules_request("GET", "sessions", params=params)

async def get_session(session: str) -> Dict[str, Any]:
    try:
        return await make_jules_request("GET", validate_session_name(session))
    except ValueError as e:
        return format_error(400, "Bad Request", {"message": str(e)})

async def send_message(session: str, prompt: str) -> Dict[str, Any]:
    try:
        return await make_jules_request("POST", f"{validate_session_name(session)}:sendMessage", json_data={"prompt": prompt})
    except ValueError as e:
        return format_error(400, "Bad Request", {"message": str(e)})

async def approve_plan(session: str) -> Dict[str, Any]:
    try:
        return await make_jules_request("POST", f"{validate_session_name(session)}:approvePlan")
    except ValueError as e:
        return format_error(400, "Bad Request", {"message": str(e)})

async def list_activities(session: str, page_size: int = 50, page_token: str = "") -> Dict[str, Any]:
    try:
        clean_session = validate_session_name(session)
    except ValueError as e:
        return format_error(400, "Bad Request", {"message": str(e)})

    page_size = max(1, min(page_size, 100))
    params = {"pageSize": page_size}
    if page_token:
        params["pageToken"] = page_token
    return await make_jules_request("GET", f"{clean_session}/activities", params=params)

async def get_activity(activity: str) -> Dict[str, Any]:
    try:
        return await make_jules_request("GET", validate_activity_name(activity))
    except ValueError as e:
        return format_error(400, "Bad Request", {"message": str(e)})

async def wait_for_activity(
    session: str,
    match_text: str = "",
    timeout_seconds: int = 600,
    poll_interval_seconds: int = 10,
    page_size: int = 50
) -> Dict[str, Any]:
    """
    Polls the session and activities until a terminal state is reached,
    a timeout occurs, or match_text is found in a new activity.
    """
    # Cap timeout and enforce minimum poll interval
    timeout_seconds = max(1, min(timeout_seconds, 1800))
    poll_interval_seconds = max(1, min(poll_interval_seconds, 300))
    page_size = max(1, min(page_size, 100))

    start_time = time.monotonic()

    while True:
        current_time = time.monotonic()
        if (current_time - start_time) >= timeout_seconds:
            # Fetch latest to return something useful
            sess_res = await get_session(session)
            act_res = await list_activities(session, page_size=page_size)
            return {
                "ok": True,
                "data": {
                    "status": "timeout",
                    "sessionState": sess_res.get("data", {}).get("state", "UNKNOWN") if sess_res.get("ok") else "UNKNOWN",
                    "matchedActivity": None,
                    "latestActivities": act_res.get("data", {}).get("activities", []) if act_res.get("ok") else [],
                    "timedOut": True
                }
            }

        # 1. Fetch Session
        session_resp = await get_session(session)
        if not session_resp.get("ok"):
            return session_resp # Propagate error

        session_data = session_resp.get("data", {})
        session_state = session_data.get("state", "")

        # 2. Fetch Activities
        activities_resp = await list_activities(session, page_size=page_size)
        if not activities_resp.get("ok"):
            return activities_resp

        activities_data = activities_resp.get("data", {})
        activities = activities_data.get("activities", [])

        # 3. Check for match_text
        if match_text:
            for act in activities:
                # Basic string match against JSON representation of activity
                if match_text in json.dumps(act):
                    return {
                        "ok": True,
                        "data": {
                            "status": "matched",
                            "sessionState": session_state,
                            "matchedActivity": act,
                            "latestActivities": activities,
                            "timedOut": False
                        }
                    }

        # 4. Check for terminal / awaiting states
        terminal_states = {"COMPLETED", "FAILED"}
        awaiting_states = {"AWAITING_PLAN_APPROVAL", "AWAITING_USER_FEEDBACK"}

        inferred_status = None
        # Also check for union fields
        for act in activities:
            if "sessionCompleted" in act:
                inferred_status = "completed"
            elif "sessionFailed" in act:
                inferred_status = "failed"

        if session_state in terminal_states or inferred_status:
            if not inferred_status:
                inferred_status = "completed" if session_state == "COMPLETED" else "failed"
            return {
                "ok": True,
                "data": {
                    "status": inferred_status,
                    "sessionState": session_state,
                    "matchedActivity": None,
                    "latestActivities": activities,
                    "timedOut": False
                }
            }

        if session_state in awaiting_states:
            status = "awaiting_plan_approval" if session_state == "AWAITING_PLAN_APPROVAL" else "awaiting_user_feedback"
            return {
                "ok": True,
                "data": {
                    "status": status,
                    "sessionState": session_state,
                    "matchedActivity": None,
                    "latestActivities": activities,
                    "timedOut": False
                }
            }

        # Sleep before next poll
        await asyncio.sleep(poll_interval_seconds)
