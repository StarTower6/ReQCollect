"""Authentication API endpoints.

Routes:
  POST   /api/auth/login       — username/password login → JWT
  POST   /api/auth/refresh     — refresh access token
  GET    /api/auth/me          — current user info
  POST   /api/auth/register    — register new user
  GET    /api/auth/users       — list all users (admin)
  PATCH  /api/auth/users/{user_id}/status  — enable/disable user (admin)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from app.core.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)


def _svc():
    from app.main import get_pm_agent_service
    s = get_pm_agent_service()
    if s is None:
        raise RuntimeError("Service not initialized")
    return s


def _ds():
    from app.main import get_datastore
    d = get_datastore()
    if d is None:
        raise RuntimeError("DataStore not initialized")
    return d


router = APIRouter()


# ── Request / Response models ──


from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    display_name: str = ""
    email: str = ""
    department: str = ""
    role: str = "business"


class UserStatusUpdate(BaseModel):
    is_active: bool


# ── Routes ──


@router.post("/auth/login")
async def auth_login(body: LoginRequest):
    """Username/password login. Returns JWT access token."""
    ds = _ds()
    user = await ds.get_user_by_username(body.username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    stored_hash = user.get("password_hash", "")
    if not stored_hash or not verify_password(body.password, stored_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is disabled",
        )

    token = create_access_token(data={"sub": user["id"]})
    logger.info(f"User '{body.username}' logged in")
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {k: v for k, v in user.items() if k != "password_hash"},
    }


@router.post("/auth/refresh")
async def auth_refresh(current_user: dict = Depends(get_current_user)):
    """Refresh the current user's access token."""
    token = create_access_token(data={"sub": current_user["id"]})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/auth/me")
async def auth_me(current_user: dict = Depends(get_current_user)):
    """Return the currently authenticated user's info."""
    return {
        "success": True,
        "user": {k: v for k, v in current_user.items() if k != "password_hash"},
    }


@router.post("/auth/register")
async def auth_register(body: RegisterRequest):
    """Register a new user."""
    ds = _ds()
    hashed = hash_password(body.password)
    try:
        user = await ds.create_user(
            username=body.username,
            password_hash=hashed,
            display_name=body.display_name,
            email=body.email,
            department=body.department,
            role=body.role,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    logger.info(f"New user registered: '{body.username}'")
    return {"success": True, "user": user}


@router.get("/auth/users")
async def auth_list_users(current_user: dict = Depends(get_current_user)):
    """List all users. Admin only."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    ds = _ds()
    users = await ds.list_users()
    return {"success": True, "users": users}


@router.patch("/auth/users/{user_id}/status")
async def auth_update_user_status(
    user_id: str,
    body: UserStatusUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Enable or disable a user. Admin only."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    ds = _ds()
    updated = await ds.update_user(user_id, is_active=body.is_active)
    if updated is None:
        raise HTTPException(status_code=404, detail="User not found")
    logger.info(f"User '{user_id}' active status set to {body.is_active}")
    return {"success": True, "user": updated}
