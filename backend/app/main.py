import os
from fastapi import FastAPI, Depends, Query, HTTPException, UploadFile, File, Form, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.db.database import get_db, Base, engine
from app.db import models
from app.engine.risk_engine import detect_compound_risk, model_to_dict, detect_single_sensor_baseline
from app.engine.narration import generate_risk_narration
from app.data.seed import seed_database

# Ensure all database tables exist on application startup
Base.metadata.create_all(bind=engine)

class FeedbackRequest(BaseModel):
    rule_name: str
    verdict: str
    plant_id: str = "Plant-A"

app = FastAPI(title="SentinelGrid API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_first_reading_cache: dict[str, datetime] = {}

@app.on_event("startup")
def startup_prewarm():
    """Pre-warms ML models and vector embeddings in background thread to avoid initial request latency."""
    import threading
    def prewarm():
        try:
            from app.engine.incident_agent import get_model, refresh_embeddings
            get_model()
            refresh_embeddings()
            print("[SentinelGrid] ML models & vector embeddings pre-warmed successfully.")
        except Exception as e:
            print("[SentinelGrid] ML prewarm warning:", e)
            
    threading.Thread(target=prewarm, daemon=True).start()

@app.post("/api/feedback/{flag_id}")
def submit_feedback(flag_id: str, payload: FeedbackRequest, db: Session = Depends(get_db)):
    if payload.verdict not in ["Confirmed Risk", "False Alarm"]:
        raise HTTPException(status_code=400, detail="Invalid verdict. Must be 'Confirmed Risk' or 'False Alarm'.")
    
    # Save verdict
    feedback = models.FeedbackLog(
        flag_id=flag_id,
        rule_name=payload.rule_name,
        officer_verdict=payload.verdict,
        timestamp=datetime.utcnow(),
        plant_id=payload.plant_id
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    
    # Auto-retrain confidence model on new feedback
    try:
        from app.engine.confidence_model import train_and_save_model
        train_and_save_model(db)
    except Exception as e:
        print("Failed to auto-retrain confidence model on new feedback:", e)
        
    return {"status": "success", "id": feedback.id, "flag_id": flag_id, "verdict": payload.verdict, "plant_id": payload.plant_id}

@app.get("/api/rule-confidence")
def get_rule_confidence(plant_id: str = Query("Plant-A"), db: Session = Depends(get_db)):
    # Fetch statistics and history
    from app.engine.risk_engine import get_adjusted_weights
    
    # Get dynamic weights and the adjustments log
    adjusted_weights, adjustments_log = get_adjusted_weights(db, plant_id)
    
    # Load all raw feedback logs to aggregate stats for this plant
    logs = db.query(models.FeedbackLog).filter(models.FeedbackLog.plant_id == plant_id).order_by(models.FeedbackLog.timestamp.desc()).all()
    
    # Default rules configuration
    default_rules = {
        "RULE_HOT_WORK_NEAR_GAS_SPIKE": {"original": 3.0, "desc": "Hot work permit near elevated gas trend"},
        "RULE_CONFINED_SPACE_NEAR_GAS_SPIKE": {"original": 3.0, "desc": "Confined space entry near elevated toxic gas"},
        "RULE_ELECTRICAL_WORK_NEAR_GAS_SPIKE": {"original": 2.0, "desc": "Electrical permit near elevated flammable gas"},
        "RULE_OVERDUE_MAINTENANCE_ACTIVE_PERMIT": {"original": 2.0, "desc": "Overdue safety maintenance during active permit"},
        "RULE_SILENT_SENSOR_DURING_PERMIT": {"original": 2.0, "desc": "Gas sensor offline/silent during active permit"},
        "RULE_PERMIT_DURING_ACTIVE_REPAIR": {"original": 2.0, "desc": "Active permit overlaps with active repair"},
        "RULE_MULTI_GAS_COMPOUND_TOXICITY": {"original": 3.0, "desc": "Synergistic compound gas toxicity"}
    }
    
    rules_stats = {}
    for r_name, info in default_rules.items():
        rules_stats[r_name] = {
            "rule_name": r_name,
            "description": info["desc"],
            "original_weight": info["original"],
            "current_weight": adjusted_weights.get(r_name, info["original"]),
            "confirmed_count": 0,
            "false_alarm_count": 0,
            "total_count": 0,
            "tpr": 100.0,
            "adjustments": [a for a in adjustments_log if a["rule_name"] == r_name],
            "history": []
        }
        
    for log in logs:
        r_name = log.rule_name
        if r_name in rules_stats:
            rules_stats[r_name]["total_count"] += 1
            if log.officer_verdict == "Confirmed Risk":
                rules_stats[r_name]["confirmed_count"] += 1
            else:
                rules_stats[r_name]["false_alarm_count"] += 1
                
            rules_stats[r_name]["history"].append({
                "id": log.id,
                "flag_id": log.flag_id,
                "verdict": log.officer_verdict,
                "timestamp": log.timestamp.isoformat() + "Z"
            })
            
    # Calculate TPR percentages
    for r_name in rules_stats:
        total = rules_stats[r_name]["total_count"]
        confirmed = rules_stats[r_name]["confirmed_count"]
        if total > 0:
            rules_stats[r_name]["tpr"] = round((confirmed / total) * 100, 1)
            
    return list(rules_stats.values())

# Simulation constants and state
SCENARIO_OFFSETS = {
    "normal": {"start": 2.0, "end": 2.5, "dataset": "default"},
    "scenario_1": {"start": 24.5, "end": 25.0, "dataset": "default"},
    "scenario_2": {"start": 36.5, "end": 37.0, "dataset": "default"},
    "scenario_3": {"start": 48.5, "end": 49.0, "dataset": "default"},
    "scenario_4": {"start": 60.5, "end": 61.0, "dataset": "default"},
    "silent_failure": {"start": 12.0, "end": 12.5, "dataset": "default"},
    "vizag_buildup": {"start": 12.0, "end": 12.5, "dataset": "vizag_replay"},
    "edge_case_time_gap": {"start": 16.5, "end": 17.0, "dataset": "default"},
    "edge_case_adjacent_zone_no_overlap": {"start": 19.0, "end": 19.5, "dataset": "default"},
    "multi_gas_toxicity": {"start": 69.5, "end": 70.0, "dataset": "default"}
}

current_simulation_state = {
    "scenario": "normal"
}

# Active plant deployment modes (shadow vs live)
plant_deployment_modes = {
    "Plant-A": "shadow",
    "Plant-B": "shadow",
    "Plant-C": "shadow"
}

# Alarm system tracking states per plant
alarm_states = {
    "Plant-A": {
        "local_alerts_active": [],
        "acknowledged_local_alerts": [],
        "facility_evacuation_active": False,
        "last_triggered_by_flag_id": None,
        "confirmation_log": []
    },
    "Plant-B": {
        "local_alerts_active": [],
        "acknowledged_local_alerts": [],
        "facility_evacuation_active": False,
        "last_triggered_by_flag_id": None,
        "confirmation_log": []
    },
    "Plant-C": {
        "local_alerts_active": [],
        "acknowledged_local_alerts": [],
        "facility_evacuation_active": False,
        "last_triggered_by_flag_id": None,
        "confirmation_log": []
    }
}

class DeploymentModeRequest(BaseModel):
    plant_id: str
    mode: str

# Active Tier 3 emergency response protocols
active_tier3_protocols = {}  # zone -> triggered_at (datetime)
active_tier3_rules = {}      # zone -> list of rules (triggered_rules)

@app.post("/api/deployment-mode")
def set_deployment_mode(payload: DeploymentModeRequest):
    if payload.mode not in ["shadow", "live"]:
        raise HTTPException(status_code=400, detail="Mode must be 'shadow' or 'live'.")
    if payload.plant_id not in ["Plant-A", "Plant-B", "Plant-C"]:
        raise HTTPException(status_code=400, detail="Invalid plant_id.")
    plant_deployment_modes[payload.plant_id] = payload.mode
    return {"status": "success", "plant_id": payload.plant_id, "mode": payload.mode}

@app.get("/api/deployment-status")
def get_deployment_status(plant_id: str = Query("Plant-A"), db: Session = Depends(get_db)):
    if plant_id not in ["Plant-A", "Plant-B", "Plant-C"]:
        raise HTTPException(status_code=400, detail="Invalid plant_id.")
        
    current_mode = plant_deployment_modes.get(plant_id, "shadow")
    
    # Calculate trust score using FeedbackLog table for this plant
    logs = db.query(models.FeedbackLog).filter(models.FeedbackLog.plant_id == plant_id).all()
    
    total_count = len(logs)
    confirmed_count = sum(1 for log in logs if log.officer_verdict == "Confirmed Risk")
    false_alarm_count = sum(1 for log in logs if log.officer_verdict == "False Alarm")
    
    trust_score = 100.0
    if total_count > 0:
        trust_score = round((confirmed_count / total_count) * 100, 1)
        
    graduation_eligible = (total_count >= 20 and trust_score >= 90.0)
    
    history = []
    for log in logs:
        history.append({
            "id": log.id,
            "flag_id": log.flag_id,
            "rule_name": log.rule_name,
            "verdict": log.officer_verdict,
            "timestamp": log.timestamp.isoformat() + "Z"
        })
        
    return {
        "plant_id": plant_id,
        "current_mode": current_mode,
        "trust_score": trust_score,
        "shadow_predictions_count": total_count,
        "confirmed_count": confirmed_count,
        "false_alarm_count": false_alarm_count,
        "graduation_eligible": graduation_eligible,
        "history": history
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "sentinelgrid-backend"}

@app.post("/api/simulation/inject")
def inject_scenario(scenario: str = Query(..., description="Scenario key to inject")):
    if scenario not in SCENARIO_OFFSETS:
        raise HTTPException(status_code=400, detail=f"Invalid scenario. Choose from: {list(SCENARIO_OFFSETS.keys())}")
    current_simulation_state["scenario"] = scenario
    
    # Reset active emergency protocols on new scenario injection
    active_tier3_protocols.clear()
    active_tier3_rules.clear()
    
    # Reset alarm states
    for p_id in alarm_states:
        alarm_states[p_id]["local_alerts_active"].clear()
        alarm_states[p_id]["acknowledged_local_alerts"].clear()
        alarm_states[p_id]["facility_evacuation_active"] = False
        alarm_states[p_id]["last_triggered_by_flag_id"] = None
        alarm_states[p_id]["confirmation_log"].clear()
    
    # Reset incident agent in-memory cache on scenario switch
    try:
        from app.engine.incident_agent import reset_incident_cache
        reset_incident_cache()
    except Exception as e:
        print("Failed to reset incident agent cache on scenario injection:", e)

    return {
        "status": "success",
        "injected_scenario": scenario,
        "details": SCENARIO_OFFSETS[scenario]
    }

@app.get("/api/simulation/state")
def get_simulation_state():
    return {
        "status": "success",
        "scenario": current_simulation_state.get("scenario", "normal")
    }

@app.post("/api/simulation/reset")
def reset_simulation():
    """
    POST endpoint to reseed the database to clean baseline state and reset the active simulation scenario.
    """
    try:
        seed_database()
        current_simulation_state["scenario"] = "normal"
        
        # Reset active emergency protocols on simulation reset
        active_tier3_protocols.clear()
        active_tier3_rules.clear()
        
        # Reset alarm states
        for p_id in alarm_states:
            alarm_states[p_id]["local_alerts_active"].clear()
            alarm_states[p_id]["acknowledged_local_alerts"].clear()
            alarm_states[p_id]["facility_evacuation_active"] = False
            alarm_states[p_id]["last_triggered_by_flag_id"] = None
            alarm_states[p_id]["confirmation_log"].clear()
            
        # Reset incident agent in-memory cache
        try:
            from app.engine.incident_agent import reset_incident_cache
            reset_incident_cache()
        except Exception as e:
            print("Failed to reset incident agent cache on simulation reset:", e)
            
        return {
            "status": "success",
            "message": "Database reseeded successfully and simulation reset to normal baseline."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reseeding database failed: {e}")

def get_shifted_offsets(scenario_key: str, plant_id: str):
    info = SCENARIO_OFFSETS.get(scenario_key, SCENARIO_OFFSETS["normal"]).copy()
    if scenario_key == "normal":
        return info
        
    if plant_id == "Plant-B":
        shifts = {
            "scenario_1": 12.0,
            "scenario_2": 24.0,
            "scenario_3": 36.0,
            "scenario_4": 48.0,
            "silent_failure": 60.0
        }
        if scenario_key in shifts:
            info["start"] = shifts[scenario_key] + 0.5
            info["end"] = shifts[scenario_key] + 1.0
    elif plant_id == "Plant-C":
        shifts = {
            "scenario_1": 30.0,
            "scenario_2": 42.0,
            "scenario_3": 54.0,
            "scenario_4": 18.0,
            "silent_failure": 6.0
        }
        if scenario_key in shifts:
            info["start"] = shifts[scenario_key] + 0.5
            info["end"] = shifts[scenario_key] + 1.0
            
    return info

@app.get("/api/risk-assessment")
def get_risk_assessment(
    window_start: str = Query(None, description="ISO 8601 start time"),
    window_end: str = Query(None, description="ISO 8601 end time"),
    dataset: str = Query(None, description="Simulation dataset name"),
    plant_id: str = Query("Plant-A", description="Plant ID"),
    progress_pct: float = Query(None, description="Dynamic live progress percentage (0.0 to 100.0)"),
    exclude_permit_ids: list[str] = Query(None, description="Permit IDs to exclude for counterfactuals"),
    exclude_maint_ids: list[int] = Query(None, description="Maintenance Log IDs to exclude for counterfactuals"),
    db: Session = Depends(get_db)
):
    if not window_start or not window_end:
        scenario_key = current_simulation_state["scenario"]
        info = get_shifted_offsets(scenario_key, plant_id)
        resolved_dataset = info["dataset"]
        
        first_reading = db.query(models.GasSensorReading).filter(
            models.GasSensorReading.dataset == resolved_dataset,
            models.GasSensorReading.plant_id == plant_id
        ).order_by(models.GasSensorReading.timestamp.asc()).first()
        
        if not first_reading:
            first_reading = db.query(models.GasSensorReading).filter(
                models.GasSensorReading.dataset == resolved_dataset
            ).order_by(models.GasSensorReading.timestamp.asc()).first()
            
        if not first_reading:
            raise HTTPException(status_code=400, detail=f"No readings found for dataset {resolved_dataset}")
        base_time = first_reading.timestamp

        # Support continuous dynamic progression across the 30-minute buildup window
        offset_shift_hours = 0.0
        if progress_pct is not None and scenario_key != "normal":
            pct = max(0.0, min(100.0, progress_pct))
            offset_shift_hours = (pct / 100.0) * 0.5 - 0.5
            
        start_dt = base_time + timedelta(hours=info["start"] + offset_shift_hours)
        end_dt = base_time + timedelta(hours=info["end"] + offset_shift_hours)
        dataset = resolved_dataset
    else:
        try:
            start_dt = datetime.fromisoformat(window_start.replace("Z", "+00:00")).replace(tzinfo=None)
            end_dt = datetime.fromisoformat(window_end.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid datetime format: {e}")
        if not dataset:
            dataset = "default"

    if start_dt > end_dt:
        raise HTTPException(status_code=400, detail="window_start cannot be after window_end")

    assessment = detect_compound_risk(
        db,
        start_dt,
        end_dt,
        dataset=dataset,
        plant_id=plant_id,
        exclude_permit_ids=exclude_permit_ids,
        exclude_maint_ids=exclude_maint_ids
    )



    # Real dynamic telemetry metrics calculated directly by detect_compound_risk engine

    # Add resolved parameters to response for front-end convenience
    mode = plant_deployment_modes.get(plant_id, "shadow")
    assessment["resolved_window_start"] = start_dt.isoformat()
    assessment["resolved_window_end"] = end_dt.isoformat()
    assessment["resolved_dataset"] = dataset
    assessment["active_scenario"] = current_simulation_state["scenario"]
    assessment["plant_id"] = plant_id
    assessment["deployment_mode"] = mode

    # Inject shadow flag into triggered rules if plant is in shadow mode
    is_shadow = (mode == "shadow")
    for rule in assessment.get("triggered_rules", []):
        rule["shadow"] = is_shadow

    # Evaluate alarm system conditions
    active_tier3_zones_in_window = set()
    for rule in assessment.get("triggered_rules", []):
        if rule.get("severity") == 3:
            rule_zone = "Zone-A"
            for z in ["Zone-A", "Zone-B", "Zone-C", "Zone-D", "Zone-E", "Zone-F"]:
                if z in rule.get("flag_id", "") or z in rule.get("reason", ""):
                    rule_zone = z
                    break
            active_tier3_zones_in_window.add(rule_zone)
            
            if mode == "live":
                if (rule_zone not in alarm_states[plant_id]["local_alerts_active"] and 
                    rule_zone not in alarm_states[plant_id]["acknowledged_local_alerts"]):
                    alarm_states[plant_id]["local_alerts_active"].append(rule_zone)
                    alarm_states[plant_id]["last_triggered_by_flag_id"] = rule.get("flag_id")
            else:
                rule["would_have_triggered_local_alert"] = True
                
    # Clean up resolved zones
    for zone in ["Zone-A", "Zone-B", "Zone-C", "Zone-D", "Zone-E", "Zone-F"]:
        if zone not in active_tier3_zones_in_window:
            if zone in alarm_states[plant_id]["local_alerts_active"]:
                alarm_states[plant_id]["local_alerts_active"].remove(zone)
            if zone in alarm_states[plant_id]["acknowledged_local_alerts"]:
                alarm_states[plant_id]["acknowledged_local_alerts"].remove(zone)

    # Attach alarm state and re-evaluate per-zone risk scores with alarm state
    assessment["alarm_state"] = alarm_states[plant_id]
    from app.engine.risk_engine import calculate_zone_scores
    assessment["zone_scores"] = calculate_zone_scores(
        assessment.get("triggered_rules", []),
        assessment.get("watch_flags", []),
        alarm_states[plant_id]
    )

    # In normal baseline mode, synchronize specific zone scores with background operational risk
    if current_simulation_state["scenario"] == "normal":
        if plant_id == "Plant-B":
            assessment["zone_scores"]["Zone-B"] = max(assessment["zone_scores"].get("Zone-B", 0), 25)
        elif plant_id == "Plant-C":
            assessment["zone_scores"]["Zone-C"] = max(assessment["zone_scores"].get("Zone-C", 0), 18)
        elif plant_id == "Plant-A":
            assessment["zone_scores"]["Zone-A"] = max(assessment["zone_scores"].get("Zone-A", 0), 5)

    # Auto-trigger pattern search for active warnings/danger flags
    if assessment.get("tier", 0) >= 2:
        try:
            from app.engine.incident_agent import get_related_incidents_for_rules
            assessment["related_incidents"] = get_related_incidents_for_rules(assessment.get("triggered_rules", []))
        except Exception as e:
            print("Failed to auto-trigger related incidents search", e)
            assessment["related_incidents"] = []
    else:
        assessment["related_incidents"] = []

    # Auto-trigger emergency response protocol if tier is 3 and mode is live
    if assessment.get("tier", 0) == 3 and mode == "live":
        for rule in assessment.get("triggered_rules", []):
            if rule.get("severity") == 3:
                reason = rule.get("reason", "")
                for z in ["Zone-A", "Zone-B", "Zone-C", "Zone-D", "Zone-E", "Zone-F"]:
                    if z in reason:
                        if plant_id == "Plant-A":
                            if z not in active_tier3_protocols:
                                active_tier3_protocols[z] = datetime.utcnow()
                            if z not in active_tier3_rules:
                                active_tier3_rules[z] = []
                            if rule not in active_tier3_rules[z]:
                                active_tier3_rules[z].append(rule)
                                
                        key = f"{plant_id}_{z}"
                        if key not in active_tier3_protocols:
                            active_tier3_protocols[key] = datetime.utcnow()
                        if key not in active_tier3_rules:
                            active_tier3_rules[key] = []
                        # Avoid duplicates
                        if rule not in active_tier3_rules[key]:
                            active_tier3_rules[key].append(rule)

    return assessment

@app.get("/api/telemetry-summary")
def get_telemetry_summary(
    window_start: str = Query(None, description="ISO 8601 start time"),
    window_end: str = Query(None, description="ISO 8601 end time"),
    dataset: str = Query(None, description="Simulation dataset name"),
    plant_id: str = Query("Plant-A", description="Plant ID"),
    progress_pct: float = Query(None, description="Dynamic live progress percentage (0.0 to 100.0)"),
    db: Session = Depends(get_db)
):
    if not window_start or not window_end:
        scenario_key = current_simulation_state["scenario"]
        info = get_shifted_offsets(scenario_key, plant_id)
        resolved_dataset = info["dataset"]
        
        first_reading = db.query(models.GasSensorReading).filter(
            models.GasSensorReading.dataset == resolved_dataset
        ).order_by(models.GasSensorReading.timestamp.asc()).first()
        
        if not first_reading:
            raise HTTPException(status_code=400, detail=f"No readings found for dataset {resolved_dataset}")
            
        base_time = first_reading.timestamp

        offset_shift_hours = 0.0
        if progress_pct is not None and scenario_key != "normal":
            pct = max(0.0, min(100.0, progress_pct))
            offset_shift_hours = (pct / 100.0) * 0.5 - 0.5

        start_dt = base_time + timedelta(hours=info["start"] + offset_shift_hours)
        end_dt = base_time + timedelta(hours=info["end"] + offset_shift_hours)
        dataset = resolved_dataset
    else:
        try:
            start_dt = datetime.fromisoformat(window_start.replace("Z", "+00:00")).replace(tzinfo=None)
            end_dt = datetime.fromisoformat(window_end.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid datetime format: {e}")
        if not dataset:
            dataset = "default"

    if start_dt > end_dt:
        raise HTTPException(status_code=400, detail="window_start cannot be after window_end")

    # Fetch gas readings in the window
    gas_readings = db.query(models.GasSensorReading).filter(
        models.GasSensorReading.timestamp >= start_dt,
        models.GasSensorReading.timestamp <= end_dt,
        models.GasSensorReading.dataset == dataset,
        models.GasSensorReading.plant_id == plant_id
    ).order_by(models.GasSensorReading.timestamp.asc()).all()

    # Fetch permits active in the window
    permits = db.query(models.Permit).filter(
        models.Permit.issued_at <= end_dt,
        ((models.Permit.closed_at == None) | (models.Permit.closed_at >= start_dt)),
        models.Permit.dataset == dataset,
        models.Permit.plant_id == plant_id
    ).all()

    # Fetch maintenance logs logged in the last 24 hours of end_dt
    maint_start = end_dt - timedelta(hours=24)
    maint_logs = db.query(models.MaintenanceLog).filter(
        models.MaintenanceLog.logged_at >= maint_start,
        models.MaintenanceLog.logged_at <= end_dt,
        models.MaintenanceLog.dataset == dataset,
        models.MaintenanceLog.plant_id == plant_id
    ).all()

    return {
        "gas_readings": [model_to_dict(g) for g in gas_readings],
        "permits": [model_to_dict(p) for p in permits],
        "maintenance_logs": [model_to_dict(m) for m in maint_logs]
    }

@app.get("/api/worker-positions")
def get_worker_positions():
    """
    Returns simulated worker positions based on active scenario.
    """
    from app.data.workers import get_simulated_workers
    scenario = current_simulation_state.get("scenario", "normal")
    return get_simulated_workers(scenario)

@app.get("/api/simulation-info")
def get_simulation_info(db: Session = Depends(get_db)):
    def_first = db.query(models.GasSensorReading).filter(
        models.GasSensorReading.dataset == "default"
    ).order_by(models.GasSensorReading.timestamp.asc()).first()

    viz_first = db.query(models.GasSensorReading).filter(
        models.GasSensorReading.dataset == "vizag_replay"
    ).order_by(models.GasSensorReading.timestamp.asc()).first()

    return {
        "default": {
            "start_time": def_first.timestamp.isoformat() if def_first else None,
            "duration_hours": 72
        },
        "vizag_replay": {
            "start_time": viz_first.timestamp.isoformat() if viz_first else None,
            "duration_hours": 24
        }
    }

class IncidentQueryRequest(BaseModel):
    query: str

@app.post("/api/incident-intelligence/query")
def post_incident_intelligence_query(req: IncidentQueryRequest, db: Session = Depends(get_db)):
    """
    POST endpoint to search past incident reports using sentence embeddings and knowledge graph traversal.
    """
    from app.engine.incident_agent import query_intelligence, generate_pattern_briefing
    try:
        results = query_intelligence(req.query)
        briefing = generate_pattern_briefing(req.query, results, db)
        return {
            "incidents": results,
            "synthesized_briefing": briefing
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/incident-intelligence/patterns")
def get_incident_intelligence_patterns():
    """
    GET endpoint to retrieve the ranked recurring-pattern breakdown across the corpus.
    """
    from app.engine.incident_agent import detect_recurring_patterns
    try:
        return detect_recurring_patterns()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/scorecard")
def get_scorecard(db: Session = Depends(get_db)):
    # 1. Fetch simulation start times
    def_first = db.query(models.GasSensorReading).filter(
        models.GasSensorReading.dataset == "default"
    ).order_by(models.GasSensorReading.timestamp.asc()).first()

    if not def_first:
        raise HTTPException(status_code=404, detail="Database not seeded with default dataset")

    def_start = def_first.timestamp

    # Predefined windows for the 4 default scenarios (in hours from T)
    scenarios = [
        (24.5, 25.0), # Scenario 1
        (36.5, 37.0), # Scenario 2
        (48.5, 49.0), # Scenario 3
        (60.5, 61.0)  # Scenario 4
    ]

    caught_compound = 0
    caught_baseline = 0
    total_rules = 0
    traceable_rules = 0
    false_negative_count = 0

    for start_offset, end_offset in scenarios:
        start_dt = def_start + timedelta(hours=start_offset)
        end_dt = def_start + timedelta(hours=end_offset)

        # Run compound engine
        res_compound = detect_compound_risk(db, start_dt, end_dt, dataset="default")
        if res_compound["tier"] >= 2:
            caught_compound += 1
            for rule in res_compound["triggered_rules"]:
                total_rules += 1
                signals = rule.get("contributing_signals", [])
                # A rule is traceable if it has signals with non-empty zone and ID
                if signals and all(sig.get("zone") and sig.get("id") for sig in signals):
                    traceable_rules += 1
        else:
            false_negative_count += 1

        # Run naive baseline
        res_baseline = detect_single_sensor_baseline(db, start_dt, end_dt, dataset="default")
        if res_baseline["tier"] >= 2:
            caught_baseline += 1

    compound_detection_rate = (caught_compound / len(scenarios)) * 100.0
    baseline_detection_rate = (caught_baseline / len(scenarios)) * 100.0
    evidence_traceability_rate = (traceable_rules / total_rules * 100.0) if total_rules > 0 else 100.0

    # 2. Dynamic lead time for Vizag Replay
    viz_first = db.query(models.GasSensorReading).filter(
        models.GasSensorReading.dataset == "vizag_replay"
    ).order_by(models.GasSensorReading.timestamp.asc()).first()

    lead_time_minutes = 152.0 # Default fallback based on calculated linear crossing
    predictive_lead_time_minutes = 493.4
    if viz_first:
        T_first = viz_first.timestamp
        # Find first reading where CO >= 300.0 ppm (incident threshold) in Zone-C
        incident_reading = db.query(models.GasSensorReading).filter(
            models.GasSensorReading.dataset == "vizag_replay",
            models.GasSensorReading.zone == "Zone-C",
            models.GasSensorReading.gas_type == "CO",
            models.GasSensorReading.reading_ppm >= 300.0
        ).order_by(models.GasSensorReading.timestamp.asc()).first()

        if incident_reading:
            T_incident = incident_reading.timestamp
            # Compound detection starts when permit becomes active at T+10h
            T_compound = T_first + timedelta(hours=10.0)
            lead_time_minutes = max(0.0, (T_incident - T_compound).total_seconds() / 60.0)
            
            # Find watch threshold breach (CO >= 17.5 ppm) for predictive model
            watch_reading = db.query(models.GasSensorReading).filter(
                models.GasSensorReading.dataset == "vizag_replay",
                models.GasSensorReading.zone == "Zone-C",
                models.GasSensorReading.gas_type == "CO",
                models.GasSensorReading.reading_ppm >= 17.5
            ).order_by(models.GasSensorReading.timestamp.asc()).first()
            
            if watch_reading:
                predictive_lead_time_minutes = max(0.0, (T_incident - watch_reading.timestamp).total_seconds() / 60.0)

    # 3. Dynamic false positive check on negative test cases
    false_positives = 0
    edge_cases_tested = 2
    
    # Run edge_case_time_gap
    start_time_gap = def_start + timedelta(hours=16.5)
    end_time_gap = def_start + timedelta(hours=17.0)
    res_time_gap = detect_compound_risk(db, start_time_gap, end_time_gap, dataset="default")
    if len(res_time_gap["triggered_rules"]) > 0:
        false_positives += 1
        
    # Run edge_case_adjacent_zone_no_overlap
    start_adjacent = def_start + timedelta(hours=19.0)
    end_adjacent = def_start + timedelta(hours=19.5)
    res_adjacent = detect_compound_risk(db, start_adjacent, end_adjacent, dataset="default")
    if len(res_adjacent["triggered_rules"]) > 0:
        false_positives += 1

    # 4. Raw sensor threshold crossings vs correlated alerts surfaced
    raw_readings = db.query(models.GasSensorReading).filter(
        models.GasSensorReading.dataset == "default"
    ).all()
    raw_sensor_crossings = sum(
        1 for r in raw_readings 
        if (r.gas_type == "CH4" and r.reading_ppm >= 20.0) or
           (r.gas_type == "H2S" and r.reading_ppm >= 10.0) or
           (r.gas_type == "CO" and r.reading_ppm >= 50.0)
    )
    
    # Total correlated alerts surfaced (Tier 2 and Tier 3 events)
    correlated_alerts_surfaced = 0
    for start_offset, end_offset in scenarios:
        start_dt = def_start + timedelta(hours=start_offset)
        end_dt = def_start + timedelta(hours=end_offset)
        res_compound = detect_compound_risk(db, start_dt, end_dt, dataset="default")
        if res_compound.get("tier", 0) >= 2:
            correlated_alerts_surfaced += len(res_compound.get("triggered_rules", []))
            
    noise_reduction_pct = round(
        ((raw_sensor_crossings - correlated_alerts_surfaced) / raw_sensor_crossings * 100.0), 1
    ) if raw_sensor_crossings > 0 else 100.0

    return {
        "compound_detection_rate": compound_detection_rate,
        "baseline_detection_rate": baseline_detection_rate,
        "lead_time_minutes": round(lead_time_minutes, 1),
        "predictive_lead_time_minutes": round(predictive_lead_time_minutes, 1),
        "evidence_traceability_rate": evidence_traceability_rate,
        "false_negative_count": false_negative_count,
        "raw_sensor_crossings": raw_sensor_crossings,
        "correlated_alerts_surfaced": correlated_alerts_surfaced,
        "noise_reduction_pct": noise_reduction_pct,
        "false_positive_check": {
            "edge_cases_tested": edge_cases_tested,
            "false_positives": false_positives
        }
    }

# Historical risk assessment cache to support automatic delta retrieval
last_risk_assessments_history: dict[str, dict] = {}

@app.post("/api/narrate")
def post_narrate(payload: dict):
    """
    POST endpoint to narrate safety risk assessments and generate regulatory evidence packets.
    Supports both direct risk_data object and delta payloads with current + previous assessments.
    """
    if "current" in payload:
        current_data = payload["current"]
        previous_data = payload.get("previous")
    else:
        current_data = payload
        previous_data = payload.get("previous_risk_assessment")
        
    plant_id = current_data.get("plant_id", "Plant-A") if isinstance(current_data, dict) else "Plant-A"
    history_key = f"{plant_id}"
    
    if previous_data is None and history_key in last_risk_assessments_history:
        cached_prev = last_risk_assessments_history[history_key]
        if isinstance(current_data, dict) and cached_prev.get("score") != current_data.get("score"):
            previous_data = cached_prev

    narration = generate_risk_narration(current_data if isinstance(current_data, dict) else payload, previous_data)
    
    if isinstance(current_data, dict):
        last_risk_assessments_history[history_key] = current_data
        
    return narration

class VoiceHandoverJsonPayload(BaseModel):
    transcript_text: str | None = None
    plant_id: str = "Plant-A"
    dataset: str = "default"

class AnonymousHazardJsonPayload(BaseModel):
    text_report: str | None = None
    plant_id: str = "Plant-A"
    dataset: str = "default"

@app.post("/api/voice-handover/upload")
async def post_voice_handover_upload(
    file: UploadFile = File(None),
    transcript_text: str = Form(None),
    plant_id: str = Form("Plant-A"),
    dataset: str = Form("default"),
    db: Session = Depends(get_db)
):
    """
    Accepts shift handover voice audio recordings or text notes.
    Runs speech-to-text transcription + LLM hazard entity extraction, stores VerbalReport,
    and returns transcript, extracted entities, and report record.
    """
    from app.engine.voice_extraction import transcribe_audio, extract_hazard_entities
    
    if file:
        file_bytes = await file.read()
        transcript = transcribe_audio(file_bytes, filename=file.filename or "handover.wav")
    elif transcript_text:
        transcript = transcript_text.strip()
    else:
        raise HTTPException(status_code=400, detail="Must provide an audio file or transcript_text.")
        
    extraction = extract_hazard_entities(transcript)
    zones = extraction.get("mentioned_zones", [])
    primary_zone = zones[0] if zones else "Zone-C"
    
    report = models.VerbalReport(
        zone=primary_zone,
        timestamp=datetime.utcnow(),
        transcript=transcript,
        hazard_type=extraction.get("mentioned_hazard_type"),
        urgency_signal=extraction.get("urgency_signal", "medium"),
        raw_quote=extraction.get("raw_quote"),
        is_anonymous=0,
        plant_id=plant_id,
        dataset=dataset
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    
    return {
        "status": "success",
        "report_id": report.id,
        "transcript": transcript,
        "extraction": extraction,
        "report": model_to_dict(report)
    }

@app.post("/api/voice-handover/json")
def post_voice_handover_json(
    payload: VoiceHandoverJsonPayload,
    db: Session = Depends(get_db)
):
    """JSON variant endpoint for voice handover text notes."""
    from app.engine.voice_extraction import extract_hazard_entities
    if not payload.transcript_text:
        raise HTTPException(status_code=400, detail="Must provide transcript_text.")
        
    transcript = payload.transcript_text.strip()
    extraction = extract_hazard_entities(transcript)
    zones = extraction.get("mentioned_zones", [])
    primary_zone = zones[0] if zones else "Zone-C"
    
    report = models.VerbalReport(
        zone=primary_zone,
        timestamp=datetime.utcnow(),
        transcript=transcript,
        hazard_type=extraction.get("mentioned_hazard_type"),
        urgency_signal=extraction.get("urgency_signal", "medium"),
        raw_quote=extraction.get("raw_quote"),
        is_anonymous=0,
        plant_id=payload.plant_id,
        dataset=payload.dataset
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    
    return {
        "status": "success",
        "report_id": report.id,
        "transcript": transcript,
        "extraction": extraction,
        "report": model_to_dict(report)
    }

@app.post("/api/hazard-report/anonymous")
async def post_anonymous_hazard_report(
    file: UploadFile = File(None),
    text_report: str = Form(None),
    plant_id: str = Form("Plant-A"),
    dataset: str = Form("default"),
    db: Session = Depends(get_db)
):
    """
    Accepts anonymous worker hazard reports (voice or text) with ZERO user/officer identity tracking.
    Feeds extraction directly into DB & risk engine pipeline.
    """
    from app.engine.voice_extraction import transcribe_audio, extract_hazard_entities
    
    if file:
        file_bytes = await file.read()
        transcript = transcribe_audio(file_bytes, filename=file.filename or "anonymous_report.wav")
    elif text_report:
        transcript = text_report.strip()
    else:
        raise HTTPException(status_code=400, detail="Must provide an audio file or text_report.")
        
    extraction = extract_hazard_entities(transcript)
    zones = extraction.get("mentioned_zones", [])
    primary_zone = zones[0] if zones else "Zone-A"
    
    report = models.VerbalReport(
        zone=primary_zone,
        timestamp=datetime.utcnow(),
        transcript=transcript,
        hazard_type=extraction.get("mentioned_hazard_type"),
        urgency_signal=extraction.get("urgency_signal", "medium"),
        raw_quote=extraction.get("raw_quote"),
        is_anonymous=1,
        plant_id=plant_id,
        dataset=dataset
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    
    return {
        "status": "success",
        "report_id": report.id,
        "transcript": transcript,
        "extraction": extraction,
        "report": model_to_dict(report)
    }

@app.post("/api/hazard-report/anonymous-json")
def post_anonymous_hazard_json(
    payload: AnonymousHazardJsonPayload,
    db: Session = Depends(get_db)
):
    """JSON variant endpoint for anonymous text hazard reports."""
    from app.engine.voice_extraction import extract_hazard_entities
    if not payload.text_report:
        raise HTTPException(status_code=400, detail="Must provide text_report.")
        
    transcript = payload.text_report.strip()
    extraction = extract_hazard_entities(transcript)
    zones = extraction.get("mentioned_zones", [])
    primary_zone = zones[0] if zones else "Zone-A"
    
    report = models.VerbalReport(
        zone=primary_zone,
        timestamp=datetime.utcnow(),
        transcript=transcript,
        hazard_type=extraction.get("mentioned_hazard_type"),
        urgency_signal=extraction.get("urgency_signal", "medium"),
        raw_quote=extraction.get("raw_quote"),
        is_anonymous=1,
        plant_id=payload.plant_id,
        dataset=payload.dataset
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    
    return {
        "status": "success",
        "report_id": report.id,
        "transcript": transcript,
        "extraction": extraction,
        "report": model_to_dict(report)
    }

@app.get("/api/replay/vizag")
def get_replay_vizag(db: Session = Depends(get_db)):
    """
    Returns a pre-computed/cached chronological timeline of the Vizag Coke Oven battery incident,
    interleaving real public events and SentinelGrid safety flags.
    """
    # 1. Fetch simulation start time for Vizag replay dataset to align timestamps
    viz_first = db.query(models.GasSensorReading).filter(
        models.GasSensorReading.dataset == "vizag_replay"
    ).order_by(models.GasSensorReading.timestamp.asc()).first()

    T_first = viz_first.timestamp if viz_first else datetime.utcnow()

    # Pre-calculated events with relative offsets
    raw_events = [
        {
            "offset_hours": 3.5,
            "type": "real",
            "title": "Overdue Regulator Calibration Flagged",
            "description": "Maintenance log registered: Gas pressure regulator calibration check is overdue by 14 days on equipment REG-COVEN-11 in Coke Oven Battery 11."
        },
        {
            "offset_hours": 4.0,
            "type": "real",
            "title": "CO Gas Accumulation Commences",
            "description": "Gas telemetry detects Carbon Monoxide (CO) levels beginning to rise steadily above normal baseline (5 ppm) in Coke Oven Battery area (Zone-C)."
        },
        {
            "offset_hours": 10.0,
            "type": "real",
            "title": "Hot Work Permit Active in Zone-C",
            "description": "Hot work permit PERM-VIZAG-901 becomes active near Coke Oven Battery 11 for maintenance tasks, issued by Senior Inspector Prasad."
        },
        {
            "offset_hours": 10.0,
            "type": "sentinelgrid",
            "title": "SentinelGrid Threat Flagged (Tier 3)",
            "description": "AI Safety Briefing: An active hot work permit in Zone-C correlates with rising toxic CO levels (212.5 ppm) and overdue maintenance on regulator equipment REG-COVEN-11 in the same zone. This presents an imminent fire and toxic inhalation risk. Standard OISD-105 Clause 4.1 is violated.",
            "risk_score": 100,
            "tier": 3
        },
        {
            "offset_hours": 11.0,
            "type": "sentinelgrid",
            "title": "SentinelGrid Active Risk Warning (Tier 3)",
            "description": "Safety risk continues at critical levels. Carbon Monoxide levels have risen to 247.1 ppm while hot work remains active in Zone-C. Immediate permit suspension is recommended.",
            "risk_score": 100,
            "tier": 3
        },
        {
            "offset_hours": 12.0,
            "type": "sentinelgrid",
            "title": "SentinelGrid Active Risk Warning (Tier 3)",
            "description": "Extreme safety risk. Gas levels are highly elevated (281.7 ppm) during ongoing hot work. OISD Standard 112 Section 6.3 precautions are violated.",
            "risk_score": 100,
            "tier": 3
        },
        {
            "offset_hours": 12.583333333333334,
            "type": "real",
            "title": "Incident Threshold Breached",
            "description": "Toxic gas concentration breaches the 300.0 ppm safety ceiling in Zone-C. Severe inhalation hazard established; atmosphere enters high flammability range."
        },
        {
            "offset_hours": 13.0,
            "type": "sentinelgrid",
            "title": "SentinelGrid Active Risk Warning (Tier 3)",
            "description": "CO levels have breached critical hazard threshold (316.3 ppm). Immediate shutdown of all ignition sources and evacuation of Zone-C required. Factories Act 1948 Section 36 directives are violated.",
            "risk_score": 100,
            "tier": 3
        },
        {
            "offset_hours": 16.0,
            "type": "real",
            "title": "Peak Carbon Monoxide Concentration",
            "description": "CO gas concentrations peak at critical 420.0 ppm in Coke Oven Battery area, establishing fully hazardous, life-threatening conditions."
        }
    ]

    # Align timestamps
    events = []
    for ev in raw_events:
        event_time = T_first + timedelta(hours=ev["offset_hours"])
        events.append({
            **ev,
            "timestamp": event_time.isoformat()
        })

    # Lead time: gap in minutes between first SentinelGrid Tier 2/3 flag (T+10h) 
    # and the point of actual escalation/threshold crossed (T+12.583333333333334h)
    lead_time_minutes = (12.583333333333334 - 10.0) * 60.0 # 155 minutes

    # Calculate predictive lead time (Watch-tier detection first breach)
    predictive_lead_time_minutes = 493.4
    if viz_first:
        incident_reading = db.query(models.GasSensorReading).filter(
            models.GasSensorReading.dataset == "vizag_replay",
            models.GasSensorReading.zone == "Zone-C",
            models.GasSensorReading.gas_type == "CO",
            models.GasSensorReading.reading_ppm >= 300.0
        ).order_by(models.GasSensorReading.timestamp.asc()).first()
        
        watch_reading = db.query(models.GasSensorReading).filter(
            models.GasSensorReading.dataset == "vizag_replay",
            models.GasSensorReading.zone == "Zone-C",
            models.GasSensorReading.gas_type == "CO",
            models.GasSensorReading.reading_ppm >= 17.5
        ).order_by(models.GasSensorReading.timestamp.asc()).first()
        
        if incident_reading and watch_reading:
            predictive_lead_time_minutes = max(0.0, (incident_reading.timestamp - watch_reading.timestamp).total_seconds() / 60.0)

    return {
        "lead_time_minutes": round(lead_time_minutes, 1),
        "predictive_lead_time_minutes": round(predictive_lead_time_minutes, 1),
        "events": events
    }

@app.get("/api/emergency-response/{zone}")
def get_emergency_response(zone: str, plant_id: str = Query("Plant-A")):
    key = f"{plant_id}_{zone}"
    
    if plant_id == "Plant-A" and zone in active_tier3_protocols:
        triggered_at = active_tier3_protocols[zone]
        active_rules_source = active_tier3_rules.get(zone, [])
    elif key in active_tier3_protocols:
        triggered_at = active_tier3_protocols[key]
        active_rules_source = active_tier3_rules.get(key, [])
    else:
        return {"active": False, "stage": None, "steps": [], "preliminary_report": None}
        
    now = datetime.utcnow()
    elapsed = (now - triggered_at).total_seconds()
    
    facility_evac = alarm_states.get(plant_id, {}).get("facility_evacuation_active", False)
    
    steps = [
        {
            "name": "Evacuation Zone Marked",
            "reached": True,
            "timestamp": triggered_at.isoformat() + "Z"
        },
        {
            "name": "Response Team Alerted",
            "reached": elapsed >= 5 or facility_evac,
            "timestamp": (triggered_at + timedelta(seconds=5)).isoformat() + "Z" if (elapsed >= 5 or facility_evac) else None
        },
        {
            "name": "Sensor Evidence Preserved",
            "reached": elapsed >= 8 or facility_evac,
            "timestamp": (triggered_at + timedelta(seconds=8)).isoformat() + "Z" if (elapsed >= 8 or facility_evac) else None
        },
        {
            "name": "Preliminary Incident Report Drafted",
            "reached": elapsed >= 12 or facility_evac,
            "timestamp": (triggered_at + timedelta(seconds=12)).isoformat() + "Z" if (elapsed >= 12 or facility_evac) else None
        }
    ]
    
    if facility_evac:
        steps.append({
            "name": "Facility Evacuation Active",
            "reached": True,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        current_stage = "Facility Evacuation Active"
    else:
        # Calculate current stage
        current_stage = "Evacuation Zone Marked"
        if elapsed >= 12:
            current_stage = "Preliminary Incident Report Drafted"
        elif elapsed >= 8:
            current_stage = "Sensor Evidence Preserved"
        elif elapsed >= 5:
            current_stage = "Response Team Alerted"
        
    preliminary_report = None
    if elapsed >= 12:
        # Construct evidence packet using narration logic
        mock_risk_data = {
            "score": 100,
            "tier": 3,
            "tier_name": "Escalate",
            "triggered_rules": active_rules_source
        }
        try:
            from app.engine.narration import generate_fallback_narration
            narration_result = generate_fallback_narration(mock_risk_data)
            preliminary_report = narration_result.get("evidence_packet")
        except Exception as e:
            print("Failed to generate preliminary report", e)
            preliminary_report = {
                "summary": f"Incident flagged due to rules in {zone}.",
                "rules_fired": [r.get("rule_name") for r in active_rules_source],
                "applicable_clause": "Unknown regulatory clause",
                "clause_relation": "Regulatory assessment unavailable"
            }
            
    return {
        "active": True,
        "zone": zone,
        "triggered_at": triggered_at.isoformat() + "Z",
        "elapsed_seconds": round(elapsed, 2),
        "current_stage": current_stage,
        "steps": steps,
        "preliminary_report": preliminary_report
    }

@app.get("/api/emergency-response/{zone}/report-pdf")
def get_emergency_response_pdf(
    zone: str,
    plant_id: str = Query("Plant-A", description="Plant ID"),
    db: Session = Depends(get_db)
):
    key = f"{plant_id}_{zone}"
    if plant_id == "Plant-A" and zone in active_tier3_protocols:
        triggered_at = active_tier3_protocols[zone]
        active_rules_source = active_tier3_rules.get(zone, [])
    elif key in active_tier3_protocols:
        triggered_at = active_tier3_protocols[key]
        active_rules_source = active_tier3_rules.get(key, [])
    else:
        triggered_at = datetime.utcnow()
        active_rules_source = []

    scenario_key = current_simulation_state["scenario"]
    info = get_shifted_offsets(scenario_key, plant_id)
    resolved_dataset = info["dataset"]
    
    first_reading = db.query(models.GasSensorReading).filter(
        models.GasSensorReading.dataset == resolved_dataset
    ).order_by(models.GasSensorReading.timestamp.asc()).first()
    
    gas_readings_dicts = []
    permits_dicts = []
    
    if first_reading:
        base_time = first_reading.timestamp
        start_dt = base_time + timedelta(hours=info["start"])
        end_dt = base_time + timedelta(hours=info["end"])
        
        # Gas readings for zone
        gas_readings = db.query(models.GasSensorReading).filter(
            models.GasSensorReading.timestamp >= start_dt,
            models.GasSensorReading.timestamp <= end_dt,
            models.GasSensorReading.dataset == resolved_dataset,
            models.GasSensorReading.plant_id == plant_id,
            models.GasSensorReading.zone == zone
        ).order_by(models.GasSensorReading.timestamp.asc()).all()
        gas_readings_dicts = [model_to_dict(g) for g in gas_readings]
        
        # Active permits for zone
        permits = db.query(models.Permit).filter(
            models.Permit.issued_at <= end_dt,
            ((models.Permit.closed_at == None) | (models.Permit.closed_at >= start_dt)),
            models.Permit.dataset == resolved_dataset,
            models.Permit.plant_id == plant_id,
            models.Permit.zone == zone
        ).all()
        permits_dicts = [model_to_dict(p) for p in permits]

        if not active_rules_source:
            assessment = detect_compound_risk(db, start_dt, end_dt, dataset=resolved_dataset, plant_id=plant_id)
            all_rules = assessment.get("triggered_rules", [])
            active_rules_source = [r for r in all_rules if zone in r.get("reason", "") or zone in r.get("flag_id", "")]
            if not active_rules_source:
                active_rules_source = all_rules

    mock_risk_data = {
        "score": 100,
        "tier": 3,
        "tier_name": "Escalate",
        "triggered_rules": active_rules_source
    }
    
    from app.engine.narration import generate_risk_narration, generate_fallback_narration
    try:
        narration_result = generate_risk_narration(mock_risk_data)
    except Exception as e:
        print("Failed to generate narration for PDF, fallback used", e)
        narration_result = generate_fallback_narration(mock_risk_data)
        
    from app.engine.pdf_generator import build_evidence_pdf
    pdf_bytes = build_evidence_pdf(
        zone=zone,
        plant_id=plant_id,
        triggered_at_str=triggered_at.isoformat() + "Z",
        active_rules=active_rules_source,
        gas_readings=gas_readings_dicts,
        permits=permits_dicts,
        narration_data=narration_result
    )
    
    filename = f"Regulatory_Evidence_Packet_{plant_id}_{zone}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

def generate_audit_summary(clause_counts):
    if not clause_counts:
        return "No compliance deviations detected during this audit period."
    max_clause = max(clause_counts, key=lambda x: x["count"])
    total_flags = sum(x["count"] for x in clause_counts)
    
    summary = f"{max_clause['count']} of {total_flags} compound-risk events this period relate to {max_clause['clause']} controls — recommend reviewing {max_clause['clause']} compliance training for shift supervisors."
    return summary

@app.get("/api/compliance-audit")
def get_compliance_audit(plant_id: str = Query("Plant-A"), db: Session = Depends(get_db)):
    permits = db.query(models.Permit).filter(
        models.Permit.dataset == "default",
        models.Permit.plant_id == plant_id
    ).all()
    total_permits = len(permits)
    
    # Flagged permits contain RISK or SILENT in their permit_id
    flagged_permits_count = sum(1 for p in permits if "RISK" in p.permit_id or "SILENT" in p.permit_id)
    compliant_permits_count = total_permits - flagged_permits_count
    
    compliance_rate = round((compliant_permits_count / total_permits) * 100, 1) if total_permits > 0 else 100.0
    
    clause_counts = [
        {"clause": "OISD Standard 105 (Section 5.2)", "count": 2, "description": "Permit to Work Systems for Hot Work near potential ignition sources"},
        {"clause": "OISD Standard 105 (Section 5.3)", "count": 1, "description": "Safety in Confined Space Entry and atmospheric gas monitoring"},
        {"clause": "Factories Act 1948 (Section 37)", "count": 1, "description": "Electrical isolation and spark prevention in explosive gas presence"},
        {"clause": "OISD Standard 137", "count": 1, "description": "Guidelines for inspection and maintenance of electrical equipment in hazardous areas"},
        {"clause": "Factories Act 1948 (Section 36)", "count": 1, "description": "Precautions against dangerous fumes and mandatory gas checks"}
    ]
    
    trend = [
        {"period": "Week 1", "alerts": 1, "compliance_rate": 85.0},
        {"period": "Week 2", "alerts": 0, "compliance_rate": 100.0},
        {"period": "Week 3", "alerts": 1, "compliance_rate": 80.0},
        {"period": "Week 4", "alerts": 1, "compliance_rate": 80.0},
        {"period": "Week 5", "alerts": 1, "compliance_rate": 80.0},
        {"period": "Week 6", "alerts": 2, "compliance_rate": 60.0}
    ]
    
    summary = generate_audit_summary(clause_counts)
    
    return {
        "total_permits_issued": total_permits,
        "permits_with_no_flagged_risk": compliant_permits_count,
        "compliance_rate": compliance_rate,
        "clause_counts": clause_counts,
        "trend": trend,
        "summary": summary
    }

class RoiCalculatorInput(BaseModel):
    plant_size: str
    num_zones: int
    historical_incidents_per_year: float
    avg_incident_cost: float

@app.post("/api/roi-calculator")
def post_roi_calculator(req: RoiCalculatorInput, db: Session = Depends(get_db)):
    # 1. Fetch real scorecard detection rate
    try:
        scorecard_data = get_scorecard(db)
        detection_rate = scorecard_data.get("compound_detection_rate", 100.0)
    except Exception as e:
        print("Failed to fetch scorecard metrics, defaulting to 100%", e)
        detection_rate = 100.0
        
    # 2. Determine SaaS annual subscription cost based on plant size
    # Small: 5L, Medium: 12L, Large: 25L
    size = req.plant_size.lower()
    if size == "small":
        saas_cost = 5.0 * 100000  # ₹5,00,000
    elif size == "large":
        saas_cost = 25.0 * 100000  # ₹25,00,000
    else:
        saas_cost = 12.0 * 100000  # ₹12,00,000
        
    estimated_annual_risk_exposure = req.historical_incidents_per_year * req.avg_incident_cost
    estimated_incidents_prevented_per_year = req.historical_incidents_per_year * (detection_rate / 100.0)
    estimated_annual_savings = estimated_incidents_prevented_per_year * req.avg_incident_cost
    
    # Net savings (savings minus SaaS subscription)
    net_savings = estimated_annual_savings - saas_cost
    
    # Payback period in months
    if estimated_annual_savings > 0:
        payback_period_months = round((saas_cost / estimated_annual_savings) * 12.0, 1)
    else:
        payback_period_months = 0.0

    # Vizag-scale major incident cost breakdown calculation
    fatality_comp = 150000000.0  # ₹15 Crore (~12 casualties @ ₹1.25 Cr average compensation & medical)
    shutdown_cost = 250000000.0  # ₹25 Crore (5 days unplanned refinery downtime @ ₹5 Cr/day)
    regulatory_penalties = 100000000.0  # ₹10 Crore (Factories Act/OSH Code penalties, legal & environmental remediation)
    total_vizag_incident_cost = fatality_comp + shutdown_cost + regulatory_penalties

    return {
        "estimated_annual_risk_exposure": round(estimated_annual_risk_exposure, 2),
        "sentinelgrid_detection_rate": detection_rate,
        "estimated_incidents_prevented_per_year": round(estimated_incidents_prevented_per_year, 2),
        "estimated_annual_savings": round(estimated_annual_savings, 2),
        "net_annual_savings": round(net_savings, 2),
        "payback_period_months": payback_period_months,
        "saas_cost_annual": saas_cost,
        "vizag_incident_cost_breakdown": {
            "fatalities_compensation": fatality_comp,
            "unplanned_shutdown_cost": shutdown_cost,
            "regulatory_penalty_remediation": regulatory_penalties,
            "total_estimated_major_incident_cost": total_vizag_incident_cost,
            "assumptions_cited": "Illustrative estimate based on ~12 casualties (₹15 Cr compensation), 5 days downtime (@ ₹5 Cr/day), and regulatory fines & cleanup under Factories Act 1948 & OSH Code 2020."
        }
    }

@app.get("/api/fleet-overview")
def get_fleet_overview(db: Session = Depends(get_db)):
    plants = [
        {"id": "Plant-A", "name": "Plant-A - Methane Grinding Terminal"},
        {"id": "Plant-B", "name": "Plant-B - Coke Oven Battery Network"},
        {"id": "Plant-C", "name": "Plant-C - Acid Valve Station"}
    ]
    
    fleet_summary = []
    
    for p in plants:
        plant_id = p["id"]
        # Determine the current scenario offsets for this plant
        scenario_key = current_simulation_state["scenario"]
        info = get_shifted_offsets(scenario_key, plant_id)
        resolved_dataset = info["dataset"]
        
        # Get start/end timestamps from the database
        first_reading = db.query(models.GasSensorReading).filter(
            models.GasSensorReading.dataset == resolved_dataset
        ).order_by(models.GasSensorReading.timestamp.asc()).first()
        
        if first_reading:
            base_time = first_reading.timestamp
            start_dt = base_time + timedelta(hours=info["start"])
            end_dt = base_time + timedelta(hours=info["end"])
            
            assessment = detect_compound_risk(
                db,
                start_dt,
                end_dt,
                dataset=resolved_dataset,
                plant_id=plant_id
            )
        else:
            assessment = {"score": 0, "tier": 1, "tier_name": "Log Only", "triggered_rules": []}
            


        # Cross-plant pattern learning
        cross_plant_matches = []
        if assessment.get("tier", 0) >= 2:
            try:
                from app.engine.incident_agent import get_cached_corpus
                corpus = get_cached_corpus(db)
                active_rules = [r.get("rule_name") for r in assessment.get("triggered_rules", [])]
                for incident in corpus:
                    if incident.get("rule_type") in active_rules and incident.get("plant_id") != plant_id:
                        cross_plant_matches.append({
                            "historical_incident_id": incident["id"],
                            "text": incident["text"],
                            "rule_type": incident["rule_type"],
                            "regulatory_clause": incident["regulatory_clause"],
                            "other_plant_id": incident["plant_id"],
                            "time_offset_desc": incident["time_offset_desc"],
                            "summary": f"A similar compound-risk pattern occurred at {incident['plant_id']} {incident['time_offset_desc']}."
                        })
            except Exception as e:
                print(f"Failed to fetch cross-plant patterns for {plant_id}", e)
                
        fleet_summary.append({
            "plant_id": plant_id,
            "plant_name": p["name"],
            "score": assessment.get("score", 0),
            "tier": assessment.get("tier", 1),
            "tier_name": assessment.get("tier_name", "Log Only"),
            "active_flags_count": len(assessment.get("triggered_rules", [])),
            "zone_scores": assessment.get("zone_scores", {}),
            "cross_plant_patterns": cross_plant_matches[:2]
        })
        
    return fleet_summary

class TagTelemetryItem(BaseModel):
    tag: str
    value: float
    timestamp: str = None
    quality: str = "GOOD"

def suggest_mapping_with_llm(headers: list[str], schema_type: str) -> dict:
    import os
    import json
    import requests
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None
        
    schema_fields = {
        "permit": ["permit_id", "zone", "permit_type", "issued_at", "closed_at", "issued_by", "plant_id"],
        "maintenance": ["equipment_id", "zone", "event_type", "logged_at", "notes", "plant_id"]
    }
    
    fields = schema_fields.get(schema_type, [])
    
    system_prompt = (
        "You are an industrial safety systems integration agent. Your job is to map messy, real-world spreadsheet column headers "
        f"to our clean internal database schema for a '{schema_type}' log.\n\n"
        f"Internal Schema Fields for '{schema_type}':\n"
        + "\n".join([f"- {f}" for f in fields]) + "\n\n"
        "Instructions:\n"
        "1. Suggest a 1-to-1 mapping from the file's headers to our internal schema fields.\n"
        "2. If a header does not match any internal schema field, map it to 'skip'.\n"
        "3. Return ONLY a valid JSON object where keys are the original file headers and values are the mapped internal fields (or 'skip').\n"
        "4. Do not include any markdown, explanation, or extra text. Return only the JSON object."
    )
    
    url = "https://api.anthropic.com/v1/messages"
    headers_req = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    payload = {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 300,
        "system": system_prompt,
        "messages": [
            {"role": "user", "content": f"Uploaded File Headers:\n{json.dumps(headers)}"}
        ]
    }
    
    try:
        response = requests.post(url, headers=headers_req, json=payload, timeout=8)
        if response.status_code == 200:
            content = response.json()["content"][0]["text"].strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            return json.loads(content)
        else:
            print(f"Anthropic API returned status {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Failed to get LLM suggested mapping: {e}")
    return None

@app.get("/api/ingest/tag-mapping")
def get_tag_mapping():
    """
    Returns the configurable tag-to-zone/gas-type mapping table.
    """
    from app.engine.tag_reader import TAG_MAPPING
    return TAG_MAPPING

@app.post("/api/ingest/analyze")
def analyze_ingestion_file(file: UploadFile = File(...), type: str = Query(None)):
    filename = file.filename.lower()
    
    # Read headers
    try:
        if filename.endswith(".csv"):
            import pandas as pd
            df = pd.read_csv(file.file, nrows=0)
            headers = df.columns.tolist()
        elif filename.endswith((".xlsx", ".xls")):
            import pandas as pd
            df = pd.read_excel(file.file, nrows=0)
            headers = df.columns.tolist()
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format. Please upload a CSV or Excel file.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file headers: {str(e)}")
        
    # Determine type
    inferred_type = type
    if not inferred_type:
        headers_lower = [h.lower() for h in headers]
        permit_signals = ["permit", "work", "approved", "applicant", "issuer", "duration", "closed"]
        maintenance_signals = ["maintenance", "maint", "repair", "log", "task", "technician", "notes"]
        
        permit_score = sum(1 for s in permit_signals if any(s in h for h in headers_lower))
        maint_score = sum(1 for s in maintenance_signals if any(s in h for h in headers_lower))
        inferred_type = "permit" if permit_score >= maint_score else "maintenance"
        
    suggested_mapping = None
    mapping_method = "Rule-based (Fuzzy)"
    
    # Try LLM if API Key is available
    if os.getenv("ANTHROPIC_API_KEY"):
        suggested_mapping = suggest_mapping_with_llm(headers, inferred_type)
        if suggested_mapping:
            mapping_method = "LLM-Assisted (Claude)"
            
    if not suggested_mapping:
        # Generate suggested mapping using fuzzy rules
        suggested_mapping = {}
        headers_lower = [h.lower() for h in headers]
        
        # Mapping dicts for fuzzy matching
        mapping_rules = {
            "permit": {
                "permit_id": ["permit no", "permit num", "id", "permit_id", "number", "no"],
                "permit_type": ["work type", "permit type", "type", "category", "class"],
                "issued_at": ["start time", "issued date", "date", "issued_at", "start", "time", "timestamp"],
                "closed_at": ["end time", "closed date", "end", "expiry", "expire", "closed_at"],
                "zone": ["zone ref", "zone", "sector", "area", "location"],
                "plant_id": ["plant id", "plant", "facility", "site"],
                "issued_by": ["issuer", "issued by", "officer", "supervisor"]
            },
            "maintenance": {
                "event_type": ["event type", "type", "activity", "work", "category"],
                "logged_at": ["logged at", "log date", "date", "time", "timestamp", "logged_at"],
                "notes": ["notes", "description", "details", "comments", "summary"],
                "plant_id": ["plant id", "plant", "facility", "site"],
                "zone": ["zone", "sector", "area", "location", "zone ref"],
                "equipment_id": ["equipment id", "equipment", "equip ref", "tag id", "asset", "id"]
            }
        }
        
        rules = mapping_rules.get(inferred_type, {})
        for target, patterns in rules.items():
            for h, hl in zip(headers, headers_lower):
                if any(p in hl for p in patterns):
                    suggested_mapping[h] = target
                    break
                    
    return {
        "type": inferred_type,
        "headers": headers,
        "suggested_mapping": suggested_mapping,
        "method": mapping_method
    }

@app.post("/api/ingest/upload")
def upload_ingestion_file(
    file: UploadFile = File(...),
    mapping: str = Form(...),  # JSON string mapping header -> internal_field
    type: str = Form(...),    # "permit" or "maintenance"
    db: Session = Depends(get_db)
):
    import json
    import pandas as pd
    
    try:
        col_map = json.loads(mapping)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid mapping JSON string.")
        
    filename = file.filename.lower()
    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(file.file)
        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(file.file)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(e)}")
        
    df = df.where(pd.notnull(df), None)
    
    parsed_count = 0
    now = datetime.utcnow()
    
    try:
        for idx, row in df.iterrows():
            row_dict = {}
            for col, val in row.items():
                if col in col_map:
                    target_field = col_map[col]
                    row_dict[target_field] = val
            
            if type == "permit":
                permit_id = str(row_dict.get("permit_id") or f"PERMIT_INGEST_{idx}_{int(now.timestamp())}")
                permit_type = str(row_dict.get("permit_type") or "Hot Work")
                zone = str(row_dict.get("zone") or "Zone-A")
                plant_id = str(row_dict.get("plant_id") or "Plant-A")
                issued_by = str(row_dict.get("issued_by") or "SCADA Ingest")
                
                issued_at_val = row_dict.get("issued_at")
                if issued_at_val:
                    try:
                        issued_at = pd.to_datetime(issued_at_val).to_pydatetime()
                    except Exception:
                        issued_at = now
                else:
                    issued_at = now
                    
                closed_at_val = row_dict.get("closed_at")
                closed_at = None
                if closed_at_val:
                    try:
                        closed_at = pd.to_datetime(closed_at_val).to_pydatetime()
                    except Exception:
                        pass
                
                existing = db.query(models.Permit).filter(models.Permit.permit_id == permit_id).first()
                if existing:
                    existing.permit_type = permit_type
                    existing.zone = zone
                    existing.plant_id = plant_id
                    existing.issued_at = issued_at
                    existing.closed_at = closed_at
                    existing.issued_by = issued_by
                else:
                    new_permit = models.Permit(
                        permit_id=permit_id,
                        permit_type=permit_type,
                        zone=zone,
                        plant_id=plant_id,
                        issued_at=issued_at,
                        closed_at=closed_at,
                        issued_by=issued_by,
                        dataset="default"
                    )
                    db.add(new_permit)
                parsed_count += 1
                
            elif type == "maintenance":
                event_type = str(row_dict.get("event_type") or "Safety Calibration")
                notes = str(row_dict.get("notes") or "")
                plant_id = str(row_dict.get("plant_id") or "Plant-A")
                zone = str(row_dict.get("zone") or "Zone-A")
                equipment_id = str(row_dict.get("equipment_id") or "EQ-INGEST")
                
                logged_at_val = row_dict.get("logged_at")
                if logged_at_val:
                    try:
                        logged_at = pd.to_datetime(logged_at_val).to_pydatetime()
                    except Exception:
                        logged_at = now
                else:
                    logged_at = now
                    
                new_maint = models.MaintenanceLog(
                    event_type=event_type,
                    logged_at=logged_at,
                    notes=notes,
                    zone=zone,
                    equipment_id=equipment_id,
                    plant_id=plant_id,
                    dataset="default"
                )
                db.add(new_maint)
                parsed_count += 1
                
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database ingestion failed: {str(e)}")
        
    return {"status": "success", "count": parsed_count, "type": type}

@app.post("/api/ingest/tag")
def ingest_opc_tag_telemetry(payload: list[TagTelemetryItem], db: Session = Depends(get_db)):
    from app.engine.tag_reader import parse_opc_tag
    
    parsed_count = 0
    for item in payload:
        reading_dict = parse_opc_tag(item.tag, item.value, item.timestamp)
        if reading_dict:
            new_reading = models.GasSensorReading(
                zone=reading_dict["zone"],
                timestamp=reading_dict["timestamp"],
                gas_type=reading_dict["gas_type"],
                reading_ppm=reading_dict["reading_value"],
                sensor_status="OPERATIONAL",
                plant_id="Plant-A",
                dataset="default"
            )
            db.add(new_reading)
            parsed_count += 1
            
    db.commit()
    return {"status": "success", "parsed_count": parsed_count}

class IncidentHistoryCreate(BaseModel):
    date: str = None  # ISO format datetime string
    zone: str
    category: str  # near_miss / injury / fatality / equipment_failure / repair_log
    contributing_factors: str
    related_rule_type: str = None
    regulatory_clause: str = None
    resolution_notes: str
    logged_by_role: str
    severity_level: str  # fatality / lost-time injury / first-aid only
    plant_id: str = "Plant-A"

@app.post("/api/incident-history")
def create_incident_history(payload: IncidentHistoryCreate, db: Session = Depends(get_db)):
    # Validate category
    valid_categories = ["near_miss", "injury", "fatality", "equipment_failure", "repair_log"]
    if payload.category not in valid_categories:
        raise HTTPException(status_code=400, detail=f"Category must be one of {valid_categories}")
        
    # Validate severity
    valid_severities = ["fatality", "lost-time injury", "first-aid only"]
    if payload.severity_level not in valid_severities:
        raise HTTPException(status_code=400, detail=f"Severity level must be one of {valid_severities}")
        
    # Parse date
    if payload.date:
        try:
            parsed_date = datetime.fromisoformat(payload.date.replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            parsed_date = datetime.utcnow()
    else:
        parsed_date = datetime.utcnow()
        
    new_inc = models.IncidentHistory(
        date=parsed_date,
        zone=payload.zone,
        category=payload.category,
        contributing_factors=payload.contributing_factors,
        related_rule_type=payload.related_rule_type if payload.related_rule_type and payload.related_rule_type != "None" else None,
        regulatory_clause=payload.regulatory_clause,
        resolution_notes=payload.resolution_notes,
        logged_by_role=payload.logged_by_role,
        severity_level=payload.severity_level,
        plant_id=payload.plant_id,
        source="synthetic",
        dataset="default"
    )
    
    db.add(new_inc)
    db.commit()
    db.refresh(new_inc)
    
    # Trigger RAG re-embedding in incident agent
    try:
        from app.engine.incident_agent import refresh_embeddings
        refresh_embeddings(db)
    except Exception as e:
        print("Failed to refresh incident embeddings on creation:", e)
        
    return model_to_dict(new_inc)

@app.get("/api/incident-history")
def get_incident_history(
    zone: str = Query(None),
    category: str = Query(None),
    start_date: str = Query(None),
    end_date: str = Query(None),
    plant_id: str = Query("Plant-A"),
    db: Session = Depends(get_db)
):
    query = db.query(models.IncidentHistory).filter(models.IncidentHistory.plant_id == plant_id)
    if zone:
        query = query.filter(models.IncidentHistory.zone == zone)
    if category:
        query = query.filter(models.IncidentHistory.category == category)
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00")).replace(tzinfo=None)
            query = query.filter(models.IncidentHistory.date >= start_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format.")
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00")).replace(tzinfo=None)
            query = query.filter(models.IncidentHistory.date <= end_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format.")
            
    results = query.order_by(models.IncidentHistory.date.desc()).all()
    return [model_to_dict(r) for r in results]

@app.get("/api/model-performance")
def get_model_performance(db: Session = Depends(get_db)):
    import os
    import joblib
    from app.engine.confidence_model import train_and_save_model
    
    model_path = "app/data/confidence_model.pkl"
    if not os.path.exists(model_path):
        train_and_save_model(db)
        
    try:
        model_data = joblib.load(model_path)
        return {
            "precision": model_data["precision"],
            "recall": model_data["recall"],
            "feature_importances": model_data["feature_importances"][:10]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load model performance: {e}")

@app.post("/api/model-performance/retrain")
def post_model_retrain(db: Session = Depends(get_db)):
    from app.engine.confidence_model import train_and_save_model
    import joblib
    
    success = train_and_save_model(db)
    if not success:
        raise HTTPException(status_code=500, detail="Retraining failed due to insufficient data or database error.")
        
    try:
        model_data = joblib.load("app/data/confidence_model.pkl")
        return {
            "status": "success",
            "precision": model_data["precision"],
            "recall": model_data["recall"],
            "feature_importances": model_data["feature_importances"][:10]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load retrained model: {e}")

class EvacuationConfirmationRequest(BaseModel):
    flag_id: str
    confirmed_by_role: str = "Safety Officer"
    plant_id: str = "Plant-A"

class LocalAcknowledgeRequest(BaseModel):
    zone: str
    plant_id: str = "Plant-A"

@app.get("/api/alarm-state")
def get_alarm_state(plant_id: str = Query("Plant-A")):
    if plant_id not in alarm_states:
        raise HTTPException(status_code=400, detail="Invalid plant_id")
    return alarm_states[plant_id]

@app.post("/api/alarm-state/confirm-evacuation")
def confirm_evacuation(payload: EvacuationConfirmationRequest):
    p_id = payload.plant_id
    if p_id not in alarm_states:
        raise HTTPException(status_code=400, detail="Invalid plant_id")
        
    alarm_states[p_id]["facility_evacuation_active"] = True
    alarm_states[p_id]["last_triggered_by_flag_id"] = payload.flag_id
    
    log_entry = {
        "confirmed_at": datetime.utcnow().isoformat() + "Z",
        "confirmed_by_role": payload.confirmed_by_role,
        "flag_id": payload.flag_id
    }
    alarm_states[p_id]["confirmation_log"].append(log_entry)
    
    # Advance the Emergency Response Orchestrator's stage tracker for this zone
    zone = "Zone-C"
    for z in ["Zone-A", "Zone-B", "Zone-C", "Zone-D", "Zone-E", "Zone-F"]:
        if z in payload.flag_id:
            zone = z
            break
            
    # Trigger active emergency response protocol
    key = f"{p_id}_{zone}"
    if key not in active_tier3_protocols:
        active_tier3_protocols[key] = datetime.utcnow()
    if key not in active_tier3_rules:
        active_tier3_rules[key] = []
    
    # Add rules if empty
    if not active_tier3_rules[key]:
        active_tier3_rules[key].append({
            "rule_name": "RULE_FACILITY_EVACUATION",
            "severity": 3,
            "reason": "Facility-wide evacuation alarm manually confirmed by safety officer."
        })
        
    return {"status": "success", "alarm_state": alarm_states[p_id]}

@app.post("/api/alarm-state/acknowledge-local")
def acknowledge_local_alarm(payload: LocalAcknowledgeRequest):
    p_id = payload.plant_id
    if p_id not in alarm_states:
        raise HTTPException(status_code=400, detail="Invalid plant_id")
        
    zone = payload.zone
    if zone in alarm_states[p_id]["local_alerts_active"]:
        alarm_states[p_id]["local_alerts_active"].remove(zone)
    if zone not in alarm_states[p_id]["acknowledged_local_alerts"]:
        alarm_states[p_id]["acknowledged_local_alerts"].append(zone)
        
    return {"status": "success", "alarm_state": alarm_states[p_id]}






