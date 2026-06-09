import pytest
from src.jules_mcp_server.auth import APIKeyMiddleware, jules_api_key_var
from fastapi import FastAPI
from fastapi.testclient import TestClient

app = FastAPI()
app.add_middleware(APIKeyMiddleware)

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/api/test")
def protected_route():
    key = jules_api_key_var.get()
    return {"key": key}

client = TestClient(app)

def test_health_no_auth():
    response = client.get("/health")
    assert response.status_code == 200

def test_missing_auth():
    response = client.get("/api/test")
    assert response.status_code == 401
    assert response.json()["error"] == "Unauthorized"
    assert response.json()["ok"] is False

def test_valid_auth():
    response = client.get("/api/test", headers={"X-Goog-Api-Key": "secret123"})
    assert response.status_code == 200
    assert response.json()["key"] == "secret123"
