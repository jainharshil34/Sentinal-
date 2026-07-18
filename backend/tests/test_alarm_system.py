import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from app.main import app, alarm_states, plant_deployment_modes

client = TestClient(app)

def test_alarm_state_and_muting_flows():
    # 1. Reset alarm state and set live mode
    plant_deployment_modes["Plant-A"] = "live"
    for p_id in alarm_states:
        alarm_states[p_id]["local_alerts_active"].clear()
        alarm_states[p_id]["acknowledged_local_alerts"].clear()
        alarm_states[p_id]["facility_evacuation_active"] = False
        alarm_states[p_id]["last_triggered_by_flag_id"] = None
        alarm_states[p_id]["confirmation_log"].clear()
        
    # 2. Get alarm state
    response = client.get("/api/alarm-state?plant_id=Plant-A")
    assert response.status_code == 200
    state = response.json()
    assert state["facility_evacuation_active"] is False
    assert len(state["local_alerts_active"]) == 0
    assert len(state["acknowledged_local_alerts"]) == 0
    
    # 3. Simulate local alert activation manually
    alarm_states["Plant-A"]["local_alerts_active"].append("Zone-A")
    
    # Acknowledge local alert
    ack_res = client.post("/api/alarm-state/acknowledge-local", json={
        "zone": "Zone-A",
        "plant_id": "Plant-A"
    })
    assert ack_res.status_code == 200
    state2 = ack_res.json()["alarm_state"]
    assert "Zone-A" not in state2["local_alerts_active"]
    assert "Zone-A" in state2["acknowledged_local_alerts"]
    
    # 4. Confirm evacuation
    confirm_res = client.post("/api/alarm-state/confirm-evacuation", json={
        "flag_id": "RULE_HOT_WORK_NEAR_GAS_SPIKE_Zone-A_12345",
        "confirmed_by_role": "Safety Officer",
        "plant_id": "Plant-A"
    })
    assert confirm_res.status_code == 200
    state3 = confirm_res.json()["alarm_state"]
    assert state3["facility_evacuation_active"] is True
    assert len(state3["confirmation_log"]) == 1
    assert state3["confirmation_log"][0]["confirmed_by_role"] == "Safety Officer"
    assert state3["confirmation_log"][0]["flag_id"] == "RULE_HOT_WORK_NEAR_GAS_SPIKE_Zone-A_12345"
    
    # 5. Check Emergency Response stage is advanced to Facility Evacuation Active
    er_res = client.get("/api/emergency-response/Zone-A?plant_id=Plant-A")
    assert er_res.status_code == 200
    er_data = er_res.json()
    assert er_data["active"] is True
    assert er_data["current_stage"] == "Facility Evacuation Active"
    assert any(step["name"] == "Facility Evacuation Active" for step in er_data["steps"])
