"""
Infrastructure Configuration - Unified Configuration System
==========================================================
Single source of truth for all application configuration.

ARCHITECTURE COMPLIANCE:
- AppSettings is the single source of truth
- No singleton patterns or service locators
- Settings created once in main.py via Composition Root
"""

from .settings import AppSettings

__all__ = ['AppSettings']