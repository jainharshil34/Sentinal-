from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.db import models

# Adjacency map for industrial zones
ADJACENCY_MAP = {
    "Zone-A": ["Zone-A", "Zone-B"],
    "Zone-B": ["Zone-A", "Zone-B", "Zone-C"],
    "Zone-C": ["Zone-B", "Zone-C", "Zone-D"],
    "Zone-D": ["Zone-C", "Zone-D", "Zone-E"],
    "Zone-E": ["Zone-D", "Zone-E", "Zone-F"],
    "Zone-F": ["Zone-E", "Zone-F"],
}

GAS_TYPES = ["H2S", "CO", "CH4"]

def model_to_dict(instance):
    """Helper to convert SQLAlchemy model instance to dictionary for JSON output"""
    if instance is None:
        return None
    return {col.name: (getattr(instance, col.name).isoformat() if isinstance(getattr(instance, col.name), datetime) else getattr(instance, col.name))
            for col in instance.__table__.columns}

def get_adjusted_weights(db: Session, plant_id: str = "Plant-A") -> tuple[dict[str, float], list[dict]]:
    """
    Queries feedback_logs, calculates True Positive Rate (TPR) per rule, and returns:
    1. A dictionary mapping rule_name to adjusted_severity (float)
    2. A list of auditable adjustment log objects
    """
    if db is None:
        return {}, []

    # Dynamic import to prevent circular dependencies
    from app.db.models import FeedbackLog
    
    logs = db.query(FeedbackLog).filter(FeedbackLog.plant_id == plant_id).all()
    
    # Aggregate verdicts per rule_name
    stats = {}
    for log in logs:
        r_name = log.rule_name
        if r_name not in stats:
            stats[r_name] = {"confirmed": 0, "false_alarm": 0, "total": 0}
        stats[r_name]["total"] += 1
        if log.officer_verdict == "Confirmed Risk":
            stats[r_name]["confirmed"] += 1
        else:
            stats[r_name]["false_alarm"] += 1
            
    # Default severities for reference
    default_severities = {
        "RULE_HOT_WORK_NEAR_GAS_SPIKE": 3.0,
        "RULE_CONFINED_SPACE_NEAR_GAS_SPIKE": 3.0,
        "RULE_ELECTRICAL_WORK_NEAR_GAS_SPIKE": 2.0,
        "RULE_OVERDUE_MAINTENANCE_ACTIVE_PERMIT": 2.0,
        "RULE_SILENT_SENSOR_DURING_PERMIT": 2.0,
        "RULE_PERMIT_DURING_ACTIVE_REPAIR": 2.0,
        "RULE_MULTI_GAS_COMPOUND_TOXICITY": 3.0,
        "RULE_VERBAL_HAZARD_REPORT_ACTIVE_PERMIT": 3.0,
        "RULE_ADJACENT_ZONE_ESCALATION": 1.0
    }
    
    adjusted_weights = {}
    adjustments_log = []
    
    for rule_name, default_sev in default_severities.items():
        adjusted_weights[rule_name] = default_sev
        
        if rule_name in stats:
            s = stats[rule_name]
            total = s["total"]
            false_alarms = s["false_alarm"]
            confirmed = s["confirmed"]
            tpr = confirmed / total if total > 0 else 1.0
            
            # Check adjustment triggers
            if false_alarms >= 3:
                reduction = 0.0
                if tpr < 0.4:
                    reduction = 1.0
                elif tpr < 0.7:
                    reduction = 0.5
                    
                if reduction > 0.0:
                    adjusted_sev = max(0.5, default_sev - reduction)
                    adjusted_weights[rule_name] = adjusted_sev
                    
                    adjustments_log.append({
                        "rule_name": rule_name,
                        "original_severity": default_sev,
                        "adjusted_severity": adjusted_sev,
                        "verdict_ratio": f"{confirmed}/{total} ({round(tpr*100, 1)}% TPR)",
                        "reason": f"Accumulated {false_alarms} False Alarms (threshold: 3). Severity reduced by {reduction} to mitigate alarm fatigue."
                    })
                    
    return adjusted_weights, adjustments_log


def forecast_time_to_threshold(readings: list, threshold: float) -> tuple[float | None, float | None]:
    """
    Fits a simple linear regression on the provided sensor readings list.
    Returns: (predicted_minutes_to_breach, confidence_interval_minutes) or (None, None).
    """
    import math
    if len(readings) < 3:
        return None, None
        
    t0 = readings[0].timestamp
    x = []
    y = []
    for r in readings:
        minutes = (r.timestamp - t0).total_seconds() / 60.0
        x.append(minutes)
        y.append(r.reading_ppm)
        
    n = len(readings)
    sum_x = sum(x)
    sum_y = sum(y)
    sum_xx = sum(xi * xi for xi in x)
    sum_xy = sum(xi * yi for xi, yi in zip(x, y))
    
    denom = n * sum_xx - sum_x * sum_x
    if denom == 0:
        return None, None
        
    m = (n * sum_xy - sum_x * sum_y) / denom
    c = (sum_y - m * sum_x) / n
    
    # Check if the trend is rising
    if m <= 0.0001:
        return None, None
        
    last_x = x[-1]
    last_y = y[-1]
    
    # Already breached
    if last_y >= threshold:
        return 0.0, 0.0
        
    x_cross = (threshold - c) / m
    predicted_minutes = x_cross - last_x
    if predicted_minutes < 0:
        return None, None
        
    # Standard Error of Residuals
    residuals = []
    for xi, yi in zip(x, y):
        pred_y = m * xi + c
        residuals.append(yi - pred_y)
        
    if n > 2:
        rss = sum(r * r for r in residuals)
        se = math.sqrt(rss / (n - 2))
    else:
        se = 0.5
        
    time_err = (1.96 * se) / m if m > 0 else 0.0
    time_err = max(1.0, min(time_err, predicted_minutes * 0.5))
    
    return round(predicted_minutes, 1), round(time_err, 1)


def detect_compound_risk(
    db: Session,
    start_time: datetime,
    end_time: datetime,
    dataset: str = "default",
    plant_id: str = "Plant-A",
    exclude_permit_ids: list[str] = None,
    exclude_maint_ids: list[int] = None
) -> dict:
    """
    LAYER 1 — Rule-based correlation:
    Scans gas sensor readings, permits, and maintenance logs in the given window
    and correlates them to detect compound risks.
    """
    # 1. Fetch relevant records
    # Gas readings: fetch within the window, and also 15 min prior to verify trends
    gas_start = start_time - timedelta(minutes=15)
    gas_readings = db.query(models.GasSensorReading).filter(
        models.GasSensorReading.timestamp >= gas_start,
        models.GasSensorReading.timestamp <= end_time,
        models.GasSensorReading.dataset == dataset,
        models.GasSensorReading.plant_id == plant_id
    ).order_by(models.GasSensorReading.timestamp.asc()).all()

    # Permits active in the window
    permits = db.query(models.Permit).filter(
        models.Permit.issued_at <= end_time,
        models.Permit.dataset == dataset,
        models.Permit.plant_id == plant_id
    ).all()
    # filter in python for closed_at to support nullable/active permits
    permits = [p for p in permits if p.closed_at is None or p.closed_at >= start_time]

    # Maintenance logs logged in the window
    # Overdue maintenance logs can be queried in a trailing 24h window
    maint_start = end_time - timedelta(hours=24)
    maint_logs = db.query(models.MaintenanceLog).filter(
        models.MaintenanceLog.logged_at >= maint_start,
        models.MaintenanceLog.logged_at <= end_time,
        models.MaintenanceLog.dataset == dataset,
        models.MaintenanceLog.plant_id == plant_id
    ).all()

    # Verbal hazard reports logged in a trailing 12h window
    verbal_start = end_time - timedelta(hours=12)
    verbal_reports = db.query(models.VerbalReport).filter(
        models.VerbalReport.timestamp >= verbal_start,
        models.VerbalReport.timestamp <= end_time,
        models.VerbalReport.dataset == dataset,
        models.VerbalReport.plant_id == plant_id
    ).all()

    # Apply exclusions for counterfactual simulation
    if exclude_permit_ids:
        permits = [p for p in permits if p.permit_id not in exclude_permit_ids]
    if exclude_maint_ids:
        maint_logs = [m for m in maint_logs if m.id not in exclude_maint_ids]

    # Fetch adjusted weights based on feedback
    adjusted_weights, adjustments_log = get_adjusted_weights(db, plant_id)

    triggered_rules = []
    all_contributing_records = set()

    # Helper to track contributing database objects
    def add_contrib(record):
        all_contributing_records.add(record)
        return model_to_dict(record)

    # Pre-process gas readings: group by (zone, gas_type)
    gas_by_zone_type = {}
    for r in gas_readings:
        key = (r.zone, r.gas_type)
        if key not in gas_by_zone_type:
            gas_by_zone_type[key] = []
        gas_by_zone_type[key].append(r)

    # Helper to analyze gas trend in the last 15 min of the window
    def get_gas_trend(zone: str, gas_type: str) -> tuple[float, float, list]:
        """Returns: (final_reading, increase_15m, contributing_readings)"""
        readings = gas_by_zone_type.get((zone, gas_type), [])
        # filter to last 15 min of the window: [end_time - 15m, end_time]
        window_15m_start = end_time - timedelta(minutes=15)
        recent_readings = [r for r in readings if window_15m_start <= r.timestamp <= end_time]
        
        if not recent_readings:
            return 0.0, 0.0, []
        
        final_val = recent_readings[-1].reading_ppm
        first_val = recent_readings[0].reading_ppm
        increase = final_val - first_val
        return final_val, increase, recent_readings

    watch_flags = []

    # Helper to check proximity and trend for Watch flags
    def evaluate_watch(zone: str, gas_type: str, threshold: float, proximity_low: float):
        readings = gas_by_zone_type.get((zone, gas_type), [])
        # filter to end_time
        readings = [r for r in readings if r.timestamp <= end_time]
        if len(readings) < 3:
            return
        
        v3 = readings[-3].reading_ppm
        v2 = readings[-2].reading_ppm
        v1 = readings[-1].reading_ppm
        
        # Determine trend
        if v1 > v2 > v3:
            trend = "rising"
        elif v1 < v2 < v3:
            trend = "falling"
        else:
            if v1 > v3:
                trend = "rising"
            elif v1 < v3:
                trend = "falling"
            else:
                trend = "stable"
                
        if proximity_low <= v1 < threshold and trend == "rising":
            # Run forecasting on trailing 45 minutes of readings
            m45_start = end_time - timedelta(minutes=45)
            forecast_readings = [r for r in readings if r.timestamp >= m45_start]
            
            pred_minutes, conf_int = forecast_time_to_threshold(forecast_readings, threshold)
            
            if pred_minutes is not None:
                message = f"{gas_type} trending up, {round(v1, 1)}ppm → predicted to cross {threshold}ppm threshold in approximately {int(round(pred_minutes))} minutes (±{int(round(conf_int))} mins)."
            else:
                message = f"{gas_type} trending up, {round(v1, 1)}ppm, threshold {threshold}ppm."
                
            watch_flags.append({
                "zone": zone,
                "signal_type": gas_type,
                "current_value": round(v1, 2),
                "threshold": threshold,
                "trend": trend,
                "predicted_threshold_breach_minutes": pred_minutes,
                "confidence_interval": conf_int,
                "message": message
            })

    # --- RULE EVALUATIONS ---
    for permit in permits:
        p_zone = permit.zone
        p_type = permit.permit_type
        adjacent_zones = ADJACENCY_MAP.get(p_zone, [p_zone])

        # Evaluate watch flags for relevant gas rule conditions
        for zone in adjacent_zones:
            if p_type == "hot_work":
                evaluate_watch(zone, "CH4", 10.0, 7.0)
                evaluate_watch(zone, "H2S", 5.0, 3.5)
                evaluate_watch(zone, "CO", 25.0, 17.5)
            elif p_type == "confined_space":
                evaluate_watch(zone, "CO", 25.0, 17.5)
                evaluate_watch(zone, "H2S", 2.0, 1.4)
            elif p_type == "electrical":
                evaluate_watch(zone, "CH4", 10.0, 7.0)

        # A. RULE_HOT_WORK_NEAR_GAS_SPIKE (Severity: 3)
        # Aligns with safety standards:
        # - CH4: > 10.0 % LEL (representing 10% of Lower Explosive Limit, i.e., 5,000 ppm equivalent)
        # - H2S: > 5.0 ppm (ACGIH 15-minute Short-Term Exposure Limit STEL is 5 ppm)
        # - CO: > 25.0 ppm (ACGIH 8-hour Time-Weighted Average TWA is 25 ppm)
        if p_type == "hot_work":
            # Check CH4, H2S, CO in same/adjacent zones
            for zone in adjacent_zones:
                # CH4 Trend/Threshold check (CH4 >= 10.0% LEL)
                ch4_val, ch4_inc, ch4_contrib = get_gas_trend(zone, "CH4")
                if ch4_val >= 10.0:
                    contrib = [add_contrib(permit)] + [add_contrib(r) for r in ch4_contrib]
                    r_name = "RULE_HOT_WORK_NEAR_GAS_SPIKE"
                    triggered_rules.append({
                        "flag_id": f"{r_name}_{zone}_{int(end_time.timestamp())}",
                        "rule_name": r_name,
                        "severity": adjusted_weights.get(r_name, 3.0),
                        "reason": f"Active hot work permit in {p_zone} correlates with elevated explosive CH4 levels ({ch4_val}% LEL) in adjacent {zone}.",
                        "contributing_signals": contrib
                    })

                # H2S Trend/Threshold check (H2S >= 5.0 ppm, aligned with ACGIH STEL)
                h2s_val, h2s_inc, h2s_contrib = get_gas_trend(zone, "H2S")
                if h2s_val >= 5.0:
                    contrib = [add_contrib(permit)] + [add_contrib(r) for r in h2s_contrib]
                    r_name = "RULE_HOT_WORK_NEAR_GAS_SPIKE"
                    triggered_rules.append({
                        "flag_id": f"{r_name}_{zone}_{int(end_time.timestamp())}",
                        "rule_name": r_name,
                        "severity": adjusted_weights.get(r_name, 3.0),
                        "reason": f"Active hot work permit in {p_zone} correlates with elevated toxic H2S levels ({h2s_val} ppm) in adjacent {zone}.",
                        "contributing_signals": contrib
                    })

                # CO Trend/Threshold check (CO >= 25.0 ppm, aligned with ACGIH TLV-TWA)
                co_val, co_inc, co_contrib = get_gas_trend(zone, "CO")
                if co_val >= 25.0:
                    contrib = [add_contrib(permit)] + [add_contrib(r) for r in co_contrib]
                    r_name = "RULE_HOT_WORK_NEAR_GAS_SPIKE"
                    triggered_rules.append({
                        "flag_id": f"{r_name}_{zone}_{int(end_time.timestamp())}",
                        "rule_name": r_name,
                        "severity": adjusted_weights.get(r_name, 3.0),
                        "reason": f"Active hot work permit in {p_zone} correlates with elevated toxic CO levels ({co_val} ppm) in adjacent {zone}.",
                        "contributing_signals": contrib
                    })

        # B. RULE_CONFINED_SPACE_NEAR_GAS_SPIKE (Severity: 3)
        # Aligns with safety standards:
        # - CO: >= 25.0 ppm (ACGIH TLV-TWA is 25 ppm)
        # - H2S: >= 2.0 ppm (highly toxic, above ACGIH TLV-TWA of 1 ppm)
        if p_type == "confined_space":
            # Check CO, H2S in same/adjacent zones
            for zone in adjacent_zones:
                # CO Trend/Threshold check (CO >= 25.0 ppm)
                co_val, co_inc, co_contrib = get_gas_trend(zone, "CO")
                if co_val >= 25.0:
                    contrib = [add_contrib(permit)] + [add_contrib(r) for r in co_contrib]
                    r_name = "RULE_CONFINED_SPACE_NEAR_GAS_SPIKE"
                    triggered_rules.append({
                        "flag_id": f"{r_name}_{zone}_{int(end_time.timestamp())}",
                        "rule_name": r_name,
                        "severity": adjusted_weights.get(r_name, 3.0),
                        "reason": f"Active confined space entry in {p_zone} correlates with elevated toxic CO levels ({co_val} ppm) in adjacent {zone}.",
                        "contributing_signals": contrib
                    })

                # H2S Trend/Threshold check (H2S >= 2.0 ppm)
                h2s_val, h2s_inc, h2s_contrib = get_gas_trend(zone, "H2S")
                if h2s_val >= 2.0:
                    contrib = [add_contrib(permit)] + [add_contrib(r) for r in h2s_contrib]
                    r_name = "RULE_CONFINED_SPACE_NEAR_GAS_SPIKE"
                    triggered_rules.append({
                        "flag_id": f"{r_name}_{zone}_{int(end_time.timestamp())}",
                        "rule_name": r_name,
                        "severity": adjusted_weights.get(r_name, 3.0),
                        "reason": f"Active confined space entry in {p_zone} correlates with elevated highly toxic H2S levels ({h2s_val} ppm) in adjacent {zone}.",
                        "contributing_signals": contrib
                    })

        # C. RULE_ELECTRICAL_WORK_NEAR_GAS_SPIKE (Severity: 2)
        # Aligns with safety standards:
        # - CH4: >= 10.0 % LEL (spark hazards at 10% LEL)
        if p_type == "electrical":
            for zone in adjacent_zones:
                ch4_val, ch4_inc, ch4_contrib = get_gas_trend(zone, "CH4")
                if ch4_val >= 10.0:
                    contrib = [add_contrib(permit)] + [add_contrib(r) for r in ch4_contrib]
                    r_name = "RULE_ELECTRICAL_WORK_NEAR_GAS_SPIKE"
                    triggered_rules.append({
                        "flag_id": f"{r_name}_{zone}_{int(end_time.timestamp())}",
                        "rule_name": r_name,
                        "severity": adjusted_weights.get(r_name, 2.0),
                        "reason": f"Active electrical permit in {p_zone} correlates with elevated flammable CH4 levels ({ch4_val}% LEL) in adjacent {zone}.",
                        "contributing_signals": contrib
                    })

        # D. RULE_OVERDUE_MAINTENANCE_ACTIVE_PERMIT (Severity: 2)
        # Check for any overdue maintenance in the same zone as the active permit
        for log in maint_logs:
            if log.zone == p_zone and log.event_type == "overdue_flag":
                contrib = [add_contrib(permit), add_contrib(log)]
                r_name = "RULE_OVERDUE_MAINTENANCE_ACTIVE_PERMIT"
                triggered_rules.append({
                    "flag_id": f"{r_name}_{p_zone}_{int(end_time.timestamp())}",
                    "rule_name": r_name,
                    "severity": adjusted_weights.get(r_name, 2.0),
                    "reason": f"Active permit ({p_type}) in {p_zone} correlates with overdue maintenance on equipment {log.equipment_id} in the same zone.",
                    "contributing_signals": contrib
                })

        # E. RULE_SILENT_SENSOR_DURING_PERMIT (Severity: 2)
        # Check if any sensor in the permit zone is silent during the current window
        for gas in GAS_TYPES:
            readings_in_window = gas_by_zone_type.get((p_zone, gas), [])
            # filter to active window
            window_readings = [r for r in readings_in_window if start_time <= r.timestamp <= end_time]
            silent_readings = [r for r in window_readings if r.sensor_status == "silent"]
            
            if silent_readings:
                contrib = [add_contrib(permit)] + [add_contrib(r) for r in silent_readings]
                r_name = "RULE_SILENT_SENSOR_DURING_PERMIT"
                triggered_rules.append({
                    "flag_id": f"{r_name}_{p_zone}_{int(end_time.timestamp())}",
                    "rule_name": r_name,
                    "severity": adjusted_weights.get(r_name, 2.0),
                    "reason": f"Sensor for {gas} in {p_zone} went silent during active permit ({p_type}). Safety telemetry is offline.",
                    "contributing_signals": contrib
                })
                # Break to avoid duplicate alerts for the same zone/permit if multiple readings are silent
                break

        # F. RULE_PERMIT_DURING_ACTIVE_REPAIR (Severity: 2)
        for log in maint_logs:
            if log.zone == p_zone and log.event_type == "repair":
                contrib = [add_contrib(permit), add_contrib(log)]
                r_name = "RULE_PERMIT_DURING_ACTIVE_REPAIR"
                triggered_rules.append({
                    "flag_id": f"{r_name}_{p_zone}_{int(end_time.timestamp())}",
                    "rule_name": r_name,
                    "severity": adjusted_weights.get(r_name, 2.0),
                    "reason": f"Active permit ({p_type}) in {p_zone} overlaps with ongoing equipment repair ({log.equipment_id}) in the same zone.",
                    "contributing_signals": contrib
                })

    # F2. RULE_VERBAL_HAZARD_REPORT_ACTIVE_PERMIT (Severity: 3)
    for vr in verbal_reports:
        if vr.urgency_signal in ["high", "medium"]:
            v_zone = vr.zone
            active_p_in_zone = [p for p in permits if p.zone == v_zone]
            if active_p_in_zone:
                contrib = [add_contrib(vr)] + [add_contrib(p) for p in active_p_in_zone]
                r_name = "RULE_VERBAL_HAZARD_REPORT_ACTIVE_PERMIT"
                quote_str = f"'{vr.raw_quote}'" if vr.raw_quote else f"'{vr.transcript}'"
                triggered_rules.append({
                    "flag_id": f"{r_name}_{v_zone}_{int(end_time.timestamp())}",
                    "rule_name": r_name,
                    "severity": adjusted_weights.get(r_name, 3.0),
                    "reason": f"Verbal hazard report in {v_zone} ({quote_str}) correlates with active permit ({active_p_in_zone[0].permit_type}) in the same zone.",
                    "contributing_signals": contrib
                })

    # SECOND PASS — Cascading Risk Escalation (RULE_ADJACENT_ZONE_ESCALATION)
    # Find all zones that reached Tier 3 based on the primary first-pass rules.
    tier3_zones = set()
    for rule in triggered_rules:
        if rule.get("severity", 0) >= 3:
            for sig in rule.get("contributing_signals", []):
                if sig.get("zone"):
                    tier3_zones.add(sig["zone"])

    cascaded_zones = set()
    # Iterate over Tier 3 zones to evaluate adjacent zones with active permits
    for Z_A in list(tier3_zones):
        adjacents = ADJACENCY_MAP.get(Z_A, [])
        for Z_B in adjacents:
            if Z_B != Z_A and Z_B not in tier3_zones and Z_B not in cascaded_zones:
                active_p_in_zb = [p for p in permits if p.zone == Z_B]
                if active_p_in_zb:
                    cascaded_zones.add(Z_B)
                    contrib = []
                    for p in active_p_in_zb:
                        all_contributing_records.add(p)
                        contrib.append(model_to_dict(p))
                        
                    r_name = "RULE_ADJACENT_ZONE_ESCALATION"
                    triggered_rules.append({
                        "flag_id": f"{r_name}_{Z_B}_{int(end_time.timestamp())}",
                        "rule_name": r_name,
                        "severity": 1,
                        "reason": f"Elevated due to cascading risk from adjacent {Z_A} reaching Tier 3.",
                        "contributing_signals": contrib
                    })

    # G. RULE_MULTI_GAS_COMPOUND_TOXICITY (Severity: 3)
    # Toxicological compound-exposure risk: OSHA/ACGIH Mixture Exposure Hazard Index formula:
    # HI = sum(C_i / TLV_i) where TLV: CH4=10.0% LEL, H2S=5.0 ppm, CO=25.0 ppm.
    # Simultaneous presence of multiple sub-threshold gases presents synergistic toxicity/explosion danger.
    for zone in ["Zone-A", "Zone-B", "Zone-C", "Zone-D", "Zone-E", "Zone-F"]:
        ch4_val, _, ch4_contrib = get_gas_trend(zone, "CH4")
        h2s_val, _, h2s_contrib = get_gas_trend(zone, "H2S")
        co_val, _, co_contrib = get_gas_trend(zone, "CO")
        
        # Calculate OSHA/ACGIH Mixture Exposure Hazard Index
        ch4_frac = ch4_val / 10.0
        h2s_frac = h2s_val / 5.0
        co_frac = co_val / 25.0
        hazard_index = round(ch4_frac + h2s_frac + co_frac, 2)
        
        elevated_gases = []
        contrib_readings = []
        
        if ch4_val > 6.0 or ch4_frac >= 0.3:
            elevated_gases.append(f"CH4 ({ch4_val}% LEL)")
            contrib_readings.extend(ch4_contrib)
        if h2s_val > 3.0 or h2s_frac >= 0.3:
            elevated_gases.append(f"H2S ({h2s_val} ppm)")
            contrib_readings.extend(h2s_contrib)
        if co_val > 15.0 or co_frac >= 0.3:
            elevated_gases.append(f"CO ({co_val} ppm)")
            contrib_readings.extend(co_contrib)
            
        if len(elevated_gases) >= 2:
            contrib = []
            for r in contrib_readings:
                all_contributing_records.add(r)
                contrib.append(model_to_dict(r))
            
            r_name = "RULE_MULTI_GAS_COMPOUND_TOXICITY"
            triggered_rules.append({
                "flag_id": f"{r_name}_{zone}_{int(end_time.timestamp())}",
                "rule_name": r_name,
                "severity": adjusted_weights.get(r_name, 3.0),
                "reason": f"Simultaneous elevated gases detected in {zone}: {', '.join(elevated_gases)} (OSHA Hazard Index HI={hazard_index}). Synergistic toxic/flammable compound exposure.",
                "contributing_signals": contrib
            })

    # Deduplicate watch flags
    unique_watch = []
    seen_wf = set()
    for wf in watch_flags:
        key = (wf["zone"], wf["signal_type"])
        if key not in seen_wf:
            seen_wf.add(key)
            unique_watch.append(wf)

    # Predict safety officer confirmation confidence for each active rule
    try:
        from app.engine.confidence_model import predict_flag_confidence
        for rule in triggered_rules:
            r_name = rule["rule_name"]
            zone = "Zone-A"
            for z in ["Zone-A", "Zone-B", "Zone-C", "Zone-D", "Zone-E", "Zone-F"]:
                if z in rule.get("flag_id", ""):
                    zone = z
                    break
            
            num_co_firing = len(triggered_rules)
            conf = predict_flag_confidence(db, r_name, zone, end_time, num_co_firing)
            rule["predicted_confidence"] = round(conf, 3)
            
            # Count past similar flags for this rule
            total_past_logs = db.query(models.FeedbackLog).filter(models.FeedbackLog.rule_name == r_name).count()
            rule["past_similar_flags_count"] = total_past_logs
    except Exception as e:
        print("Confidence prediction failed:", e)

    # LAYER 2 — Aggregate scoring
    assessment = calculate_aggregate_score(triggered_rules, unique_watch)
    assessment["zone_scores"] = calculate_zone_scores(triggered_rules, unique_watch)
    
    # Format contributing signals (ensure unique values by ID)
    unique_contrib = []
    seen_ids = set()
    for rec in all_contributing_records:
        rec_dict = model_to_dict(rec)
        # Combine model class name with ID to form unique key
        unique_key = f"{rec.__class__.__name__}_{rec.id}"
        if unique_key not in seen_ids:
            seen_ids.add(unique_key)
            # Add table/model identifier for frontend convenience
            rec_dict["type"] = rec.__class__.__name__
            unique_contrib.append(rec_dict)

    assessment["contributing_signals"] = unique_contrib
    assessment["watch_flags"] = unique_watch
    assessment["confidence_adjustments"] = adjustments_log
    return assessment


def compute_watch_score(watch_flags: list[dict]) -> int:
    """
    Calculates dynamic watch score (15-39) based on gas proximity ratio to threshold
    and linear regression forecast breach time.
    """
    if not watch_flags:
        return 0
    scores = []
    for wf in watch_flags:
        v = wf.get("current_value", 0.0)
        t = wf.get("threshold", 1.0)
        proximity_ratio = min(1.0, max(0.0, v / t)) if t > 0 else 0.0
        
        # Urgency multiplier for predicted threshold breach time
        pred_min = wf.get("predicted_threshold_breach_minutes")
        time_factor = 1.0
        if pred_min is not None and pred_min > 0:
            time_factor = max(1.0, min(1.5, 1.5 - (pred_min / 60.0)))
            
        wf_score = 15 + int(proximity_ratio * 10.0 * (time_factor - 1.0))
        scores.append(wf_score)
        
    base_wf_score = max(scores) if scores else 15
    multi_watch_bonus = min(10, (len(watch_flags) - 1) * 4) if len(watch_flags) > 1 else 0
    return max(15, min(39, base_wf_score + multi_watch_bonus))


def calculate_zone_scores(triggered_rules: list[dict], watch_flags: list[dict] = None, alarm_state: dict = None) -> dict[str, int]:
    """
    Calculates per-zone risk scores (0-100 scale) based on triggered rules,
    watch flags, and alarm states for each zone.
    """
    zones = ["Zone-A", "Zone-B", "Zone-C", "Zone-D", "Zone-E", "Zone-F"]
    zone_scores = {z: 0 for z in zones}

    is_evac = alarm_state.get("facility_evacuation_active", False) if alarm_state else False
    local_alerts = alarm_state.get("local_alerts_active", []) if alarm_state else []

    for z in zones:
        if is_evac or z in local_alerts:
            zone_scores[z] = 100
            continue

        # Find rules relevant to this zone
        z_rules = []
        for r in triggered_rules:
            flag_id = r.get("flag_id", "")
            reason = r.get("reason", "")
            signals = r.get("contributing_signals", [])
            if f"_{z}_" in flag_id or flag_id.endswith(f"_{z}") or f"in {z}" in reason or f"adjacent {z}" in reason or any(isinstance(s, dict) and s.get("zone") == z for s in signals):
                z_rules.append(r)

        z_watch = [wf for wf in (watch_flags or []) if isinstance(wf, dict) and wf.get("zone") == z]

        if z_rules:
            base_score = sum(r.get("severity", 1) * 20 for r in z_rules)
            rule_count = len(z_rules)
            multiplier = 1.0 if rule_count == 1 else (1.3 if rule_count == 2 else 1.6)
            score = min(100, int(base_score * multiplier))
            zone_scores[z] = score
        elif z_watch:
            zone_scores[z] = compute_watch_score(z_watch)
        else:
            zone_scores[z] = 0

    return zone_scores


def calculate_aggregate_score(triggered_rules: list[dict], watch_flags: list[dict] = None) -> dict:
    """
    LAYER 2 — Aggregate scoring:
    Calculates a single risk score (0-100) and maps it to a safety tier:
    - Tier 0 (Watch): 15 <= score < 40, dynamic watch proximity & forecast scoring
    - Tier 1 (Log Only): score < 40 (0 if no rules/watch)
    - Tier 2 (Dashboard Flag): 40 <= score < 75
    - Tier 3 (Escalate): score >= 75
    
    A higher weight is applied when multiple rules trigger simultaneously.
    """
    if not triggered_rules:
        if watch_flags:
            score = compute_watch_score(watch_flags)
            return {
                "score": score,
                "tier": 0,
                "tier_name": "Watch",
                "triggered_rules": []
            }
        return {
            "score": 0,
            "tier": 1,
            "tier_name": "Log Only",
            "triggered_rules": []
        }

    # Base score: sum of (severity * 20)
    base_score = sum(rule["severity"] * 20 for rule in triggered_rules)
    
    # Co-firing multiplier:
    # 1 rule -> 1.0
    # 2 rules -> 1.3
    # 3+ rules -> 1.6
    rule_count = len(triggered_rules)
    if rule_count == 1:
        multiplier = 1.0
    elif rule_count == 2:
        multiplier = 1.3
    else:
        multiplier = 1.6

    score = min(100, int(base_score * multiplier))
    
    # Map to safety tiers
    if score < 40:
        tier = 1
        tier_name = "Log Only"
    elif score < 75:
        tier = 2
        tier_name = "Dashboard Flag"
    else:
        tier = 3
        tier_name = "Escalate"

    return {
        "score": score,
        "tier": tier,
        "tier_name": tier_name,
        "triggered_rules": triggered_rules
    }

def detect_single_sensor_baseline(db: Session, start_time: datetime, end_time: datetime, dataset: str = "default", plant_id: str = "Plant-A") -> dict:
    """
    Naive single-sensor baseline detector for comparison purposes.
    Flags high risk only when an individual gas reading crosses a static threshold
    (CH4 >= 20.0, H2S >= 10.0, CO >= 50.0), with no permit/maintenance correlation.
    """
    # Fetch gas readings in the window
    gas_readings = db.query(models.GasSensorReading).filter(
        models.GasSensorReading.timestamp >= start_time,
        models.GasSensorReading.timestamp <= end_time,
        models.GasSensorReading.dataset == dataset,
        models.GasSensorReading.plant_id == plant_id
    ).all()

    triggered_alarms = []
    for r in gas_readings:
        if r.gas_type == "CH4" and r.reading_ppm >= 20.0:
            triggered_alarms.append({
                "rule_name": "BASELINE_CH4_HIGH_ALARM",
                "severity": 3,
                "reason": f"Methane level crossed threshold: {r.reading_ppm} ppm in {r.zone}.",
                "contributing_signals": [model_to_dict(r)]
            })
        elif r.gas_type == "H2S" and r.reading_ppm >= 10.0:
            triggered_alarms.append({
                "rule_name": "BASELINE_H2S_HIGH_ALARM",
                "severity": 3,
                "reason": f"Hydrogen Sulfide level crossed threshold: {r.reading_ppm} ppm in {r.zone}.",
                "contributing_signals": [model_to_dict(r)]
            })
        elif r.gas_type == "CO" and r.reading_ppm >= 50.0:
            triggered_alarms.append({
                "rule_name": "BASELINE_CO_HIGH_ALARM",
                "severity": 3,
                "reason": f"Carbon Monoxide level crossed threshold: {r.reading_ppm} ppm in {r.zone}.",
                "contributing_signals": [model_to_dict(r)]
            })

    if triggered_alarms:
        return {
            "score": 80,
            "tier": 3,
            "tier_name": "Escalate",
            "triggered_rules": triggered_alarms
        }
    return {
        "score": 0,
        "tier": 1,
        "tier_name": "Log Only",
        "triggered_rules": []
    }

