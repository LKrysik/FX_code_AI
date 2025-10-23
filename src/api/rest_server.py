
"""Legacy REST server adapter built on top of the unified API."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, UTC
from typing import Iterable, Optional, Sequence, Set

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.api.auth_handler import UserSession
from .unified_server import create_unified_app


def _apply_external_container(app: FastAPI, container) -> None:
    rest_service = getattr(app.state, "rest_service", None)
    if rest_service is None:
        return

    rest_service.container = container
    if hasattr(rest_service, "_controller"):
        rest_service._controller = None
    if hasattr(rest_service, "_strategy_manager"):
        rest_service._strategy_manager = None


def _build_legacy_user() -> UserSession:
    now = datetime.now(UTC)
    return UserSession(
        last_activity=now,
        user_id="legacy_user",
        username="legacy",
        permissions=["admin_system"],
        authenticated_at=now,
        expires_at=now + timedelta(hours=8),
        client_ip="127.0.0.1",
        user_agent="legacy_rest",
        session_token="legacy-session-token",
        refresh_token="legacy-refresh-token",
    )


def _install_legacy_envelope(app: FastAPI) -> None:
    @app.middleware("http")
    async def legacy_envelope(request: Request, call_next):
        response = await call_next(request)

        if not isinstance(response, JSONResponse):
            return response

        try:
            payload = json.loads(response.body)
        except Exception:  # pragma: no cover - non-JSON payloads
            return response

        if payload.get("type") == "response":
            data_section = payload.get("data") or {}
            status_value = data_section.get("status")
            if request.url.path == "/health":
                payload["status"] = "ok"
            elif status_value and "status" not in payload:
                payload["status"] = status_value

            for key in ("error_code", "error_message"):
                if key in data_section and key not in payload:
                    payload[key] = data_section[key]

            response = JSONResponse(payload, status_code=response.status_code)
        elif payload.get("type") == "error":
            data_section = payload.get("data") or {}
            if "error_code" in data_section and "error_code" not in payload:
                payload["error_code"] = data_section["error_code"]
                response = JSONResponse(payload, status_code=response.status_code)

        return response


def _install_legacy_auth_bypass(app: FastAPI) -> None:
    dependency = getattr(app.state, "get_current_user_dependency", None)
    if dependency is None:
        return

    async def _legacy_user_dependency():
        return _build_legacy_user()

    app.dependency_overrides[dependency] = _legacy_user_dependency


def _replace_route(app: FastAPI, path: str, methods: Sequence[str], handler) -> None:
    target_methods: Set[str] = {m.upper() for m in methods}
    for route in list(app.router.routes):
        route_methods: Iterable[str] = getattr(route, "methods", set()) or set()
        if getattr(route, "path", None) == path and set(route_methods) & target_methods:
            app.router.routes.remove(route)
    app.add_api_route(path, handler, methods=list(target_methods), include_in_schema=False)


def _install_legacy_routes(app: FastAPI) -> None:
    async def legacy_health():
        body = {
            "type": "response",
            "status": "ok",
            "timestamp": datetime.now(UTC).isoformat(),
            "data": {
                "status": "healthy",
                "version": "1.0",
            },
        }
        return JSONResponse(body)

    _replace_route(app, "/health", ["GET"], legacy_health)


def create_rest_app(container: Optional[object] = None) -> FastAPI:
    app = create_unified_app()

    if container is not None:
        _apply_external_container(app, container)

    _install_legacy_auth_bypass(app)
    _install_legacy_envelope(app)
    _install_legacy_routes(app)

    return app
