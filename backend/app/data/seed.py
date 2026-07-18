import os
import json
from datetime import datetime, timedelta
from app.db.database import Base, engine, SessionLocal
from app.db import models
from app.data.generator import generate_default_dataset, vizag_replay_dataset

# Ensure fixtures directory exists
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
os.makedirs(FIXTURES_DIR, exist_ok=True)

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def seed_database():
    print("Initializing SentinelGrid database seeding...")
    
    # Create tables by first dropping them to apply schema upgrades
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # 1. Wipe database tables
        print("Wiping existing records...")
        db.query(models.GasSensorReading).delete()
        db.query(models.Permit).delete()
        db.query(models.MaintenanceLog).delete()
        db.commit()
        print("Database wiped successfully.")

        # 2. Generate datasets
        now = datetime.utcnow()
        start_time_default = now - timedelta(days=3)
        start_time_vizag = now - timedelta(days=1)

        print(f"Generating default dataset for Plant-A starting at {start_time_default}...")
        gas_a, permits_a, maint_a = generate_default_dataset(start_time_default, plant_id="Plant-A")
        
        print(f"Generating default dataset for Plant-B starting at {start_time_default}...")
        gas_b, permits_b, maint_b = generate_default_dataset(start_time_default, plant_id="Plant-B")

        print(f"Generating default dataset for Plant-C starting at {start_time_default}...")
        gas_c, permits_c, maint_c = generate_default_dataset(start_time_default, plant_id="Plant-C")
        
        print(f"Generating Vizag replay dataset starting at {start_time_vizag}...")
        gas_vizag, permits_vizag, maint_vizag = vizag_replay_dataset(start_time_vizag)

        for g in gas_vizag:
            g["plant_id"] = "Plant-A"
        for p in permits_vizag:
            p["plant_id"] = "Plant-A"
        for m in maint_vizag:
            m["plant_id"] = "Plant-A"

        # Merge for database seeding
        all_gas = gas_a + gas_b + gas_c + gas_vizag
        all_permits = permits_a + permits_b + permits_c + permits_vizag
        all_maint = maint_a + maint_b + maint_c + maint_vizag

        # 3. Save JSON fixtures
        print("Saving raw JSON fixtures to backend/app/data/fixtures/ ...")
        with open(os.path.join(FIXTURES_DIR, "gas_sensor_readings.json"), "w") as f:
            json.dump(all_gas, f, default=json_serial, indent=2)
        with open(os.path.join(FIXTURES_DIR, "permits.json"), "w") as f:
            json.dump(all_permits, f, default=json_serial, indent=2)
        with open(os.path.join(FIXTURES_DIR, "maintenance_logs.json"), "w") as f:
            json.dump(all_maint, f, default=json_serial, indent=2)
        print("JSON fixtures saved successfully.")

        # 4. Insert into database
        print(f"Inserting {len(all_gas)} gas readings, {len(all_permits)} permits, and {len(all_maint)} maintenance logs...")
        
        # bulk_insert_mappings expects dictionaries
        db.bulk_insert_mappings(models.GasSensorReading, all_gas)
        db.bulk_insert_mappings(models.Permit, all_permits)
        db.bulk_insert_mappings(models.MaintenanceLog, all_maint)
        db.commit()

        # Seed Feedback Logs
        print("Pre-seeding historical safety officer feedback logs...")
        feedback_data = []
        now = datetime.utcnow()
        
        # --- PLANT-A: 51 Confirmed, 5 False Alarms (Total: 56, TPR: 91.1%, Eligible, passes unit tests) ---
        # 1. RULE_OVERDUE_MAINTENANCE_ACTIVE_PERMIT: 4 False Alarms, 1 Confirmed Risk
        for i in range(4):
            feedback_data.append({
                "flag_id": f"RULE_OVERDUE_MAINTENANCE_ACTIVE_PERMIT_Zone-A_HIST_{i}",
                "rule_name": "RULE_OVERDUE_MAINTENANCE_ACTIVE_PERMIT",
                "officer_verdict": "False Alarm",
                "timestamp": now - timedelta(days=5 - i),
                "plant_id": "Plant-A"
            })
        feedback_data.append({
            "flag_id": "RULE_OVERDUE_MAINTENANCE_ACTIVE_PERMIT_Zone-A_HIST_4",
            "rule_name": "RULE_OVERDUE_MAINTENANCE_ACTIVE_PERMIT",
            "officer_verdict": "Confirmed Risk",
            "timestamp": now - timedelta(days=1),
            "plant_id": "Plant-A"
        })
        
        # 2. RULE_HOT_WORK_NEAR_GAS_SPIKE: 5 Confirmed Risks, 1 False Alarm
        for i in range(5):
            feedback_data.append({
                "flag_id": f"RULE_HOT_WORK_NEAR_GAS_SPIKE_Zone-A_HIST_{i}",
                "rule_name": "RULE_HOT_WORK_NEAR_GAS_SPIKE",
                "officer_verdict": "Confirmed Risk",
                "timestamp": now - timedelta(days=6 - i),
                "plant_id": "Plant-A"
            })
        feedback_data.append({
            "flag_id": "RULE_HOT_WORK_NEAR_GAS_SPIKE_Zone-A_HIST_5",
            "rule_name": "RULE_HOT_WORK_NEAR_GAS_SPIKE",
            "officer_verdict": "False Alarm",
            "timestamp": now - timedelta(hours=12),
            "plant_id": "Plant-A"
        })

        # 3. RULE_CONFINED_SPACE_NEAR_GAS_SPIKE: 50 Confirmed Risks, 0 False Alarms (for graduation threshold)
        for i in range(50):
            feedback_data.append({
                "flag_id": f"RULE_CONFINED_SPACE_NEAR_GAS_SPIKE_A_HIST_{i}",
                "rule_name": "RULE_CONFINED_SPACE_NEAR_GAS_SPIKE",
                "officer_verdict": "Confirmed Risk",
                "timestamp": now - timedelta(days=15 - i/4),
                "plant_id": "Plant-A"
            })

        # --- PLANT-B: 14 Confirmed, 1 False Alarm (Total: 15, TPR: 93.3%, Not Eligible - count < 20) ---
        for i in range(14):
            feedback_data.append({
                "flag_id": f"RULE_HOT_WORK_NEAR_GAS_SPIKE_B_HIST_{i}",
                "rule_name": "RULE_HOT_WORK_NEAR_GAS_SPIKE",
                "officer_verdict": "Confirmed Risk",
                "timestamp": now - timedelta(days=10 - i/2),
                "plant_id": "Plant-B"
            })
        feedback_data.append({
            "flag_id": "RULE_OVERDUE_MAINTENANCE_ACTIVE_PERMIT_B_HIST_0",
            "rule_name": "RULE_OVERDUE_MAINTENANCE_ACTIVE_PERMIT",
            "officer_verdict": "False Alarm",
            "timestamp": now - timedelta(days=2),
            "plant_id": "Plant-B"
        })

        # --- PLANT-C: 16 Confirmed, 5 False Alarms (Total: 21, TPR: 76.2%, Not Eligible - TPR < 90%) ---
        for i in range(16):
            feedback_data.append({
                "flag_id": f"RULE_HOT_WORK_NEAR_GAS_SPIKE_C_HIST_{i}",
                "rule_name": "RULE_HOT_WORK_NEAR_GAS_SPIKE",
                "officer_verdict": "Confirmed Risk",
                "timestamp": now - timedelta(days=10 - i/2),
                "plant_id": "Plant-C"
            })
        for i in range(5):
            feedback_data.append({
                "flag_id": f"RULE_OVERDUE_MAINTENANCE_ACTIVE_PERMIT_C_HIST_{i}",
                "rule_name": "RULE_OVERDUE_MAINTENANCE_ACTIVE_PERMIT",
                "officer_verdict": "False Alarm",
                "timestamp": now - timedelta(days=3 - i/2),
                "plant_id": "Plant-C"
            })

        db.bulk_insert_mappings(models.FeedbackLog, feedback_data)
        db.commit()

        # Seed Incident History
        print("Pre-seeding historical incident logs...")
        from app.data.incidents import INCIDENT_CORPUS
        
        incidents_seeded = []
        for idx, inc in enumerate(INCIDENT_CORPUS):
            offset_desc = inc.get("time_offset_desc", "four months ago")
            days_ago = 120
            if "one" in offset_desc:
                days_ago = 30
            elif "two" in offset_desc:
                days_ago = 60
            elif "three" in offset_desc:
                days_ago = 90
            elif "four" in offset_desc:
                days_ago = 120
            elif "five" in offset_desc:
                days_ago = 150
            elif "six" in offset_desc:
                days_ago = 180
            elif "seven" in offset_desc:
                days_ago = 210
            elif "eight" in offset_desc:
                days_ago = 240
            elif "nine" in offset_desc:
                days_ago = 270
            elif "ten" in offset_desc:
                days_ago = 300
                
            inc_date = now - timedelta(days=days_ago)
            
            txt = inc["text"].lower()
            if "injury" in txt or "burns" in txt or "unconsciousness" in txt or "unconscious" in txt:
                category = "injury"
                severity = "lost-time injury"
            elif "fatality" in txt or "fatal" in txt:
                category = "fatality"
                severity = "fatality"
            elif "calibration" in txt or "offline" in txt or "silent" in txt or "overdue" in txt:
                category = "equipment_failure"
                severity = "first-aid only"
            else:
                category = "near_miss"
                severity = "first-aid only"
                
            incidents_seeded.append({
                "id": inc["id"],
                "date": inc_date,
                "zone": inc["zone"],
                "category": category,
                "contributing_factors": inc["text"],
                "related_rule_type": inc.get("rule_type"),
                "regulatory_clause": inc.get("regulatory_clause"),
                "resolution_notes": "Standard isolation protocol enforced and calibration logs verified.",
                "logged_by_role": "Safety Officer",
                "severity_level": severity,
                "plant_id": inc.get("plant_id", "Plant-A"),
                "dataset": "default",
                "source": inc.get("source", "synthetic")
            })
            
        db.bulk_insert_mappings(models.IncidentHistory, incidents_seeded)
        db.commit()

        # Reset incident agent in-memory cache to recalculate with newly seeded data
        try:
            from app.engine.incident_agent import reset_incident_cache
            reset_incident_cache()
        except Exception as e:
            print("Failed to reset incident agent cache during seed:", e)

        print("Database seeded successfully with all records!")

    except Exception as e:
        db.rollback()
        print(f"Error during seeding: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
