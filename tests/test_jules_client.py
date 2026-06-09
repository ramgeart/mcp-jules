import pytest
from src.jules_mcp_server.jules_client import validate_resource_name, validate_source_name, validate_session_name, validate_activity_name

def test_validate_resource_name():
    assert validate_resource_name("sources/test") == "sources/test"
    assert validate_resource_name("/sources/test") == "sources/test"

    with pytest.raises(ValueError):
        validate_resource_name("http://example.com")
    with pytest.raises(ValueError):
        validate_resource_name("../sources")
    with pytest.raises(ValueError):
        validate_resource_name("")
    with pytest.raises(ValueError):
        validate_resource_name("   ")
    with pytest.raises(ValueError):
        validate_resource_name("a?b")

def test_validate_source_name():
    assert validate_source_name("sources/test") == "sources/test"
    with pytest.raises(ValueError):
        validate_source_name("sessions/test")

def test_validate_session_name():
    assert validate_session_name("sessions/123") == "sessions/123"
    with pytest.raises(ValueError):
        validate_session_name("sources/test")

def test_validate_activity_name():
    assert validate_activity_name("sessions/123/activities/456") == "sessions/123/activities/456"
    with pytest.raises(ValueError):
        validate_activity_name("sessions/123")
