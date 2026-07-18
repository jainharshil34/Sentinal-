import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.database import get_db
from app.db import models

client = TestClient(app)

def test_rule_confidence_endpoint_and_flow():
    # 1. Fetch initial confidence stats
    response = client.get("/api/rule-confidence")
    assert response.status_code == 200
    data = response.json()
    
    # Pre-seeded logs should cause OVERDUE_MAINTENANCE to have adjusted severity weight of 1.0 (from 2.0 default)
    overdue_rule = next(r for r in data if r["rule_name"] == "RULE_OVERDUE_MAINTENANCE_ACTIVE_PERMIT")
    assert overdue_rule["original_weight"] == 2.0
    assert overdue_rule["current_weight"] == 1.0
    assert overdue_rule["false_alarm_count"] == 4
    assert overdue_rule["confirmed_count"] == 1
    assert overdue_rule["tpr"] == 20.0
    assert len(overdue_rule["adjustments"]) > 0

    # 2. Submit a new verdict (POST /api/feedback/{flag_id})
    feedback_payload = {
        "rule_name": "RULE_HOT_WORK_NEAR_GAS_SPIKE",
        "verdict": "False Alarm"
    }
    flag_id = "test_flag_hot_work_12345"
    post_res = client.post(f"/api/feedback/{flag_id}", json=feedback_payload)
    assert post_res.status_code == 200
    assert post_res.json()["status"] == "success"
    
    # 3. Query confidence stats again and assert increments
    res2 = client.get("/api/rule-confidence")
    data2 = res2.json()
    hotwork_rule = next(r for r in data2 if r["rule_name"] == "RULE_HOT_WORK_NEAR_GAS_SPIKE")
    # Pre-seeded had 5 confirmed, 1 false alarm. Now 2 false alarms.
    assert hotwork_rule["false_alarm_count"] == 2
    assert hotwork_rule["total_count"] == 7
    # Since false_alarm_count is 2 (below 3 threshold), current_weight is still 3.0
    assert hotwork_rule["current_weight"] == 3.0
