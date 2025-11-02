import csv
import importlib
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _build_price_csv(path: Path, count: int = 60) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["timestamp", "price", "volume"])
        base_ts = 1_700_000_000.0
        price = 100.0
        for idx in range(count):
            writer.writerow([base_ts + idx * 5, price + idx * 0.1, 10 + idx])


@pytest.fixture()
def app(monkeypatch, tmp_path):
    data_root = tmp_path / "data"
    session_id = "session_test"
    symbol = "TEST_USDT"
    prices_path = data_root / session_id / symbol / "prices.csv"
    _build_price_csv(prices_path)

    monkeypatch.setenv("INDICATOR_DATA_DIR", str(data_root))
    from src.api import indicators_routes

    importlib.reload(indicators_routes)
    indicators_routes._reset_indicators_state_for_tests()

    application = FastAPI()
    application.include_router(indicators_routes.router)

    yield application

    indicators_routes._reset_indicators_state_for_tests()


def test_indicator_history_flow(app):
    client = TestClient(app)
    session_id = "session_test"
    symbol = "TEST_USDT"

    variant_resp = client.post(
        "/api/indicators/variants",
        json={
            "name": "Test SMA",
            "indicator_type": "SMA",
            "variant_type": "price",
            "parameters": {"period": 5},
        },
    )
    assert variant_resp.status_code == 200
    variant_id = variant_resp.json()["data"]["variant_id"]

    add_resp = client.post(
        f"/api/indicators/sessions/{session_id}/symbols/{symbol}/indicators",
        json={"variant_id": variant_id},
    )
    assert add_resp.status_code == 200
    add_payload = add_resp.json()["data"]
    indicator_id = add_payload["indicator_id"]

    file_info = add_payload["file"]
    assert file_info["exists"] is True
    saved_path = Path(file_info["file_path"])
    assert saved_path.exists()
    assert saved_path.with_name(saved_path.name).is_file()

    history_resp = client.get(
        f"/api/indicators/sessions/{session_id}/symbols/{symbol}/indicators/{indicator_id}/history"
    )
    assert history_resp.status_code == 200
    history_data = history_resp.json()["data"]
    assert history_data["total_count"] > 0
    assert history_data["history"][0]["value"] is not None

    values_resp = client.get(f"/api/indicators/sessions/{session_id}/symbols/{symbol}/values")
    assert values_resp.status_code == 200
    values_data = values_resp.json()["data"]
    assert indicator_id in values_data["files"]
    assert values_data["files"][indicator_id]["exists"] is True
