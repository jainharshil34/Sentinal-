import json
import random
from datetime import datetime, timedelta

# Fictional plant zones
ZONES = ["Zone-A", "Zone-B", "Zone-C", "Zone-D", "Zone-E", "Zone-F"]
GAS_TYPES = ["H2S", "CO", "CH4"]

def generate_default_dataset(start_time: datetime, plant_id: str = "Plant-A") -> tuple[list[dict], list[dict], list[dict]]:
    """
    Generates a 72-hour synthetic dataset at 5-minute intervals.
    Includes 70%+ normal operations, 4 compound-risk scenarios, and 1 silent failure.
    """
    gas_readings = []
    permits = []
    maintenance_logs = []

    # Total intervals: 72 hours * 12 intervals/hour = 864 intervals
    intervals = 72 * 12
    timestamps = [start_time + timedelta(minutes=5 * i) for i in range(intervals)]

    # Initialize baselines for normal operations (random walk / noise)
    baselines = {
        zone: {
            "CH4": {"base": 1.8, "noise": 0.3},
            "CO": {"base": 4.5, "noise": 0.8},
            "H2S": {"base": 0.2, "noise": 0.05}
        } for zone in ZONES
    }

    # Assign zones and offsets per plant to randomize scenarios
    if plant_id == "Plant-B":
        s1_zone, s1_start = "Zone-B", 12.0
        s2_zone, s2_start = "Zone-C", 24.0
        s3_zone, s3_start = "Zone-D", 36.0
        s4_zone, s4_start = "Zone-E", 48.0
        s5_zone, s5_start = "Zone-F", 60.0
        s6_zone, s6_start = "Zone-B", 15.75
        s7_zone, s7_start = "Zone-E", 18.5
        s8_zone, s8_start = "Zone-A", 68.0
    elif plant_id == "Plant-C":
        s1_zone, s1_start = "Zone-C", 30.0
        s2_zone, s2_start = "Zone-D", 42.0
        s3_zone, s3_start = "Zone-E", 54.0
        s4_zone, s4_start = "Zone-F", 18.0
        s5_zone, s5_start = "Zone-A", 6.0
        s6_zone, s6_start = "Zone-C", 15.75
        s7_zone, s7_start = "Zone-F", 18.5
        s8_zone, s8_start = "Zone-B", 68.0
    else: # Plant-A
        s1_zone, s1_start = "Zone-A", 24.0
        s2_zone, s2_start = "Zone-B", 36.0
        s3_zone, s3_start = "Zone-C", 48.0
        s4_zone, s4_start = "Zone-D", 60.0
        s5_zone, s5_start = "Zone-E", 11.5
        s6_zone, s6_start = "Zone-A", 15.75
        s7_zone, s7_start = "Zone-D", 18.5
        s8_zone, s8_start = "Zone-F", 68.0

    # Helper to check if a timestamp falls within a specific window
    def is_in_window(ts: datetime, start_offset_hr: float, duration_hr: float) -> bool:
        window_start = start_time + timedelta(hours=start_offset_hr)
        window_end = window_start + timedelta(hours=duration_hr)
        return window_start <= ts <= window_end

    # --- 1. POPULATE GAS READINGS & INJECT ANOMALIES ---
    for ts in timestamps:
        for zone in ZONES:
            for gas in GAS_TYPES:
                reading = baselines[zone][gas]["base"] + random.uniform(-baselines[zone][gas]["noise"], baselines[zone][gas]["noise"])
                reading = max(0.0, reading)
                status = "active"

                # Scenario 1 (s1_zone, CH4 climb)
                if zone == s1_zone and gas == "CH4" and is_in_window(ts, s1_start, 3.5):
                    elapsed = (ts - (start_time + timedelta(hours=s1_start))).total_seconds() / 3600.0
                    reading = 2.0 + (46.5 * (elapsed / 3.5))

                # Scenario 2 (s2_zone, CO climb)
                elif zone == s2_zone and gas == "CO" and is_in_window(ts, s2_start, 4.0):
                    elapsed = (ts - (start_time + timedelta(hours=s2_start))).total_seconds() / 3600.0
                    reading = 4.5 + (140.5 * (elapsed / 4.0))

                # Scenario 3 (s3_zone, H2S climb)
                elif zone == s3_zone and gas == "H2S" and is_in_window(ts, s3_start, 4.0):
                    elapsed = (ts - (start_time + timedelta(hours=s3_start))).total_seconds() / 3600.0
                    reading = 0.2 + (27.8 * (elapsed / 4.0))

                # Scenario 4 (s4_zone, CH4 climb)
                elif zone == s4_zone and gas == "CH4" and is_in_window(ts, s4_start, 4.0):
                    elapsed = (ts - (start_time + timedelta(hours=s4_start))).total_seconds() / 3600.0
                    reading = 1.8 + (36.2 * (elapsed / 4.0))

                # Scenario 5 (s5_zone, SILENT FAILURE)
                elif zone == s5_zone and is_in_window(ts, s5_start, 2.0):
                    status = "silent"
                    reading = baselines[zone][gas]["base"]

                # Negative Scenario 6 (edge_case_time_gap)
                elif zone == s6_zone and gas == "CH4" and is_in_window(ts, s6_start, 1.75):
                    elapsed = (ts - (start_time + timedelta(hours=s6_start))).total_seconds() / 3600.0
                    reading = 2.0 + (33.0 * (elapsed / 1.75))

                # Negative Scenario 7 (edge_case_adjacent_zone_no_overlap)
                elif zone == s7_zone and gas == "CH4" and is_in_window(ts, s7_start, 1.5):
                    elapsed = (ts - (start_time + timedelta(hours=s7_start))).total_seconds() / 3600.0
                    reading = 1.8 + (33.2 * (elapsed / 1.5))

                # Scenario 8 (s8_zone, Multi-gas toxicity)
                elif zone == s8_zone and is_in_window(ts, s8_start, 3.0):
                    elapsed = (ts - (start_time + timedelta(hours=s8_start))).total_seconds() / 3600.0
                    if gas == "CO":
                        reading = 4.5 + (15.5 * min(1.0, elapsed / 2.0))
                    elif gas == "H2S":
                        reading = 0.2 + (4.0 * min(1.0, elapsed / 2.0))

                gas_readings.append({
                    "zone": zone,
                    "timestamp": ts,
                    "gas_type": gas,
                    "reading_ppm": round(reading, 2),
                    "sensor_status": status,
                    "dataset": "default",
                    "plant_id": plant_id
                })

    # --- 2. INJECT PERMITS ---
    shift_h = 0.0
    if plant_id == "Plant-B":
        shift_h = 4.0
    elif plant_id == "Plant-C":
        shift_h = 8.0

    normal_permits_data = [
        ("Zone-A", "routine", (4.0 + shift_h) % 72, (8.0 + shift_h) % 72, "Supervisor Jack"),
        ("Zone-B", "electrical", (10.0 + shift_h) % 72, (14.0 + shift_h) % 72, "Engineer Mike"),
        ("Zone-F", "routine", (18.0 + shift_h) % 72, (22.0 + shift_h) % 72, "Officer Sarah"),
        ("Zone-C", "electrical", (28.0 + shift_h) % 72, (32.0 + shift_h) % 72, "Engineer Mike"),
        ("Zone-D", "routine", (42.0 + shift_h) % 72, (46.0 + shift_h) % 72, "Officer Sarah"),
        ("Zone-F", "confined_space", (50.0 + shift_h) % 72, (53.0 + shift_h) % 72, "Supervisor Jack"),
        ("Zone-E", "routine", (64.0 + shift_h) % 72, (68.0 + shift_h) % 72, "Officer Sarah")
    ]
    for i, (zone, p_type, start_off, end_off, issuer) in enumerate(normal_permits_data):
        permits.append({
            "permit_id": f"PERM-NORM-{100 + i}" if plant_id == "Plant-A" else f"PERM-{plant_id}-NORM-{100 + i}",
            "zone": zone,
            "permit_type": p_type,
            "issued_at": start_time + timedelta(hours=start_off),
            "closed_at": start_time + timedelta(hours=end_off),
            "issued_by": issuer,
            "dataset": "default",
            "plant_id": plant_id
        })

    # Compound Risk Permits
    permits.append({
        "permit_id": "PERM-RISK-201" if plant_id == "Plant-A" else f"PERM-{plant_id}-RISK-201",
        "zone": s1_zone,
        "permit_type": "hot_work",
        "issued_at": start_time + timedelta(hours=s1_start + 0.5),
        "closed_at": start_time + timedelta(hours=s1_start + 3.0),
        "issued_by": "Supervisor Jack",
        "dataset": "default",
        "plant_id": plant_id
    })
    
    permits.append({
        "permit_id": "PERM-RISK-202" if plant_id == "Plant-A" else f"PERM-{plant_id}-RISK-202",
        "zone": s2_zone,
        "permit_type": "confined_space",
        "issued_at": start_time + timedelta(hours=s2_start + 0.5),
        "closed_at": start_time + timedelta(hours=s2_start + 3.5),
        "issued_by": "Officer Sarah",
        "dataset": "default",
        "plant_id": plant_id
    })

    permits.append({
        "permit_id": "PERM-RISK-203" if plant_id == "Plant-A" else f"PERM-{plant_id}-RISK-203",
        "zone": s3_zone,
        "permit_type": "hot_work",
        "issued_at": start_time + timedelta(hours=s3_start + 0.5),
        "closed_at": start_time + timedelta(hours=s3_start + 3.5),
        "issued_by": "Supervisor Jack",
        "dataset": "default",
        "plant_id": plant_id
    })

    permits.append({
        "permit_id": "PERM-RISK-204" if plant_id == "Plant-A" else f"PERM-{plant_id}-RISK-204",
        "zone": s4_zone,
        "permit_type": "electrical",
        "issued_at": start_time + timedelta(hours=s4_start + 0.5),
        "closed_at": start_time + timedelta(hours=s4_start + 3.5),
        "issued_by": "Engineer Mike",
        "dataset": "default",
        "plant_id": plant_id
    })

    # Silent Failure Permit
    permits.append({
        "permit_id": "PERM-SILENT-301" if plant_id == "Plant-A" else f"PERM-{plant_id}-SILENT-301",
        "zone": s5_zone,
        "permit_type": "confined_space",
        "issued_at": start_time + timedelta(hours=s5_start - 0.5),
        "closed_at": start_time + timedelta(hours=s5_start + 2.5),
        "issued_by": "Supervisor Jack",
        "dataset": "default",
        "plant_id": plant_id
    })

    # Negative Scenario 6
    permits.append({
        "permit_id": "PERM-NEG-TIMEGAP" if plant_id == "Plant-A" else f"PERM-{plant_id}-NEG-TIMEGAP",
        "zone": s6_zone,
        "permit_type": "hot_work",
        "issued_at": start_time + timedelta(hours=s6_start - 1.75),
        "closed_at": start_time + timedelta(hours=s6_start - 0.75),
        "issued_by": "Supervisor Jack",
        "dataset": "default",
        "plant_id": plant_id
    })

    # Negative Scenario 7
    permits.append({
        "permit_id": "PERM-NEG-ADJACENT" if plant_id == "Plant-A" else f"PERM-{plant_id}-NEG-ADJACENT",
        "zone": "Zone-A" if s7_zone != "Zone-A" else "Zone-D",
        "permit_type": "hot_work",
        "issued_at": start_time + timedelta(hours=s7_start),
        "closed_at": start_time + timedelta(hours=s7_start + 1.5),
        "issued_by": "Supervisor Jack",
        "dataset": "default",
        "plant_id": plant_id
    })

    # --- 3. INJECT MAINTENANCE LOGS ---
    normal_logs_data = [
        ("Zone-F", f"PUMP-{plant_id}-ZF-11", "inspection", 6.0, "Routine pump vibration analysis. Normal."),
        ("Zone-C", f"HVAC-{plant_id}-ZC-02", "repair", 15.0, "Replaced filter belt. Operational."),
        ("Zone-D", f"VALVE-{plant_id}-ZD-99", "inspection", 30.0, "Visual seal inspection completed."),
        ("Zone-E", f"FAN-{plant_id}-ZE-14", "inspection", 45.0, "Bearing temperature nominal.")
    ]
    for zone, equip, ev_type, log_off, note in normal_logs_data:
        maintenance_logs.append({
            "zone": zone,
            "equipment_id": equip,
            "event_type": ev_type,
            "logged_at": start_time + timedelta(hours=(log_off + shift_h) % 72),
            "notes": note,
            "dataset": "default",
            "plant_id": plant_id
        })

    # Scenario 1 Overdue Ventilation maintenance
    maintenance_logs.append({
        "zone": s1_zone,
        "equipment_id": "VENT-ZA-09" if plant_id == "Plant-A" else f"VENT-ZA-09-{plant_id}",
        "event_type": "overdue_flag",
        "logged_at": start_time + timedelta(hours=s1_start + 0.25),
        "notes": "Annual exhaust fan airflow validation. Overdue by 15 days.",
        "dataset": "default",
        "plant_id": plant_id
    })

    # Scenario 2 Overdue sensor calibration
    maintenance_logs.append({
        "zone": s2_zone,
        "equipment_id": "DET-ZB-02" if plant_id == "Plant-A" else f"DET-ZB-02-{plant_id}",
        "event_type": "overdue_flag",
        "logged_at": start_time + timedelta(hours=s2_start - 0.5),
        "notes": "Carbon Monoxide electrochemical cell calibration. Overdue by 10 days.",
        "dataset": "default",
        "plant_id": plant_id
    })

    # Scenario 3 Active repair
    maintenance_logs.append({
        "zone": s3_zone,
        "equipment_id": "VALVE-ZC-44" if plant_id == "Plant-A" else f"VALVE-ZC-44-{plant_id}",
        "event_type": "repair",
        "logged_at": start_time + timedelta(hours=s3_start + 0.25),
        "notes": "Active repair: replacing bonnet gasket on acid gas valve.",
        "dataset": "default",
        "plant_id": plant_id
    })

    # Scenario 4 Overdue Isolation checks
    maintenance_logs.append({
        "zone": s4_zone,
        "equipment_id": "SW-ZD-01" if plant_id == "Plant-A" else f"SW-ZD-01-{plant_id}",
        "event_type": "overdue_flag",
        "logged_at": start_time + timedelta(hours=s4_start - 0.25),
        "notes": "Substation switchgear safety isolator physical inspection. Overdue by 5 days.",
        "dataset": "default",
        "plant_id": plant_id
    })

    return gas_readings, permits, maintenance_logs


def vizag_replay_dataset(start_time: datetime) -> tuple[list[dict], list[dict], list[dict]]:
    """
    Generates a reconstructed timeline loosely modeled on public reporting about the January 2025
    Vizag Steel Plant coke oven battery incident (gas pressure anomaly building over time, permit activity nearby,
    no cross-system correlation flagged).
    
    Reconstructed for demonstration purposes based on public incident reporting, not verified internal plant data.
    """
    gas_readings = []
    permits = []
    maintenance_logs = []

    # Span 24 hours at 5-minute intervals: 288 intervals
    intervals = 24 * 12
    timestamps = [start_time + timedelta(minutes=5 * i) for i in range(intervals)]

    # Incident occurs in Zone-C (representing Coke Oven Battery 11)
    # CO level builds up steadily over a 12-hour window due to blockages/leaks
    for ts in timestamps:
        for zone in ZONES:
            for gas in GAS_TYPES:
                # Default normal reading
                reading = 2.0 if gas == "CO" else (1.5 if gas == "CH4" else 0.1)
                status = "active"

                # In Zone-C, CO levels start building up from T+4h to T+16h
                if zone == "Zone-C" and gas == "CO" and (start_time + timedelta(hours=4.0)) <= ts <= (start_time + timedelta(hours=16.0)):
                    elapsed_hours = (ts - (start_time + timedelta(hours=4.0))).total_seconds() / 3600.0
                    # Rises from 5.0 ppm to 420.0 ppm
                    reading = 5.0 + (415.0 * (elapsed_hours / 12.0))
                # Beyond T+16h it remains extremely high
                elif zone == "Zone-C" and gas == "CO" and ts > (start_time + timedelta(hours=16.0)):
                    reading = 420.0 + random.uniform(-10.0, 10.0)

                gas_readings.append({
                    "zone": zone,
                    "timestamp": ts,
                    "gas_type": gas,
                    "reading_ppm": round(reading, 2),
                    "sensor_status": status,
                    "dataset": "vizag_replay"
                })

    # Permit activity nearby: Hot work permit issued in Zone-C (Coke Oven Battery area)
    # from T+10h to T+15h, active during the CO buildup
    permits.append({
        "permit_id": "PERM-VIZAG-901",
        "zone": "Zone-C",
        "permit_type": "hot_work",
        "issued_at": start_time + timedelta(hours=10.0),
        "closed_at": start_time + timedelta(hours=15.0),
        "issued_by": "Senior Inspector Prasad",
        "dataset": "vizag_replay"
    })

    # Maintenance activity: Overdue pressure regulator calibration flagged right before
    maintenance_logs.append({
        "zone": "Zone-C",
        "equipment_id": "REG-COVEN-11",
        "event_type": "overdue_flag",
        "logged_at": start_time + timedelta(hours=3.5),
        "notes": "Coke oven battery gas collector pressure regulator calibration overdue.",
        "dataset": "vizag_replay"
    })

    return gas_readings, permits, maintenance_logs
