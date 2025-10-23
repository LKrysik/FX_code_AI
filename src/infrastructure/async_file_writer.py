"""
Async File Writer for High-Performance Data Collection
Eliminates I/O blocking that causes event drops
"""

import asyncio
import aiofiles
from pathlib import Path
from typing import Dict, List
import time

class AsyncBatchFileWriter:
    """
    High-performance async file writer with batching to eliminate I/O blocking.
    Prevents EventBus timeouts by making file operations non-blocking.
    """
    
    def __init__(self, 
                 batch_size: int = 100,
                 flush_interval: float = 1.0,
                 max_buffer_size: int = 10000):
        """
        Args:
            batch_size: Number of records to batch before writing
            flush_interval: Max seconds to wait before flushing
            max_buffer_size: Max records per symbol buffer (backpressure protection)
        """
        self._buffers: Dict[str, List[str]] = {}  # No defaultdict to prevent memory leaks
        self._last_flush: Dict[str, float] = {}  # No defaultdict to prevent memory leaks
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._max_buffer_size = max_buffer_size
        self._flush_tasks: Dict[str, asyncio.Task] = {}
        self._shutdown_requested = False
        
    async def write_record(self, file_path: Path, record: str) -> bool:
        """
        Write record asynchronously with batching.
        Returns immediately to prevent EventBus timeouts.
        
        Returns:
            True if record was queued, False if buffer full (backpressure)
        """
        if self._shutdown_requested:
            return False
            
        file_key = str(file_path)

        # Initialize buffer and last_flush for new files
        if file_key not in self._buffers:
            self._buffers[file_key] = []
            self._last_flush[file_key] = 0.0

        # Backpressure protection
        if len(self._buffers[file_key]) >= self._max_buffer_size:
            return False  # Drop record to prevent memory explosion

        # Add to buffer
        self._buffers[file_key].append(record)

        # Check if should flush
        now = time.time()
        should_flush = (
            len(self._buffers[file_key]) >= self._batch_size or
            (now - self._last_flush[file_key]) >= self._flush_interval
        )
        
        if should_flush:
            await self._schedule_flush(file_path, file_key)
            
        return True
    
    async def _schedule_flush(self, file_path: Path, file_key: str):
        """Schedule async flush for file (non-blocking)"""
        # Cancel existing flush task for this file
        if file_key in self._flush_tasks and not self._flush_tasks[file_key].done():
            self._flush_tasks[file_key].cancel()
        
        # Schedule new flush
        self._flush_tasks[file_key] = asyncio.create_task(
            self._flush_buffer(file_path, file_key)
        )
    
    async def _flush_buffer(self, file_path: Path, file_key: str):
        """Flush buffer to file asynchronously"""
        if not self._buffers[file_key]:
            return
        
        # Get records to write
        records = self._buffers[file_key].copy()
        self._buffers[file_key].clear()
        self._last_flush[file_key] = time.time()
        
        max_retries = 3
        for attempt in range(max_retries):
            f = None
            try:
                # Async file write with explicit resource management
                f = await aiofiles.open(file_path, 'a')
                await f.write('\n'.join(records) + '\n')
                break  # Success, exit retry loop
            except Exception as e:
                if attempt == max_retries - 1:
                    # Put records back if all retries failed
                    self._buffers[file_key] = records + self._buffers[file_key]
                    # Log error but don't crash
                    print(f"Async write error for {file_path} after {max_retries} attempts: {e}")
                else:
                    # Wait before retry
                    await asyncio.sleep(0.1 * (attempt + 1))
            finally:
                # Mandatory cleanup to prevent file descriptor leaks
                if f is not None:
                    try:
                        await f.close()
                    except Exception:
                        pass  # Ignore close errors to prevent masking original exception
    
    async def flush_all(self):
        """Flush all buffers (for shutdown)"""
        tasks = []
        for file_key, buffer in self._buffers.items():
            if buffer:
                file_path = Path(file_key)
                tasks.append(self._flush_buffer(file_path, file_key))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def shutdown(self):
        """Graceful shutdown with buffer flush"""
        self._shutdown_requested = True
        
        # Cancel pending flush tasks
        for task in self._flush_tasks.values():
            if not task.done():
                task.cancel()
        
        # Flush all remaining data
        await self.flush_all()
        
        # Clear buffers
        self._buffers.clear()
        self._last_flush.clear()
        self._flush_tasks.clear()
    
    def get_stats(self) -> dict:
        """Get writer statistics"""
        return {
            "files": len(self._buffers),
            "total_buffered": sum(len(buf) for buf in self._buffers.values()),
            "active_flushes": sum(1 for task in self._flush_tasks.values() if not task.done()),
            "shutdown_requested": self._shutdown_requested
        }
