"""
Enterprise JWT Authentication & RBAC Module
============================================
Database-backed user authentication, bcrypt password hashing, and GxP role enforcement.
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr
import psycopg2.extras

from common.db_pool import get_db_conn, get_db_cursor
from common.audit_logger import log_audit_event

logger = logging.getLogger("auth")

JWT_SECRET = os.environ.get("JWT_SECRET", "zydus_secret_key_change_in_production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = int(os.environ.get("JWT_EXPIRY_HOURS", "24"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Fallback in-memory users if database is temporarily connecting during bootstrap
BOOTSTRAP_USERS = {
    "admin": {
        "username": "admin",
        "hashed_password": "",
        "role": "admin",
        "full_name": "System Administrator",
    },
    "engineer1": {
        "username": "engineer1",
        "hashed_password": ".4tMz4pjulhnE1HC.gmemq0wNK1Xpvta",
        "role": "engineer",
        "full_name": "Lead Reliability Engineer",
    },
    "viewer1": {
        "username": "viewer1",
        "hashed_password": ".S68WaxziQ9GN0/.2DHQohesN5Dw0QHbSOl9R3HuGEhVR1G",
        "role": "viewer",
        "full_name": "Operations Viewer",
    },
    "auditor1": {
        "username": "auditor1",
        "hashed_password": "/wPvUGMlkW",
        "role": "auditor",
        "full_name": "GxP Quality Auditor",
    },
}


# -- Pydantic Models -----------------------------------------
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str


class UserResponse(BaseModel):
    username: str
    role: str
    full_name: Optional[str] = None
    email: Optional[str] = None


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None


# -- Password & Token Helpers --------------------------------
def hash_password(plain_password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception as exc:
        logger.error("Password verification error: %s", exc)
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=JWT_EXPIRY_HOURS))
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def fetch_user_by_username(username: str) -> Optional[dict]:
    """Fetch user record from PostgreSQL users table, with fallback to bootstrap credentials."""
    try:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT id, username, hashed_password, role, full_name, email, is_active
                FROM users
                WHERE username = %s
                """,
                (username,),
            )
            row = cur.fetchone()
            if row:
                return dict(row)
    except Exception as exc:
        logger.debug("Database user lookup failed (%s); using bootstrap store", exc)

    return BOOTSTRAP_USERS.get(username)


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Dependency that validates JWT and returns the authenticated user dictionary."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"error": True, "message": "Invalid or expired token", "code": 401},
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = fetch_user_by_username(username)
    if user is None or not user.get("is_active", True):
        raise credentials_exception
    return user


def require_role(*roles: str | list[str] | tuple[str, ...]):
    """Dependency factory enforcing Role-Based Access Control."""
    allowed_set = set()
    for r in roles:
        if isinstance(r, (list, tuple, set)):
            allowed_set.update(r)
        else:
            allowed_set.add(r)

    def checker(user: dict = Depends(get_current_user)):
        user_role = user.get("role", "")
        if user_role not in allowed_set:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": True,
                    "message": "Insufficient permissions",
                    "required_roles": sorted(list(allowed_set)),
                    "user_role": user_role,
                    "code": 401,
                },
            )
        return user
    return checker


# -- Router --------------------------------------------------
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    user = fetch_user_by_username(form_data.username)
    client_ip = request.client.host if request.client else "unknown"

    if not user or not verify_password(form_data.password, user["hashed_password"]):
        log_audit_event(
            user_id=form_data.username,
            user_role="unknown",
            action="LOGIN_FAILED",
            entity_type="AUTH",
            entity_id=form_data.username,
            reason_for_change="Invalid username or password",
            ip_address=client_ip,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": True, "message": "Invalid username or password", "code": 401},
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update last login timestamp
    try:
        with get_db_cursor() as cur:
            cur.execute("UPDATE users SET last_login_at = NOW() WHERE username = %s", (user["username"],))
    except Exception:
        pass

    token = create_access_token(data={"sub": user["username"], "role": user["role"]})

    log_audit_event(
        user_id=user["username"],
        user_role=user["role"],
        action="LOGIN_SUCCESS",
        entity_type="AUTH",
        entity_id=user["username"],
        ip_address=client_ip,
    )

    return TokenResponse(
        access_token=token,
        role=user["role"],
        username=user["username"],
    )


@router.get("/me", response_model=UserResponse)
async def get_me(user: dict = Depends(get_current_user)):
    return UserResponse(
        username=user["username"],
        role=user["role"],
        full_name=user.get("full_name"),
        email=user.get("email"),
    )


@router.post("/users", response_model=UserResponse)
async def create_user(
    new_user: CreateUserRequest,
    current_user: dict = Depends(require_role("admin")),
):
    """Admin-only endpoint to register a new user in PostgreSQL."""
    if new_user.role not in {"admin", "engineer", "viewer", "auditor"}:
        raise HTTPException(
            status_code=400,
            detail={"error": True, "message": f"Invalid role: {new_user.role}"},
        )

    hashed = hash_password(new_user.password)
    try:
        with get_db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (username, hashed_password, role, full_name, email)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING username, role, full_name, email
                """,
                (new_user.username, hashed, new_user.role, new_user.full_name, new_user.email),
            )
            created = cur.fetchone()

        log_audit_event(
            user_id=current_user["username"],
            user_role=current_user["role"],
            action="CREATE_USER",
            entity_type="USER",
            entity_id=new_user.username,
            after_state={"username": new_user.username, "role": new_user.role},
            reason_for_change=f"Created new user with role {new_user.role}",
        )
        return UserResponse(**dict(created))
    except psycopg2.IntegrityError:
        raise HTTPException(
            status_code=400,
            detail={"error": True, "message": f"Username '{new_user.username}' already exists"},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"error": True, "message": str(exc)})

