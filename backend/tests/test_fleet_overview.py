import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_fleet_overview_scenarios():
    # 1. Start with normal scenario
    client.post("/api/simulation/inject?scenario=normal")
    response = client.get("/api/fleet-overview")
    assert response.status_code == 200
    data = response.json()
    
    assert len(data) == 3
    for plant in data:
        assert plant["plant_id"] in ["Plant-A", "Plant-B", "Plant-C"]
        assert plant["tier"] == 1  # Nominal safe status
        assert plant["active_flags_count"] == 0
        assert len(plant["cross_plant_patterns"]) == 0
        
    # 2. Inject Scenario 1 (which causes hot work violations on all plants at shifted windows)
    client.post("/api/simulation/inject?scenario=scenario_1")
    response_s1 = client.get("/api/fleet-overview")
    assert response_s1.status_code == 200
    data_s1 = response_s1.json()
    
    plant_a = next(p for p in data_s1 if p["plant_id"] == "Plant-A")
    plant_b = next(p for p in data_s1 if p["plant_id"] == "Plant-B")
    plant_c = next(p for p in data_s1 if p["plant_id"] == "Plant-C")
    
    # All plants should show Tier 3 risks because their shifted windows fall inside their respective Scenario 1 timelines
    assert plant_a["tier"] == 3
    assert plant_b["tier"] == 3
    assert plant_c["tier"] == 3
    
    # Plant-A should have hot work near gas spike active, and surface cross-plant learning patterns from Plant-C and Plant-B
    assert plant_a["active_flags_count"] > 0
    patterns = plant_a["cross_plant_patterns"]
    assert len(patterns) > 0
    
    # Verify that the pattern matches reference other plants and have correct wording
    top_pattern = patterns[0]
    assert top_pattern["other_plant_id"] in ["Plant-B", "Plant-C"]
    assert "A similar compound-risk pattern occurred at" in top_pattern["summary"]
