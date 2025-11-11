"""
FastAPI Dependencies for API Routes

This module contains reusable dependency functions for FastAPI endpoints.
Separated from unified_server.py to avoid circular imports.
"""

import time
from typing import Optional
from fastapi import Request, HTTPException, status


async def verify_csrf_token(request: Request) -> str:
    """
    FastAPI dependency to verify CSRF token for state-changing requests.

    This dependency validates the X-CSRF-Token header against tokens stored in
    app.state._csrf_tokens. Raises HTTPException (which properly passes through
    CORSMiddleware) instead of returning JSONResponse directly.

    Returns:
        str: Valid CSRF token

    Raises:
        HTTPException: 403 if token missing, invalid, or expired
    """
    token = request.headers.get("X-CSRF-Token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token required",
        )

    current_time = time.time()

    # Check if token exists in valid token set
    if token not in request.app.state._csrf_tokens:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid CSRF token",
        )

    # Check if token is expired
    if request.app.state._csrf_token_expiry.get(token, 0) < current_time:
        # Clean up expired token
        request.app.state._csrf_tokens.discard(token)
        request.app.state._csrf_token_expiry.pop(token, None)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token expired",
        )

    return token
