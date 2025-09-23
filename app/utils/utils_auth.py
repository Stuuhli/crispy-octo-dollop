from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Union

from app.config import (
    USER_DB_PATH,
    BACKEND_FASTAPI_LOG,
    JWT_SECRET_KEY,
    JWT_ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from pydantic import BaseModel
import json
import os
import jwt
from app.utils.utils_logging import initialize_logging, logger
initialize_logging(BACKEND_FASTAPI_LOG)


class AuthenticatedUser(BaseModel):
    username: str
    admin: bool
    collections: List[str]

class user_auth_format(BaseModel):
    """ Request template for sending data for creation of new user account """
    username: str
    fullname: str
    password: str
    disabled: bool = False
    admin: bool = False

class user_auth_validate(BaseModel):
    """ Request template for sending data for validation of user account """
    username: str
    password: str
    USER_DB_PATH: str = USER_DB_PATH

def write_json(username, new_data, filename=USER_DB_PATH):
    """ Write user data into existing db for the new user name 
    """
    empty_dict= {}
    # If the json database does not exist
    if not os.path.exists(filename):
        with open(filename, 'w') as file:
            file.write(str(empty_dict))
    # Open the file 
    with open(filename,'r+') as file:
        try:
            file_data = json.load(file)
        except Exception as e: 
            logger.error("Error occured: %s", str(e))
            with open(filename, 'w') as file:
                file.write(str(empty_dict))
            file_data = json.load(file)
        file_data[username]= new_data
        file.seek(0)
        json.dump(file_data, file, indent = 4)


def load_json(filename=USER_DB_PATH):
    """ Load the user db for authentication 
    """
    empty_dict= {}
    # If the json database does not exist
    if not os.path.exists(filename):
        with open(filename, 'w') as file:
            file.write(str(empty_dict))
    # Open the file 
    with open(filename,'r+') as file:
        try:
            file_data = json.load(file)
        except Exception as e: 
            logger.error("Error occured: %s", str(e))
            with open(filename, 'w') as file:
                file.write(str(empty_dict))
            file_data = json.load(file)
    return file_data


def _collections_claim(collections: Iterable[str]) -> List[str]:
    """Normalize collections into a list claim."""

    if isinstance(collections, str):
        return [collections]
    return list(collections)


def create_jwt_token(name: str, admin: bool, collections: Union[Iterable[str], str]) -> str:
    """Create a signed JWT with default expiration."""

    if not JWT_SECRET_KEY or not JWT_ALGORITHM:
        raise ValueError("JWT configuration missing: secret key or algorithm not set")

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": name,
        "admin": admin,
        "collections": _collections_claim(collections),
        "exp": int(expires_at.timestamp()),
    }

    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_jwt_token(token: str) -> AuthenticatedUser:
    """Decode JWT and return authenticated user model."""

    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        logger.warning("JWT decode failed: %s", str(exc))
        raise

    username = payload.get("sub")
    if not username:
        raise jwt.InvalidTokenError("Token missing subject")

    collections = payload.get("collections", [])
    if isinstance(collections, str):
        collections = [collections]

    return AuthenticatedUser(
        username=username,
        admin=payload.get("admin", False),
        collections=collections,
    )
