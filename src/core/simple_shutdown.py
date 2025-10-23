"""
Simple Shutdown Manager - Pragmatic approach for crypto trading systems
=====================================================================
Minimal, focused shutdown handling without over-engineering.
"""

import asyncio
import signal
import sys
import threading
import time
from typing import Set, List, Callable, Optional


class SimpleShutdown:
    """Minimal shutdown manager focused on practical needs"""

    _stop_event = threading.Event()
    _asyncio_event: Optional[asyncio.Event] = None
    _instances: Set['SimpleShutdown'] = set()
    _signal_registered = False
    
    def __init__(self, name: str = "Component"):
        self.name = name
        self._cleanup_callbacks: List[Callable] = []
        self._tasks: Set[asyncio.Task] = set()
        
        SimpleShutdown._instances.add(self)
        
        # Register signal handlers once
        if not SimpleShutdown._signal_registered:
            self._setup_signals()
            SimpleShutdown._signal_registered = True
    
    def _setup_signals(self):
        """Setup basic signal handling"""
        def signal_handler(signum, frame):
            print(f"\n[SHUTDOWN] Signal {signum} received")
            SimpleShutdown._stop_event.set()

            # Set asyncio event if available
            if SimpleShutdown._asyncio_event:
                try:
                    loop = asyncio.get_running_loop()
                    loop.call_soon_threadsafe(SimpleShutdown._asyncio_event.set)
                except RuntimeError:
                    pass  # No running loop

            # ✅ FIXED: Longer grace period to allow proper cleanup
            # Force exit after 10 seconds instead of 5
            def force_exit():
                time.sleep(10.0)
                print("[SHUTDOWN] Grace period expired - force exit")
                sys.exit(1)

            threading.Thread(target=force_exit, daemon=True).start()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    @classmethod
    def set_asyncio_event(cls, event: asyncio.Event):
        """Set asyncio event for unified shutdown handling"""
        cls._asyncio_event = event

    @property
    def is_shutdown_requested(self) -> bool:
        """Check if shutdown was requested"""
        return SimpleShutdown._stop_event.is_set() or (
            SimpleShutdown._asyncio_event and SimpleShutdown._asyncio_event.is_set()
        )
    
    def register_cleanup(self, callback: Callable):
        """Register cleanup callback"""
        self._cleanup_callbacks.append(callback)
    
    def register_task(self, task: asyncio.Task):
        """Register task for cleanup"""
        self._tasks.add(task)
        task.add_done_callback(lambda t: self._tasks.discard(t))
    
    async def cleanup(self):
        """Simple cleanup"""
        print(f"[SHUTDOWN] Cleaning up {self.name}")
        
        # Cancel tasks
        for task in list(self._tasks):
            if not task.done():
                task.cancel()
        
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        
        # Run callbacks
        for callback in self._cleanup_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                print(f"[SHUTDOWN] Cleanup error: {e}")
        
        SimpleShutdown._instances.discard(self)
    
    @classmethod
    async def cleanup_all(cls):
        """Cleanup all instances"""
        tasks = []
        for instance in list(cls._instances):
            tasks.append(instance.cleanup())
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


# Global convenience functions
_last_heartbeat = 0.0

def heartbeat():
    """Signal activity to watchdog - no-op implementation for compatibility"""
    global _last_heartbeat
    _last_heartbeat = time.time()

def is_shutdown_requested() -> bool:
    """Check if shutdown was requested"""
    return SimpleShutdown._stop_event.is_set() or (
        SimpleShutdown._asyncio_event and SimpleShutdown._asyncio_event.is_set()
    )


async def sleep_with_shutdown_check(duration: float):
    """Sleep with shutdown check"""
    end_time = time.time() + duration
    while time.time() < end_time and not is_shutdown_requested():
        await asyncio.sleep(min(0.1, end_time - time.time()))


def run_with_shutdown_protection(main_coro):
    """Run coroutine with basic shutdown protection"""
    async def protected_main():
        try:
            await main_coro
        except KeyboardInterrupt:
            print("\n[SHUTDOWN] Keyboard interrupt")
        finally:
            await SimpleShutdown.cleanup_all()
    
    try:
        asyncio.run(protected_main())
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Final interrupt")
    finally:
        print("[SHUTDOWN] Complete")