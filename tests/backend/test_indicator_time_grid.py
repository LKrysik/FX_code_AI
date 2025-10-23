import csv
from types import SimpleNamespace

import pytest

from src.api import indicators_routes as routes


def test_compute_indicator_series_uses_uniform_time_grid(tmp_path):
    original_base_path = routes.DATA_BASE_PATH
    routes.DATA_BASE_PATH = tmp_path
    routes._reset_indicators_state_for_tests()

    session_id = "session_exec_unit"
    symbol = "BTC_USDT"
    price_dir = tmp_path / session_id / symbol
    price_dir.mkdir(parents=True, exist_ok=True)

    with (price_dir / "prices.csv").open("w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["timestamp", "price", "volume"])
        writer.writerow([0.0, 100.0, 1.0])
        writer.writerow([0.4, 101.0, 1.5])
        writer.writerow([1.7, 102.0, 2.0])
        writer.writerow([2.9, 103.0, 1.2])
        writer.writerow([4.2, 104.0, 1.0])

    variant = SimpleNamespace(
        id="variant-twpa",
        parameters={"t1": 3.0, "t2": 0.0},
        variant_type="general",
        base_indicator_type="TWPA",
        name="TWPA",
    )

    try:
        _, offline_engine = routes._ensure_support_services()
        series = routes._compute_indicator_series(
            indicator_id="ind-1",
            session_id=session_id,
            symbol=symbol,
            variant=variant,
            override_parameters={},
            algorithm_registry=None,
            offline_engine=offline_engine,
        )
    finally:
        routes._reset_indicators_state_for_tests()
        routes.DATA_BASE_PATH = original_base_path

    assert series, "expected indicator series to be produced"

    timestamps = [value.timestamp for value in series]
    refresh_interval = series[0].metadata.get("refresh_interval_seconds", 1.0)

    assert timestamps[0] == pytest.approx(0.0)
    assert timestamps[-1] == pytest.approx(4.0)

    for prev, curr in zip(timestamps, timestamps[1:]):
        assert curr - prev == pytest.approx(refresh_interval, rel=0.0, abs=1e-6)

    assert any(value.value is not None for value in series), "indicator should yield at least one value"


def test_twpa_ratio_returns_values(tmp_path):
    original_base_path = routes.DATA_BASE_PATH
    routes.DATA_BASE_PATH = tmp_path
    routes._reset_indicators_state_for_tests()

    session_id = "session_exec_ratio"
    symbol = "ETH_USDT"
    price_dir = tmp_path / session_id / symbol
    price_dir.mkdir(parents=True, exist_ok=True)

    with (price_dir / "prices.csv").open("w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["timestamp", "price", "volume"])
        for second in range(0, 601):
            writer.writerow([float(second), 100.0, 1.0])

    variant = SimpleNamespace(
        id="variant-twpa-ratio",
        parameters={"t1": 120.0, "t2": 60.0, "t3": 300.0, "t4": 180.0},
        variant_type="general",
        base_indicator_type="TWPA_RATIO",
        name="TWPA_RATIO",
    )

    try:
        _, offline_engine = routes._ensure_support_services()
        series = routes._compute_indicator_series(
            indicator_id="ratio-1",
            session_id=session_id,
            symbol=symbol,
            variant=variant,
            override_parameters={},
            algorithm_registry=None,
            offline_engine=offline_engine,
        )
    finally:
        routes._reset_indicators_state_for_tests()
        routes.DATA_BASE_PATH = original_base_path

    assert series, "expected series for TWPA ratio"
    values = [value.value for value in series if value.value is not None]
    assert values, "TWPA ratio should eventually yield numeric values"
    assert values[-1] == pytest.approx(1.0, rel=0.0, abs=1e-6)
