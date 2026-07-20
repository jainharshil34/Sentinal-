from sqlalchemy import Column, Integer, String, Float, DateTime
from app.db.database import Base

class GasSensorReading(Base):
    __tablename__ = "gas_sensor_readings"

    id = Column(Integer, primary_key=True, index=True)
    zone = Column(String(50), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    gas_type = Column(String(50), nullable=False)
    reading_ppm = Column(Float, nullable=False)
    sensor_status = Column(String(50), nullable=False)
    dataset = Column(String(50), default="default", nullable=False, index=True)
    plant_id = Column(String(50), default="Plant-A", nullable=False, index=True)

class Permit(Base):
    __tablename__ = "permits"

    id = Column(Integer, primary_key=True, index=True)
    permit_id = Column(String(100), nullable=False, index=True)
    zone = Column(String(50), nullable=False, index=True)
    permit_type = Column(String(50), nullable=False)
    issued_at = Column(DateTime, nullable=False, index=True)
    closed_at = Column(DateTime, nullable=True)
    issued_by = Column(String(100), nullable=False)
    dataset = Column(String(50), default="default", nullable=False, index=True)
    plant_id = Column(String(50), default="Plant-A", nullable=False, index=True)

class MaintenanceLog(Base):
    __tablename__ = "maintenance_logs"

    id = Column(Integer, primary_key=True, index=True)
    zone = Column(String(50), nullable=False, index=True)
    equipment_id = Column(String(100), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)
    logged_at = Column(DateTime, nullable=False, index=True)
    notes = Column(String(500), nullable=True)
    dataset = Column(String(50), default="default", nullable=False, index=True)
    plant_id = Column(String(50), default="Plant-A", nullable=False, index=True)

class FeedbackLog(Base):
    __tablename__ = "feedback_logs"

    id = Column(Integer, primary_key=True, index=True)
    flag_id = Column(String(100), nullable=False, index=True)
    rule_name = Column(String(100), nullable=False, index=True)
    officer_verdict = Column(String(50), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    plant_id = Column(String(50), default="Plant-A", nullable=False, index=True)

class IncidentHistory(Base):
    __tablename__ = "incident_history"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, nullable=False, index=True)
    zone = Column(String(50), nullable=False, index=True)
    category = Column(String(100), nullable=False)  # near_miss / injury / fatality / equipment_failure / repair_log
    contributing_factors = Column(String(1000), nullable=False)
    related_rule_type = Column(String(100), nullable=True)
    regulatory_clause = Column(String(100), nullable=True)
    resolution_notes = Column(String(1000), nullable=False)
    logged_by_role = Column(String(100), nullable=False)  # e.g., "Safety Officer", "Shift Supervisor"
    severity_level = Column(String(50), nullable=False)  # fatality / lost-time injury / first-aid only
    plant_id = Column(String(50), default="Plant-A", nullable=False, index=True)
    dataset = Column(String(50), default="default", nullable=False, index=True)
    source = Column(String(50), default="synthetic", nullable=False)

class VerbalReport(Base):
    __tablename__ = "verbal_reports"

    id = Column(Integer, primary_key=True, index=True)
    zone = Column(String(50), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    transcript = Column(String(1000), nullable=False)
    hazard_type = Column(String(50), nullable=True)  # gas/equipment/permit/other
    urgency_signal = Column(String(50), nullable=False, default="medium")  # low/medium/high
    raw_quote = Column(String(500), nullable=True)
    is_anonymous = Column(Integer, default=0, nullable=False)  # 1 if anonymous, 0 if shift handover
    plant_id = Column(String(50), default="Plant-A", nullable=False, index=True)
    dataset = Column(String(50), default="default", nullable=False, index=True)

