import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_roi_calculator_math():
    # Setup test input parameters
    payload = {
        "plant_size": "medium",
        "num_zones": 6,
        "historical_incidents_per_year": 2.0,
        "avg_incident_cost": 50000000.0  # ₹5 Crore
    }
    
    # 1. Test medium plant calculation
    response = client.post("/api/roi-calculator", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["estimated_annual_risk_exposure"] == 100000000.0  # ₹10 Crore
    assert data["sentinelgrid_detection_rate"] == 100.0
    assert data["estimated_incidents_prevented_per_year"] == 2.0
    assert data["estimated_annual_savings"] == 100000000.0  # ₹10 Crore
    assert data["net_annual_savings"] == 98800000.0  # ₹9.88 Crore (₹10 Crore - ₹12 Lakh SaaS cost)
    assert data["payback_period_months"] == 0.1  # (12,00,000 / 10,00,00,000) * 12 = 0.144 -> 0.1 rounded
    assert data["saas_cost_annual"] == 1200000.0  # ₹12 Lakh
    
    # 2. Test small plant calculation (SaaS cost = ₹5 Lakh)
    payload["plant_size"] = "small"
    response_small = client.post("/api/roi-calculator", json=payload)
    data_small = response_small.json()
    assert data_small["saas_cost_annual"] == 500000.0
    assert data_small["net_annual_savings"] == 99500000.0
    assert data_small["payback_period_months"] == 0.1  # (5,00,000 / 10,00,00,000) * 12 = 0.06 -> 0.1 rounded
    
    # 3. Test large plant calculation (SaaS cost = ₹25 Lakh)
    payload["plant_size"] = "large"
    response_large = client.post("/api/roi-calculator", json=payload)
    data_large = response_large.json()
    assert data_large["saas_cost_annual"] == 2500000.0
    assert data_large["net_annual_savings"] == 97500000.0
    assert data_large["payback_period_months"] == 0.3  # (25,00,000 / 10,00,00,000) * 12 = 0.3
