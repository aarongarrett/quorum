"""Authentication endpoints."""
from fastapi import APIRouter, HTTPException, Response

from app.schemas import AdminLoginRequest, AdminLoginResponse
from app.core.security import verify_admin_password, create_access_token
from app.core import config

router = APIRouter()


@router.post("/admin/login")
async def admin_login(request: AdminLoginRequest, response: Response):
    """Admin login endpoint - sets JWT token in httpOnly cookie."""
    if not verify_admin_password(request.password):
        raise HTTPException(status_code=401, detail="Invalid password")

    access_token = create_access_token(data={"is_admin": True})

    # Set token in httpOnly cookie for security and SSE compatibility
    # secure flag is automatically set based on environment
    response.set_cookie(
        key="admin_token",
        value=access_token,
        httponly=True,  # Prevents JavaScript access (XSS protection)
        secure=config.settings.ENVIRONMENT == "production",  # Requires HTTPS in production
        samesite="lax", # CSRF protection
        max_age=config.settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert minutes to seconds
    )

    return {"success": True, "message": "Logged in successfully"}


@router.post("/admin/logout")
async def admin_logout(response: Response):
    """Admin logout endpoint - clears JWT cookie."""
    response.delete_cookie(key="admin_token")
    return {"success": True, "message": "Logged out successfully"}
