#!/bin/bash

# Test State Machine API Endpoints
# Prerequisites: Backend server running on localhost:8080

set -e

BASE_URL="http://localhost:8080"
SESSION_ID=""

echo "=== State Machine API Test Suite ==="
echo ""

# Test 1: Get state for non-existent session (should return IDLE)
echo "Test 1: Get state for non-existent session"
curl -s -X GET "$BASE_URL/api/sessions/unknown_session/state" | jq .
echo ""

# Test 2: Start a paper trading session
echo "Test 2: Starting paper trading session..."
SESSION_RESPONSE=$(curl -s -X POST "$BASE_URL/sessions/start" \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["BTC_USDT", "ETH_USDT"],
    "session_type": "paper",
    "strategy_config": {
      "strategy_name": "pump_peak_short",
      "direction": "SHORT",
      "signal_detection": {
        "conditions": [
          {"name": "pump_magnitude_pct", "operator": "gte", "value": 5.0}
        ]
      }
    }
  }')

echo "$SESSION_RESPONSE" | jq .

# Extract session_id (assuming envelope format)
SESSION_ID=$(echo "$SESSION_RESPONSE" | jq -r '.data.session_id // .session_id // empty')

if [ -z "$SESSION_ID" ]; then
  echo "ERROR: Failed to start session or extract session_id"
  exit 1
fi

echo "Session ID: $SESSION_ID"
echo ""

# Wait for session to start
sleep 2

# Test 3: Get session state (should be RUNNING)
echo "Test 3: Get session state (should be RUNNING)"
curl -s -X GET "$BASE_URL/api/sessions/$SESSION_ID/state" | jq .
echo ""

# Test 4: Get session transitions (should be empty - placeholder)
echo "Test 4: Get session transitions (should be empty)"
curl -s -X GET "$BASE_URL/api/sessions/$SESSION_ID/transitions" | jq .
echo ""

# Test 5: Verify allowed_transitions for RUNNING state
echo "Test 5: Verify allowed_transitions"
ALLOWED_TRANSITIONS=$(curl -s -X GET "$BASE_URL/api/sessions/$SESSION_ID/state" | jq -r '.allowed_transitions // .data.allowed_transitions')
echo "Allowed transitions from RUNNING: $ALLOWED_TRANSITIONS"
echo ""

# Test 6: Verify instances list (strategy × symbol)
echo "Test 6: Verify instances list"
INSTANCES=$(curl -s -X GET "$BASE_URL/api/sessions/$SESSION_ID/state" | jq -r '.instances // .data.instances')
echo "Active instances:"
echo "$INSTANCES" | jq .
echo ""

# Test 7: Stop session
echo "Test 7: Stopping session..."
curl -s -X POST "$BASE_URL/sessions/stop" \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION_ID\"}" | jq .
echo ""

# Wait for session to stop
sleep 2

# Test 8: Get session state after stop (should be STOPPED)
echo "Test 8: Get session state after stop (should be STOPPED)"
curl -s -X GET "$BASE_URL/api/sessions/$SESSION_ID/state" | jq .
echo ""

echo "=== Test Suite Complete ==="
