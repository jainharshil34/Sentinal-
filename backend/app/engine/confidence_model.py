import os
import joblib
import numpy as np
from datetime import datetime, timedelta
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_score, recall_score
from app.db import models

# Define rule names and zones in a fixed order for one-hot encoding
RULE_LIST = [
    "RULE_HOT_WORK_NEAR_GAS_SPIKE",
    "RULE_CONFINED_SPACE_NEAR_GAS_SPIKE",
    "RULE_ELECTRICAL_WORK_NEAR_GAS_SPIKE",
    "RULE_OVERDUE_MAINTENANCE_ACTIVE_PERMIT",
    "RULE_SILENT_SENSOR_DURING_PERMIT",
    "RULE_PERMIT_DURING_ACTIVE_REPAIR",
    "RULE_MULTI_GAS_COMPOUND_TOXICITY",
    "RULE_ADJACENT_ZONE_ESCALATION"
]

ZONE_LIST = ["Zone-A", "Zone-B", "Zone-C", "Zone-D", "Zone-E", "Zone-F"]

def extract_features_for_log(db, log):
    # 1. Rule Name One-Hot
    rule_vec = [0.0] * len(RULE_LIST)
    if log.rule_name in RULE_LIST:
        rule_idx = RULE_LIST.index(log.rule_name)
        rule_vec[rule_idx] = 1.0
        
    # 2. Zone Name One-Hot
    zone = "Zone-A"
    for z in ZONE_LIST:
        if z in log.flag_id:
            zone = z
            break
            
    zone_vec = [0.0] * len(ZONE_LIST)
    if zone in ZONE_LIST:
        zone_idx = ZONE_LIST.index(zone)
        zone_vec[zone_idx] = 1.0
        
    # 3. Shift period One-Hot
    hour = log.timestamp.hour
    shift_vec = [0.0, 0.0, 0.0]
    if 6 <= hour < 14:
        shift_vec[0] = 1.0  # Morning Shift
    elif 14 <= hour < 22:
        shift_vec[1] = 1.0  # Afternoon Shift
    else:
        shift_vec[2] = 1.0  # Night Shift
        
    # 4. Co-firing rules count (within a 5 minute window around this flag)
    co_firing_count = db.query(models.FeedbackLog).filter(
        models.FeedbackLog.timestamp >= log.timestamp - timedelta(minutes=5),
        models.FeedbackLog.timestamp <= log.timestamp + timedelta(minutes=5),
        models.FeedbackLog.plant_id == log.plant_id
    ).count()
    num_co_firing = max(0.0, float(co_firing_count - 1))
    
    # 5. Days since last maintenance in that zone
    latest_maint = db.query(models.MaintenanceLog).filter(
        models.MaintenanceLog.zone == zone,
        models.MaintenanceLog.logged_at <= log.timestamp,
        models.MaintenanceLog.plant_id == log.plant_id
    ).order_by(models.MaintenanceLog.logged_at.desc()).first()
    
    if latest_maint:
        days_since_maint = (log.timestamp - latest_maint.logged_at).total_seconds() / (24 * 3600.0)
    else:
        days_since_maint = 30.0  # default fallback
        
    # 6. Rule false alarm rate (up to this log's timestamp)
    total_rule_logs = db.query(models.FeedbackLog).filter(
        models.FeedbackLog.rule_name == log.rule_name,
        models.FeedbackLog.timestamp < log.timestamp
    ).count()
    false_rule_logs = db.query(models.FeedbackLog).filter(
        models.FeedbackLog.rule_name == log.rule_name,
        models.FeedbackLog.officer_verdict == "False Alarm",
        models.FeedbackLog.timestamp < log.timestamp
    ).count()
    rule_fa_rate = false_rule_logs / total_rule_logs if total_rule_logs > 0 else 0.1
    
    # 7. Historical incident frequency in that zone
    incident_count = db.query(models.IncidentHistory).filter(
        models.IncidentHistory.zone == zone
    ).count()
    
    features = (
        rule_vec +
        zone_vec +
        shift_vec +
        [num_co_firing, days_since_maint, rule_fa_rate, float(incident_count)]
    )
    return features

def train_and_save_model(db=None):
    close_db = False
    if db is None:
        from app.db.database import SessionLocal
        db = SessionLocal()
        close_db = True
        
    try:
        logs = db.query(models.FeedbackLog).all()
        if len(logs) < 10:
            print(f"Not enough feedback logs ({len(logs)}) to train the model.")
            return False
            
        X = []
        y = []
        for log in logs:
            feats = extract_features_for_log(db, log)
            label = 1 if log.officer_verdict == "Confirmed Risk" else 0
            X.append(feats)
            y.append(label)
            
        X = np.array(X)
        y = np.array(y)
        
        # Train-test split
        X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Fit logistic regression classifier
        clf = LogisticRegression(max_iter=1000)
        clf.fit(X_train, y_train)
        
        # Calculate metrics on validation split
        y_pred = clf.predict(X_val)
        precision = float(precision_score(y_val, y_pred, zero_division=0))
        recall = float(recall_score(y_val, y_pred, zero_division=0))
        
        model_data = {
            "model": clf,
            "precision": precision,
            "recall": recall,
            "feature_names": (
                [f"Rule_{r}" for r in RULE_LIST] +
                [f"Zone_{z}" for z in ZONE_LIST] +
                ["Shift_Morning", "Shift_Afternoon", "Shift_Night"] +
                ["co_firing_rules", "days_since_maintenance", "historical_rule_false_alarm_rate", "zone_incident_frequency"]
            )
        }
        
        # Calculate feature importances based on coefficients
        coefficients = clf.coef_[0]
        feature_importances = []
        for name, coef in zip(model_data["feature_names"], coefficients):
            feature_importances.append({
                "feature": name,
                "importance": float(abs(coef)),
                "direction": "positive" if coef > 0 else "negative"
            })
        feature_importances.sort(key=lambda x: x["importance"], reverse=True)
        model_data["feature_importances"] = feature_importances
        
        # Save model file
        os.makedirs("app/data", exist_ok=True)
        joblib.dump(model_data, "app/data/confidence_model.pkl")
        print(f"Model successfully trained and saved. Precision: {precision:.2f}, Recall: {recall:.2f}")
        return True
    finally:
        if close_db:
            db.close()

def predict_flag_confidence(db, rule_name: str, zone: str, timestamp: datetime, num_co_firing: int) -> float:
    model_path = "app/data/confidence_model.pkl"
    if not os.path.exists(model_path):
        train_and_save_model(db)
        
    try:
        model_data = joblib.load(model_path)
        clf = model_data["model"]
    except Exception as e:
        print("Failed to load confidence model, returning default 0.85:", e)
        return 0.85
        
    # Build feature vector
    rule_vec = [0.0] * len(RULE_LIST)
    if rule_name in RULE_LIST:
        rule_vec[RULE_LIST.index(rule_name)] = 1.0
        
    zone_vec = [0.0] * len(ZONE_LIST)
    if zone in ZONE_LIST:
        zone_vec[ZONE_LIST.index(zone)] = 1.0
        
    hour = timestamp.hour
    shift_vec = [0.0, 0.0, 0.0]
    if 6 <= hour < 14:
        shift_vec[0] = 1.0
    elif 14 <= hour < 22:
        shift_vec[1] = 1.0
    else:
        shift_vec[2] = 1.0
        
    latest_maint = db.query(models.MaintenanceLog).filter(
        models.MaintenanceLog.zone == zone,
        models.MaintenanceLog.logged_at <= timestamp
    ).order_by(models.MaintenanceLog.logged_at.desc()).first()
    
    if latest_maint:
        days_since_maint = (timestamp - latest_maint.logged_at).total_seconds() / (24 * 3600.0)
    else:
        days_since_maint = 30.0
        
    total_rule_logs = db.query(models.FeedbackLog).filter(
        models.FeedbackLog.rule_name == rule_name,
        models.FeedbackLog.timestamp < timestamp
    ).count()
    false_rule_logs = db.query(models.FeedbackLog).filter(
        models.FeedbackLog.rule_name == rule_name,
        models.FeedbackLog.officer_verdict == "False Alarm",
        models.FeedbackLog.timestamp < timestamp
    ).count()
    rule_fa_rate = false_rule_logs / total_rule_logs if total_rule_logs > 0 else 0.1
    
    incident_count = db.query(models.IncidentHistory).filter(
        models.IncidentHistory.zone == zone
    ).count()
    
    features = (
        rule_vec +
        zone_vec +
        shift_vec +
        [float(num_co_firing), days_since_maint, rule_fa_rate, float(incident_count)]
    )
    
    X = np.array([features])
    probs = clf.predict_proba(X)[0]
    return float(probs[1])
