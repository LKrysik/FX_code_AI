"""
Notification Interfaces - Ports for notification services
=========================================================
Abstract interfaces for sending notifications and alerts.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

from ..models.signals import FlashPumpSignal, ReversalSignal
from ..models.trading import Trade, Position


class NotificationLevel(str, Enum):
    """Notification priority levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class NotificationType(str, Enum):
    """Types of notifications"""
    GENERAL_INFO = "general_info"
    SIGNAL_DETECTED = "signal_detected"
    TRADE_EXECUTED = "trade_executed"
    POSITION_CLOSED = "position_closed"
    RISK_ALERT = "risk_alert"
    SYSTEM_ERROR = "system_error"
    PERFORMANCE_REPORT = "performance_report"


class INotificationService(ABC):
    """
    Interface for notification services.
    Abstracts away specific notification channels (Telegram, email, etc.).
    """
    
    @abstractmethod
    async def connect(self) -> None:
        """Initialize connection to notification service"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to notification service"""
        pass
    
    @abstractmethod
    async def send_notification(
        self,
        message: str,
        level: NotificationLevel = NotificationLevel.INFO,
        notification_type: NotificationType = NotificationType.GENERAL_INFO,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send a generic notification.
        Returns True if sent successfully.
        """
        pass
    
    @abstractmethod
    async def send_signal_alert(self, signal: FlashPumpSignal) -> bool:
        """Send alert for detected signal"""
        pass
    
    @abstractmethod
    async def send_reversal_alert(self, signal: ReversalSignal) -> bool:
        """Send alert for reversal signal"""
        pass
    
    @abstractmethod
    async def send_trade_notification(self, trade: Trade, action: str) -> bool:
        """Send notification for trade action (opened/closed)"""
        pass
    
    @abstractmethod
    async def send_position_update(self, position: Position, current_pnl: float) -> bool:
        """Send position update notification"""
        pass
    
    @abstractmethod
    async def send_risk_alert(
        self,
        risk_type: str,
        message: str,
        severity: NotificationLevel,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send risk management alert"""
        pass
    
    @abstractmethod
    async def send_system_error(
        self,
        error_message: str,
        component: str,
        stack_trace: Optional[str] = None
    ) -> bool:
        """Send system error notification"""
        pass
    
    @abstractmethod
    async def send_performance_report(self, report_data: Dict[str, Any]) -> bool:
        """Send performance report"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if notification service is healthy"""
        pass
    
    @abstractmethod
    def get_service_name(self) -> str:
        """Get the name of the notification service"""
        pass


class INotificationFormatter(ABC):
    """
    Interface for formatting notifications.
    Converts data objects into human-readable messages.
    """
    
    @abstractmethod
    def format_signal_message(self, signal: FlashPumpSignal) -> str:
        """Format flash pump signal into readable message"""
        pass
    
    @abstractmethod
    def format_reversal_message(self, signal: ReversalSignal) -> str:
        """Format reversal signal into readable message"""
        pass
    
    @abstractmethod
    def format_trade_message(self, trade: Trade, action: str) -> str:
        """Format trade information into readable message"""
        pass
    
    @abstractmethod
    def format_position_message(self, position: Position, current_pnl: float) -> str:
        """Format position update into readable message"""
        pass
    
    @abstractmethod
    def format_risk_message(
        self,
        risk_type: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Format risk alert into readable message"""
        pass
    
    @abstractmethod
    def format_performance_message(self, report_data: Dict[str, Any]) -> str:
        """Format performance report into readable message"""
        pass
    
    @abstractmethod
    def format_error_message(
        self,
        error_message: str,
        component: str,
        stack_trace: Optional[str] = None
    ) -> str:
        """Format error information into readable message"""
        pass


class INotificationFilter(ABC):
    """
    Interface for filtering notifications.
    Determines which notifications should be sent based on rules.
    """
    
    @abstractmethod
    async def should_send_signal_alert(self, signal: FlashPumpSignal) -> bool:
        """Check if signal alert should be sent"""
        pass
    
    @abstractmethod
    async def should_send_trade_notification(self, trade: Trade, action: str) -> bool:
        """Check if trade notification should be sent"""
        pass
    
    @abstractmethod
    async def should_send_position_update(self, position: Position, current_pnl: float) -> bool:
        """Check if position update should be sent"""
        pass
    
    @abstractmethod
    async def should_send_risk_alert(
        self,
        risk_type: str,
        severity: NotificationLevel,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Check if risk alert should be sent"""
        pass
    
    @abstractmethod
    async def get_notification_frequency_limit(self, notification_type: NotificationType) -> int:
        """Get frequency limit for notification type (per hour)"""
        pass
    
    @abstractmethod
    async def is_notification_throttled(self, notification_type: NotificationType) -> bool:
        """Check if notification type is currently throttled"""
        pass


class INotificationHistory(ABC):
    """
    Interface for notification history tracking.
    Keeps track of sent notifications for analytics and throttling.
    """
    
    @abstractmethod
    async def record_notification(
        self,
        service_name: str,
        notification_type: NotificationType,
        level: NotificationLevel,
        message: str,
        success: bool,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record a sent notification"""
        pass
    
    @abstractmethod
    async def get_notification_count(
        self,
        notification_type: NotificationType,
        hours: int = 1
    ) -> int:
        """Get count of notifications sent in last N hours"""
        pass
    
    @abstractmethod
    async def get_failed_notifications(
        self,
        service_name: Optional[str] = None,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Get failed notifications in last N hours"""
        pass
    
    @abstractmethod
    async def get_notification_statistics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get notification statistics for time period"""
        pass
    
    @abstractmethod
    async def cleanup_old_records(self, days: int = 30) -> int:
        """Clean up notification records older than N days"""
        pass


class INotificationAggregator(ABC):
    """
    Interface for aggregating notifications from multiple services.
    Manages multiple notification channels and fallbacks.
    """
    
    @abstractmethod
    async def add_service(self, service: INotificationService, priority: int = 1) -> None:
        """Add a notification service with priority"""
        pass
    
    @abstractmethod
    async def remove_service(self, service_name: str) -> None:
        """Remove a notification service"""
        pass
    
    @abstractmethod
    async def send_to_all_services(
        self,
        message: str,
        level: NotificationLevel = NotificationLevel.INFO,
        notification_type: NotificationType = NotificationType.GENERAL_INFO,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, bool]:
        """
        Send notification to all services.
        Returns dict of service_name -> success
        """
        pass
    
    @abstractmethod
    async def send_with_fallback(
        self,
        message: str,
        level: NotificationLevel = NotificationLevel.INFO,
        notification_type: NotificationType = NotificationType.GENERAL_INFO,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send notification using services in priority order with fallback.
        Returns True if any service succeeded.
        """
        pass
    
    @abstractmethod
    async def get_service_health(self) -> Dict[str, bool]:
        """Get health status of all services"""
        pass
    
    @abstractmethod
    async def get_service_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all services"""
        pass


class IAlertManager(ABC):
    """
    Interface for managing trading alerts and notifications.
    High-level interface for trading-specific notifications.
    """
    
    @abstractmethod
    async def alert_pump_detected(
        self,
        signal: FlashPumpSignal,
        confidence_threshold: float = 70.0
    ) -> None:
        """Send alert when pump is detected above confidence threshold"""
        pass
    
    @abstractmethod
    async def alert_reversal_detected(
        self,
        signal: ReversalSignal,
        position: Optional[Position] = None
    ) -> None:
        """Send alert when reversal is detected"""
        pass
    
    @abstractmethod
    async def alert_trade_opened(self, trade: Trade, signal: FlashPumpSignal) -> None:
        """Send alert when trade is opened"""
        pass
    
    @abstractmethod
    async def alert_trade_closed(
        self,
        trade: Trade,
        reason: str,
        pnl_pct: float
    ) -> None:
        """Send alert when trade is closed"""
        pass
    
    @abstractmethod
    async def alert_daily_summary(self, summary_data: Dict[str, Any]) -> None:
        """Send daily trading summary"""
        pass
    
    @abstractmethod
    async def alert_risk_limit_exceeded(
        self,
        limit_type: str,
        current_value: float,
        limit_value: float,
        action_taken: str
    ) -> None:
        """Send alert when risk limit is exceeded"""
        pass
    
    @abstractmethod
    async def alert_system_issue(
        self,
        component: str,
        issue_type: str,
        description: str,
        severity: NotificationLevel = NotificationLevel.ERROR
    ) -> None:
        """Send alert for system issues"""
        pass
    
    @abstractmethod
    async def alert_connection_lost(self, service: str, reconnect_attempts: int) -> None:
        """Send alert when connection to external service is lost"""
        pass
    
    @abstractmethod
    async def alert_connection_restored(self, service: str, downtime_seconds: int) -> None:
        """Send alert when connection is restored"""
        pass