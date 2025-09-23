from app.auth import password_create
from app.utils.utils_auth import write_json, load_json, create_jwt_token
from app.config import JWT_SECRET_KEY, JWT_ALGORITHM
from app.main import get_current_user
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
import jwt
import pytest
from unit_tests.non_LLM_tests.conftest import TEST_DB_PATH
from pathlib import Path

def test_health(test_client):
    """ Test if the connection is stable
    """
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"health": "ok"}

def test_validate_returns_jwt(test_client, make_db):
    """Valid credentials should return a JWT payload."""
    username = list(make_db.keys())[0]
    payload = {
        "username": make_db[username]["username"],
        "password": "test",
        "USER_DB_PATH": TEST_DB_PATH,
    }

    response = test_client.post(f"/validate_user/{username}", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == {"access_token", "token_type"}
    assert data["token_type"].lower() == "bearer"

    decoded = jwt.decode(
        data["access_token"],
        JWT_SECRET_KEY,
        algorithms=[JWT_ALGORITHM],
    )
    assert decoded["sub"] == username
    assert decoded["admin"] is False
    assert decoded["collections"] == []

def test_validate_wrong_password(test_client, make_db):
    """Invalid credentials should return 401."""
    username = list(make_db.keys())[0]
    payload = {
        "username": make_db[username]["username"],
        "password": "test_wrong",
        "USER_DB_PATH": TEST_DB_PATH,
    }

    response = test_client.post(f"/validate_user/{username}", json=payload)

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password"

def test_create_new_user(test_client):
    """ send payload and check userdb for the exact payload with password match
    """
    payload_create= {
        "username": "new_user",
        "full_name": "new user",
        "hashed_password": password_create("new_test").decode("utf-8"),
        "disabled": False,
        "admin": False
    }
    write_json(username=payload_create["username"], new_data=payload_create, filename=TEST_DB_PATH)
    payload_valid = {
        "username": payload_create["username"],
        "password": "new_test",
        "USER_DB_PATH": TEST_DB_PATH,
    }
    response = test_client.post(
        f"/validate_user/{payload_create['username']}",
        json=payload_valid,
    )
    Path(TEST_DB_PATH).unlink()
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_get_current_user_requires_token():
    """Missing or malformed credentials should raise HTTP 401."""
    with pytest.raises(HTTPException) as excinfo:
        get_current_user(None)
    assert excinfo.value.status_code == 401

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid")
    with pytest.raises(HTTPException) as excinfo:
        get_current_user(credentials)
    assert excinfo.value.status_code == 401


def test_get_current_user_valid_claims():
    """A valid token should produce an AuthenticatedUser model."""
    token = create_jwt_token(name="alice", admin=True, collections=["sales"])
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    user = get_current_user(credentials)

    assert user.username == "alice"
    assert user.admin is True
    assert user.collections == ["sales"]
