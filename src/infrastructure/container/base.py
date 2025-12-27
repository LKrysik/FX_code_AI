"""
Container Module Base - Shared Infrastructure for DI Modules
=============================================================

Provides base class and utilities for all container modules.
Implements singleton pattern and async factory pattern.
"""

import asyncio
from abc import ABC
from typing import Any, Callable, Dict, Optional, TypeVar, Awaitable, Union

T = TypeVar('T')


class ContainerModule(ABC):
    """
    Base class for container modules.

    Provides:
    - Singleton management with thread-safe access
    - Async factory pattern support
    - Reference to parent container for cross-module dependencies
    """

    def __init__(self, parent_container: 'Container'):
        """
        Initialize module with reference to parent container.

        Args:
            parent_container: Main Container instance for cross-module access
        """
        self._parent = parent_container
        self._singletons: Dict[str, Any] = {}
        self._singleton_locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

    @property
    def settings(self):
        """Access settings from parent container"""
        return self._parent.settings

    @property
    def event_bus(self):
        """Access event bus from parent container"""
        return self._parent.event_bus

    @property
    def logger(self):
        """Access logger from parent container"""
        return self._parent.logger

    def _get_or_create_singleton(self, name: str, factory: Callable[[], T]) -> T:
        """
        Thread-safe singleton factory for synchronous creation.

        Args:
            name: Unique name for the singleton
            factory: Callable that creates the instance

        Returns:
            Singleton instance
        """
        if name not in self._singletons:
            self._singletons[name] = factory()
        return self._singletons[name]

    async def _get_or_create_singleton_async(
        self,
        name: str,
        factory: Union[Callable[[], T], Callable[[], Awaitable[T]]]
    ) -> T:
        """
        Async-safe singleton factory with double-checked locking.

        Args:
            name: Unique name for the singleton
            factory: Sync or async callable that creates the instance

        Returns:
            Singleton instance
        """
        # Fast path: already created
        if name in self._singletons:
            return self._singletons[name]

        # Slow path: need to create with lock
        async with self._global_lock:
            # Get or create lock for this specific singleton
            if name not in self._singleton_locks:
                self._singleton_locks[name] = asyncio.Lock()

        async with self._singleton_locks[name]:
            # Double-check after acquiring lock
            if name in self._singletons:
                return self._singletons[name]

            # Create instance
            if asyncio.iscoroutinefunction(factory):
                instance = await factory()
            else:
                instance = factory()

            self._singletons[name] = instance
            return instance

    def get_singleton(self, name: str) -> Optional[Any]:
        """
        Get existing singleton without creating.

        Args:
            name: Singleton name

        Returns:
            Singleton instance or None if not created
        """
        return self._singletons.get(name)

    def has_singleton(self, name: str) -> bool:
        """Check if singleton exists"""
        return name in self._singletons

    async def cleanup(self) -> None:
        """
        Cleanup module singletons.
        Override in subclasses for specific cleanup logic.
        """
        self._singletons.clear()
        self._singleton_locks.clear()

    def list_singletons(self) -> list:
        """List all created singletons in this module"""
        return list(self._singletons.keys())
