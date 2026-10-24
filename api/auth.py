"""Authentication routes backed by Supabase Auth."""

from fastapi import APIRouter, HTTPException, status
from supabase_auth.errors import AuthApiError

from database.connection import supabase_auth
from schemas.auth import AuthUser, LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Sign in with email and password",
)
def login(credentials: LoginRequest) -> LoginResponse:
    """Validate credentials with Supabase and return the resulting session."""

    try:
        response = supabase_auth.auth.sign_in_with_password(
            {"email": str(credentials.email), "password": credentials.password}
        )
    except AuthApiError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    session = response.session
    user = response.user
    if session is None or user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to create an authenticated session.",
        )

    return LoginResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        expires_in=session.expires_in,
        expires_at=session.expires_at,
        user=AuthUser(id=user.id, email=user.email),
    )
