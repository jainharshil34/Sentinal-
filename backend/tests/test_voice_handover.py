import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.database import Base
from app.db import models
from app.engine.voice_extraction import extract_hazard_entities
from app.engine.risk_engine import detect_compound_risk

@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()

def test_voice_hazard_extraction_and_risk_cofiring(db):
    transcript = "Shift supervisor note: The main methane gas line valve in Zone-C is acting up real bad and leaking gas near the furnace."
    
    # 1. Verify entity extraction
    extraction = extract_hazard_entities(transcript)
    assert "Zone-C" in extraction["mentioned_zones"]
    assert extraction["mentioned_hazard_type"] in ["gas", "equipment"]
    assert extraction["urgency_signal"] in ["high", "medium"]
    assert extraction["raw_quote"] is not None
    assert "Zone-C" in extraction["raw_quote"] or "valve" in extraction["raw_quote"] or "methane" in extraction["raw_quote"]

    now = datetime.utcnow()
    
    # 2. Seed synthetic active permit in Zone-C
    permit = models.Permit(
        permit_id="PERMIT-ZC-901",
        zone="Zone-C",
        permit_type="hot_work",
        issued_at=now,
        closed_at=None,
        issued_by="Officer Safety-1",
        dataset="default",
        plant_id="Plant-A"
    )
    db.add(permit)
    
    # 3. Seed extracted verbal report in Zone-C
    verbal_report = models.VerbalReport(
        zone="Zone-C",
        timestamp=now,
        transcript=transcript,
        hazard_type=extraction["mentioned_hazard_type"],
        urgency_signal=extraction["urgency_signal"],
        raw_quote=extraction["raw_quote"],
        is_anonymous=0,
        plant_id="Plant-A",
        dataset="default"
    )
    db.add(verbal_report)
    db.commit()

    # 4. Run risk engine evaluation
    assessment = detect_compound_risk(
        db,
        start_time=now,
        end_time=now,
        dataset="default",
        plant_id="Plant-A"
    )

    # 5. Assert RULE_VERBAL_HAZARD_REPORT_ACTIVE_PERMIT triggered
    rules = assessment["triggered_rules"]
    verbal_rule = next((r for r in rules if r["rule_name"] == "RULE_VERBAL_HAZARD_REPORT_ACTIVE_PERMIT"), None)
    
    assert verbal_rule is not None, "RULE_VERBAL_HAZARD_REPORT_ACTIVE_PERMIT should trigger when voice report co-occurs with active permit in Zone-C"
    assert verbal_rule["severity"] >= 2.0
    assert "Zone-C" in verbal_rule["reason"]
    assert extraction["raw_quote"] in verbal_rule["reason"] or "Zone-C" in verbal_rule["reason"]
    assert assessment["score"] >= 40, "Co-firing verbal hazard + active permit should escalate risk score"


def test_small_talk_voice_note_filtering():
    small_talk = "Good morning team, coffee machine is refilled in the breakroom."
    extraction = extract_hazard_entities(small_talk)
    
    assert extraction["mentioned_zones"] == []
    assert extraction["mentioned_hazard_type"] is None
    assert extraction["urgency_signal"] == "low"
    assert extraction["raw_quote"] is None
