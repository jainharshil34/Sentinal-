import re
from datetime import datetime

# Regex pattern for parsing SCADA tags like ZC.GAS.CH4.ZONE_A
TAG_REGEX = re.compile(r"^ZC\.GAS\.(CH4|H2S|CO|O2)\.ZONE_([A-F])$", re.IGNORECASE)

# Configurable tag-to-zone/gas-type mapping table
# This maps raw industrial plant telemetry tags to internal schema attributes.
TAG_MAPPING = {
    # Industrial tags where zone is not explicitly named in the string (e.g. .PV)
    "ZC.GAS.CH4.PV": {"zone": "Zone-A", "gas_type": "CH4"},
    "ZC.GAS.H2S.PV": {"zone": "Zone-C", "gas_type": "H2S"},
    "ZC.GAS.CO.PV": {"zone": "Zone-E", "gas_type": "CO"},
    "ZC.GAS.O2.PV": {"zone": "Zone-B", "gas_type": "O2"},
    
    # Modbus style register mappings
    "40001.CH4": {"zone": "Zone-A", "gas_type": "CH4"},
    "40002.H2S": {"zone": "Zone-C", "gas_type": "H2S"},
    "40003.CO": {"zone": "Zone-E", "gas_type": "CO"},
    "40004.O2": {"zone": "Zone-B", "gas_type": "O2"},
    
    # Standard tags that include zone explicitly (backwards compatibility)
    "ZC.GAS.CH4.ZONE_A": {"zone": "Zone-A", "gas_type": "CH4"},
    "ZC.GAS.H2S.ZONE_C": {"zone": "Zone-C", "gas_type": "H2S"},
    "ZC.GAS.CO.ZONE_E": {"zone": "Zone-E", "gas_type": "CO"},
    "ZC.GAS.O2.ZONE_B": {"zone": "Zone-B", "gas_type": "O2"},
}

def parse_opc_tag(tag_name: str, value: float, timestamp_str: str = None) -> dict:
    """
    Parses a raw OPC-UA/Modbus tag name (e.g., 'ZC.GAS.H2S.PV') and returns a dictionary
    conforming to the internal GasSensorReading model.
    
    Uses a configurable mapping table first, falling back to regex tag resolution.
    Returns None if the tag format is unrecognized.
    """
    mapping = TAG_MAPPING.get(tag_name.upper())
    if mapping:
        gas_type = mapping["gas_type"].upper()
        zone = mapping["zone"]
    else:
        # Fallback to regex pattern matching
        match = TAG_REGEX.match(tag_name)
        if not match:
            return None
            
        gas_type = match.group(1).upper()
        zone_letter = match.group(2).upper()
        zone = f"Zone-{zone_letter}"
    
    # Parse timestamp
    if timestamp_str:
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            timestamp = datetime.utcnow()
    else:
        timestamp = datetime.utcnow()
        
    return {
        "sensor_id": f"scada_{gas_type.lower()}_{zone.lower().replace('-', '_')}",
        "gas_type": gas_type,
        "reading_value": float(value),
        "zone": zone,
        "timestamp": timestamp
    }

