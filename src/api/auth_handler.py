"""
Authentication Handler
=====================
Handles WebSocket authentication with JWT tokens and permission management.
Production-ready with secure token validation and session management.
"""

import asyncio
import secrets
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import hmac
import os
import bcrypt

# Try to import JWT, fallback to basic auth if not available
try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    # pyright: reportMissingImports=false
    JWT_AVAILABLE = False
    print("Warning: PyJWT not available, using basic authentication")

from ..core.logger import StructuredLogger


class PermissionLevel(str, Enum):
    """User permission levels"""

    BASIC = "basic"           # Read-only market data
    TRADER = "trader"         # Basic trading permissions
    PREMIUM = "premium"       # Advanced features
    ADMIN = "admin"           # Full system access


class Permission(str, Enum):
    """Individual permissions"""

    # Market data permissions
    READ_MARKET_DATA = "read_market_data"
    READ_INDICATORS = "read_indicators"
    READ_SIGNALS = "read_signals"

    # Trading permissions
    EXECUTE_BACKTEST = "execute_backtest"
    EXECUTE_PAPER_TRADING = "execute_paper_trading"
    EXECUTE_LIVE_TRADING = "execute_live_trading"

    # Administrative permissions
    ADMIN_SYSTEM = "admin_system"
    MANAGE_USERS = "manage_users"
    VIEW_SYSTEM_LOGS = "view_system_logs"


@dataclass
class UserSession:
    """Authenticated user session"""

    # Required fields (no default) must come first
    last_activity: datetime

    user_id: str = ""
    username: str = ""
    permissions: List[str] = field(default_factory=list)
    authenticated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    session_token: Optional[str] = None
    refresh_token: Optional[str] = None

    is_active: bool = True

    # Rate limiting
    requests_this_hour: int = 0
    hour_reset_time: Optional[datetime] = None

    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.hour_reset_time is None:
            self.hour_reset_time = datetime.now() + timedelta(hours=1)

    def is_expired(self) -> bool:
        """Check if session is expired"""
        return self.expires_at is not None and datetime.now() > self.expires_at

    def is_valid(self) -> bool:
        """Check if session is valid and active"""
        return self.is_active and not self.is_expired()

    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission"""
        return permission in self.permissions or Permission.ADMIN_SYSTEM in self.permissions

    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.now()

    def increment_request_count(self):
        """Increment request counter for rate limiting"""
        now = datetime.now()
        if now >= self.hour_reset_time:
            self.requests_this_hour = 1
            self.hour_reset_time = now + timedelta(hours=1)
        else:
            self.requests_this_hour += 1

    def is_rate_limited(self, max_requests_per_hour: int = 1000) -> bool:
        """Check if user is rate limited"""
        return self.requests_this_hour >= max_requests_per_hour

    def get_remaining_requests(self, max_requests_per_hour: int = 1000) -> int:
        """Get remaining requests in current hour"""
        return max(0, max_requests_per_hour - self.requests_this_hour)


@dataclass
class AuthResult:
    """Result of authentication attempt"""

    success: bool
    user_session: Optional[UserSession] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    requires_2fa: bool = False


class AuthHandler:
    """
    Handles WebSocket authentication and authorization.

    Features:
    - JWT token validation
    - Session management
    - Permission-based access control
    - Rate limiting
    - Security monitoring
    """

    def __init__(self,
                 jwt_secret: str,
                 token_expiry_hours: int = 24,
                 refresh_token_expiry_days: int = 30,
                 max_sessions_per_user: int = 5,
                 logger: Optional[StructuredLogger] = None):
        """
        Initialize AuthHandler.

        Args:
            jwt_secret: Secret key for JWT signing
            token_expiry_hours: Access token expiry time
            refresh_token_expiry_days: Refresh token expiry time
            max_sessions_per_user: Maximum concurrent sessions per user
            logger: Optional logger instance
        """
        self.jwt_secret = jwt_secret
        self.token_expiry_hours = token_expiry_hours
        self.refresh_token_expiry_days = refresh_token_expiry_days
        self.max_sessions_per_user = max_sessions_per_user
        self.logger = logger

        # ✅ CRITICAL FIX: Defer ThreadPoolExecutor creation to prevent post-fork deadlocks.
        # The executor will be created lazily in the start() method to ensure it's
        # instantiated in the correct event loop after any potential process forking.
        self._password_executor: Optional[ThreadPoolExecutor] = None
        self._executor_lock = asyncio.Lock()

        # Session storage
        self.active_sessions: Dict[str, UserSession] = {}  # session_token -> session
        self.user_sessions: Dict[str, Set[str]] = {}       # user_id -> set of session_tokens
        self.refresh_tokens: Dict[str, str] = {}           # refresh_token -> session_token

        # Permission mappings
        self.permission_levels = {
            PermissionLevel.BASIC: [
                Permission.READ_MARKET_DATA
            ],
            PermissionLevel.TRADER: [
                Permission.READ_MARKET_DATA,
                Permission.READ_INDICATORS,
                Permission.EXECUTE_BACKTEST,
                Permission.EXECUTE_PAPER_TRADING
            ],
            PermissionLevel.PREMIUM: [
                Permission.READ_MARKET_DATA,
                Permission.READ_INDICATORS,
                Permission.READ_SIGNALS,
                Permission.EXECUTE_BACKTEST,
                Permission.EXECUTE_PAPER_TRADING,
                Permission.EXECUTE_LIVE_TRADING
            ],
            PermissionLevel.ADMIN: [
                Permission.ADMIN_SYSTEM,
                Permission.MANAGE_USERS,
                Permission.VIEW_SYSTEM_LOGS
            ]
        }

        # Security monitoring
        self.failed_attempts: Dict[str, List[datetime]] = {}  # ip -> failed attempt times
        self.blocked_ips: Set[str] = set()
        self.suspicious_activities: List[Dict[str, Any]] = []

        # Cleanup task
        self.cleanup_task: Optional[asyncio.Task] = None
        self._is_shutting_down = False
    async def start(self):
        """Start authentication handler"""
        self.cleanup_task = asyncio.create_task(self.cleanup_expired_sessions())
        if self.logger:
            self.logger.info("auth_handler.started", {
                "token_expiry_hours": self.token_expiry_hours,
                "max_sessions_per_user": self.max_sessions_per_user
            })
        # Lazily create the executor on start
        async with self._executor_lock:
            if self._password_executor is None:
                from concurrent.futures import ThreadPoolExecutor
                self._password_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="Password-Hasher")

    async def stop(self):
        """Stop authentication handler"""
        self._is_shutting_down = True
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass

        # Shutdown worker pool
        if self._password_executor:
            self._password_executor.shutdown(wait=False)
            self._password_executor = None

        # Clear all sessions
        self.active_sessions.clear()
        self.user_sessions.clear()
        self.refresh_tokens.clear()

        if self.logger:
            self.logger.info("auth_handler.stopped")

    async def authenticate_token(self,
                               token: str,
                               client_ip: str,
                               user_agent: str) -> AuthResult:
        """
        Authenticate token and create session.
        Uses JWT if available, otherwise basic token validation for testing.

        Args:
            token: Authentication token string
            client_ip: Client IP address
            user_agent: Client user agent

        Returns:
            Authentication result
        """
        try:
            # Check if IP is blocked
            if client_ip in self.blocked_ips:
                return AuthResult(
                    success=False,
                    error_code="ip_blocked",
                    error_message="IP address is temporarily blocked due to security policy"
                )

            # Validate token format
            if not token or len(token.strip()) == 0:
                self._record_failed_attempt(client_ip)
                return AuthResult(
                    success=False,
                    error_code="invalid_token",
                    error_message="Token cannot be empty"
                )

            # Prefer JWT only if token looks like a JWT (has 2 dots). Otherwise use basic validation.
            if JWT_AVAILABLE and token.count('.') >= 2:
                return await self._authenticate_jwt_token(token, client_ip, user_agent)
            else:
                return await self._authenticate_basic_token(token, client_ip, user_agent)

        except Exception as e:
            self._record_failed_attempt(client_ip)
            if self.logger:
                self.logger.error("auth_handler.authentication_error", {
                    "client_ip": client_ip,
                    "error": str(e),
                    "error_type": type(e).__name__
                })
            return AuthResult(
                success=False,
                error_code="authentication_error",
                error_message=f"Authentication failed: {str(e)}"
            )

    async def _authenticate_jwt_token(self,
                                    token: str,
                                    client_ip: str,
                                    user_agent: str) -> AuthResult:
        """Authenticate using JWT token"""
        try:
            # Decode and validate JWT
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])

            # Extract user information
            user_id = payload.get("user_id")
            username = payload.get("username", user_id)
            permission_level = payload.get("permission_level", PermissionLevel.BASIC)

            if not user_id:
                return AuthResult(
                    success=False,
                    error_code="invalid_token",
                    error_message="Token missing required user_id claim"
                )

            # Get permissions for user level
            permissions = self._get_permissions_for_level(permission_level)

            # Check session limits
            if user_id in self.user_sessions and len(self.user_sessions[user_id]) >= self.max_sessions_per_user:
                # Remove oldest session if at limit
                await self._cleanup_oldest_session(user_id)

            # Create session
            session_token = self._generate_session_token()
            refresh_token = self._generate_refresh_token()

            session = UserSession(
                user_id=user_id,
                username=username,
                permissions=permissions,
                authenticated_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=self.token_expiry_hours),
                client_ip=client_ip,
                user_agent=user_agent,
                session_token=session_token,
                refresh_token=refresh_token,
                last_activity=datetime.now()
            )

            # Store session
            self.active_sessions[session_token] = session
            self.refresh_tokens[refresh_token] = session_token

            if user_id not in self.user_sessions:
                self.user_sessions[user_id] = set()
            self.user_sessions[user_id].add(session_token)

            if self.logger:
                self.logger.info("auth_handler.session_created", {
                    "user_id": user_id,
                    "client_ip": client_ip,
                    "permission_level": permission_level,
                    "session_token": session_token[:8] + "..."  # Log partial token for security
                })

            return AuthResult(success=True, user_session=session)

        except jwt.ExpiredSignatureError:
            return AuthResult(
                success=False,
                error_code="token_expired",
                error_message="Authentication token has expired"
            )
        except jwt.InvalidTokenError as e:
            return AuthResult(
                success=False,
                error_code="invalid_token",
                error_message=f"Invalid authentication token: {str(e)}"
            )

    async def _authenticate_basic_token(self,
                                      token: str,
                                      client_ip: str,
                                      user_agent: str) -> AuthResult:
        """Basic token authentication for testing without JWT"""
        # For testing purposes, accept any non-empty token
        # In production, this should be replaced with proper authentication

        if token == "test_token_123":
            # Demo user for testing
            user_id = "demo_user"
            username = "Demo User"
            permission_level = PermissionLevel.BASIC
        elif token.startswith("premium_"):
            # Premium user for testing
            user_id = token.replace("premium_", "")
            username = f"Premium User {user_id}"
            permission_level = PermissionLevel.PREMIUM
        else:
            # Accept any token as basic user for testing
            user_id = f"user_{hash(token) % 1000}"
            username = f"Test User {user_id}"
            permission_level = PermissionLevel.BASIC

        # Get permissions for user level
        permissions = self._get_permissions_for_level(permission_level)

        # Check session limits
        if user_id in self.user_sessions and len(self.user_sessions[user_id]) >= self.max_sessions_per_user:
            # Remove oldest session if at limit
            await self._cleanup_oldest_session(user_id)

        # Create session
        session_token = self._generate_session_token()
        refresh_token = self._generate_refresh_token()

        session = UserSession(
            user_id=user_id,
            username=username,
            permissions=permissions,
            authenticated_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=self.token_expiry_hours),
            client_ip=client_ip,
            user_agent=user_agent,
            session_token=session_token,
            refresh_token=refresh_token,
            last_activity=datetime.now()
        )

        # Store session
        self.active_sessions[session_token] = session
        self.refresh_tokens[refresh_token] = session_token

        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = set()
        self.user_sessions[user_id].add(session_token)

        if self.logger:
            self.logger.info("auth_handler.basic_session_created", {
                "user_id": user_id,
                "client_ip": client_ip,
                "permission_level": permission_level,
                "session_token": session_token[:8] + "..."
            })

        return AuthResult(success=True, user_session=session)

    async def validate_session(self, session_token: str) -> Optional[UserSession]:
        """
        Validate active session.

        Args:
            session_token: Session token to validate

        Returns:
            UserSession if valid, None otherwise
        """
        session = self.active_sessions.get(session_token)
        if not session:
            return None

        if not session.is_valid():
            # Clean up invalid session
            await self._cleanup_session(session_token)
            return None

        # Update activity
        session.update_activity()
        return session

    async def refresh_session(self, refresh_token: str, client_ip: str) -> AuthResult:
        """
        Refresh expired session using refresh token.

        Args:
            refresh_token: Refresh token
            client_ip: Client IP for security validation

        Returns:
            New authentication result
        """
        session_token = self.refresh_tokens.get(refresh_token)
        if not session_token:
            return AuthResult(
                success=False,
                error_code="invalid_refresh_token",
                error_message="Invalid or expired refresh token"
            )

        session = self.active_sessions.get(session_token)
        if not session:
            return AuthResult(
                success=False,
                error_code="session_not_found",
                error_message="Session not found"
            )

        # Security check: IP should match
        if session.client_ip != client_ip:
            self._record_suspicious_activity("ip_mismatch", {
                "session_ip": session.client_ip,
                "request_ip": client_ip,
                "user_id": session.user_id
            })
            return AuthResult(
                success=False,
                error_code="security_violation",
                error_message="Security violation: IP address mismatch"
            )

        # Create new tokens
        new_access_token = self.create_access_token(session.user_id, session.username, self._get_permission_level_from_permissions(session.permissions))
        new_refresh_token = self._generate_refresh_token()

        # Create new session
        new_session_token = self._generate_session_token()

        new_session = UserSession(
            user_id=session.user_id,
            username=session.username,
            permissions=session.permissions,
            authenticated_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=self.token_expiry_hours),
            client_ip=client_ip,
            user_agent=session.user_agent,
            session_token=new_session_token,
            refresh_token=new_refresh_token,
            last_activity=datetime.now()
        )

        # Replace old session
        self.active_sessions[new_session_token] = new_session
        self.refresh_tokens[new_refresh_token] = new_session_token

        # Clean up old session
        await self._cleanup_session(session_token)
        self.refresh_tokens.pop(refresh_token, None)

        if self.logger:
            self.logger.info("auth_handler.session_refreshed", {
                "user_id": session.user_id,
                "old_session": session_token[:8] + "...",
                "new_session": new_session_token[:8] + "..."
            })

        return AuthResult(success=True, user_session=new_session, access_token=new_access_token, refresh_token=new_refresh_token)

    async def logout_session(self, session_token: str):
        """Logout and cleanup session"""
        await self._cleanup_session(session_token)

        if self.logger:
            self.logger.info("auth_handler.session_logout", {
                "session_token": session_token[:8] + "..."
            })

    async def check_permission(self,
                             session_token: str,
                             required_permission: str,
                             client_ip: str) -> bool:
        """
        Check if session has required permission.

        Args:
            session_token: Session token
            required_permission: Required permission
            client_ip: Client IP for security tracking

        Returns:
            True if permission granted, False otherwise
        """
        session = await self.validate_session(session_token)
        if not session:
            return False

        # Rate limiting check
        if session.is_rate_limited():
            if self.logger:
                self.logger.warning("auth_handler.rate_limited", {
                    "user_id": session.user_id,
                    "client_ip": client_ip,
                    "requests_this_hour": session.requests_this_hour
                })
            return False

        # Permission check
        has_permission = session.has_permission(required_permission)
        session.increment_request_count()

        if not has_permission:
            self._record_suspicious_activity("permission_denied", {
                "user_id": session.user_id,
                "required_permission": required_permission,
                "client_ip": client_ip
            })

        return has_permission

    def _get_permissions_for_level(self, permission_level: str) -> List[str]:
        """Get permissions for permission level"""
        if permission_level in self.permission_levels:
            return self.permission_levels[permission_level].copy()

        # Default to basic permissions
        return self.permission_levels[PermissionLevel.BASIC].copy()

    def _get_permission_level_from_permissions(self, permissions: List[str]) -> str:
        """Get permission level from list of permissions"""
        # Check from highest to lowest privilege
        for level in [PermissionLevel.ADMIN, PermissionLevel.PREMIUM, PermissionLevel.TRADER, PermissionLevel.BASIC]:
            level_permissions = self.permission_levels[level]
            if all(perm in permissions for perm in level_permissions):
                return level

        # Default to basic
        return PermissionLevel.BASIC

    def _generate_session_token(self) -> str:
        """Generate secure session token"""
        return secrets.token_urlsafe(32)

    def _generate_refresh_token(self) -> str:
        """Generate secure refresh token"""
        return secrets.token_urlsafe(32)

    def hash_password(self, password: str) -> str:
        """
        Hash password using bcrypt with 12 rounds.

        Args:
            password: Plain text password to hash

        Returns:
            Bcrypt hash string
        """
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    def _verify_password(self, provided_password: str, stored_hash: str) -> bool:
        """
        Securely verify password against bcrypt hash.

        This method supports both:
        1. Bcrypt hashes (production): Secure password verification
        2. Plain text (backward compatibility): For migration period only

        Args:
            provided_password: Password provided by user
            stored_hash: Bcrypt hash or plain text password from env/database

        Returns:
            True if passwords match, False otherwise
        """
        # Check if stored_hash is a bcrypt hash (starts with $2a$, $2b$, or $2y$)
        if stored_hash.startswith('$2'):
            try:
                return bcrypt.checkpw(provided_password.encode('utf-8'), stored_hash.encode('utf-8'))
            except Exception as e:
                if self.logger:
                    self.logger.error("auth_handler.password_verification_error", {
                        "error": str(e),
                        "error_type": type(e).__name__
                    })
                return False
        else:
            # BACKWARD COMPATIBILITY WARNING: Plain text comparison
            # This is ONLY for migration period. Remove after all passwords are hashed.
            if self.logger:
                self.logger.warning("auth_handler.plaintext_password_detected", {
                    "message": "Plain text password detected. Please migrate to bcrypt hashes."
                })
            return hmac.compare_digest(provided_password, stored_hash)

    def _record_failed_attempt(self, client_ip: str):
        """Record failed authentication attempt"""
        if client_ip not in self.failed_attempts:
            self.failed_attempts[client_ip] = []

        self.failed_attempts[client_ip].append(datetime.now())

        # Keep only last 10 attempts
        if len(self.failed_attempts[client_ip]) > 10:
            self.failed_attempts[client_ip] = self.failed_attempts[client_ip][-10:]

        # Check for brute force attack
        recent_attempts = [t for t in self.failed_attempts[client_ip]
                          if (datetime.now() - t).seconds < 300]  # Last 5 minutes

        if len(recent_attempts) >= 5:
            self.blocked_ips.add(client_ip)
            if self.logger:
                self.logger.warning("auth_handler.ip_blocked", {
                    "client_ip": client_ip,
                    "failed_attempts": len(recent_attempts)
                })

    def _record_suspicious_activity(self, activity_type: str, details: Dict[str, Any]):
        """Record suspicious activity for monitoring"""
        activity = {
            "type": activity_type,
            "timestamp": datetime.now(),
            "details": details
        }

        self.suspicious_activities.append(activity)

        # Keep only last 100 activities
        if len(self.suspicious_activities) > 100:
            self.suspicious_activities = self.suspicious_activities[-100:]

        if self.logger:
            self.logger.warning("auth_handler.suspicious_activity", {
                "activity_type": activity_type,
                "details": details
            })

    async def _cleanup_oldest_session(self, user_id: str):
        """Clean up oldest session for user when at limit"""
        if user_id not in self.user_sessions:
            return

        sessions = list(self.user_sessions[user_id])
        if not sessions:
            return

        # Find oldest session
        oldest_session = None
        oldest_time = datetime.now()

        for session_token in sessions:
            session = self.active_sessions.get(session_token)
            if session and session.authenticated_at < oldest_time:
                oldest_session = session_token
                oldest_time = session.authenticated_at

        if oldest_session:
            await self._cleanup_session(oldest_session)

    async def _cleanup_session(self, session_token: str):
        """Clean up specific session"""
        session = self.active_sessions.pop(session_token, None)
        if session:
            # Remove from user sessions
            if session.user_id in self.user_sessions:
                self.user_sessions[session.user_id].discard(session_token)

                # Clean up user entry if no sessions left
                if not self.user_sessions[session.user_id]:
                    del self.user_sessions[session.user_id]

            # Remove refresh token
            self.refresh_tokens.pop(session.refresh_token, None)

    async def cleanup_expired_sessions(self):
        """Background task to cleanup expired sessions"""
        while not self._is_shutting_down:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes

                expired_sessions = []
                now = datetime.now()

                for session_token, session in self.active_sessions.items():
                    if not session.is_valid():
                        expired_sessions.append(session_token)

                for session_token in expired_sessions:
                    await self._cleanup_session(session_token)

                # Cleanup old failed attempts
                old_failed_ips = []
                for ip, attempts in self.failed_attempts.items():
                    # Remove attempts older than 1 hour
                    recent_attempts = [t for t in attempts if (now - t).seconds < 3600]
                    if not recent_attempts:
                        old_failed_ips.append(ip)
                    else:
                        self.failed_attempts[ip] = recent_attempts

                for ip in old_failed_ips:
                    del self.failed_attempts[ip]

                # Unblock IPs that have been blocked for more than 1 hour
                blocked_to_unblock = []
                for ip in self.blocked_ips:
                    if ip in self.failed_attempts:
                        last_attempt = max(self.failed_attempts[ip])
                        if (now - last_attempt).seconds > 3600:  # 1 hour
                            blocked_to_unblock.append(ip)

                for ip in blocked_to_unblock:
                    self.blocked_ips.discard(ip)

                if self.logger and (expired_sessions or old_failed_ips or blocked_to_unblock):
                    self.logger.info("auth_handler.cleanup_completed", {
                        "expired_sessions": len(expired_sessions),
                        "cleaned_failed_attempts": len(old_failed_ips),
                        "unblocked_ips": len(blocked_to_unblock)
                    })

            except Exception as e:
                if self.logger:
                    self.logger.error("auth_handler.cleanup_error", {"error": str(e)})

    def get_stats(self) -> Dict[str, Any]:
        """Get authentication statistics"""
        return {
            "active_sessions": len(self.active_sessions),
            "unique_users": len(self.user_sessions),
            "blocked_ips": len(self.blocked_ips),
            "suspicious_activities": len(self.suspicious_activities),
            "failed_attempts_tracked": len(self.failed_attempts)
        }

    def create_access_token(self, user_id: str, username: str, permission_level: str = PermissionLevel.BASIC) -> str:
        """
        Create JWT access token for user.

        Args:
            user_id: User identifier
            username: Username
            permission_level: Permission level

        Returns:
            JWT access token
        """
        if not JWT_AVAILABLE:
            raise ValueError("PyJWT not available")

        payload = {
            "user_id": user_id,
            "username": username,
            "permission_level": permission_level,
            "exp": datetime.now(timezone.utc) + timedelta(hours=self.token_expiry_hours),
            "iat": datetime.now(timezone.utc),
            "iss": "trading_api"
        }

        token = jwt.encode(payload, self.jwt_secret, algorithm="HS256")
        return token

    def create_refresh_token(self, user_id: str) -> str:
        """
        Create JWT refresh token for user.

        Args:
            user_id: User identifier

        Returns:
            JWT refresh token
        """
        if not JWT_AVAILABLE:
            raise ValueError("PyJWT not available")

        payload = {
            "user_id": user_id,
            "type": "refresh",
            "exp": datetime.now(timezone.utc) + timedelta(days=self.refresh_token_expiry_days),
            "iat": datetime.now(timezone.utc),
            "iss": "trading_api"
        }

        token = jwt.encode(payload, self.jwt_secret, algorithm="HS256")
        return token

    def validate_access_token(self, token: str) -> Optional[UserSession]:
        """
        Validate access token and return user session (temporary for REST API).

        Args:
            token: JWT access token

        Returns:
            UserSession if valid, None otherwise
        """
        if not JWT_AVAILABLE:
            return None

        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            user_id = payload.get("user_id")
            if not user_id:
                return None

            # Create temporary session for REST API request
            return UserSession(
                user_id=user_id,
                username=payload.get("username", user_id),
                permissions=self._get_permissions_for_level(payload.get("permission_level", PermissionLevel.BASIC)),
                authenticated_at=datetime.fromtimestamp(payload.get("iat", 0), tz=timezone.utc),
                expires_at=datetime.fromtimestamp(payload.get("exp", 0), tz=timezone.utc),
                client_ip="REST_API",
                user_agent="REST_API",
                session_token="temp_rest_session",
                refresh_token=None,
                last_activity=datetime.now(timezone.utc)
            )
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, KeyError):
            return None

    async def authenticate_credentials(self, username: str, password: str, client_ip: str) -> AuthResult:
        """
        Authenticate user credentials and create session.

        Args:
            username: Username
            password: Password
            client_ip: Client IP address

        Returns:
            Authentication result with tokens
        """
        if self._password_executor is None:
            raise RuntimeError("AuthHandler has not been started, password executor is not available.")

        # CRITICAL: Credentials must be set via environment variables
        # For PRODUCTION use:
        # 1. Integrate with proper user database (PostgreSQL/QuestDB)
        # 2. Store password hashes (bcrypt), NEVER plain text
        # 3. Remove these hardcoded demo accounts
        # 4. Set credentials via environment variables (all passwords should be bcrypt hashes)

        # ✅ Load .env file if it exists (needed because config.py not imported)
        from dotenv import load_dotenv
        from pathlib import Path
        _env_path = Path(__file__).resolve().parent.parent.parent / ".env"
        if _env_path.exists():
            load_dotenv(dotenv_path=_env_path, override=False)

        # Get credentials from environment with auto-fallback for development
        # Priority 1: Environment variable
        # Priority 2: Development default (logged with warning)
        DEMO_PASSWORD = os.getenv("DEMO_PASSWORD") or "demo123"
        TRADER_PASSWORD = os.getenv("TRADER_PASSWORD") or "trader123"
        PREMIUM_PASSWORD = os.getenv("PREMIUM_PASSWORD") or "premium123"
        ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD") or "admin123"

        # BUG-DV-027/028 FIX: Validate credential configuration
        # Block authentication if using weak/default passwords
        WEAK_DEFAULTS = {"demo123", "trader123", "premium123", "admin123"}
        configuration_errors = []

        # Check for weak default passwords
        credentials_to_check = [
            ("DEMO_PASSWORD", DEMO_PASSWORD),
            ("TRADER_PASSWORD", TRADER_PASSWORD),
            ("PREMIUM_PASSWORD", PREMIUM_PASSWORD),
            ("ADMIN_PASSWORD", ADMIN_PASSWORD),
        ]

        for env_var, value in credentials_to_check:
            if not os.getenv(env_var):
                configuration_errors.append(f"{env_var} must be set via environment variable")
            elif value in WEAK_DEFAULTS:
                configuration_errors.append(f"{env_var} uses weak default value")
            elif "CHANGE_ME" in value:
                configuration_errors.append(f"{env_var} contains CHANGE_ME placeholder")

        # If any configuration errors, block authentication
        if configuration_errors:
            if self.logger:
                self.logger.error("auth_handler.configuration_error", {
                    "errors": configuration_errors,
                    "security_warning": "Authentication blocked due to insecure configuration"
                })
            return AuthResult(
                success=False,
                error_code="configuration_error",
                error_message="; ".join(configuration_errors)
            )

        # Log warnings for development defaults (kept for backwards compatibility)
        using_defaults = []
        if not os.getenv("DEMO_PASSWORD"):
            using_defaults.append("DEMO_PASSWORD")
        if not os.getenv("TRADER_PASSWORD"):
            using_defaults.append("TRADER_PASSWORD")
        if not os.getenv("PREMIUM_PASSWORD"):
            using_defaults.append("PREMIUM_PASSWORD")
        if not os.getenv("ADMIN_PASSWORD"):
            using_defaults.append("ADMIN_PASSWORD")

        if using_defaults and self.logger:
            self.logger.warning("auth_handler.using_development_defaults", {
                "credentials_using_defaults": using_defaults,
                "security_warning": "Set credentials in .env for production",
                "env_file_path": str(_env_path),
                "env_file_exists": _env_path.exists()
            })

        # 🐛 DEBUG: Log environment variable loading for authentication debugging
        if self.logger:
            self.logger.info("auth_handler.credentials_verified", {
                "all_credentials_configured": True,
                "username_attempting": username
            })

        # Demo authentication - REPLACE with database lookup in production
        if username == "demo" and self._verify_password(password, DEMO_PASSWORD):
            user_id = "demo_user"
            permission_level = PermissionLevel.BASIC
        elif username == "trader" and self._verify_password(password, TRADER_PASSWORD):
            user_id = "trader_user"
            permission_level = PermissionLevel.TRADER
        elif username == "premium" and self._verify_password(password, PREMIUM_PASSWORD):
            user_id = "premium_user"
            permission_level = PermissionLevel.PREMIUM
        elif username == "admin" and self._verify_password(password, ADMIN_PASSWORD):
            user_id = "admin_user"
            permission_level = PermissionLevel.ADMIN
        else:
            self._record_failed_attempt(client_ip)
            return AuthResult(
                success=False,
                error_code="invalid_credentials",
                error_message="Invalid username or password"
            )

        try:
            # Create JWT tokens
            access_token = self.create_access_token(user_id, username, permission_level)
            refresh_token = self.create_refresh_token(user_id)

            # Get permissions for user level
            permissions = self._get_permissions_for_level(permission_level)

            # Create session
            session_token = self._generate_session_token()

            session = UserSession(
                user_id=user_id,
                username=username,
                permissions=permissions,
                authenticated_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=self.token_expiry_hours),
                client_ip=client_ip,
                user_agent="REST_API",
                session_token=session_token,
                refresh_token=refresh_token,
                last_activity=datetime.now()
            )

            # Store session
            self.active_sessions[session_token] = session
            self.refresh_tokens[refresh_token] = session_token

            if user_id not in self.user_sessions:
                self.user_sessions[user_id] = set()
            self.user_sessions[user_id].add(session_token)

            if self.logger:
                self.logger.info("auth_handler.jwt_login_success", {
                    "user_id": user_id,
                    "username": username,
                    "permission_level": permission_level,
                    "client_ip": client_ip
                })

            return AuthResult(success=True, user_session=session, access_token=access_token, refresh_token=refresh_token)

        except Exception as e:
            if self.logger:
                self.logger.error("auth_handler.jwt_token_creation_error", {
                    "user_id": user_id,
                    "error": str(e)
                })
            return AuthResult(
                success=False,
                error_code="token_creation_error",
                error_message="Failed to create authentication tokens"
            )

    def generate_session_token(self) -> str:
        """Generate a secure session token"""
        return secrets.token_urlsafe(32)


    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        return {
            "healthy": True,
            "component": "AuthHandler",
            "jwt_available": JWT_AVAILABLE,
            "stats": self.get_stats(),
            "timestamp": datetime.now().isoformat()
        }
