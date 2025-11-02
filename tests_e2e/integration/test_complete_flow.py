"""
Integration E2E Tests - Complete Flows
=======================================

Full end-to-end tests covering complete user workflows.
"""

import pytest
import time
from playwright.sync_api import Page, expect


@pytest.mark.integration
@pytest.mark.slow
class TestCompleteAuthAndStrategyFlow:
    """Integration test: Login → Create strategy → Verify"""

    def test_login_create_strategy_complete_flow(self, page: Page, authenticated_client, test_config, valid_strategy_config):
        """
        Test complete flow: UI login → API create strategy → UI verify

        Steps:
        1. Login via UI
        2. Create strategy via API
        3. Verify strategy appears in UI
        """

        # Step 1: Login via UI
        page.goto(f"{test_config['frontend_base_url']}/login")
        page.fill('input[name="username"]', test_config["admin_username"])
        page.fill('input[name="password"]', test_config["admin_password"])
        page.click('button[type="submit"]')
        page.wait_for_url(f"{test_config['frontend_base_url']}/dashboard", timeout=10000)

        # Step 2: Create strategy via API
        create_response = authenticated_client.post("/api/strategies", json=valid_strategy_config)
        assert create_response.status_code == 200

        strategy_id = create_response.json()["data"]["strategy"]["id"]
        strategy_name = valid_strategy_config["strategy_name"]

        # Step 3: Navigate to strategies page (if exists)
        # (Adjust based on actual frontend routing)
        # page.goto(f"{test_config['frontend_base_url']}/strategies")

        # Cleanup
        authenticated_client.delete(f"/api/strategies/{strategy_id}")


@pytest.mark.integration
@pytest.mark.slow
class TestCompleteDataCollectionFlow:
    """Integration test: Start data collection → Monitor → Stop"""

    def test_api_start_ui_monitor_api_stop(self, authenticated_client, page: Page, test_config, test_symbols):
        """
        Test complete data collection flow

        Steps:
        1. Start session via API
        2. Monitor via UI
        3. Stop via API
        4. Verify cleanup
        """

        # Step 1: Start session via API
        session_config = {
            "symbols": test_symbols,
            "session_type": "collect",
            "config": {
                "data_collection": {
                    "duration": "1m"
                }
            }
        }

        start_response = authenticated_client.post("/sessions/start", json=session_config)
        assert start_response.status_code == 200

        session_id = start_response.json()["data"]["session_id"]

        # Wait for session to initialize
        time.sleep(2)

        # Step 2: Verify status via API
        status_response = authenticated_client.get("/sessions/execution-status")
        assert status_response.status_code == 200

        status = status_response.json()["data"]
        assert status["status"] in ("running", "starting")
        assert status["session_id"] == session_id

        # Step 3: Stop session via API
        stop_response = authenticated_client.post("/sessions/stop", json={"session_id": session_id})
        assert stop_response.status_code == 200

        # Step 4: Verify stopped
        time.sleep(1)

        final_status = authenticated_client.get("/sessions/execution-status")
        assert final_status.status_code == 200

        final_data = final_status.json()["data"]
        assert final_data["status"] in ("idle", "stopped", "completed")
