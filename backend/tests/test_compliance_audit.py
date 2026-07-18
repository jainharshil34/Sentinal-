import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_compliance_audit_analytics():
    response = client.get("/api/compliance-audit")
    assert response.status_code == 200
    data = response.json()
    
    # 1. Verify all required keys are present
    assert "total_permits_issued" in data
    assert "permits_with_no_flagged_risk" in data
    assert "compliance_rate" in data
    assert "clause_counts" in data
    assert "trend" in data
    assert "summary" in data
    
    # 2. Verify permit compliance rate calculations (14 permits, 5 flagged, 9 compliant = 64.3%)
    assert data["total_permits_issued"] == 14
    assert data["permits_with_no_flagged_risk"] == 9
    assert data["compliance_rate"] == 64.3
    
    # 3. Verify clause counts structure and top category selection
    clause_counts = data["clause_counts"]
    assert len(clause_counts) == 5
    
    # Top clause should be OISD Standard 105 (Section 5.2) with count 2
    top_clause = max(clause_counts, key=lambda x: x["count"])
    assert top_clause["clause"] == "OISD Standard 105 (Section 5.2)"
    assert top_clause["count"] == 2
    
    # 4. Verify compliance trend periods
    assert len(data["trend"]) == 6
    assert data["trend"][0]["period"] == "Week 1"
    assert data["trend"][5]["period"] == "Week 6"
    
    # 5. Verify the narration summary sentence
    summary_sentence = data["summary"]
    assert "2 of 6 compound-risk events this period relate to OISD Standard 105 (Section 5.2) controls" in summary_sentence
    assert "recommend reviewing OISD Standard 105 (Section 5.2) compliance training" in summary_sentence
