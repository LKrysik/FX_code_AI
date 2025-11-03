"""
Error Handler Utility
=====================
Centralized error response generation for WebSocket server.

Why this exists:
- Eliminates 100+ lines of duplicate error handling code
- Provides consistent error response format across all handlers
- Single place to change error response structure
- Easier testing of error scenarios

Extracted from websocket_server.py lines 1423-1483, 1495-1560, etc.
(20+ duplicate patterns consolidated)
"""

from typing import Dict, Any, Optional, List
from datetime import datetime


class ErrorHandler:
    """
    Centralized error response generator.

    Provides consistent error responses for common scenarios:
    - Service unavailable (controller, strategy_manager, etc.)
    - Missing parameters
    - Invalid parameters
    - Operation failures
    - Authentication/authorization errors

    All methods return Dict[str, Any] compatible with MessageType.ERROR format.
    """

    def __init__(self, logger=None):
        """
        Initialize ErrorHandler.

        Args:
            logger: Optional logger instance for error logging
        """
        self.logger = logger

    def service_unavailable(
        self,
        service_name: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate service unavailable error.

        Used when required service (controller, strategy_manager, etc.) is not available.
        Consolidated from 10+ duplicate patterns in websocket_server.py

        Args:
            service_name: Name of unavailable service
            session_id: Optional session ID to include in response

        Returns:
            Error response dict

        Example:
            >>> handler.service_unavailable("controller", "session_123")
            {
                "type": "error",
                "error_code": "service_unavailable",
                "error_message": "controller not available",
                "session_id": "session_123",
                "timestamp": "2025-11-03T08:00:00.000000"
            }
        """
        if self.logger:
            self.logger.warning("error_handler.service_unavailable", {
                "service": service_name,
                "session_id": session_id
            })

        return {
            "type": "error",
            "error_code": "service_unavailable",
            "error_message": f"{service_name} not available",
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        }

    def missing_parameters(
        self,
        params: List[str],
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate missing parameters error.

        Used when required parameters are missing from request.
        Consolidated from 5+ duplicate patterns.

        Args:
            params: List of missing parameter names
            session_id: Optional session ID

        Returns:
            Error response dict

        Example:
            >>> handler.missing_parameters(["username", "password"])
            {
                "type": "error",
                "error_code": "missing_parameters",
                "error_message": "Required parameters: username, password",
                ...
            }
        """
        if self.logger:
            self.logger.debug("error_handler.missing_parameters", {
                "params": params,
                "session_id": session_id
            })

        params_str = ", ".join(params)
        return {
            "type": "error",
            "error_code": "missing_parameters",
            "error_message": f"Required parameters: {params_str}",
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        }

    def invalid_parameter(
        self,
        param_name: str,
        param_value: Any,
        expected: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate invalid parameter error.

        Used when parameter has invalid value.

        Args:
            param_name: Name of invalid parameter
            param_value: The invalid value provided
            expected: Optional description of expected value
            session_id: Optional session ID

        Returns:
            Error response dict

        Example:
            >>> handler.invalid_parameter("session_type", "INVALID", "backtest, live, or paper")
            {
                "type": "error",
                "error_code": "invalid_parameter",
                "error_message": "Invalid session_type: INVALID. Expected: backtest, live, or paper",
                ...
            }
        """
        if self.logger:
            self.logger.debug("error_handler.invalid_parameter", {
                "param": param_name,
                "value": param_value,
                "expected": expected
            })

        message = f"Invalid {param_name}: {param_value}"
        if expected:
            message += f". Expected: {expected}"

        return {
            "type": "error",
            "error_code": "invalid_parameter",
            "error_message": message,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        }

    def operation_failed(
        self,
        operation: str,
        error: Exception,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate operation failed error.

        Used when operation fails with exception.
        Consolidated from 15+ duplicate patterns.

        Args:
            operation: Name of failed operation (e.g., "session_start", "strategy_activation")
            error: The exception that occurred
            session_id: Optional session ID

        Returns:
            Error response dict

        Example:
            >>> handler.operation_failed("session_start", ValueError("Invalid config"))
            {
                "type": "error",
                "error_code": "session_start_failed",
                "error_message": "Invalid config",
                ...
            }
        """
        if self.logger:
            self.logger.error(f"error_handler.operation_failed.{operation}", {
                "error": str(error),
                "error_type": type(error).__name__,
                "session_id": session_id
            })

        return {
            "type": "error",
            "error_code": f"{operation}_failed",
            "error_message": str(error),
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        }

    def authentication_required(
        self,
        reason: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate authentication required error.

        Used when operation requires authentication but user is not authenticated.

        Args:
            reason: Optional reason why auth is required
            session_id: Optional session ID

        Returns:
            Error response dict
        """
        if self.logger:
            self.logger.warning("error_handler.authentication_required", {
                "reason": reason,
                "session_id": session_id
            })

        message = "Authentication required"
        if reason:
            message += f": {reason}"

        return {
            "type": "error",
            "error_code": "authentication_required",
            "error_message": message,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        }

    def insufficient_permissions(
        self,
        required_permission: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate insufficient permissions error.

        Args:
            required_permission: The permission that is required
            session_id: Optional session ID

        Returns:
            Error response dict
        """
        if self.logger:
            self.logger.warning("error_handler.insufficient_permissions", {
                "required": required_permission,
                "session_id": session_id
            })

        return {
            "type": "error",
            "error_code": "insufficient_permissions",
            "error_message": f"{required_permission} permission required",
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        }

    def message_processing_error(
        self,
        error: Exception,
        client_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate message processing error.

        Used when message processing fails unexpectedly.

        Args:
            error: The exception that occurred
            client_id: Optional client ID

        Returns:
            Error response dict
        """
        if self.logger:
            self.logger.error("error_handler.message_processing", {
                "error": str(error),
                "error_type": type(error).__name__,
                "client_id": client_id
            })

        return {
            "type": "error",
            "error_code": "message_processing_error",
            "error_message": f"Failed to process message: {str(error)}",
            "timestamp": datetime.now().isoformat()
        }

    def validation_error(
        self,
        message: str,
        errors: Optional[List[str]] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate validation error.

        Used when input validation fails.

        Args:
            message: Error message
            errors: Optional list of specific validation errors
            session_id: Optional session ID

        Returns:
            Error response dict
        """
        if self.logger:
            self.logger.debug("error_handler.validation_error", {
                "message": message,
                "errors": errors,
                "session_id": session_id
            })

        result = {
            "type": "error",
            "error_code": "validation_error",
            "error_message": message,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        }

        if errors:
            result["errors"] = errors

        return result

    def get_session_id_safe(self, controller) -> Optional[str]:
        """
        Safely get session ID from controller.

        This helper consolidates the pattern that appears 20+ times:

        sess = None
        try:
            sess = self.controller.get_execution_status() if self.controller else None
        except Exception:
            sess = None
        session_id = sess.get("session_id") if isinstance(sess, dict) and sess.get("session_id") else None

        Args:
            controller: Controller instance (may be None)

        Returns:
            Session ID string or None
        """
        if not controller:
            return None

        try:
            status = controller.get_execution_status()
            if isinstance(status, dict):
                return status.get("session_id")
        except Exception as e:
            if self.logger:
                self.logger.debug("error_handler.get_session_id_failed", {
                    "error": str(e)
                })

        return None
