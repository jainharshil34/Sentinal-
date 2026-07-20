import pytest
from app.engine.narration import generate_fallback_narration, generate_risk_narration

def test_fallback_narration_nominal():
    risk_data = {
        "score": 0,
        "tier": 1,
        "tier_name": "Log Only",
        "triggered_rules": []
    }
    
    res = generate_fallback_narration(risk_data)
    assert "No safety risk anomalies" in res["explanation"]
    assert res["evidence_packet"] is None

def test_fallback_narration_tier3_hot_work():
    risk_data = {
        "score": 100,
        "tier": 3,
        "tier_name": "Escalate",
        "triggered_rules": [
            {
                "rule_name": "RULE_HOT_WORK_NEAR_GAS_SPIKE",
                "severity": 3,
                "reason": "Active hot work permit in Zone-A correlates with rising explosive CH4 levels (15.28 ppm) in adjacent Zone-A.",
                "contributing_signals": []
            },
            {
                "rule_name": "RULE_OVERDUE_MAINTENANCE_ACTIVE_PERMIT",
                "severity": 2,
                "reason": "Active permit (hot_work) in Zone-A correlates with overdue maintenance on equipment VENT-ZA-09 in the same zone.",
                "contributing_signals": []
            }
        ]
    }
    
    res = generate_fallback_narration(risk_data)
    assert "Active hot work permit in Zone-A" in res["explanation"]
    assert "VENT-ZA-09" in res["explanation"]
    
    packet = res["evidence_packet"]
    assert packet is not None
    assert "RULE_HOT_WORK_NEAR_GAS_SPIKE" in packet["rules_fired"]
    assert "OISD Standard 105" in packet["applicable_clause"]
    assert "violates safety directives" in packet["clause_relation"]

def test_generate_risk_narration_graceful_fallback():
    # If ANTHROPIC_API_KEY is not set (which is true in test sandbox),
    # it should gracefully invoke and return the programmatic fallback
    risk_data = {
        "score": 100,
        "tier": 3,
        "tier_name": "Escalate",
        "triggered_rules": [
            {
                "rule_name": "RULE_SILENT_SENSOR_DURING_PERMIT",
                "severity": 2,
                "reason": "Sensor for H2S in Zone-E went silent during active permit (confined_space).",
                "contributing_signals": []
            }
        ]
    }
    
    res = generate_risk_narration(risk_data)
    assert res is not None
    assert "explanation" in res
    assert "evidence_packet" in res
    assert "OISD Standard 137" in res["evidence_packet"]["applicable_clause"]


def test_delta_aware_fallback_narration():
    prev_data = {
        "score": 41,
        "tier": 2,
        "tier_name": "Dashboard Flag",
        "triggered_rules": [
            {
                "rule_name": "RULE_OVERDUE_MAINTENANCE_ACTIVE_PERMIT",
                "severity": 2,
                "reason": "Overdue maintenance on equipment VENT-ZA-09."
            }
        ]
    }
    curr_data = {
        "score": 83,
        "tier": 3,
        "tier_name": "Escalate",
        "triggered_rules": [
            {
                "rule_name": "RULE_HOT_WORK_NEAR_GAS_SPIKE",
                "severity": 3,
                "reason": "Active hot work permit in Zone-A correlates with rising CH4 levels."
            },
            {
                "rule_name": "RULE_OVERDUE_MAINTENANCE_ACTIVE_PERMIT",
                "severity": 2,
                "reason": "Overdue maintenance on equipment VENT-ZA-09."
            }
        ]
    }

    res = generate_risk_narration(curr_data, previous_risk_data=prev_data)
    assert res is not None
    assert "explanation" in res
    assert "increased from 41 to 83" in res["explanation"]
    assert "1.3x multiplier" in res["explanation"] or "co-firing" in res["explanation"]
    assert res["delta_info"]["previous_score"] == 41
    assert res["delta_info"]["current_score"] == 83
    assert res["delta_info"]["co_firing_multiplier"] == 1.3


def test_first_reading_non_delta_fallback():
    curr_data = {
        "score": 60,
        "tier": 2,
        "tier_name": "Dashboard Flag",
        "triggered_rules": [
            {
                "rule_name": "RULE_HOT_WORK_NEAR_GAS_SPIKE",
                "severity": 3,
                "reason": "Active hot work permit in Zone-A correlates with rising CH4 levels."
            }
        ]
    }

    # First reading (previous_risk_data is None)
    res = generate_risk_narration(curr_data, previous_risk_data=None)
    assert res is not None
    assert "increased from" not in res["explanation"]
    assert "SentinelGrid's compound risk engine" in res["explanation"]
    assert res["delta_info"]["previous_score"] is None

