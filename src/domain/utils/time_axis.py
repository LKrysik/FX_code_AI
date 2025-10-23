"""
Time Axis Utilities
===================

Helper functions for generating deterministic timestamp sequences that honour
`refresh_interval_seconds` requirements from USER_REC_14.  The generator
produces arithmetic progressions aligned to the requested cadence and keeps
sequences gap-free even when market data arrives irregularly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Iterator, List
import math


@dataclass(frozen=True)
class TimeAxisBounds:
    """Bounds for generating timestamps."""

    start: float
    end: float
    interval: float

    def __post_init__(self) -> None:
        if self.interval <= 0:
            raise ValueError("interval must be positive")
        if self.end < self.start:
            raise ValueError("end must be greater than or equal to start")


class TimeAxisGenerator:
    """
    Utility class that generates arithmetic timestamp sequences.

    The class exposes pure helpers so both streaming and offline engines can
    share the same logic when synthesising the target time grid.
    """

    @staticmethod
    def align_start(start: float, interval: float) -> float:
        """
        Align the start timestamp to the nearest lower-or-equal interval boundary.
        """
        if interval <= 0:
            raise ValueError("interval must be positive")
        remainder = math.fmod(start, interval)
        if remainder < 0:
            remainder += interval
        if math.isclose(remainder, 0.0, abs_tol=1e-9):
            return start
        return start - remainder

    @staticmethod
    def generate(bounds: TimeAxisBounds) -> Iterator[float]:
        """
        Generate timestamps within the provided bounds (inclusive).

        The first timestamp is aligned to the interval boundary less than or
        equal to ``bounds.start``.  The last timestamp will not exceed
        ``bounds.end``.
        """
        aligned_start = TimeAxisGenerator.align_start(bounds.start, bounds.interval)
        current = aligned_start
        # Guard against floating point accumulation by counting iterations.
        index = 0
        while current <= bounds.end + 1e-9:
            yield round(current, 9)
            index += 1
            current = aligned_start + (bounds.interval * index)

    @staticmethod
    def as_list(start: float, end: float, interval: float) -> List[float]:
        """Convenience helper returning the generated timestamps as a list."""
        bounds = TimeAxisBounds(start=start, end=end, interval=interval)
        return list(TimeAxisGenerator.generate(bounds))


__all__ = ["TimeAxisGenerator", "TimeAxisBounds"]
