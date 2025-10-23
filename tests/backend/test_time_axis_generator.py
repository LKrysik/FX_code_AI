import pytest

from src.domain.utils import TimeAxisGenerator, TimeAxisBounds


def test_time_axis_alignment():
    bounds = TimeAxisBounds(start=0.3, end=3.2, interval=1.0)
    axis = list(TimeAxisGenerator.generate(bounds))

    assert axis[0] == pytest.approx(1.0)
    assert axis[-1] == pytest.approx(3.0)
    deltas = [axis[i + 1] - axis[i] for i in range(len(axis) - 1)]
    assert all(delta == pytest.approx(1.0) for delta in deltas)


def test_time_axis_handles_fractional_intervals():
    bounds = TimeAxisBounds(start=10.2, end=12.4, interval=0.5)
    axis = TimeAxisGenerator.as_list(bounds.start, bounds.end, bounds.interval)

    assert axis[0] == pytest.approx(10.5)
    assert axis[-1] == pytest.approx(12.0)
    assert len(axis) == 4  # 10.5, 11.0, 11.5, 12.0
