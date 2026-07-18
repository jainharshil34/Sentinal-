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

def generate_fallback_narration(risk_data: dict) -> dict:
    """
    Fallback explanation builder if the Anthropic API is unavailable.
    """
    triggered_rules = risk_data.get("triggered_rules", [])
    tier = risk_data.get("tier", 1)
    
    if not triggered_rules:
        return {
            "explanation": "No safety risk anomalies or rule violations are currently detected in the facility. Operations are normal.",
            "evidence_packet": None
        }
        
    # Generate 2-3 sentences based on rules
    reasons = [r["reason"] for r in triggered_rules]
    rule_names = [r["rule_name"] for r in triggered_rules]
    
    # Format a human-readable explanation
    explanation = "SentinelGrid's compound risk engine has flagged an active safety alert. " + " ".join(reasons)
    
    evidence_packet = None
    if tier == 3:
        # Determine clause programmatically
        clause_key = "FACTORIES_36"
        if "RULE_HOT_WORK_NEAR_GAS_SPIKE" in rule_names:
            clause_key = "OISD_105"
        elif "RULE_CONFINED_SPACE_NEAR_GAS_SPIKE" in rule_names:
            clause_key = "OISD_112"
        elif "RULE_ELECTRICAL_WORK_NEAR_GAS_SPIKE" in rule_names:
            clause_key = "FACTORIES_37"
        elif "RULE_SILENT_SENSOR_DURING_PERMIT" in rule_names:
            clause_key = "OISD_137"
            
        clause = REGULATORY_CLAUSES.get(clause_key)
        evidence_packet = {
            "summary": f"Incident flagged due to co-occurrence of: {', '.join(rule_names)}.",
            "rules_fired": rule_names,
            "applicable_clause": clause,
            "clause_relation": f"This scenario violates safety directives under {clause} because active permit tasks overlap with equipment/gas anomalies in the same area."
        }
        
    return {
        "explanation": explanation,
        "evidence_packet": evidence_packet
    }

def generate_risk_narration(risk_data: dict) -> dict:
    """
    Translates structured risk engine outputs into natural language safety reports using Claude or Gemini.
    """
    gemini_key = os.getenv("GEMINI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    
    if not gemini_key and not anthropic_key:
        return generate_fallback_narration(risk_data)
        
    system_prompt = (
        "You are an industrial safety officer writing an explanation and a regulatory evidence packet for a safety report.\n"
        "Strict constraint: Do not alter, reassess, or ignore the deterministic engine's output. Only translate the provided structured details.\n"
        "You must NEVER invent regulatory clauses. You must choose ONLY from this list (by selecting the single most applicable one):\n"
        "1. OISD Standard 105 (Section 5.2): Permit to Work Systems for Hot Work near potential ignition sources in hazardous areas.\n"
        "2. OISD Standard 105 (Section 5.3): Safety in Confined Space Entry and atmospheric gas monitoring.\n"
        "3. Factories Act 1948 (Section 36): Precautions against dangerous fumes and mandatory gas testing before entry.\n"
        "4. Factories Act 1948 (Section 37): Electrical isolation and spark prevention in explosive gas presence.\n"
        "5. OISD Standard 137: Guidelines for periodic inspection and maintenance of electrical equipment in hazardous areas.\n\n"
        "Return your response as a valid JSON object with the following fields:\n"
        "{\n"
        "  \"explanation\": \"A 2-3 sentence plain-language explanation of what happened for a non-technical safety officer.\",\n"
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
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": f"Structured Risk Data:\n{json.dumps(risk_data, indent=2)}"
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
            "generationConfig": {
                "responseMimeType": "application/json"
            }
        }
        try:
            response = requests.post(url, json=payload, timeout=8)
            if response.status_code == 200:
                res_json = response.json()
                text = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                if text.startswith("```json"):
                    text = text[7:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()
                parsed = json.loads(text)
                return parsed
            else:
                print(f"Gemini API returned status {response.status_code}: {response.text}")
        except Exception as e:
            print(f"Error calling Gemini API: {e}")

    # 2. Fall back to Anthropic
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
                {"role": "user", "content": f"Structured Risk Data:\n{json.dumps(risk_data, indent=2)}"}
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
                return parsed
            else:
                print(f"Anthropic API returned status {response.status_code}: {response.text}")
        except Exception as e:
            print(f"Error calling Anthropic API: {e}")
            
    return generate_fallback_narration(risk_data)
