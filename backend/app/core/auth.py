import hmac

from fastapi import Header, HTTPException, status

from app.core.config import settings


def require_internal_api_token(
    x_internal_api_token: str | None = Header(default=None),
) -> None:
    if not settings.internal_api_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="internal_api_token_not_configured",
        )

    if not x_internal_api_token or not hmac.compare_digest(
        x_internal_api_token,
        settings.internal_api_token,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_internal_api_token",
        )
