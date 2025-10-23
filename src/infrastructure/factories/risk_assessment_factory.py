"""
Factory for RiskAssessmentService
=================================
"""

from ...domain.services.risk_assessment import RiskAssessmentService
from ...infrastructure.config.settings import AppSettings

class RiskAssessmentServiceFactory:
    @staticmethod
    def create(settings: AppSettings) -> RiskAssessmentService:
        """Create risk assessment service from Settings."""
        return RiskAssessmentService(
            settings.risk_management,
            settings.entry_conditions,
            settings.safety_limits
        )
