import json
import io
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.database import SessionLocal
from app.db import models

client = TestClient(app)

def test_analyze_and_upload_csv_permit():
    # 1. Prepare messy CSV mock file in-memory
    csv_content = (
        "Permit No,Work Type,Start Time,Zone Ref,Plant ID\n"
        "PERMIT-SCADA-9988,Confined Space,2026-07-16 10:00:00,Zone-C,Plant-A\n"
        "PERMIT-SCADA-9989,Hot Work,2026-07-16 11:30:00,Zone-D,Plant-A\n"
    )
    file_bytes = csv_content.encode("utf-8")
    
    # 2. Call POST /api/ingest/analyze
    files = {"file": ("permits_messy.csv", file_bytes, "text/csv")}
    analyze_res = client.post("/api/ingest/analyze", files=files)
    assert analyze_res.status_code == 200
    analyze_data = analyze_res.json()
    
    assert analyze_data["type"] == "permit"
    assert "Permit No" in analyze_data["headers"]
    
    suggested = analyze_data["suggested_mapping"]
    assert suggested.get("Permit No") == "permit_id"
    assert suggested.get("Work Type") == "permit_type"
    assert suggested.get("Start Time") == "issued_at"
    assert suggested.get("Zone Ref") == "zone"

    # 3. Perform ingestion upload
    mapping_payload = {
        "Permit No": "permit_id",
        "Work Type": "permit_type",
        "Start Time": "issued_at",
        "Zone Ref": "zone",
        "Plant ID": "plant_id"
    }
    
    upload_files = {"file": ("permits_messy.csv", file_bytes, "text/csv")}
    form_data = {
        "mapping": json.dumps(mapping_payload),
        "type": "permit"
    }
    
    upload_res = client.post("/api/ingest/upload", files=upload_files, data=form_data)
    assert upload_res.status_code == 200
    upload_data = upload_res.json()
    assert upload_data["status"] == "success"
    assert upload_data["count"] == 2
    assert upload_data["type"] == "permit"
    
    # Verify in DB
    db = SessionLocal()
    permit = db.query(models.Permit).filter(models.Permit.permit_id == "PERMIT-SCADA-9988").first()
    assert permit is not None
    assert permit.permit_type == "Confined Space"
    assert permit.zone == "Zone-C"
    
    # Clean up test permits to keep DB pristine for other tests
    db.query(models.Permit).filter(models.Permit.permit_id.in_(["PERMIT-SCADA-9988", "PERMIT-SCADA-9989"])).delete()
    db.commit()
    db.close()

def test_ingest_opc_tag_telemetry():
    # Submit raw SCADA tags and custom PV / Modbus tags
    payload = [
        {"tag": "ZC.GAS.CH4.ZONE_A", "value": 2.5, "quality": "GOOD"},
        {"tag": "ZC.GAS.H2S.PV", "value": 4.8, "quality": "GOOD"},
        {"tag": "40003.CO", "value": 11.2, "quality": "GOOD"},
        {"tag": "INVALID_TAG", "value": 9.9, "quality": "BAD"}
    ]
    
    res = client.post("/api/ingest/tag", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["parsed_count"] == 3  # Custom mapped tags resolved correctly
    
    # Verify in DB
    db = SessionLocal()
    # 1. ZC.GAS.H2S.PV -> Zone-C, H2S
    reading_h2s = db.query(models.GasSensorReading).filter(
        models.GasSensorReading.zone == "Zone-C",
        models.GasSensorReading.gas_type == "H2S"
    ).order_by(models.GasSensorReading.timestamp.desc()).first()
    assert reading_h2s is not None
    assert reading_h2s.reading_ppm == 4.8

    # 2. 40003.CO -> Zone-E, CO
    reading_co = db.query(models.GasSensorReading).filter(
        models.GasSensorReading.zone == "Zone-E",
        models.GasSensorReading.gas_type == "CO"
    ).order_by(models.GasSensorReading.timestamp.desc()).first()
    assert reading_co is not None
    assert reading_co.reading_ppm == 11.2
    db.close()

def test_get_tag_mapping():
    res = client.get("/api/ingest/tag-mapping")
    assert res.status_code == 200
    data = res.json()
    assert "ZC.GAS.H2S.PV" in data
    assert data["ZC.GAS.H2S.PV"]["zone"] == "Zone-C"
    assert data["ZC.GAS.H2S.PV"]["gas_type"] == "H2S"

def test_analyze_with_forced_type():
    csv_content = (
        "ColumnA,ColumnB,ColumnC\n"
        "1,2,3\n"
    )
    file_bytes = csv_content.encode("utf-8")
    files = {"file": ("random_file.csv", file_bytes, "text/csv")}
    
    # Analyze with forced type 'maintenance'
    res = client.post("/api/ingest/analyze?type=maintenance", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["type"] == "maintenance"
    assert data["method"] in ["Rule-based (Fuzzy)", "LLM-Assisted (Claude)"]

