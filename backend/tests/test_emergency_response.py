import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from app.main import app, active_tier3_protocols, active_tier3_rules

client = TestClient(app)

def test_emergency_response_flow_and_simulation():
    # Set Plant-A to live mode to allow emergency trigger execution
    from app.main import plant_deployment_modes
    plant_deployment_modes["Plant-A"] = "live"

    # 1. Inject scenario_1 to trigger Tier 3 risk assessment
    response = client.post("/api/simulation/inject?scenario=scenario_1")
    assert response.status_code == 200
    
    # Clear any leftover state first
    active_tier3_protocols.clear()
    active_tier3_rules.clear()
    
    # 2. Query risk-assessment to trigger the emergency auto-trigger on the backend
    assessment_res = client.get("/api/risk-assessment")
    assert assessment_res.status_code == 200
    assert assessment_res.json()["tier"] == 3
    
    # Verify that Zone-A was auto-registered in active protocols
    assert "Zone-A" in active_tier3_protocols
    assert "Zone-A" in active_tier3_rules
    assert len(active_tier3_rules["Zone-A"]) > 0
    
    # 3. Test stage calculations based on mocked trigger offsets
    now = datetime.utcnow()
    
    # CASE A: Immediate (0 seconds elapsed)
    active_tier3_protocols["Zone-A"] = now
    res = client.get("/api/emergency-response/Zone-A")
    assert res.status_code == 200
    data = res.json()
    assert data["active"] is True
    assert data["current_stage"] == "Evacuation Zone Marked"
    assert data["steps"][0]["reached"] is True
    assert data["steps"][1]["reached"] is False
    assert data["preliminary_report"] is None
    
    # CASE B: +6 seconds elapsed (Response Team Alerted)
    active_tier3_protocols["Zone-A"] = now - timedelta(seconds=6)
    res = client.get("/api/emergency-response/Zone-A")
    data = res.json()
    assert data["current_stage"] == "Response Team Alerted"
    assert data["steps"][0]["reached"] is True
    assert data["steps"][1]["reached"] is True
    assert data["steps"][2]["reached"] is False
    assert data["preliminary_report"] is None
    
    # CASE C: +9 seconds elapsed (Sensor Evidence Preserved)
    active_tier3_protocols["Zone-A"] = now - timedelta(seconds=9)
    res = client.get("/api/emergency-response/Zone-A")
    data = res.json()
    assert data["current_stage"] == "Sensor Evidence Preserved"
    assert data["steps"][2]["reached"] is True
    assert data["steps"][3]["reached"] is False
    assert data["preliminary_report"] is None
    
    # CASE D: +13 seconds elapsed (Preliminary Incident Report Drafted)
    active_tier3_protocols["Zone-A"] = now - timedelta(seconds=13)
    res = client.get("/api/emergency-response/Zone-A")
    data = res.json()
    assert data["current_stage"] == "Preliminary Incident Report Drafted"
    assert data["steps"][3]["reached"] is True
    assert data["preliminary_report"] is not None
    assert "RULE_HOT_WORK_NEAR_GAS_SPIKE" in data["preliminary_report"]["rules_fired"]
    assert "OISD Standard 105" in data["preliminary_report"]["applicable_clause"]
    
    # 4. Test state clearing on Reset
    reset_res = client.post("/api/simulation/reset")
    assert reset_res.status_code == 200
    assert len(active_tier3_protocols) == 0
    assert len(active_tier3_rules) == 0
    
    # Verify that querying emergency response now reports inactive
    res_inactive = client.get("/api/emergency-response/Zone-A")
    assert res_inactive.status_code == 200
    assert res_inactive.json()["active"] is False
