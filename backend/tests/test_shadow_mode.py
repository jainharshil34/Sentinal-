import pytest
from fastapi.testclient import TestClient
from app.main import app, plant_deployment_modes, active_tier3_protocols, active_tier3_rules

client = TestClient(app)

def test_shadow_mode_flow_and_graduation():
    # Setup baseline modes
    plant_deployment_modes["Plant-A"] = "shadow"
    active_tier3_protocols.clear()
    active_tier3_rules.clear()

    # 1. Verify Plant-A deployment status starts in shadow
    status_res = client.get("/api/deployment-status?plant_id=Plant-A")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["current_mode"] == "shadow"
    assert status_data["graduation_eligible"] is True  # Pre-seeded logs: 56 logs, 91.1% TPR
    assert status_data["shadow_predictions_count"] >= 20
    
    # 2. Inject Scenario 1 (normally triggers Tier 3 in Zone-A)
    inj_res = client.post("/api/simulation/inject?scenario=scenario_1")
    assert inj_res.status_code == 200

    # 3. Call risk assessment in shadow mode
    assessment_res = client.get("/api/risk-assessment?plant_id=Plant-A")
    assert assessment_res.status_code == 200
    assessment_data = assessment_res.json()
    
    assert assessment_data["tier"] == 3
    assert assessment_data["deployment_mode"] == "shadow"
    for rule in assessment_data["triggered_rules"]:
        assert rule["shadow"] is True

    # Confirm emergency response sequence was NOT triggered
    assert "Plant-A_Zone-A" not in active_tier3_protocols

    # 4. Promote to Live Mode
    promote_payload = {
        "plant_id": "Plant-A",
        "mode": "live"
    }
    promote_res = client.post("/api/deployment-mode", json=promote_payload)
    assert promote_res.status_code == 200
    assert promote_res.json()["mode"] == "live"

    # Confirm mode update
    status_res_live = client.get("/api/deployment-status?plant_id=Plant-A")
    assert status_res_live.json()["current_mode"] == "live"

    # 5. Call risk assessment in live mode
    assessment_res_live = client.get("/api/risk-assessment?plant_id=Plant-A")
    assert assessment_res_live.status_code == 200
    
    # Confirm emergency response sequence was triggered in live mode
    assert "Plant-A_Zone-A" in active_tier3_protocols
