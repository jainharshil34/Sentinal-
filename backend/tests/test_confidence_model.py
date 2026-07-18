import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_model_performance_endpoint():
    response = client.get("/api/model-performance")
    assert response.status_code == 200
    data = response.json()
    assert "precision" in data
    assert "recall" in data
    assert "feature_importances" in data
    
    assert isinstance(data["precision"], float)
    assert isinstance(data["recall"], float)
    assert isinstance(data["feature_importances"], list)
    
    # Verify the structure of feature importances
    if len(data["feature_importances"]) > 0:
        feat = data["feature_importances"][0]
        assert "feature" in feat
        assert "importance" in feat
        assert "direction" in feat

def test_model_retrain_endpoint():
    response = client.post("/api/model-performance/retrain")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "precision" in data
    assert "recall" in data
    assert "feature_importances" in data
