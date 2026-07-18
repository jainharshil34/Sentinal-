import pytest
import numpy as np
from app.engine.incident_agent import query_intelligence, detect_recurring_patterns, get_model, get_embeddings, cosine_similarity, INCIDENT_CORPUS

def test_query_hot_work_near_gas():
    # 1. Query about hot-work-near-gas
    query = "grinding and welding with rising methane levels during hot work"
    results = query_intelligence(query, top_k=5)
    
    # 2. Verify we returned results
    assert len(results) > 0
    
    # 3. Check that the top reports are RULE_HOT_WORK_NEAR_GAS_SPIKE
    top_result_rule = results[0]["rule_type"]
    assert top_result_rule == "RULE_HOT_WORK_NEAR_GAS_SPIKE"
    
    # 4. Check that unrelated reports (like clerical errors or routine safety walks) are not ranked above them
    unrelated_ids = [14, 15, 16, 17] # clerical, compliance training, sensor calibration, routine walk
    for idx, r in enumerate(results):
        if r["id"] in unrelated_ids:
            # Unrelated IDs must be ranked lower than the relevant ones
            assert idx > 1

def test_graph_traversal_dissimilar_surfaced():
    # Query related to tank cleanout CO poisoning (Report 3 and 4)
    query = "tank cleanout technicians lost consciousness CO carbon monoxide"
    
    model = get_model()
    embeddings = get_embeddings()
    query_emb = model.encode(query, convert_to_numpy=True)
    sims = cosine_similarity(query_emb, embeddings)
    
    # Sort all reports purely by semantic similarity
    semantic_sorted_indices = np.argsort(sims)[::-1]
    semantic_sorted_ids = [INCIDENT_CORPUS[int(idx)]["id"] for idx in semantic_sorted_indices]
    
    # Report 6 is the silent sensor / telemetry dropped incident.
    # It shares OSHA 1910.146 with Report 3, but is textually very different.
    report_6_id = 6
    
    # Verify that Report 6 is NOT in the top 3 semantically (it would be missed by naive top-3 text search)
    assert report_6_id not in semantic_sorted_ids[:3]
    
    # Now run the intelligent search that includes Layer B graph traversal
    results = query_intelligence(query, top_k=8)
    result_ids = [r["id"] for r in results]
    
    # Verify that Report 6 is successfully returned in the top-8 results (pushed down slightly due to new high-quality real incidents)
    assert report_6_id in result_ids
    
    # Find Report 6 in results and check reasons
    r6_match = next(r for r in results if r["id"] == report_6_id)
    assert "Shared regulatory clause: OSHA 1910.146" in r6_match["reasons"]
    
def test_pattern_detection():
    patterns = detect_recurring_patterns()
    
    # Verify we returned patterns
    assert len(patterns) > 0
    
    # Verify the top pattern traces back to OISD 105 or OSHA 1910.146
    top_pattern = patterns[0]
    assert "OISD 105" in top_pattern["category"] or "OSHA 1910.146" in top_pattern["category"]
    assert top_pattern["count"] >= 5
    assert top_pattern["type"] in ["clause", "rule"]

def test_dynamic_incident_history_rag_and_patterns():
    from app.db.database import SessionLocal
    from app.db import models
    from fastapi.testclient import TestClient
    from app.main import app
    
    client = TestClient(app)
    
    # 1. Fetch current patterns count for 'Clause: OISD 105'
    patterns_before = detect_recurring_patterns()
    clause_before_count = next((p["count"] for p in patterns_before if "OISD 105" in p["category"]), 0)
    
    # 2. Add a new incident log via API
    payload = {
        "zone": "Zone-F",
        "category": "injury",
        "contributing_factors": "A technician suffered chemical inhalation during routine inspection at the switchboard of Zone-F violating safety controls.",
        "related_rule_type": "RULE_MULTI_GAS_COMPOUND_TOXICITY",
        "regulatory_clause": "OISD 105",
        "resolution_notes": "Recalibrated and reinforced switchboard safety locks.",
        "logged_by_role": "Safety Officer",
        "severity_level": "lost-time injury"
    }
    
    res = client.post("/api/incident-history", json=payload)
    assert res.status_code == 200
    res_data = res.json()
    assert res_data["id"] is not None
    
    # 3. Verify patterns updated
    patterns_after = detect_recurring_patterns()
    clause_after_count = next((p["count"] for p in patterns_after if "OISD 105" in p["category"]), 0)
    assert clause_after_count == clause_before_count + 1
    
    # 4. Verify RAG query intelligence retrieves it
    query_results = query_intelligence("chemical inhalation switchboard in Zone-F")
    assert len(query_results) > 0
    top_match = query_results[0]
    assert "chemical inhalation" in top_match["text"]
    assert top_match["zone"] == "Zone-F"
    
    # Clean up from DB
    db = SessionLocal()
    db.query(models.IncidentHistory).filter(models.IncidentHistory.id == res_data["id"]).delete()
    db.commit()
    
    # Force rebuild cache after deleting test log
    from app.engine.incident_agent import reset_incident_cache
    reset_incident_cache()
    db.close()

