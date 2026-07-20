import os
import json
import requests

REGULATORY_CLAUSES = {
    "OISD_105": "OISD Standard 105 (Section 5.2): Permit to Work Systems for Hot Work near potential ignition sources in hazardous areas.",
    "OISD_112": "OISD Standard 105 (Section 5.3): Safety in Confined Space Entry and atmospheric gas monitoring.",
    "FACTORIES_36": "Factories Act 1948 (Section 36): Precautions against dangerous fumes and mandatory gas testing before entry.",
    "FACTORIES_37": "Factories Act 1948 (Section 37): Electrical isolation and spark prevention in explosive gas presence.",
    "OISD_137": "OISD Standard 137: Guidelines for periodic inspection and maintenance of electrical equipment in hazardous areas."
}

def generate_fallback_narration(risk_data: dict, previous_risk_data: dict | None = None) -> dict:
    """
    Fallback explanation builder if LLM APIs are unavailable.
    Constructs delta-aware explanations when previous_risk_data is provided.
    """
    triggered_rules = risk_data.get("triggered_rules", [])
    tier = risk_data.get("tier", 1)
    current_score = risk_data.get("score", 0)
    rule_count = len(triggered_rules)
    multiplier = 1.0 if rule_count <= 1 else (1.3 if rule_count == 2 else 1.6)

    # Extract primary zone
    zone = "facility"
    for r in triggered_rules:
        reason = r.get("reason", "")
        for z in ["Zone-A", "Zone-B", "Zone-C", "Zone-D", "Zone-E", "Zone-F"]:
            if z in reason or f"_{z}_" in r.get("flag_id", ""):
                zone = z
                break
        if zone != "facility":
            break

    reasons = [r["reason"] for r in triggered_rules]
    rule_names = [r["rule_name"] for r in triggered_rules]

    current_state_explanation = (
        f"SentinelGrid's compound risk engine has flagged an active safety alert. " + " ".join(reasons)
        if triggered_rules else "No safety risk anomalies or rule violations are currently detected in the facility. Operations are normal."
    )

    if previous_risk_data is not None and "score" in previous_risk_data and previous_risk_data.get("score") is not None:
        prev_score = previous_risk_data["score"]
        score_delta = current_score - prev_score
        
        if score_delta != 0:
            change_direction = "increased" if score_delta > 0 else "decreased"
            if rule_count > 1:
                mult_desc = f"{rule_count} independent rules co-firing simultaneously ({multiplier}x multiplier), which is why the score {'more than doubled' if current_score >= prev_score * 2 and prev_score > 0 else 'jumped non-linearly'}"
            else:
                mult_desc = "1 active rule evaluated with standard 1.0x baseline weighting"
                
            explanation = (
                f"Risk in {zone} {change_direction} from {prev_score} to {current_score}: "
                + (" ".join(reasons) if reasons else "telemetry baseline changed")
                + f" — {mult_desc}."
            )
        else:
            explanation = f"Risk in {zone} remained steady at {current_score}: " + (" ".join(reasons) if reasons else "Operations nominal.")
    else:
        explanation = current_state_explanation

    evidence_packet = None
    if tier == 3 and triggered_rules:
        clause_key = "FACTORIES_36"
        verbal_quote = None
        if "RULE_HOT_WORK_NEAR_GAS_SPIKE" in rule_names:
            clause_key = "OISD_105"
        elif "RULE_CONFINED_SPACE_NEAR_GAS_SPIKE" in rule_names:
            clause_key = "OISD_112"
        elif "RULE_ELECTRICAL_WORK_NEAR_GAS_SPIKE" in rule_names:
            clause_key = "FACTORIES_37"
        elif "RULE_SILENT_SENSOR_DURING_PERMIT" in rule_names:
            clause_key = "OISD_137"
        elif "RULE_VERBAL_HAZARD_REPORT_ACTIVE_PERMIT" in rule_names:
            clause_key = "OISD_105"
            for r in triggered_rules:
                if r.get("rule_name") == "RULE_VERBAL_HAZARD_REPORT_ACTIVE_PERMIT":
                    reason_text = r.get("reason", "")
                    if "(" in reason_text and ")" in reason_text:
                        verbal_quote = reason_text[reason_text.find("(")+1:reason_text.rfind(")")]
            
        clause = REGULATORY_CLAUSES.get(clause_key)
        clause_rel = f"This scenario violates safety directives under {clause} because active permit tasks overlap with equipment/gas anomalies in the same area."
        if verbal_quote:
            clause_rel = f"This scenario violates safety directives under {clause} due to active permit co-occurring with an urgent shift-handover verbal report: {verbal_quote}."

        evidence_packet = {
            "summary": f"Incident flagged due to co-occurrence of: {', '.join(rule_names)}.",
            "rules_fired": rule_names,
            "applicable_clause": clause,
            "clause_relation": clause_rel
        }
        
    return {
        "explanation": explanation,
        "current_state_explanation": current_state_explanation,
        "delta_info": {
            "previous_score": previous_risk_data.get("score") if (previous_risk_data and "score" in previous_risk_data) else None,
            "current_score": current_score,
            "score_delta": (current_score - previous_risk_data["score"]) if (previous_risk_data and "score" in previous_risk_data and previous_risk_data.get("score") is not None) else 0,
            "rule_count": rule_count,
            "co_firing_multiplier": multiplier
        },
        "evidence_packet": evidence_packet
    }

_narration_cache = {}

def generate_risk_narration(risk_data: dict, previous_risk_data: dict | None = None) -> dict:
    """
    Translates structured risk engine outputs into natural language safety reports using Claude or Gemini.
    Supports delta-aware explanations grounded in co-firing multiplier logic.
    """
    cache_payload = {"current": risk_data, "previous": previous_risk_data}
    cache_key = json.dumps(cache_payload, sort_keys=True)
    if cache_key in _narration_cache:
        return _narration_cache[cache_key]

    gemini_key = os.getenv("GEMINI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    
    if not gemini_key and not anthropic_key:
        res = generate_fallback_narration(risk_data, previous_risk_data)
        _narration_cache[cache_key] = res
        return res

    triggered_rules = risk_data.get("triggered_rules", [])
    rule_count = len(triggered_rules)
    multiplier = 1.0 if rule_count <= 1 else (1.3 if rule_count == 2 else 1.6)

    context_str = f"Current Structured Risk Data:\n{json.dumps(risk_data, indent=2)}\nCo-firing Multiplier Context: {rule_count} active rules co-firing with a {multiplier}x Layer 2 multiplier.\n"
    if previous_risk_data and "score" in previous_risk_data and previous_risk_data.get("score") is not None:
        prev_score = previous_risk_data["score"]
        curr_score = risk_data.get("score", 0)
        context_str += f"Previous Risk Assessment Data:\n{json.dumps(previous_risk_data, indent=2)}\nScore Delta: Transited from {prev_score} to {curr_score} (change: {curr_score - prev_score}).\n"
        
    system_prompt = (
        "You are an industrial safety officer writing an explanation and a regulatory evidence packet for a safety report.\n"
        "Strict constraint: Do not alter, reassess, or ignore the deterministic engine's output. Only translate the provided structured details.\n"
        "Grounding Constraint: If previous risk data is provided, state the exact score transition (e.g., from X to Y) and reference the co-firing multiplier ({multiplier}x multiplier for {rule_count} co-firing rules) as the literal source of truth for WHY the score jumped non-linearly.\n"
        "You must NEVER invent regulatory clauses. You must choose ONLY from this list (by selecting the single most applicable one):\n"
        "1. OISD Standard 105 (Section 5.2): Permit to Work Systems for Hot Work near potential ignition sources in hazardous areas.\n"
        "2. OISD Standard 105 (Section 5.3): Safety in Confined Space Entry and atmospheric gas monitoring.\n"
        "3. Factories Act 1948 (Section 36): Precautions against dangerous fumes and mandatory gas testing before entry.\n"
        "4. Factories Act 1948 (Section 37): Electrical isolation and spark prevention in explosive gas presence.\n"
        "5. OISD Standard 137: Guidelines for periodic inspection and maintenance of electrical equipment in hazardous areas.\n\n"
        "Return your response as a valid JSON object with the following fields:\n"
        "{\n"
        "  \"explanation\": \"A 2-3 sentence plain-language explanation. If previous risk data is provided, explicitly state the score change and its cause, explaining how multiple rules co-firing (with the exact multiplier) caused the non-linear score jump.\",\n"
        "  \"current_state_explanation\": \"A 1-2 sentence description of the current risk state alone.\",\n"
        "  \"evidence_packet\": {\n"
        "    \"summary\": \"A brief description of the incident.\",\n"
        "    \"rules_fired\": [\"List of triggered rule names\"],\n"
        "    \"applicable_clause\": \"The exact selected clause reference from the allowed list above.\",\n"
        "    \"clause_relation\": \"Explanation of how the clause is violated in this scenario.\"\n"
        "  }\n"
        "}\n"
        "If the safety tier is NOT Tier 3 (the risk is low or medium), set \"evidence_packet\" to null."
    )
    
    # 1. Try Gemini if key is provided
    if gemini_key:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": context_str
                        }
                    ]
                }
            ],
            "systemInstruction": {
                "parts": [
                    {
                        "text": system_prompt
                    }
                ]
            },
        }
        try:
            response = requests.post(url, json=payload, timeout=2)
            if response.status_code == 200:
                res_json = response.json()
                text = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                if text.startswith("```json"):
                    text = text[7:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()
                parsed = json.loads(text)
                _narration_cache[cache_key] = parsed
                return parsed
        except Exception as e:
            print(f"Error calling Gemini API: {e}")

    # 2. Try Anthropic if key is provided
    if anthropic_key:
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": anthropic_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        payload = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 500,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": context_str}
            ]
        }
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=8)
            if response.status_code == 200:
                res_json = response.json()
                content = res_json["content"][0]["text"]
                text = content.strip()
                if text.startswith("```json"):
                    text = text[7:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()
                parsed = json.loads(text)
                _narration_cache[cache_key] = parsed
                return parsed
        except Exception as e:
            print(f"Error calling Anthropic API: {e}")
            
    res = generate_fallback_narration(risk_data, previous_risk_data)
    _narration_cache[cache_key] = res
    return res
