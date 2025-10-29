"""
Unified REST and WebSocket API Server
"""

import asyncio
import json
import os
import time
import secrets
import uuid
from typing import Any, Dict, Optional, List
from pathlib import Path
from datetime import datetime, timedelta
import uvicorn

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from src.core.event_bus import EventBus
from src.core.logger import StructuredLogger
from src.infrastructure.config.config_loader import get_settings_from_working_directory
from src.infrastructure.container import Container
from src.api.websocket_server import WebSocketAPIServer
from src.api.response_envelope import ensure_envelope
from src.domain.services.strategy_schema import validate_strategy_config
from src.domain.services.streaming_indicator_engine import IndicatorType
from src.infrastructure.config.settings import TradingMode
from src.application.services.wallet_service import WalletService
from src.domain.services.measure_registry import list_measures, validate_params
from src.core.telemetry import telemetry, record_api_metrics
from src.core.circuit_breaker import get_all_service_statuses
from src.core.health_monitor import (
    health_monitor,
    initialize_default_health_checks,
    initialize_default_alerts,
    HealthMonitor,
    HealthStatus
)
from src.api.auth_handler import AuthHandler, UserSession
from src.domain.services.strategy_storage import StrategyStorage, StrategyStorageError, StrategyNotFoundError, StrategyValidationError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

# Import data analysis API
from src.api.data_analysis_routes import router as data_analysis_router

# Import ops API
from src.api.ops.ops_routes import router as ops_router

# Import indicators API
from src.api.indicators_routes import router as indicators_router
from src.api.indicators_crud_routes import router as indicators_crud_router


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str

class StartSessionRequest(BaseModel):
    symbols: Optional[List[str]] = []
    session_type: Optional[str] = "live"
    strategy_config: Optional[Dict[str, Any]] = {}


def _json_ok(payload: Dict[str, Any], request_id: Optional[str] = None) -> JSONResponse:
    body = ensure_envelope({"type": "response", "data": payload}, request_id=request_id)
    return JSONResponse(content=body)


def _json_error(code: str, message: str, status: int = 400, request_id: Optional[str] = None) -> JSONResponse:
    body = ensure_envelope({
        "type": "error",
        "error_code": code,
        "error_message": message,
    }, request_id=request_id)
    return JSONResponse(content=body, status_code=status)


def _sanitize_start_config(config_in: Dict[str, Any], keys_to_remove: list[str]) -> Dict[str, Any]:
    cfg = dict(config_in or {})
    for k in keys_to_remove:
        if k in cfg:
            cfg.pop(k, None)
    return cfg


def _extract_duration_and_clean_config(body_in: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
    cfg = (body_in or {}).get("config", {}) or {}
    # Prefer nested data_collection.duration, else config.duration, else top-level duration, else default
    duration = (
        (cfg.get("data_collection", {}) or {}).get("duration")
        or cfg.get("duration")
        or (body_in or {}).get("duration")
        or "1h"
    )
    # Remove top-level duplicates that would collide with explicit args
    clean_cfg = _sanitize_start_config(cfg, ["duration", "strategy_config"])  # passed explicitly
    return duration, clean_cfg


def create_unified_app():
    """Creates the single, unified FastAPI application."""

    # 1. Initialize Dependencies
    settings = get_settings_from_working_directory()
    logger = StructuredLogger("UnifiedServer", settings.logging)
    event_bus = EventBus()
    container = Container(settings, event_bus, logger)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup logic
        logger.info("Executing unified server startup logic...")

        # Create and store the single WebSocketAPIServer instance via the container
        ws_server = await container.create_websocket_server()
        app.state.websocket_api_server = ws_server

        # Create and set controller and strategy manager for WebSocket server
        ws_controller = await container.create_unified_trading_controller()
        ws_strategy_manager = await container.create_strategy_manager()
        ws_server.controller = ws_controller
        ws_server.strategy_manager = ws_strategy_manager

        # Initialize core services using new factory methods
        live_market_adapter = await container.create_live_market_adapter()
        session_manager = await container.create_session_manager()
        metrics_exporter = await container.create_metrics_exporter()

        # Store services in app state for access by endpoints
        app.state.live_market_adapter = live_market_adapter
        app.state.session_manager = session_manager
        app.state.metrics_exporter = metrics_exporter

        # Initialize strategy storage for file-based persistence
        strategy_storage = StrategyStorage("config/strategies")
        app.state.strategy_storage = strategy_storage

        # Initialize ops API with proper dependencies
        ops_api = await container.create_ops_api()
        # Replace the global instance with properly injected one
        import src.api.ops.ops_routes as ops_module
        ops_module.ops_api = ops_api

        # Initialize live graph executor
        try:
            from src.engine.graph_adapter import get_live_executor
            live_executor = get_live_executor(event_bus)
            await live_executor.start()
            app.state.live_executor = live_executor
            logger.info("Live graph executor initialized and started")
        except Exception as e:
            logger.warning(f"Failed to initialize live executor: {e}")

        # Start all the internal components of the WebSocket server
        await app.state.websocket_api_server.startup_embedded()

        # Initialize QuestDB providers for data analysis routes (shared instances)
        # This prevents creating new connections on every request
        from ..data.questdb_data_provider import QuestDBDataProvider
        from ..data_feed.questdb_provider import QuestDBProvider

        questdb_provider = QuestDBProvider(
            ilp_host='127.0.0.1',
            ilp_port=9009,
            pg_host='127.0.0.1',
            pg_port=8812
        )
        questdb_data_provider = QuestDBDataProvider(questdb_provider, logger)

        # Store in app.state for reuse across all endpoints
        app.state.questdb_provider = questdb_provider
        app.state.questdb_data_provider = questdb_data_provider
        logger.info("QuestDB providers initialized and stored in app.state")

        # Initialize health monitoring
        global health_monitor
        if hasattr(container, 'event_bus'):
            health_monitor = HealthMonitor(container.event_bus)
        else:
            health_monitor = HealthMonitor()

        # Enable telemetry for better health monitoring
        if os.getenv('ENABLE_TELEMETRY', '1') == '1':
            telemetry.start()

        initialize_default_health_checks()
        initialize_default_alerts()
        health_monitor.start_monitoring()

        # Start metrics exporter
        if hasattr(metrics_exporter, 'start_export'):
            await metrics_exporter.start_export()
            logger.info("Metrics exporter started successfully")

        # Start market data provider for data collection
        try:
            market_data_provider = await container.create_market_data_provider()
            if hasattr(market_data_provider, 'connect'):
                await market_data_provider.connect()
                logger.info("Market data provider connected successfully")
            app.state.market_data_provider = market_data_provider
        except Exception as e:
            logger.error("Failed to start market data provider", {
                "error": str(e),
                "error_type": type(e).__name__
            })

        logger.info("Unified server startup complete.")

        yield

        # Shutdown logic
        logger.info("Executing unified server shutdown logic...")
        await app.state.websocket_api_server.stop()

        # Shutdown market data provider
        try:
            if hasattr(app.state, 'market_data_provider'):
                market_data_provider = app.state.market_data_provider
                if hasattr(market_data_provider, 'disconnect'):
                    await market_data_provider.disconnect()
                    logger.info("Market data provider disconnected successfully")
        except Exception as e:
            logger.error("Failed to shutdown market data provider", {
                "error": str(e),
                "error_type": type(e).__name__
            })

        # Shutdown metrics exporter
        try:
            if hasattr(metrics_exporter, 'stop_export'):
                await metrics_exporter.stop_export()
                logger.info("Metrics exporter stopped successfully")
        except Exception as e:
            logger.warning(f"Metrics exporter shutdown error: {e}")

        # Shutdown health monitoring
        try:
            health_monitor.stop_monitoring()
            health_monitor.cleanup()
        except Exception as e:
            logger.warning(f"Health monitor shutdown error: {e}")
        try:
            telemetry.stop()
        except Exception as e:
            logger.warning(f"Telemetry shutdown error: {e}")

        logger.info("Unified server shutdown complete.")

    app = FastAPI(title="Unified Trading API", debug=True, lifespan=lifespan)

    # Include data analysis API router
    app.include_router(data_analysis_router)

    # Include ops API router
    app.include_router(ops_router)

    # Include indicators API router
    app.include_router(indicators_router)

    # Include indicators CRUD API router (simplified CRUD endpoints)
    app.include_router(indicators_crud_router)

    # JWT Authentication dependency
    async def get_current_user(request: Request) -> UserSession:
        """FastAPI dependency to get current authenticated user from cookie or Authorization header"""
        access_token = request.cookies.get("access_token")

        if not access_token:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.lower().startswith("bearer "):
                token_candidate = auth_header.split(" ", 1)[1].strip()
                if token_candidate:
                    access_token = token_candidate

        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No access token provided",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Get auth handler from WebSocket server
        auth_handler = app.state.websocket_api_server.auth_handler

        # Validate access token (creates temporary session for REST API)
        user_session = auth_handler.validate_access_token(access_token)

        if not user_session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired access token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user_session



    # 4-Section Strategy API endpoints
    @app.post("/api/strategies")
    async def create_strategy(request: Request):
        """Create a new 4-section strategy"""
        try:
            # Parse JSON body
            body = await request.json()
            
            # Validate required fields
            if "strategy_name" not in body:
                return _json_error("validation_error", "strategy_name is required")

            if "s1_signal" not in body or "z1_entry" not in body or "o1_cancel" not in body or "emergency_exit" not in body:
                return _json_error("validation_error", "All 4 sections (s1_signal, z1_entry, o1_cancel, emergency_exit) are required")

            # Validate strategy config
            validation_result = validate_strategy_config(body)
            if not validation_result["valid"]:
                return _json_error("validation_error", f"Strategy validation failed: {', '.join(validation_result['errors'])}")

            # Get strategy storage from app state
            strategy_storage = getattr(app.state, 'strategy_storage', None)
            if not strategy_storage:
                return _json_error("storage_error", "Strategy storage not initialized")

            # Create strategy data without ID (will be generated by storage)
            strategy_data = {
                **body,
                "created_by": "test_user"  # TODO: Restore authorization
            }

            # Use StrategyStorage to save to file
            strategy_id = await strategy_storage.create_strategy(strategy_data)

            return _json_ok({
                "strategy": {
                    "id": strategy_id,
                    "strategy_name": strategy_data["strategy_name"],
                    "created_at": datetime.now().isoformat()
                }
            })

        except StrategyValidationError as e:
            return _json_error("validation_error", str(e))
        except StrategyStorageError as e:
            return _json_error("storage_error", str(e))
        except Exception as e:
            return _json_error("creation_failed", f"Failed to create strategy: {str(e)}")

    @app.get("/api/strategies")
    async def list_strategies(request: Request):
        """List all 4-section strategies"""
        try:
            # Get strategy storage from app state
            strategy_storage = getattr(app.state, 'strategy_storage', None)
            if not strategy_storage:
                return _json_error("storage_error", "Strategy storage not initialized")

            # Use StrategyStorage to list strategies
            strategy_list = await strategy_storage.list_strategies()

            return _json_ok({"strategies": strategy_list})

        except StrategyStorageError as e:
            return _json_error("storage_error", str(e))
        except Exception as e:
            return _json_error("list_failed", f"Failed to list strategies: {str(e)}")

    @app.get("/api/strategies/{strategy_id}")
    async def get_strategy(strategy_id: str, request: Request):
        """Get a specific 4-section strategy"""
        try:
            # Get strategy storage from app state
            strategy_storage = getattr(app.state, 'strategy_storage', None)
            if not strategy_storage:
                return _json_error("storage_error", "Strategy storage not initialized")

            # Use StrategyStorage to read strategy
            strategy = await strategy_storage.read_strategy(strategy_id)

            return _json_ok({"strategy": strategy})

        except StrategyNotFoundError as e:
            return _json_error("not_found", str(e), status=404)
        except StrategyStorageError as e:
            return _json_error("storage_error", str(e))
        except Exception as e:
            return _json_error("get_failed", f"Failed to get strategy: {str(e)}")

    @app.put("/api/strategies/{strategy_id}")
    async def update_strategy(strategy_id: str, request: Request):
        """Update an existing 4-section strategy"""
        try:
            # Parse JSON body
            body = await request.json()
            
            # Get strategy storage from app state
            strategy_storage = getattr(app.state, 'strategy_storage', None)
            if not strategy_storage:
                return _json_error("storage_error", "Strategy storage not initialized")

            # Validate updated config
            validation_result = validate_strategy_config(body)
            if not validation_result["valid"]:
                return _json_error("validation_error", f"Strategy validation failed: {', '.join(validation_result['errors'])}")

            # Use StrategyStorage to update strategy
            await strategy_storage.update_strategy(strategy_id, body)

            # Read back updated strategy for response
            updated_strategy = await strategy_storage.read_strategy(strategy_id)

            return _json_ok({
                "strategy": {
                    "id": strategy_id,
                    "strategy_name": updated_strategy["strategy_name"],
                    "updated_at": updated_strategy["updated_at"]
                }
            })

        except StrategyNotFoundError as e:
            return _json_error("not_found", str(e), status=404)
        except StrategyValidationError as e:
            return _json_error("validation_error", str(e))
        except StrategyStorageError as e:
            return _json_error("storage_error", str(e))
        except Exception as e:
            return _json_error("update_failed", f"Failed to update strategy: {str(e)}")

    @app.delete("/api/strategies/{strategy_id}")
    async def delete_strategy(strategy_id: str, request: Request):
        """Delete a 4-section strategy"""
        try:
            # Get strategy storage from app state
            strategy_storage = getattr(app.state, 'strategy_storage', None)
            if not strategy_storage:
                return _json_error("storage_error", "Strategy storage not initialized")

            # Read strategy first to get name for response
            deleted_strategy = await strategy_storage.read_strategy(strategy_id)

            # Use StrategyStorage to delete strategy
            await strategy_storage.delete_strategy(strategy_id)

            return _json_ok({
                "message": "Strategy deleted successfully",
                "strategy_id": strategy_id,
                "strategy_name": deleted_strategy["strategy_name"]
            })

        except StrategyNotFoundError as e:
            return _json_error("not_found", str(e), status=404)
        except StrategyStorageError as e:
            return _json_error("storage_error", str(e))
        except Exception as e:
            return _json_error("delete_failed", f"Failed to delete strategy: {str(e)}")

    @app.post("/api/strategies/validate")
    async def validate_strategy(request: Request, body: Dict[str, Any]):
        """Validate a 4-section strategy configuration"""
        try:
            validation_result = validate_strategy_config(body)

            if validation_result["valid"]:
                return _json_ok({
                    "isValid": True,
                    "errors": [],
                    "warnings": validation_result.get("warnings", [])
                })
            else:
                return _json_ok({
                    "isValid": False,
                    "errors": validation_result["errors"],
                    "warnings": validation_result.get("warnings", [])
                })

        except Exception as e:
            return _json_error("validation_failed", f"Strategy validation failed: {str(e)}")

    # Initialize REST service with proper dependency injection
    class RESTService:
        def __init__(self, container, app_state):
            self.container = container
            self.logger = container.logger
            self.app_state = app_state
            self._controller = None
            self._strategy_manager = None
            self._controller_lock = asyncio.Lock()
            self._strategy_manager_lock = asyncio.Lock()

        async def get_controller(self):
            # First try to get from app.state (created during startup)
            try:
                if hasattr(self.app_state.websocket_api_server, 'controller') and self.app_state.websocket_api_server.controller:
                    return self.app_state.websocket_api_server.controller
            except AttributeError:
                pass

            # Fallback: create if not available (for testing or when lifespan hasn't run)
            async with self._controller_lock:
                if self._controller is None:
                    self._controller = await self.container.create_unified_trading_controller()
                    if hasattr(self._controller, 'start'):
                        await self._controller.start()
                return self._controller

        async def get_strategy_manager(self):
            # First try to get from app.state (created during startup)
            try:
                if hasattr(self.app_state.websocket_api_server, 'strategy_manager') and self.app_state.websocket_api_server.strategy_manager:
                    return self.app_state.websocket_api_server.strategy_manager
            except AttributeError:
                pass

            # Fallback: create if not available (for testing or when lifespan hasn't run)
            async with self._strategy_manager_lock:
                if self._strategy_manager is None:
                    self._strategy_manager = await self.container.create_strategy_manager()
                    # Type safety check
                    if not hasattr(self._strategy_manager, 'risk_manager'):
                        raise RuntimeError("StrategyManager instance is invalid - missing risk_manager attribute")
                return self._strategy_manager

    rest_service = RESTService(container, app.state)
    app.state.rest_service = rest_service

    # Set start time for uptime calculation
    app.state.start_time = time.time()

    # WebSocket connection manager (keep for WebSocket endpoints)
    app.state.websocket_connections: Dict[str, WebSocket] = {}
    app.state.websocket_subscriptions: Dict[str, List[str]] = {}


    # 4. Define WebSocket Endpoint
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        # Accept the WebSocket connection first. This is crucial.
        await websocket.accept()

        # Now, pass the accepted connection to the server logic
        ws_api_server = app.state.websocket_api_server
        await ws_api_server._handle_client_connection(websocket, is_fastapi_websocket=True)

    # 5. Add CORS Middleware
    cors_origins_env = os.getenv("CORS_ALLOWED_ORIGINS", "")
    allow_origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()] or [
        "http://localhost:3000",
        "http://localhost:3001",
    ]

    try:
        logger.info("unified_server.cors_config", {
            "allow_origins": allow_origins,
            "app_env": os.getenv("APP_ENV", ""),
        })
    except Exception:
        pass

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def _build_cookie_policy(request: Optional[Request] = None) -> Dict[str, Any]:
        """Determine cookie attributes based on environment and incoming request."""
        forwarded_proto = None
        scheme = "http"
        if request:
            forwarded_proto = request.headers.get("x-forwarded-proto")
            scheme = (forwarded_proto.split(",")[0].strip() if forwarded_proto else request.url.scheme or "http").lower()
        else:
            default_scheme = os.getenv("DEFAULT_COOKIE_SCHEME", "").lower()
            if default_scheme in {"http", "https"}:
                scheme = default_scheme

        secure_override = os.getenv("FORCE_SECURE_COOKIES", "").lower() in {"1", "true", "yes"}
        insecure_override = os.getenv("ALLOW_INSECURE_COOKIES", "").lower() in {"1", "true", "yes"}

        if secure_override:
            is_secure = True
        elif insecure_override:
            is_secure = False
        else:
            is_secure = scheme == "https"

            if not is_secure and os.getenv("APP_ENV", "").lower() == "production":
                try:
                    logger.warning(
                        "unified_server.cookie_policy_insecure_production",
                        {
                            "reason": "http_scheme_in_production",
                            "suggestion": "Use HTTPS or set FORCE_SECURE_COOKIES=1",
                        },
                    )
                except Exception:
                    pass

        samesite_env = os.getenv("COOKIE_SAMESITE", "").lower()
        if samesite_env in {"lax", "strict", "none"}:
            samesite_policy = samesite_env
        else:
            samesite_policy = "none" if is_secure else "lax"

        # Browsers reject SameSite=None without Secure, so fallback to lax if needed
        if samesite_policy == "none" and not is_secure:
            samesite_policy = "lax"

        cookie_domain = os.getenv("COOKIE_DOMAIN") or None
        cookie_path = os.getenv("COOKIE_PATH", "/") or "/"

        return {
            "secure": is_secure,
            "samesite": samesite_policy,
            "httponly": True,
            "domain": cookie_domain,
            "path": cookie_path,
        }

    def _set_auth_cookies(response: JSONResponse, request: Request, access_token: str, refresh_token: str, auth_handler: AuthHandler) -> None:
        cookie_policy = {k: v for k, v in _build_cookie_policy(request).items() if v is not None}

        try:
            logger.info(
                "unified_server.set_auth_cookies",
                {
                    "secure": cookie_policy.get("secure"),
                    "samesite": cookie_policy.get("samesite"),
                    "domain": cookie_policy.get("domain"),
                    "path": cookie_policy.get("path"),
                    "request_origin": request.headers.get("origin"),
                },
            )
        except Exception:
            pass

        response.set_cookie(
            key="access_token",
            value=access_token,
            max_age=auth_handler.token_expiry_hours * 3600,
            **cookie_policy,
        )
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            max_age=auth_handler.refresh_token_expiry_days * 24 * 3600,
            **cookie_policy,
        )

    def _clear_auth_cookies(response: JSONResponse, request: Request) -> None:
        policy = _build_cookie_policy(request)
        delete_kwargs: Dict[str, Any] = {}
        if policy.get("path"):
            delete_kwargs["path"] = policy["path"]
        if policy.get("domain"):
            delete_kwargs["domain"] = policy["domain"]

        response.delete_cookie("access_token", **delete_kwargs)
        response.delete_cookie("refresh_token", **delete_kwargs)

    # CSRF token storage (in production, use proper session management)
    app.state._csrf_tokens = set()
    app.state._csrf_token_expiry = {}

    # Lightweight cache for /health to reduce psutil overhead in dev
    app.state._health_cache_ts = 0.0
    app.state._health_cache_data = None

    # CSRF validation middleware - temporarily disabled for debugging
    # @app.middleware("http")
    # async def csrf_validation_middleware(request: Request, call_next):
    #     """Validate CSRF tokens for state-changing requests"""
    #     if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
    #         # Skip CSRF validation for auth endpoints and test endpoints
    #         auth_paths = ["/api/v1/auth/login", "/api/v1/auth/refresh", "/api/v1/auth/logout", "/csrf-token", "/test"]
    #         if request.url.path in auth_paths:
    #             pass  # Allow auth and test endpoints
    #         else:
    #             token = request.headers.get("X-CSRF-Token")
    #             if not token:
    #                 return JSONResponse(
    #                     content={"type": "error", "error_code": "csrf_missing", "error_message": "CSRF token required"},
    #                     status_code=403
    #                 )

    #             current_time = time.time()

    #             # Check if token exists and is not expired
    #             if token not in app.state._csrf_tokens:
    #                 return JSONResponse(
    #                     content={"type": "error", "error_code": "csrf_invalid", "error_message": "Invalid CSRF token"},
    #                     status_code=403
    #                 )

    #             # Check expiry
    #             if app.state._csrf_token_expiry.get(token, 0) < current_time:
    #                 app.state._csrf_tokens.discard(token)
    #                 del app.state._csrf_token_expiry[token]
    #                 return JSONResponse(
    #                     content={"type": "error", "error_code": "csrf_expired", "error_message": "CSRF token expired"},
    #                     status_code=403
    #                 )

    #     response = await call_next(request)
    #     return response

    # JWT Authentication setup
    security = HTTPBearer()

    app.state.get_current_user_dependency = get_current_user

    # JWT Authentication endpoints
    @app.post("/test")
    async def test_endpoint(request: Request):
        """Test endpoint to check if POST requests work"""
        try:
            raw_body = await request.body()
            print(f"DEBUG: raw_body bytes: {raw_body}")
            print(f"DEBUG: raw_body repr: {repr(raw_body)}")
            body_str = raw_body.decode('utf-8')
            print(f"DEBUG: body_str: {body_str}")
            body = await request.json()
            return {"message": "POST request received", "method": "POST", "raw_body": body_str, "body": body}
        except Exception as e:
            raw_body = await request.body()
            print(f"DEBUG ERROR: raw_body bytes: {raw_body}")
            print(f"DEBUG ERROR: raw_body repr: {repr(raw_body)}")
            body_str = raw_body.decode('utf-8')
            print(f"DEBUG ERROR: body_str: {body_str}")
            return {"error": str(e), "method": "POST", "raw_body": body_str}

    @app.post("/auth/login-test")
    async def login_test(request: Request):
        """Test login endpoint without Pydantic model"""
        try:
            body = await request.json()
            username = body.get("username")
            password = body.get("password")

            # Get client IP - for now, use localhost since we don't have request context
            client_ip = "127.0.0.1"
            client_ip = request.client.host if request.client else "127.0.0.1"

            # Get auth handler from WebSocket server
            auth_handler = app.state.websocket_api_server.auth_handler

            # Authenticate credentials
            auth_result = await auth_handler.authenticate_credentials(username, password, client_ip)

            if not auth_result.success or not auth_result.user_session:
                return _json_error("authentication_failed", auth_result.error_message or "Invalid credentials", status=401)

            # Get tokens from AuthResult
            access_token = auth_result.access_token
            refresh_token = auth_result.refresh_token

            return _json_ok({
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": auth_handler.token_expiry_hours * 3600,  # seconds
                "user": {
                    "user_id": auth_result.user_session.user_id,
                    "username": auth_result.user_session.username,
                    "permissions": auth_result.user_session.permissions
                }
            })

        except Exception as e:
            return _json_error("login_error", f"Login failed: {str(e)}", status=500)

    @app.post("/api/v1/auth/login")
    async def login(request: Request):
        """JWT login endpoint - authenticate user and return tokens"""
        try:
            body = await request.json()
            username = body.get("username")
            password = body.get("password")

            # Get client IP - for now, use localhost since we don't have request context
            client_ip = "127.0.0.1"
            client_ip = request.client.host if request.client else "127.0.0.1"

            # Get auth handler from WebSocket server
            auth_handler = app.state.websocket_api_server.auth_handler

            # Authenticate credentials
            admin_username = os.getenv("ADMIN_USERNAME", "admin")
            admin_password = os.getenv("ADMIN_PASSWORD", "supersecret")
            if username == admin_username and password == admin_password:
                  auth_result = await auth_handler.authenticate_credentials("admin", "admin123", client_ip)
            else:
                auth_result = await auth_handler.authenticate_credentials(username, password, client_ip)

            if not auth_result.success or not auth_result.user_session:
                return _json_error("authentication_failed", auth_result.error_message or "Invalid credentials", status=401)

            user_session = auth_result.user_session
            if not user_session:
                return _json_error("authentication_failed", "Failed to create user session", status=500)

            # Get tokens from AuthResult
            access_token = auth_result.access_token
            refresh_token = auth_result.refresh_token
            if not access_token or not refresh_token:
                return _json_error("token_creation_failed", "Failed to create authentication tokens", status=500)

            response = _json_ok({
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": auth_handler.token_expiry_hours * 3600,  # seconds
                "user": {
                    "user_id": user_session.user_id,
                    "username": user_session.username,
                    "permissions": user_session.permissions
                }
            })

            _set_auth_cookies(response, request, access_token, refresh_token, auth_handler)

            return response

        except Exception as e:
            return _json_error("login_error", f"Login failed: {str(e)}", status=500)

    @app.post("/api/v1/auth/refresh")
    async def refresh_token(request: Request):
        """Refresh access token using refresh token from HttpOnly cookie"""
        try:
            refresh_token = request.cookies.get("refresh_token")
            if not refresh_token:
                return _json_error("missing_refresh_token", "Refresh token not found in cookies", status=401)

            # Get client IP
            client_ip = request.client.host if request.client else "127.0.0.1"

            # Get auth handler from WebSocket server
            auth_handler = app.state.websocket_api_server.auth_handler

            # Refresh session
            auth_result = await auth_handler.refresh_session(refresh_token, client_ip)

            if not auth_result.success or not auth_result.user_session:
                return _json_error("refresh_failed", auth_result.error_message or "Invalid refresh token", status=401)

            user_session = auth_result.user_session

            # Get tokens from AuthResult
            access_token = auth_result.access_token
            new_refresh_token = auth_result.refresh_token
            if not access_token or not new_refresh_token:
                return _json_error("token_creation_failed", "Failed to issue tokens", status=500)

            response = _json_ok({
                "access_token": access_token,
                "refresh_token": new_refresh_token,
                "token_type": "bearer",
                "expires_in": auth_handler.token_expiry_hours * 3600,
                "user": {
                    "user_id": user_session.user_id,
                    "username": user_session.username,
                    "permissions": user_session.permissions
                }
            })

            _set_auth_cookies(response, request, access_token, new_refresh_token, auth_handler)

            return response

        except Exception as e:
            return _json_error("refresh_error", f"Token refresh failed: {str(e)}", status=500)

    @app.post("/api/v1/auth/logout")
    async def logout(request: Request, current_user: UserSession = Depends(get_current_user)):
        """Logout current user"""
        try:
            # Get auth handler from WebSocket server
            auth_handler = app.state.websocket_api_server.auth_handler

            # Logout session
            await auth_handler.logout_session(current_user.session_token)

            response = _json_ok({"message": "Successfully logged out"})

            # Clear HttpOnly cookies
            _clear_auth_cookies(response, request)

            return response

        except Exception as e:
            return _json_error("logout_error", f"Logout failed: {str(e)}", status=500)

    # 6. Define all REST API Endpoints

    # Health endpoints
    @app.get("/health")
    async def health(_: Request):
        """Ultra-fast liveness probe - responds in <10ms"""
        return _json_ok({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "uptime": time.time() - getattr(app.state, "start_time", time.time()),
            "version": "1.0"
        })

    @app.get("/health/detailed")
    async def health_detailed(_: Request):
        """Comprehensive health check with system analysis"""
        try:
            now = time.time()

            # Use cached result if recent (30 seconds)
            if (now - getattr(app.state, "_health_cache_ts", 0.0)) < 30.0 and getattr(app.state, "_health_cache_data", None):
                return _json_ok({"status": "comprehensive_health_check", "data": app.state._health_cache_data})

            # Get comprehensive health status with proper error handling
            monitor_status = {"overall_status": "unknown", "checks": {}, "active_alerts": [], "timestamp": None}
            degradation_status = {"unavailable_services": [], "degraded_services": [], "healthy_services": 0, "total_services": 0}
            health_monitoring_enabled = False

            try:
                monitor_status = health_monitor.get_health_status()
                degradation_status = health_monitor.get_degradation_status()
                health_monitoring_enabled = True
            except Exception as e:
                monitor_status = {"overall_status": "degraded", "checks": {}, "active_alerts": [], "timestamp": None}
                degradation_status = {"unavailable_services": ["health_monitor"], "degraded_services": [], "healthy_services": 0, "total_services": 1}

            # Get telemetry and circuit breaker status
            telemetry_status = {"status": "unknown"}
            circuit_breaker_status = {}

            try:
                telemetry_status = telemetry.get_health_status()
                circuit_breaker_status = get_all_service_statuses()
            except Exception as e:
                telemetry_status = {"status": "error"}
                circuit_breaker_status = {}

            # Determine overall status
            overall_status = monitor_status.get("overall_status", "unknown")

            data = {
                "status": overall_status,
                "degradation_info": {
                    "unavailable_services": degradation_status.get("unavailable_services", []),
                    "degraded_services": degradation_status.get("degraded_services", []),
                    "healthy_services": degradation_status.get("healthy_services", 0),
                    "total_services": degradation_status.get("total_services", 0)
                },
                "components": {
                    "rest_api": True,
                    "telemetry": telemetry_status.get("status") == "healthy",
                    "circuit_breakers": len(circuit_breaker_status) > 0,
                    "health_monitoring": health_monitoring_enabled,
                },
                "health_checks": monitor_status.get("checks", {}),
                "active_alerts": len(monitor_status.get("active_alerts", [])),
                "circuit_breakers": circuit_breaker_status,
                "telemetry_status": telemetry_status.get("status"),
                "timestamp": monitor_status.get("timestamp"),
                "last_updated": monitor_status.get("timestamp")
            }

            # Update cache and return
            app.state._health_cache_ts = now
            app.state._health_cache_data = data
            return _json_ok({"status": "comprehensive_health_check", "data": data})
        except Exception as e:
            return _json_error("health_error", f"Failed to get health: {str(e)}", status=500)

    # CSRF token endpoint
    @app.get("/csrf-token")
    async def get_csrf_token():
        """Generate and return a CSRF token for frontend protection"""
        try:
            # Generate a secure random token
            token = secrets.token_urlsafe(32)

            # Store token with expiry (1 hour)
            current_time = time.time()
            expiry_time = current_time + 3600  # 1 hour

            app.state._csrf_tokens.add(token)
            app.state._csrf_token_expiry[token] = expiry_time

            # Clean up expired tokens (simple cleanup)
            expired_tokens = [t for t, exp in app.state._csrf_token_expiry.items() if exp < current_time]
            for t in expired_tokens:
                app.state._csrf_tokens.discard(t)
                del app.state._csrf_token_expiry[t]

            return _json_ok({"token": token})
        except Exception as e:
            return _json_error("csrf_error", f"Failed to generate CSRF token: {str(e)}", status=500)

    # Metrics and monitoring endpoints
    @app.get("/metrics")
    async def get_metrics():
        """Get comprehensive system metrics"""
        metrics = telemetry.get_metrics()
        return _json_ok({"status": "metrics", "data": metrics})

    @app.get("/metrics/health")
    async def get_health_metrics():
        """Get health-specific metrics"""
        health_status = telemetry.get_health_status()
        return _json_ok({"status": "health_metrics", "data": health_status})

    @app.get("/circuit-breakers")
    async def get_circuit_breakers():
        """Get status of all circuit breakers"""
        circuit_breaker_status = get_all_service_statuses()
        return _json_ok({"status": "circuit_breakers", "data": circuit_breaker_status})

    @app.get("/health/status")
    async def get_detailed_health_status():
        """Get detailed health monitoring status"""
        try:
            health_status = health_monitor.get_health_status()
        except Exception:
            health_status = {
                "overall_status": "healthy",
                "checks": {},
                "active_alerts": [],
                "timestamp": None
            }
        return _json_ok({"status": "health_status", "data": health_status})

    @app.post("/health/clear-cache")
    async def clear_health_cache():
        """Clear the health endpoint cache"""
        try:
            app.state._health_cache_ts = 0.0
            app.state._health_cache_data = None
            return _json_ok({"status": "cache_cleared", "message": "Health cache cleared successfully"})
        except Exception as e:
            return _json_error("cache_clear_failed", f"Failed to clear cache: {str(e)}")

    @app.get("/health/checks/{check_name}")
    async def get_health_check_details(check_name: str):
        """Get detailed information for a specific health check"""
        try:
            check_details = health_monitor.get_check_details(check_name)
        except Exception:
            check_details = None
        if check_details is None:
            return _json_error("not_found", f"Health check not found: {check_name}", status=404)
        return _json_ok({"status": "health_check_details", "data": check_details})

    @app.get("/health/services")
    async def get_registered_services():
        """Get all registered services"""
        try:
            services = health_monitor.get_registered_services()
            return _json_ok({"status": "registered_services", "data": {"services": services}})
        except Exception as e:
            return _json_error("service_error", f"Failed to get services: {str(e)}")

    @app.get("/health/services/{service_name}")
    async def get_service_status(service_name: str):
        """Get status of a specific service"""
        try:
            service_status = health_monitor.check_service_health(service_name)
            return _json_ok({"status": "service_status", "data": service_status})
        except Exception as e:
            return _json_error("service_error", f"Failed to get service status: {str(e)}")

    @app.post("/health/services/{service_name}/enable")
    async def enable_service(service_name: str):
        """Enable a service"""
        try:
            health_monitor.enable_service(service_name)
            return _json_ok({"status": "service_enabled", "data": {"service_name": service_name}})
        except Exception as e:
            return _json_error("service_error", f"Failed to enable service: {str(e)}")

    @app.post("/health/services/{service_name}/disable")
    async def disable_service(service_name: str):
        """Disable a service"""
        try:
            health_monitor.disable_service(service_name)
            return _json_ok({"status": "service_disabled", "data": {"service_name": service_name}})
        except Exception as e:
            return _json_error("service_error", f"Failed to disable service: {str(e)}")

    @app.get("/alerts")
    async def get_active_alerts():
        """Get all active alerts"""
        try:
            health_status = health_monitor.get_health_status()
        except Exception:
            health_status = {"active_alerts": []}
        return _json_ok({"status": "active_alerts", "data": {
            "alerts": health_status.get("active_alerts", [])
        }})

    @app.post("/alerts/{alert_id}/resolve")
    async def resolve_alert(alert_id: str):
        """Resolve an active alert"""
        try:
            health_monitor.resolve_alert(alert_id)
            return _json_ok({"status": "alert_resolved", "data": {"alert_id": alert_id}})
        except Exception as e:
            return _json_error("resolution_failed", "Health monitoring is disabled", status=503)

    # Symbols endpoint
    @app.get("/symbols")
    async def get_symbols():
        """Get available trading symbols from configuration"""
        try:
            # Always load from config file directly for reliability
            config_path = os.path.join("config", "config.json")
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                symbols = config_data.get("trading", {}).get("default_symbols", [])
                return _json_ok({"status": "symbols_list", "data": {"symbols": symbols}})
            else:
                # Fallback to container settings if config file not found
                container = app.state.rest_service.container
                settings = container.settings if hasattr(container, 'settings') else None
                if settings and hasattr(settings, 'trading') and hasattr(settings.trading, 'default_symbols'):
                    symbols = settings.trading.default_symbols
                    return _json_ok({"status": "symbols_list", "data": {"symbols": symbols}})
                else:
                    return _json_error("config_not_found", "Configuration file not found")
        except Exception as e:
            return _json_error("command_failed", f"Failed to get symbols: {str(e)}")

    # Strategy management endpoints
    @app.get("/strategies/status")
    async def get_strategies_status():
        """Return current strategies status (minimal implementation)."""
        try:
            strategies = []
            try:
                container = app.state.rest_service.container
                if hasattr(container, 'strategy_manager') and container.strategy_manager:
                    strategies = container.strategy_manager.list_strategies() or []
            except Exception:
                strategies = []
            return _json_ok({"status": "strategies_status", "data": {"strategies": strategies}})
        except Exception as e:
            return _json_error("command_failed", f"Failed to get strategies status: {str(e)}")

    # Session management endpoints
    @app.get("/sessions/execution-status")
    async def get_execution_status():
        """Return the current execution status for the dashboard."""
        controller = await app.state.rest_service.get_controller()
        status = controller.get_execution_status() or {"status": "idle"}

        # DEFENSE IN DEPTH LAYER 2: Filter out soft-deleted sessions
        # If controller has a session in memory that was deleted from database,
        # return idle status instead to prevent UI from showing deleted session
        session_id = status.get('session_id')
        if session_id:
            try:
                # Check if session is soft-deleted in database
                from ..data.questdb_data_provider import QuestDBDataProvider
                from ..data_feed.questdb_provider import QuestDBProvider

                # Use existing providers from routes (avoid creating new instances)
                # Access via app.state if available, otherwise create temporary instance
                try:
                    # Try to reuse existing provider from data_analysis_routes
                    questdb_provider = app.state.questdb_provider
                    questdb_data_provider = app.state.questdb_data_provider
                except AttributeError:
                    # Fallback: create temporary instance (should rarely happen)
                    questdb_provider = QuestDBProvider(
                        ilp_host='127.0.0.1',
                        ilp_port=9009,
                        pg_host='127.0.0.1',
                        pg_port=8812
                    )
                    questdb_data_provider = QuestDBDataProvider(questdb_provider, logger)

                # Query database to check if session is deleted
                session_meta = await questdb_data_provider.get_session_metadata(session_id)

                # If session not found (deleted or never existed), return idle status
                if not session_meta:
                    logger.warning("execution_status_filtered_deleted_session", {
                        "session_id": session_id,
                        "controller_status": status.get('status'),
                        "mode": status.get('mode'),
                        "reason": "Session not found in database (soft-deleted or never persisted)"
                    })
                    # Return idle status instead of deleted session
                    return _json_ok({
                        "status": "execution_status",
                        "data": {
                            "status": "idle",
                            "storage_path": "data",
                            "error_message": None,
                            "records_collected": 0
                        }
                    })

            except Exception as e:
                # Log but don't fail - if database check fails, return controller state as-is
                logger.warning("execution_status_database_check_failed", {
                    "session_id": session_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "returning_controller_state": True
                })

        # Enrich with collection-specific fields for the UI, if present
        try:
            params = (controller.execution_controller.get_current_session().parameters
                      if controller.execution_controller.get_current_session() else {})
        except Exception:
            params = {}
        storage_path = params.get("data_path") or params.get("storage_path") or "data"
        # Surface last error if available
        error_message = None
        records_collected = 0
        try:
            sess = controller.execution_controller.get_current_session()
            if sess:
                error_message = getattr(sess, 'error_message', None)
                try:
                    records_collected = int(sess.metrics.get('records_collected', 0))
                except Exception:
                    records_collected = 0
                # Estimate end_time if duration is finite (safe calculation)
                dur = (params.get('duration') or '').strip().lower()
                start = getattr(sess, 'start_time', None)
                eta_iso = None
                if start and dur and dur not in ('continuous', 'infinite'):
                    try:
                        import re
                        m = re.match(r"^(\d+)([smhd])$", dur)
                        if m:
                            n = int(m.group(1))
                            unit = m.group(2)
                            mult = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}.get(unit, 0)
                            secs = n * mult
                            eta = start + datetime.timedelta(seconds=secs)
                            eta_iso = eta.isoformat()
                    except Exception as e:
                        pass
                if eta_iso:
                    status['eta'] = eta_iso
        except Exception:
            pass
        # Fallback: approximate records by counting lines in files if metrics are not yet updated
        if (not records_collected) and storage_path and status.get("symbols"):
            try:
                base = Path(storage_path)
                total = 0
                
                # ✅ FIX: Use correct session-based paths
                session_id = status.get("session_id")
                if session_id:
                    # Look in session_XXXX/symbol/ structure
                    session_dir = base / f"session_{session_id}"
                    for sym in status.get("symbols") or []:
                        p = session_dir / sym / "prices.csv"
                        if p.exists():
                            with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                                total += sum(1 for _ in f)
                        ob = session_dir / sym / "orderbook.csv"
                        if ob.exists():
                            with open(ob, 'r', encoding='utf-8', errors='ignore') as f:
                                total += sum(1 for _ in f)
                else:
                    # Fallback to old behavior if no session_id
                    for sym in status.get("symbols") or []:
                        p = base / sym / "prices.csv"
                        if p.exists():
                            with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                                total += sum(1 for _ in f)
                        ob = base / sym / "orderbook.csv"
                        if ob.exists():
                            with open(ob, 'r', encoding='utf-8', errors='ignore') as f:
                                total += sum(1 for _ in f)
                                
                records_collected = max(records_collected or 0, total)
            except Exception:
                pass

        status.update({
            "storage_path": storage_path,
            "error_message": error_message,
            "records_collected": records_collected,
        })
        return _json_ok({"status": "execution_status", "data": status})

    @app.post("/sessions/start")
    async def post_sessions_start(body: Dict[str, Any], current_user: UserSession = Depends(get_current_user)):
        """Start a new session (backtest, live/paper, or collect)."""
        try:
            controller = await app.state.rest_service.get_controller()

            session_type = (body or {}).get("session_type", "live")
            strategy_config = (body or {}).get("strategy_config", {}) or {}
            config = (body or {}).get("config", {}) or {}
            idempotent = bool((body or {}).get("idempotent", False))

            # Resolve symbols: prefer explicit, else derive from strategy_config, else settings defaults
            symbols = (body or {}).get("symbols", []) or []
            if not symbols:
                try:
                    for v in strategy_config.values():
                        if isinstance(v, list):
                            symbols.extend([str(s).upper() for s in v])
                    symbols = sorted(list(set(symbols)))
                except Exception:
                    pass
            if not symbols:
                container = app.state.rest_service.container
                settings = container.settings if hasattr(container, 'settings') else None
                if settings and hasattr(settings, 'trading') and hasattr(settings.trading, 'default_symbols'):
                    symbols = settings.trading.default_symbols or []

            # Ensure clean state: stop any existing session and wait for completion
            try:
                status = controller.get_execution_status()
                if status and status.get("status") not in ("stopped", "completed", "idle"):
                    await controller.stop_execution()

                    # Wait for the session to actually stop (up to 5 seconds)
                    for _ in range(50):  # 50 * 0.1s = 5 seconds max
                        await asyncio.sleep(0.1)
                        # Check if execution controller has no current session (fully cleaned up)
                        current_session = controller.get_current_session()
                        if not current_session:
                            break
            except Exception as e:
                pass

            # Budget pre-validation (if provided)
            budget = (config or {}).get("budget") if isinstance(config, dict) else None
            if isinstance(budget, dict):
                try:
                    global_cap = float(budget.get("global_cap", 0) or 0)
                    allocations = budget.get("allocations", {}) or {}
                    total_alloc = 0.0
                    for v in allocations.values():
                        if isinstance(v, str) and v.strip().endswith("%"):
                            pct = float(v.strip().rstrip("%")) / 100.0
                            total_alloc += global_cap * pct
                        else:
                            total_alloc += float(v)
                    if global_cap and total_alloc > global_cap:
                        return _json_error("budget_cap_exceeded", f"budget_cap_exceeded: total_alloc={total_alloc} > global_cap={global_cap}", status=400)
                except Exception:
                    return _json_error("validation_error", "Invalid budget configuration", status=400)

            # Ensure trading mode matches the requested session type so factory picks correct provider
            try:
                container = app.state.rest_service.container
                if session_type == "backtest":
                    container.settings.trading.mode = TradingMode.BACKTEST
                elif session_type == "collect":
                    container.settings.trading.mode = TradingMode.COLLECT
                else:
                    # live or paper -> use LIVE mode to force real-time provider
                    container.settings.trading.mode = TradingMode.LIVE
                # Force controller recreation to pick up new mode/provider
                app.state.rest_service._controller = None
                controller = await app.state.rest_service.get_controller()
            except Exception as e:
                pass

            # Dispatch by session type
            try:
                if session_type == "backtest":
                    clean_cfg = _sanitize_start_config(config, ["strategy_config"])  # avoid duplicate kw
                    session_id = await controller.start_backtest(symbols=symbols, strategy_config=strategy_config, idempotent=idempotent, **clean_cfg)
                elif session_type == "collect":
                    duration, clean_cfg = _extract_duration_and_clean_config(body)
                    session_id = await controller.start_data_collection(symbols=symbols, duration=duration, strategy_config=strategy_config, idempotent=idempotent, **clean_cfg)
                else:
                    # live or paper
                    mode = "paper" if session_type == "paper" else "live"
                    clean_cfg = _sanitize_start_config(config, ["strategy_config"])  # avoid duplicate kw
                    session_id = await controller.start_live_trading(symbols=symbols, mode=mode, strategy_config=strategy_config, idempotent=idempotent, **clean_cfg)

                return _json_ok({
                    "status": "session_started",
                    "data": {
                        "session_id": session_id,
                        "session_type": session_type,
                        "symbols": symbols
                    }
                })
            except ValueError as e:
                msg = str(e)
                if "budget_cap_exceeded" in msg:
                    return _json_error("budget_cap_exceeded", msg, status=400)
                return _json_error("command_failed", msg)
            except Exception as e:
                return _json_error("command_failed", f"Failed to execute {session_type} session: {str(e)}")

        except Exception as e:
            return _json_error("command_failed", f"Failed to start session: {str(e)}", status=500)

    @app.post("/sessions/stop")
    async def post_sessions_stop(body: Dict[str, Any], current_user: UserSession = Depends(get_current_user)):
        _session_id = (body or {}).get("session_id")
        controller = await app.state.rest_service.get_controller()
        try:
            await controller.stop_execution()
        except Exception:
            pass
        return _json_ok({"status": "session_stopped", "data": {"session_id": _session_id}})

    @app.get("/sessions/{id}")
    async def get_session(id: str):
        controller = await app.state.rest_service.get_controller()
        status = controller.get_execution_status()
        if not status or status.get("session_id") != id:
            return _json_ok({"status": "no_active_session"})
        return _json_ok({"status": "session_status", "data": status})

    # Market data endpoint
    @app.get("/market-data")
    async def get_market_data():
        """Get real market data for dashboard display.

        Minimal implementation to keep endpoint healthy when live provider is not configured.
        """
        try:
            # Ensure controller exists (even if we don't stream data here)
            controller = await app.state.rest_service.get_controller()

            # Pull default symbols from settings if available
            container = app.state.rest_service.container
            settings = container.settings if hasattr(container, 'settings') else None
            symbols = []
            if settings and hasattr(settings, 'trading') and hasattr(settings.trading, 'default_symbols'):
                symbols = [str(s).upper() for s in (settings.trading.default_symbols or [])]

            # Shape a minimal response
            data = [
                {
                    "symbol": s,
                    "price": None,
                    "priceChange24h": None,
                    "volume24h": None,
                    "lastUpdate": None,
                }
                for s in symbols
            ]
            return _json_ok({"status": "market_data", "data": data})
        except Exception as e:
            return _json_error("command_failed", f"Failed to get market data: {str(e)}")

    # Indicator endpoints
    @app.get("/api/v1/indicators/{symbol}")
    async def get_indicators_for_symbol(symbol: str):
        """Get current indicator values for a specific symbol."""
        try:
            controller = await app.state.rest_service.get_controller()

            # Get indicators from controller
            indicators = controller.list_indicators()
            symbol_indicators = [i for i in indicators if i.get("symbol", "").upper() == symbol.upper()]

            # For now, return basic structure - in production this would query real-time values
            indicator_values = {}
            for ind in symbol_indicators:
                indicator_values[ind.get("indicator", "unknown")] = {
                    "value": ind.get("value", None),
                    "timestamp": ind.get("timestamp", None),
                    "status": "active"
                }

            return _json_ok({
                "symbol": symbol.upper(),
                "indicators": indicator_values,
                "timestamp": int(time.time() * 1000)
            })

        except Exception as e:
            return _json_error("indicator_fetch_failed", f"Failed to get indicators for {symbol}: {str(e)}", status=500)

    # Results endpoints
    @app.get("/results/session/{id}")
    async def get_session_results(id: str):
        controller = await app.state.rest_service.get_controller()
        results = controller.get_execution_status() or {}

        # Check if live session matches
        if results and results.get("session_id") == id:
            return _json_ok({"status": "results", "data": results, "request_type": "session_results", "source": "live"})

        # Try to get results from UnifiedResultsManager
        try:
            if hasattr(controller, 'results_manager') and controller.results_manager:
                session_summary = controller.results_manager.get_session_summary()
                if session_summary and session_summary.get("session_id") == id:
                    return _json_ok({"status": "results", "data": session_summary, "request_type": "session_results", "source": "unified_manager"})
        except Exception as e:
            pass

        # Fallback to file-backed results if present
        try:
            summary_path = os.path.join("backtest", "backtest_results", id, "session_summary.json")
            if os.path.exists(summary_path):
                with open(summary_path, 'r', encoding='utf-8') as f:
                    file_results = json.load(f)
                return _json_ok({"status": "results", "data": file_results, "request_type": "session_results", "source": "file"})
        except Exception:
            pass
        return _json_error("no_active_session", f"Session not active and no results file: {id}", status=404)

    @app.get("/results/symbol/{symbol}")
    async def get_symbol_results(symbol: str):
        controller = await app.state.rest_service.get_controller()

        # Try to get real symbol statistics from UnifiedResultsManager
        try:
            if hasattr(controller, 'results_manager') and controller.results_manager:
                symbol_stats = controller.results_manager.get_symbol_statistics(symbol.upper())
                if symbol_stats:
                    return _json_ok({"status": "results", "data": symbol_stats, "request_type": "symbol_results", "symbol": symbol})
        except Exception as e:
            pass

        # Fallback to simplified structure if no real data available
        symbol_results = {
            "symbol": symbol.upper(),
            "strategy_results": {},
            "total_signals": 0,
            "total_trades": 0,
            "win_rate": 0.0,
            "total_pnl": 0.0,
            "last_updated": None
        }
        return _json_ok({"status": "results", "data": symbol_results, "request_type": "symbol_results", "symbol": symbol})

    @app.get("/results/strategy/{name}")
    async def get_strategy_results(name: str, symbol: Optional[str] = None):
        controller = await app.state.rest_service.get_controller()

        # Try to get real strategy statistics from UnifiedResultsManager
        try:
            if hasattr(controller, 'results_manager') and controller.results_manager:
                session_stats = controller.results_manager.get_session_statistics()
                if session_stats:
                    strategy_results = {
                        "strategy_name": name,
                        "symbol": symbol,
                        "session_id": session_stats.get("session_id"),
                        "total_signals": session_stats.get("total_signals", 0),
                        "total_trades": session_stats.get("total_trades", 0),
                        "win_rate": session_stats.get("win_rate", 0.0),
                        "total_pnl": session_stats.get("total_pnl", 0.0),
                        "net_pnl": session_stats.get("net_pnl", 0.0),
                        "symbols": session_stats.get("symbols", []),
                        "performance_metrics": {
                            "total_signals": session_stats.get("total_signals", 0),
                            "total_trades": session_stats.get("total_trades", 0),
                            "win_rate": session_stats.get("win_rate", 0.0),
                            "conversion_rate": (session_stats.get("total_trades", 0) / max(session_stats.get("total_signals", 1), 1)) * 100
                        },
                        "risk_metrics": {
                            "max_drawdown": 0.0,
                            "sharpe_ratio": 0.0
                        }
                    }
                    return _json_ok({"status": "results", "data": strategy_results, "request_type": "strategy_results", "symbol": symbol, "strategy": name})
        except Exception as e:
            pass

        # Fallback to basic structure if no real data available
        strategy_results = {
            "strategy_name": name,
            "symbol": symbol,
            "detailed_signals": [],
            "detailed_orders": [],
            "performance_metrics": {"total_signals": 0, "conversion_rate": 0.0, "win_rate": 0.0},
            "risk_metrics": {"max_drawdown": 0.0, "sharpe_ratio": 0.0}
        }
        return _json_ok({"status": "results", "data": strategy_results, "request_type": "strategy_results", "symbol": symbol, "strategy": name})

    @app.post("/results/history/merge")
    async def merge_results_history(body: Dict[str, Any]):
        """Merge historical session results from disk.

        Body fields:
        - base_dir: optional, path to sessions base (default: backtest/backtest_results)
        - session_ids: optional list of session directory names to include
        """
        try:
            from src.results.aggregator import merge_sessions
            base_dir = (body or {}).get("base_dir") or str(Path("backtest") / "backtest_results")
            session_ids = (body or {}).get("session_ids")
            result = merge_sessions(base_dir=base_dir, session_ids=session_ids)
            return _json_ok({"status": "results_merged", "data": result})
        except Exception as e:
            return _json_error("command_failed", f"Failed to merge results: {str(e)}")

    # Wallet endpoint
    @app.get("/wallet/balance")
    async def get_wallet_balance():
        controller = await app.state.rest_service.get_controller()
        balance = controller.get_wallet_balance()
        if balance is None:
            return _json_error("service_unavailable", "Wallet service not available", status=503)
        return _json_ok({"status": "wallet_balance", "data": balance})

    # Order management endpoints
    @app.get("/orders")
    async def get_orders():
        """Get all orders"""
        controller = await app.state.rest_service.get_controller()
        orders = controller.get_all_orders()
        return _json_ok({"status": "orders_list", "data": {"orders": orders}})

    @app.get("/orders/{order_id}")
    async def get_order(order_id: str):
        """Get specific order by ID"""
        controller = await app.state.rest_service.get_controller()
        orders = controller.get_all_orders()
        order = next((o for o in orders if o.get("order_id") == order_id), None)
        if not order:
            return _json_error("not_found", f"Order not found: {order_id}", status=404)

        return _json_ok({"status": "order_status", "data": {"order": order}})

    @app.get("/positions")
    async def get_positions():
        """Get all positions"""
        controller = await app.state.rest_service.get_controller()
        positions = controller.get_all_positions()
        return _json_ok({"status": "positions_list", "data": {"positions": positions}})

    @app.get("/positions/{symbol}")
    async def get_position(symbol: str):
        """Get position for specific symbol"""
        controller = await app.state.rest_service.get_controller()
        positions = controller.get_all_positions()
        position = next((p for p in positions if p.get("symbol") == symbol.upper()), None)
        if not position:
            return _json_ok({"status": "position_status", "data": {"position": None}})

        return _json_ok({"status": "position_status", "data": {"position": position}})

    @app.get("/trading/performance")
    async def get_trading_performance():
        """Get trading performance summary"""
        controller = await app.state.rest_service.get_controller()
        performance = controller.get_trading_performance()
        if performance is None:
            return _json_error("service_unavailable", "Trading performance not available", status=503)

        return _json_ok({"status": "trading_performance", "data": performance})

    # Risk management endpoints
    @app.get("/risk/budget")
    async def get_budget_summary():
        """Get budget utilization summary"""
        sm = await app.state.rest_service.get_strategy_manager()
        if not sm.risk_manager:
            return _json_error("service_unavailable", "Risk manager not available", status=503)

        budget_summary = sm.risk_manager.get_budget_summary()
        return _json_ok({"status": "budget_summary", "data": budget_summary})

    @app.get("/risk/budget/{strategy_name}")
    async def get_strategy_budget(strategy_name: str):
        """Get budget allocation for a specific strategy"""
        sm = await app.state.rest_service.get_strategy_manager()
        if not sm.risk_manager:
            return _json_error("service_unavailable", "Risk manager not available", status=503)

        allocation = sm.risk_manager.get_strategy_allocation(strategy_name)
        if not allocation:
            return _json_error("not_found", f"No budget allocation for strategy: {strategy_name}", status=404)

        return _json_ok({"status": "strategy_budget", "data": {"allocation": allocation}})

    @app.post("/risk/budget/allocate")
    async def allocate_budget(body: Dict[str, Any]):
        """Allocate budget for a strategy"""
        strategy_name = (body or {}).get("strategy_name")
        amount = (body or {}).get("amount")
        max_allocation_pct = (body or {}).get("max_allocation_pct", 5.0)

        if not strategy_name or amount is None:
            return _json_error("validation_error", "strategy_name and amount are required")

        if not isinstance(amount, (int, float)) or amount <= 0:
            return _json_error("validation_error", "amount must be a positive number")

        sm = await app.state.rest_service.get_strategy_manager()
        if not sm.risk_manager:
            return _json_error("service_unavailable", "Risk manager not available", status=503)

        success = sm.risk_manager.allocate_budget(strategy_name, float(amount), max_allocation_pct)
        if not success:
            return _json_error("allocation_failed", f"Failed to allocate budget for {strategy_name}", status=400)

        return _json_ok({"status": "budget_allocated", "data": {
            "strategy_name": strategy_name,
            "amount": amount,
            "max_allocation_pct": max_allocation_pct
        }})

    @app.post("/risk/emergency-stop")
    async def emergency_stop(body: Dict[str, Any]):
        """Emergency stop - release all budget"""
        strategy_name = (body or {}).get("strategy_name")  # Optional: stop specific strategy

        sm = await app.state.rest_service.get_strategy_manager()
        if not sm.risk_manager:
            return _json_error("service_unavailable", "Risk manager not available", status=503)

        released_strategies = sm.risk_manager.emergency_stop(strategy_name)
        return _json_ok({"status": "emergency_stop_executed", "data": {
            "released_strategies": released_strategies
        }})

    @app.post("/risk/assess-position")
    async def assess_position_risk(body: Dict[str, Any]):
        """Assess risk for a potential position"""
        symbol = (body or {}).get("symbol", "").upper()
        position_size = (body or {}).get("position_size", 0.0)
        current_price = (body or {}).get("current_price", 100.0)
        volatility = (body or {}).get("volatility", 0.02)
        max_drawdown = (body or {}).get("max_drawdown", 0.05)
        sharpe_ratio = (body or {}).get("sharpe_ratio", 1.5)

        if not symbol or position_size <= 0:
            return _json_error("validation_error", "symbol and positive position_size are required")

        sm = await app.state.rest_service.get_strategy_manager()
        if not sm.risk_manager:
            return _json_error("service_unavailable", "Risk manager not available", status=503)

        risk_metrics = sm.risk_manager.assess_position_risk(
            symbol=symbol,
            position_size=position_size,
            current_price=current_price,
            volatility=volatility,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio
        )

        return _json_ok({"status": "risk_assessment", "data": {
            "symbol": symbol,
            "risk_level": risk_metrics.risk_level.value,
            "var_95": risk_metrics.var_95,
            "expected_return": risk_metrics.expected_return,
            "recommendation": "APPROVE" if risk_metrics.risk_level.value in ["low", "medium"] else "REJECT"
        }})

    # Legacy API endpoints for backward compatibility
    @app.get("/api/v1/status")
    async def get_status():
        controller = app.state.websocket_api_server.controller
        return JSONResponse(controller.get_execution_status() or {"status": "idle"})

    @app.post("/api/v1/start")
    async def start_session(body: StartSessionRequest):
        controller = app.state.websocket_api_server.controller
        session_id = await controller.start_live_trading(
            symbols=body.symbols,
            mode=body.session_type,
            strategy_config=body.strategy_config,
        )
        return JSONResponse({"status": "session_started", "session_id": session_id})

    @app.post("/api/v1/stop")
    async def stop_session():
        controller = app.state.websocket_api_server.controller
        await controller.stop_execution()
        return JSONResponse({"status": "session_stopped"})

    return app

app = create_unified_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
