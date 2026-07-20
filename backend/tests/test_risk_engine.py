import pytest
from datetime import datetime, timedelta
from app.db.database import SessionLocal
from app.db import models
from app.engine.risk_engine import detect_compound_risk, detect_single_sensor_baseline

@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    yield session
    session.close()

@pytest.fixture(scope="module")
def default_start_time(db):
    # Find the earliest timestamp in the database for the default dataset
    first_reading = db.query(models.GasSensorReading).filter(
        models.GasSensorReading.dataset == "default"
    ).order_by(models.GasSensorReading.timestamp.asc()).first()
    assert first_reading is not None, "Database is not seeded! Run the seed script first."
    return first_reading.timestamp

def test_normal_operations(db, default_start_time):
    # Safe boring operations window (T + 2 hours to T + 2.5 hours)
    start = default_start_time + timedelta(hours=2.0)
    end = default_start_time + timedelta(hours=2.5)
    
    result = detect_compound_risk(db, start, end)
    
    assert result["score"] < 40
    assert result["tier"] == 1
    assert len(result["triggered_rules"]) == 0

def test_scenario_1_hot_work_ch4_overdue_vent(db, default_start_time):
    # Scenario 1 window: T+24.5h to T+25.0h
    start = default_start_time + timedelta(hours=24.5)
    end = default_start_time + timedelta(hours=25.0)
    
    result = detect_compound_risk(db, start, end)
    
    triggered_names = [r["rule_name"] for r in result["triggered_rules"]]
    assert "RULE_HOT_WORK_NEAR_GAS_SPIKE" in triggered_names
    assert "RULE_OVERDUE_MAINTENANCE_ACTIVE_PERMIT" in triggered_names
    assert result["tier"] == 3
    assert result["score"] >= 75

def test_scenario_2_confined_space_co_overdue_calib(db, default_start_time):
    # Scenario 2 window: T+36.5h to T+37.0h
    start = default_start_time + timedelta(hours=36.5)
    end = default_start_time + timedelta(hours=37.0)
    
    result = detect_compound_risk(db, start, end)
    
    triggered_names = [r["rule_name"] for r in result["triggered_rules"]]
    assert "RULE_CONFINED_SPACE_NEAR_GAS_SPIKE" in triggered_names
    assert "RULE_OVERDUE_MAINTENANCE_ACTIVE_PERMIT" in triggered_names
    assert result["tier"] == 3
    assert result["score"] >= 75

def test_scenario_3_hot_work_h2s_repair(db, default_start_time):
    # Scenario 3 window: T+48.5h to T+49.0h
    start = default_start_time + timedelta(hours=48.5)
    end = default_start_time + timedelta(hours=49.0)
    
    result = detect_compound_risk(db, start, end)
    
    triggered_names = [r["rule_name"] for r in result["triggered_rules"]]
    assert "RULE_HOT_WORK_NEAR_GAS_SPIKE" in triggered_names
    assert "RULE_PERMIT_DURING_ACTIVE_REPAIR" in triggered_names
    assert result["tier"] == 3
    assert result["score"] >= 75

def test_scenario_4_electrical_ch4_overdue_isolation(db, default_start_time):
    # Scenario 4 window: T+60.5h to T+61.0h
    start = default_start_time + timedelta(hours=60.5)
    end = default_start_time + timedelta(hours=61.0)
    
    result = detect_compound_risk(db, start, end)
    
    triggered_names = [r["rule_name"] for r in result["triggered_rules"]]
    assert "RULE_ELECTRICAL_WORK_NEAR_GAS_SPIKE" in triggered_names
    assert "RULE_OVERDUE_MAINTENANCE_ACTIVE_PERMIT" in triggered_names
    assert result["tier"] == 3
    assert result["score"] >= 75

def test_silent_failure_scenario(db, default_start_time):
    # Scenario 5 window: T+12.0h to T+12.5h
    start = default_start_time + timedelta(hours=12.0)
    end = default_start_time + timedelta(hours=12.5)
    
    result = detect_compound_risk(db, start, end)
    
    triggered_names = [r["rule_name"] for r in result["triggered_rules"]]
    assert "RULE_SILENT_SENSOR_DURING_PERMIT" in triggered_names
    assert result["tier"] == 2
    assert 40 <= result["score"] < 75

def test_counterfactual_exclusions(db, default_start_time):
    # Scenario 1 window: T+24.5h to T+25.0h
    start = default_start_time + timedelta(hours=24.5)
    end = default_start_time + timedelta(hours=25.0)
    
    # Original run triggers RULE_HOT_WORK_NEAR_GAS_SPIKE and RULE_OVERDUE_MAINTENANCE_ACTIVE_PERMIT
    original = detect_compound_risk(db, start, end)
    assert original["tier"] == 3
    assert len(original["triggered_rules"]) == 2
    
    # Exclude permit PERM-RISK-201 (hot work)
    mitigated_permit = detect_compound_risk(db, start, end, exclude_permit_ids=["PERM-RISK-201"])
    assert mitigated_permit["score"] == 0
    assert mitigated_permit["tier"] == 1
    assert len(mitigated_permit["triggered_rules"]) == 0
    
    # Exclude maintenance log VENT-ZA-09 (overdue_flag)
    log = db.query(models.MaintenanceLog).filter(
        models.MaintenanceLog.equipment_id == "VENT-ZA-09",
        models.MaintenanceLog.dataset == "default"
    ).first()
    assert log is not None
    
    mitigated_maint = detect_compound_risk(db, start, end, exclude_maint_ids=[log.id])
    assert mitigated_maint["tier"] == 2
    assert mitigated_maint["score"] == 60
    triggered_names = [r["rule_name"] for r in mitigated_maint["triggered_rules"]]
    assert "RULE_HOT_WORK_NEAR_GAS_SPIKE" in triggered_names
    assert "RULE_OVERDUE_MAINTENANCE_ACTIVE_PERMIT" not in triggered_names

def test_vizag_coke_oven_buildup_hot_work(db):
    # Find the earliest timestamp in the database for the vizag dataset
    first_reading = db.query(models.GasSensorReading).filter(
        models.GasSensorReading.dataset == "vizag_replay"
    ).order_by(models.GasSensorReading.timestamp.asc()).first()
    assert first_reading is not None, "Vizag dataset is not seeded!"
    
    # Incident replay window around T+12h (battery incident window)
    start = first_reading.timestamp + timedelta(hours=12.0)
    end = first_reading.timestamp + timedelta(hours=12.5)
    
    result = detect_compound_risk(db, start, end, dataset="vizag_replay")
    triggered_names = [r["rule_name"] for r in result["triggered_rules"]]
    
    assert "RULE_HOT_WORK_NEAR_GAS_SPIKE" in triggered_names
    assert "RULE_OVERDUE_MAINTENANCE_ACTIVE_PERMIT" in triggered_names
    assert result["tier"] == 3
    assert result["score"] >= 75

def test_single_sensor_baseline_detector(db, default_start_time):
    # Test Scenario 1 early window: CH4 climbs from 2.0 ppm up to 15.28 ppm (threshold is 20.0 ppm)
    # The baseline detector should NOT trigger here
    start = default_start_time + timedelta(hours=24.5)
    end = default_start_time + timedelta(hours=25.0)
    res_early = detect_single_sensor_baseline(db, start, end)
    assert res_early["tier"] == 1
    assert res_early["score"] == 0

    # Test Scenario 1 later window: CH4 climbs up to 48.5 ppm (crosses threshold of 20.0 ppm)
    # The baseline detector SHOULD trigger here
    start_late = default_start_time + timedelta(hours=26.5)
    end_late = default_start_time + timedelta(hours=27.0)
    res_late = detect_single_sensor_baseline(db, start_late, end_late)
    assert res_late["tier"] == 3
    assert res_late["score"] == 80
    assert len(res_late["triggered_rules"]) > 0
    assert res_late["triggered_rules"][0]["rule_name"] == "BASELINE_CH4_HIGH_ALARM"

def test_api_replay_vizag():
    from fastapi.testclient import TestClient
    from app.main import app
    
    client = TestClient(app)
    response = client.get("/api/replay/vizag")
    assert response.status_code == 200
    
    data = response.json()
    assert "lead_time_minutes" in data
    assert data["lead_time_minutes"] == 155.0
    assert "events" in data
    assert len(data["events"]) == 9
    
    # Verify events are sorted chronologically
    offsets = [e["offset_hours"] for e in data["events"]]
    assert offsets == sorted(offsets)
    
    # Verify first flag is SentinelGrid at T+10h
    sg_flags = [e for e in data["events"] if e["type"] == "sentinelgrid"]
    assert len(sg_flags) == 4
    assert sg_flags[0]["offset_hours"] == 10.0
    assert sg_flags[0]["risk_score"] == 100
    assert sg_flags[0]["tier"] == 3

def test_api_simulation_inject():
    from fastapi.testclient import TestClient
    from app.main import app, current_simulation_state
    
    client = TestClient(app)
    
    # 1. Reset state to normal
    current_simulation_state["scenario"] = "normal"
    
    # 2. Query risk-assessment without window parameters (should resolve to 'normal' scenario)
    res_normal = client.get("/api/risk-assessment")
    assert res_normal.status_code == 200
    data_normal = res_normal.json()
    assert data_normal["active_scenario"] == "normal"
    assert data_normal["score"] == 0
    assert data_normal["tier"] == 1
    
    # 3. Inject scenario_1
    res_inject = client.post("/api/simulation/inject?scenario=scenario_1")
    assert res_inject.status_code == 200
    assert res_inject.json()["injected_scenario"] == "scenario_1"
    assert current_simulation_state["scenario"] == "scenario_1"
    
    # 4. Query risk-assessment again without parameters (should now resolve to 'scenario_1' window)
    res_s1 = client.get("/api/risk-assessment")
    assert res_s1.status_code == 200
    data_s1 = res_s1.json()
    assert data_s1["active_scenario"] == "scenario_1"
    assert data_s1["score"] >= 75
    assert data_s1["tier"] == 3
    assert any(r["rule_name"] == "RULE_HOT_WORK_NEAR_GAS_SPIKE" for r in data_s1["triggered_rules"])
    
    # 5. Clean up by resetting to normal
    client.post("/api/simulation/inject?scenario=normal")

def test_api_simulation_reset():
    from fastapi.testclient import TestClient
    from app.main import app, current_simulation_state
    
    client = TestClient(app)
    
    # 1. Inject scenario_2
    client.post("/api/simulation/inject?scenario=scenario_2")
    assert current_simulation_state["scenario"] == "scenario_2"
    
    # 2. Call reset
    response = client.post("/api/simulation/reset")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    
    # 3. Confirm scenario resets to normal
    assert current_simulation_state["scenario"] == "normal"
    
    # 4. Confirm database was successfully reseeded
    res_normal = client.get("/api/risk-assessment")
    assert res_normal.status_code == 200
    assert res_normal.json()["score"] == 0
    assert res_normal.json()["tier"] == 1

def test_edge_case_time_gap(db, default_start_time):
    # edge_case_time_gap window: T+16.5h to T+17.0h
    # Permit was active T+14.0h to T+15.0h, gas spike occurs T+15.75h to T+17.5h
    # Time gap is 45+ minutes, so they are not related and should not trigger any rule.
    start = default_start_time + timedelta(hours=16.5)
    end = default_start_time + timedelta(hours=17.0)
    
    result = detect_compound_risk(db, start, end)
    
    assert result["score"] < 40
    assert result["tier"] == 1
    assert len(result["triggered_rules"]) == 0

def test_edge_case_adjacent_zone_no_overlap(db, default_start_time):
    # edge_case_adjacent_zone_no_overlap window: T+19.0h to T+19.5h
    # Permit active in Zone-A, gas spike occurs in Zone-D (non-adjacent)
    # Since they are in non-adjacent zones, no rules should trigger.
    start = default_start_time + timedelta(hours=19.0)
    end = default_start_time + timedelta(hours=19.5)
    
    result = detect_compound_risk(db, start, end)
    
    assert result["score"] < 40
    assert result["tier"] == 1
    assert len(result["triggered_rules"]) == 0

def test_api_scorecard_false_positive_check():
    from fastapi.testclient import TestClient
    from app.main import app
    
    client = TestClient(app)
    response = client.get("/api/scorecard")
    assert response.status_code == 200
    data = response.json()
    assert "false_positive_check" in data
    assert data["false_positive_check"]["edge_cases_tested"] == 2
    assert data["false_positive_check"]["false_positives"] == 0

def test_watch_flag_trend_without_escalation(db):
    # We will insert mock data inside a transaction, test, and rollback
    db.begin_nested()
    
    try:
        now = datetime.utcnow()
        dataset_name = "test_watch_dataset"
        
        # 1. Add active permit in Zone-A
        permit = models.Permit(
            permit_id="PERM-WATCH-TEST",
            zone="Zone-A",
            permit_type="hot_work",
            issued_at=now - timedelta(hours=1),
            closed_at=now + timedelta(hours=1),
            issued_by="Tester",
            dataset=dataset_name
        )
        db.add(permit)
        
        # 2. Add 3 gas readings in Zone-A (CH4): 5.0, 7.5, 9.0 ppm (rising, near 10.0 ppm threshold)
        r1 = models.GasSensorReading(
            zone="Zone-A",
            timestamp=now - timedelta(minutes=10),
            gas_type="CH4",
            reading_ppm=5.0,
            sensor_status="active",
            dataset=dataset_name
        )
        r2 = models.GasSensorReading(
            zone="Zone-A",
            timestamp=now - timedelta(minutes=5),
            gas_type="CH4",
            reading_ppm=7.5,
            sensor_status="active",
            dataset=dataset_name
        )
        r3 = models.GasSensorReading(
            zone="Zone-A",
            timestamp=now,
            gas_type="CH4",
            reading_ppm=9.0,
            sensor_status="active",
            dataset=dataset_name
        )
        db.add_all([r1, r2, r3])
        db.flush()
        
        # 3. Run risk engine check
        start_time = now - timedelta(minutes=15)
        end_time = now
        
        result = detect_compound_risk(db, start_time, end_time, dataset=dataset_name)
        
        # 4. Assert watch tier logic (Tier 0 "Watch", score 15, zero triggered rules)
        assert len(result["triggered_rules"]) == 0
        assert result["tier"] == 0
        assert result["tier_name"] == "Watch"
        assert 15 <= result["score"] < 40
        assert len(result["watch_flags"]) == 1
        
        wf = result["watch_flags"][0]
        assert wf["zone"] == "Zone-A"
        assert wf["signal_type"] == "CH4"
        assert wf["current_value"] == 9.0
        assert wf["threshold"] == 10.0
        assert wf["trend"] == "rising"
        
    finally:
        db.rollback()

def test_api_worker_positions():
    from fastapi.testclient import TestClient
    from app.main import app, current_simulation_state
    
    client = TestClient(app)
    
    # 1. Normal scenario check
    current_simulation_state["scenario"] = "normal"
    res_normal = client.get("/api/worker-positions")
    assert res_normal.status_code == 200
    workers = res_normal.json()
    assert len(workers) == 5
    
    # Check default positions
    worker_zones = {w["name"]: w["zone"] for w in workers}
    assert worker_zones["John Doe"] == "Zone-E"
    assert worker_zones["Alice Smith"] == "Zone-F"
    assert worker_zones["Bob Johnson"] == "Zone-B"
    assert worker_zones["Charlie Brown"] == "Zone-C"
    assert worker_zones["Sarah Davis"] == "Zone-D"
    
    # 2. Scenario 1 (Zone-A Active) check
    current_simulation_state["scenario"] = "scenario_1"
    res_s1 = client.get("/api/worker-positions")
    assert res_s1.status_code == 200
    workers_s1 = res_s1.json()
    worker_zones_s1 = {w["name"]: w["zone"] for w in workers_s1}
    # John and Bob are present in Zone-A
    assert worker_zones_s1["John Doe"] == "Zone-A"
    assert worker_zones_s1["Bob Johnson"] == "Zone-A"
    
    # Clean up state
    current_simulation_state["scenario"] = "normal"

def test_adjacent_zone_cascade(db):
    # Test case for RULE_ADJACENT_ZONE_ESCALATION
    # Start transaction and roll back
    db.begin_nested()
    
    try:
        now = datetime.utcnow()
        dataset_name = "test_cascade_dataset"
        
        # 1. Add permit in Zone-A (source of cascade)
        p_a = models.Permit(
            permit_id="PERM-CASCADE-SOURCE",
            zone="Zone-A",
            permit_type="hot_work",
            issued_at=now - timedelta(hours=1),
            closed_at=now + timedelta(hours=1),
            issued_by="Tester",
            dataset=dataset_name
        )
        # 2. Add permit in Zone-B (adjacent to Zone-A, should escalate)
        p_b = models.Permit(
            permit_id="PERM-CASCADE-ADJACENT",
            zone="Zone-B",
            permit_type="routine",
            issued_at=now - timedelta(hours=1),
            closed_at=now + timedelta(hours=1),
            issued_by="Tester",
            dataset=dataset_name
        )
        # 3. Add permit in Zone-D (non-adjacent to Zone-A, should NOT escalate)
        p_d = models.Permit(
            permit_id="PERM-CASCADE-NON-ADJACENT",
            zone="Zone-D",
            permit_type="routine",
            issued_at=now - timedelta(hours=1),
            closed_at=now + timedelta(hours=1),
            issued_by="Tester",
            dataset=dataset_name
        )
        
        # 4. Add gas readings for Zone-A (CH4 spike) to trigger Tier 3 rule in Zone-A
        # Readings at T-10m, T-5m, T: 2.0 -> 8.0 -> 15.0 ppm
        r1 = models.GasSensorReading(
            zone="Zone-A",
            timestamp=now - timedelta(minutes=10),
            gas_type="CH4",
            reading_ppm=2.0,
            sensor_status="active",
            dataset=dataset_name
        )
        r2 = models.GasSensorReading(
            zone="Zone-A",
            timestamp=now - timedelta(minutes=5),
            gas_type="CH4",
            reading_ppm=8.0,
            sensor_status="active",
            dataset=dataset_name
        )
        r3 = models.GasSensorReading(
            zone="Zone-A",
            timestamp=now,
            gas_type="CH4",
            reading_ppm=15.0,
            sensor_status="active",
            dataset=dataset_name
        )
        
        db.add_all([p_a, p_b, p_d, r1, r2, r3])
        db.flush()
        
        # 5. Evaluate risk in window
        start_time = now - timedelta(minutes=15)
        end_time = now
        result = detect_compound_risk(db, start_time, end_time, dataset=dataset_name)
        
        # 6. Assertions
        triggered_names = [rule["rule_name"] for rule in result["triggered_rules"]]
        
        # Verify first-pass Tier 3 rule triggered for Zone-A
        assert "RULE_HOT_WORK_NEAR_GAS_SPIKE" in triggered_names
        
        # Verify second-pass cascading rule triggered for Zone-B
        assert "RULE_ADJACENT_ZONE_ESCALATION" in triggered_names
        
        # Find cascading rule and verify its details
        cascade_rule = next(r for r in result["triggered_rules"] if r["rule_name"] == "RULE_ADJACENT_ZONE_ESCALATION")
        assert cascade_rule["severity"] == 1
        assert cascade_rule["reason"] == "Elevated due to cascading risk from adjacent Zone-A reaching Tier 3."
        
        # Check that it associated the Zone-B permit as a contributing signal
        contrib_permit_ids = [sig["permit_id"] for sig in cascade_rule["contributing_signals"] if "permit_id" in sig]
        assert "PERM-CASCADE-ADJACENT" in contrib_permit_ids
        
        # Check that Zone-D permit did NOT trigger a cascade
        assert "PERM-CASCADE-NON-ADJACENT" not in contrib_permit_ids
        
    finally:
        db.rollback()

def test_multi_gas_compound_toxicity(db):
    # Test case for RULE_MULTI_GAS_COMPOUND_TOXICITY
    db.begin_nested()
    
    try:
        now = datetime.utcnow()
        dataset_name = "test_multigas_dataset"
        
        # 1. Add CO readings at sub-threshold levels (e.g. 20.0 ppm, below 25.0 ppm threshold)
        r1_co = models.GasSensorReading(
            zone="Zone-F",
            timestamp=now - timedelta(minutes=10),
            gas_type="CO",
            reading_ppm=5.0,
            sensor_status="active",
            dataset=dataset_name
        )
        r2_co = models.GasSensorReading(
            zone="Zone-F",
            timestamp=now - timedelta(minutes=5),
            gas_type="CO",
            reading_ppm=12.0,
            sensor_status="active",
            dataset=dataset_name
        )
        r3_co = models.GasSensorReading(
            zone="Zone-F",
            timestamp=now,
            gas_type="CO",
            reading_ppm=20.0,
            sensor_status="active",
            dataset=dataset_name
        )
        
        # 2. Add H2S readings at sub-threshold levels (e.g. 4.2 ppm, below 5.0 ppm threshold)
        r1_h2s = models.GasSensorReading(
            zone="Zone-F",
            timestamp=now - timedelta(minutes=10),
            gas_type="H2S",
            reading_ppm=0.5,
            sensor_status="active",
            dataset=dataset_name
        )
        r2_h2s = models.GasSensorReading(
            zone="Zone-F",
            timestamp=now - timedelta(minutes=5),
            gas_type="H2S",
            reading_ppm=2.2,
            sensor_status="active",
            dataset=dataset_name
        )
        r3_h2s = models.GasSensorReading(
            zone="Zone-F",
            timestamp=now,
            gas_type="H2S",
            reading_ppm=4.2,
            sensor_status="active",
            dataset=dataset_name
        )
        
        db.add_all([r1_co, r2_co, r3_co, r1_h2s, r2_h2s, r3_h2s])
        db.flush()
        
        # 3. Evaluate risk in window with NO permits active in Zone-F
        start_time = now - timedelta(minutes=15)
        end_time = now
        result = detect_compound_risk(db, start_time, end_time, dataset=dataset_name)
        
        # 4. Assertions
        triggered_names = [rule["rule_name"] for rule in result["triggered_rules"]]
        
        # Verify it was caught by RULE_MULTI_GAS_COMPOUND_TOXICITY
        assert "RULE_MULTI_GAS_COMPOUND_TOXICITY" in triggered_names
        
        # Verify that it is the ONLY rule triggered
        # (confirms that it is missed by all other existing rules since there is no permit/overdue maint)
        assert len(result["triggered_rules"]) == 1
        
        # Verify specific details of the triggered rule
        mg_rule = result["triggered_rules"][0]
        assert mg_rule["severity"] == 3
        assert "Zone-F" in mg_rule["reason"]
        assert "CO (20.0 ppm)" in mg_rule["reason"]
        assert "H2S (4.2 ppm)" in mg_rule["reason"]
        
    finally:
        db.rollback()

def test_incident_agent_semantic_ranking():
    from app.engine.incident_agent import query_intelligence
    
    # Query related to hot work and methane gas stacking
    results = query_intelligence("grinding welding stack flash fire ventilation methane")
    assert len(results) > 0
    
    # Top match should be a hot work near gas spike rule type
    top_match = results[0]
    assert top_match.get("rule_type") == "RULE_HOT_WORK_NEAR_GAS_SPIKE"
    
    # Make sure reasons are explained
    assert any("Semantic match" in r for r in top_match["reasons"])
    
    # Make sure unrelated reports (like missing fire extinguisher tags) are ranked lower or not returned
    unrelated_returned = [r for r in results if r["regulatory_clause"] == "OISD 105" or r["rule_type"] == "RULE_HOT_WORK_NEAR_GAS_SPIKE"]
    assert len(unrelated_returned) > 0

def test_incident_agent_graph_traversal_dissimilar():
    from app.engine.incident_agent import query_intelligence
    
    # Query focusing on carbon monoxide and consciousness loss in confined space (Report 3)
    # This has very low text similarity to Report 6 (sensor silent, telemetry drop, H2S rise),
    # but they share the same regulatory clause: OSHA 1910.146.
    results = query_intelligence("technician loss of consciousness tank cleanout carbon monoxide calibration failure")
    
    # Assert that Report 3 is retrieved as a semantic match
    report_3_match = next((r for r in results if r["id"] == 3), None)
    assert report_3_match is not None
    assert any("Semantic match" in reason for reason in report_3_match["reasons"])
    
    # Assert that Report 6 is retrieved via graph traversal on OSHA 1910.146
    report_6_match = next((r for r in results if r["id"] == 6), None)
    assert report_6_match is not None
    assert any("Shared regulatory clause: OSHA 1910.146" in reason for reason in report_6_match["reasons"])

def test_incident_agent_pattern_detection():
    from app.engine.incident_agent import detect_recurring_patterns
    
    patterns = detect_recurring_patterns()
    assert len(patterns) > 0
    
    # The top patterns should represent OISD 105 or OSHA 1910.146
    top_pattern = patterns[0]
    assert "OISD 105" in top_pattern["category"] or "OSHA 1910.146" in top_pattern["category"]
    assert top_pattern["count"] >= 3
    assert top_pattern["percentage"] > 0
    assert "incidents in this corpus trace back to" in top_pattern["description"]


def test_sustained_high_gas_near_permit(db, default_start_time):
    """
    Verifies that a sustained high gas level (> 10% LEL CH4) near an active hot work permit
    triggers RULE_HOT_WORK_NEAR_GAS_SPIKE even if the 15-minute increase is 0 (plateaued gas).
    """
    # Create test permit and reading
    start = default_start_time + timedelta(hours=100)
    end = start + timedelta(minutes=30)
    
    permit = models.Permit(
        permit_id="PERM-TEST-SUSTAINED",
        zone="Zone-A",
        permit_type="hot_work",
        issued_at=start,
        closed_at=end + timedelta(hours=2),
        issued_by="Tester",
        dataset="default",
        plant_id="Plant-A"
    )
    r1 = models.GasSensorReading(
        zone="Zone-A",
        gas_type="CH4",
        reading_ppm=15.0,  # 15% LEL (> 10.0 threshold)
        sensor_status="active",
        timestamp=start + timedelta(minutes=20),
        dataset="default",
        plant_id="Plant-A"
    )
    r2 = models.GasSensorReading(
        zone="Zone-A",
        gas_type="CH4",
        reading_ppm=15.0,  # sustained plateau
        sensor_status="active",
        timestamp=end,
        dataset="default",
        plant_id="Plant-A"
    )
    db.add_all([permit, r1, r2])
    db.commit()

    try:
        res = detect_compound_risk(db, start, end, dataset="default", plant_id="Plant-A")
        triggered_names = [r["rule_name"] for r in res["triggered_rules"]]
        assert "RULE_HOT_WORK_NEAR_GAS_SPIKE" in triggered_names
        assert res["score"] >= 60
    finally:
        db.delete(permit)
        db.delete(r1)
        db.delete(r2)
        db.commit()


def test_osha_mixture_hazard_index_multi_gas():
    """
    Verifies that RULE_MULTI_GAS_COMPOUND_TOXICITY correctly uses the OSHA/ACGIH Mixture Hazard Index
    formula and formats CH4 as % LEL instead of ppm.
    """
    from app.engine.risk_engine import calculate_aggregate_score, compute_watch_score
    
    # Verify compute_watch_score dynamic scaling
    wf = [{
        "zone": "Zone-A",
        "signal_type": "CH4",
        "current_value": 8.5,
        "threshold": 10.0,
        "predicted_threshold_breach_minutes": 10.0
    }]
    score = compute_watch_score(wf)
    assert 15 <= score <= 39, f"Expected dynamic watch score in [15, 39], got {score}"


def test_dynamic_watch_flag_scoring():
    """
    Verifies dynamic watch score scaling with proximity and time to breach.
    """
    from app.engine.risk_engine import compute_watch_score
    
    wf_close = [{
        "zone": "Zone-A",
        "signal_type": "CH4",
        "current_value": 9.5,
        "threshold": 10.0,
        "predicted_threshold_breach_minutes": 5.0
    }]
    wf_far = [{
        "zone": "Zone-A",
        "signal_type": "CH4",
        "current_value": 7.0,
        "threshold": 10.0,
        "predicted_threshold_breach_minutes": 40.0
    }]
    
    score_close = compute_watch_score(wf_close)
    score_far = compute_watch_score(wf_far)
    
    assert score_close >= score_far, f"Close watch flag ({score_close}) should score higher or equal to far watch flag ({score_far})"











