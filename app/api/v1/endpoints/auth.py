"""Authentication endpoints."""
from fastapi import APIRouter, HTTPException, Response

from app.schemas import AdminLoginRequest, SuccessResponse
from app.core.security import verify_admin_password, create_access_token
from app.core import config

router = APIRouter()


@router.post("/admin/login", response_model=SuccessResponse)
async def admin_login(request: AdminLoginRequest, response: Response) -> SuccessResponse:
    """
    Authenticate admin user and set JWT token in secure httpOnly cookie.

    This endpoint validates the admin password and returns a JWT token stored
    in an httpOnly cookie for secure authentication. The token is automatically
    included in subsequent requests by the browser.

    Args:
        request: AdminLoginRequest containing the password field
        response: FastAPI Response object for setting cookies

    Returns:
        AdminLoginResponse with success status and message

    Raises:
        HTTPException: 401 Unauthorized if password is invalid

    Example:
        Request:
            POST /api/v1/auth/admin/login
            {
                "password": "your-secure-password"
            }

        Response (200):
            {
                "success": true,
                "message": "Logged in successfully"
            }
            Set-Cookie: admin_token=eyJhbGc...; HttpOnly; SameSite=Lax

        Response (401):
            {
                "detail": "Invalid password"
            }

    Security:
        - Token stored in httpOnly cookie (XSS protection)
        - SameSite=Lax (CSRF protection)
        - Secure flag enabled in production (HTTPS only)
        - Token expires based on ACCESS_TOKEN_EXPIRE_MINUTES setting
    """
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

    return SuccessResponse(success=True, message="Logged in successfully")


@router.post("/admin/logout", response_model=SuccessResponse)
async def admin_logout(response: Response) -> SuccessResponse:
    """
    Log out admin user by clearing the authentication cookie.

    This endpoint removes the admin_token cookie, effectively logging out
    the admin user. No authentication is required to call this endpoint.

    Args:
        response: FastAPI Response object for clearing cookies

    Returns:
        dict: Success message

    Example:
        Request:
            POST /api/v1/auth/admin/logout

        Response (200):
            {
                "success": true,
                "message": "Logged out successfully"
            }

    Note:
        This endpoint can be called even if the user is not logged in.
        It will simply ensure the cookie is cleared.
    """
    response.delete_cookie(key="admin_token")
    return SuccessResponse(success=True, message="Logged out successfully")
