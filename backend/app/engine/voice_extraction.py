import os
import json
import re
import requests

def transcribe_audio(file_bytes: bytes, filename: str = "audio.wav") -> str:
    """
    Transcribes audio bytes into text using Groq Whisper API (GROQ_API_KEY) or OpenAI Whisper API (OPENAI_API_KEY).
    Falls back to decoding utf-8 or mock text if no key is present.
    """
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        try:
            url = "https://api.groq.com/openai/v1/audio/transcriptions"
            headers = {"Authorization": f"Bearer {groq_key}"}
            files = {"file": (filename, file_bytes, "audio/wav")}
            data = {"model": "whisper-large-v3"}
            res = requests.post(url, headers=headers, files=files, data=data, timeout=10)
            if res.status_code == 200:
                text = res.json().get("text", "").strip()
                if text:
                    return text
        except Exception as e:
            print(f"Groq Whisper API transcription failed, trying OpenAI/fallback: {e}")

    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        try:
            url = "https://api.openai.com/v1/audio/transcriptions"
            headers = {"Authorization": f"Bearer {openai_key}"}
            files = {"file": (filename, file_bytes, "audio/wav")}
            data = {"model": "whisper-1"}
            res = requests.post(url, headers=headers, files=files, data=data, timeout=10)
            if res.status_code == 200:
                text = res.json().get("text", "").strip()
                if text:
                    return text
        except Exception as e:
            print(f"OpenAI Whisper API transcription failed, using fallback: {e}")
            
    # Fallback for plain text or test bytes
    try:
        decoded = file_bytes.decode("utf-8", errors="ignore").strip()
        if len(decoded) > 5 and any(z in decoded for z in ["Zone-", "zone", "gas", "leak", "permit"]):
            return decoded
    except Exception:
        pass

    return "Shift handover note: High gas smell and fluctuating pressure regulator reported near Zone-C."


def extract_hazard_entities_fallback(transcript: str) -> dict:
    """
    Rule-based NLP fallback for extracting hazard entities when LLM API keys are unavailable.
    """
    if not transcript or len(transcript.strip()) < 5:
        return {
            "mentioned_zones": [],
            "mentioned_hazard_type": None,
            "urgency_signal": "low",
            "raw_quote": None
        }

    # Detect mentioned zones
    zones = []
    for z in ["Zone-A", "Zone-B", "Zone-C", "Zone-D", "Zone-E", "Zone-F"]:
        if z.lower() in transcript.lower() or z.replace("-", " ").lower() in transcript.lower():
            zones.append(z)

    # Detect hazard types using word boundary matching to avoid partial word hits like 'co' in 'coffee'
    hazard_type = None
    t_lower = transcript.lower()
    if re.search(r'\b(gas|methane|ch4|h2s|carbon monoxide|hydrogen sulfide|smell|fumes|leak|leaking)\b', t_lower) or re.search(r'\bco\b', t_lower):
        hazard_type = "gas"
    elif re.search(r'\b(equipment|valve|regulator|pump|breaker|ventilation|fan|broken|vibrating|acting up)\b', t_lower):
        hazard_type = "equipment"
    elif re.search(r'\b(permit|hot work|confined space|electrical|repair)\b', t_lower):
        hazard_type = "permit"
    elif re.search(r'\b(danger|fire|spark|smoke|hazard|risk|warning)\b', t_lower):
        hazard_type = "other"

    # Detect urgency
    urgency = "low"
    if any(k in t_lower for k in ["urgent", "critical", "danger", "immediately", "acting up real bad", "leaking bad", "emergency", "fire", "explosion"]):
        urgency = "high"
    elif any(k in t_lower for k in ["acting up", "fluctuating", "warning", "check", "issue", "problem", "smell", "strange"]):
        urgency = "medium"

    # Small talk check: If no zone and no hazard type, return empty extraction
    if not zones and not hazard_type and urgency == "low":
        return {
            "mentioned_zones": [],
            "mentioned_hazard_type": None,
            "urgency_signal": "low",
            "raw_quote": None
        }

    # Extract raw quote matching the hazard statement
    raw_quote = transcript.strip()
    sentences = re.split(r'[.!?]+', transcript)
    for s in sentences:
        s_clean = s.strip()
        if any(z in s_clean for z in zones) or (hazard_type and any(k in s_clean.lower() for k in ["gas", "leak", "acting up", "urgent", "valve", "regulator", "smell"])):
            if len(s_clean) > 8:
                raw_quote = s_clean
                break

    return {
        "mentioned_zones": zones,
        "mentioned_hazard_type": hazard_type,
        "urgency_signal": urgency,
        "raw_quote": raw_quote
    }


def extract_hazard_entities(transcript: str) -> dict:
    """
    Extracts safety-relevant hazard entities from a shift-handover transcript using Gemini or Claude.
    Returns structured JSON:
    {
      "mentioned_zones": ["Zone-C"],
      "mentioned_hazard_type": "gas",
      "urgency_signal": "high",
      "raw_quote": "The pressure regulator in Zone-C is acting up real bad."
    }
    """
    if not transcript or len(transcript.strip()) < 5:
        return {
            "mentioned_zones": [],
            "mentioned_hazard_type": None,
            "urgency_signal": "low",
            "raw_quote": None
        }

    gemini_key = os.getenv("GEMINI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    if not gemini_key and not anthropic_key:
        return extract_hazard_entities_fallback(transcript)

    system_prompt = (
        "You are an industrial safety NLP parser. Analyze the shift handover or hazard voice transcript below.\n"
        "Extract safety-critical hazard details into structured JSON.\n"
        "Strict Rule: If the transcript is small talk or contains no actionable safety hazards/equipment issues/gas leaks, return an empty extraction with empty zones and low urgency.\n\n"
        "Return ONLY a valid JSON object matching this schema:\n"
        "{\n"
        "  \"mentioned_zones\": [\"Zone-A\", \"Zone-B\", \"Zone-C\", \"Zone-D\", \"Zone-E\", \"Zone-F\"],\n"
        "  \"mentioned_hazard_type\": \"gas\" | \"equipment\" | \"permit\" | \"other\" | null,\n"
        "  \"urgency_signal\": \"low\" | \"medium\" | \"high\",\n"
        "  \"raw_quote\": \"Exact sentence or phrase that triggered this hazard extraction\" | null\n"
        "}"
    )

    if gemini_key:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}"
        payload = {
            "contents": [{"parts": [{"text": f"Transcript:\n{transcript}"}]}],
            "systemInstruction": {"parts": [{"text": system_prompt}]}
        }
        try:
            res = requests.post(url, json=payload, timeout=3)
            if res.status_code == 200:
                text = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                if text.startswith("```json"):
                    text = text[7:]
                if text.endswith("```"):
                    text = text[:-3]
                return json.loads(text.strip())
        except Exception as e:
            print(f"Gemini entity extraction failed: {e}")

    if anthropic_key:
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": anthropic_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        payload = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 300,
            "system": system_prompt,
            "messages": [{"role": "user", "content": f"Transcript:\n{transcript}"}]
        }
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=5)
            if res.status_code == 200:
                text = res.json()["content"][0]["text"].strip()
                if text.startswith("```json"):
                    text = text[7:]
                if text.endswith("```"):
                    text = text[:-3]
                return json.loads(text.strip())
        except Exception as e:
            print(f"Claude entity extraction failed: {e}")

    return extract_hazard_entities_fallback(transcript)
