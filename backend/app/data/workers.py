from datetime import datetime, timedelta

# Static definitions of worker offsets relative to their zone's SVG boundary
ZONE_OFFSETS = {
    "Zone-A": {"x": 40, "y": 40},
    "Zone-B": {"x": 40, "y": 220},
    "Zone-C": {"x": 280, "y": 40},
    "Zone-D": {"x": 280, "y": 220},
    "Zone-E": {"x": 555, "y": 40},
    "Zone-F": {"x": 555, "y": 220}
}

# Worker profile template
WORKERS_PROFILES = [
    {"id": 1, "name": "John Doe", "role": "technician", "offset": {"x": 60, "y": 60}},
    {"id": 2, "name": "Alice Smith", "role": "operator", "offset": {"x": 140, "y": 60}},
    {"id": 3, "name": "Bob Johnson", "role": "contractor", "offset": {"x": 60, "y": 100}},
    {"id": 4, "name": "Charlie Brown", "role": "operator", "offset": {"x": 140, "y": 100}},
    {"id": 5, "name": "Sarah Davis", "role": "technician", "offset": {"x": 100, "y": 80}}
]

def get_simulated_workers(scenario: str) -> list[dict]:
    """
    Returns simulated worker positions (zone, absolute SVG x/y coordinates)
    based on the currently injected simulation scenario.
    Ties 1-2 workers to the danger zone for each active scenario.
    """
    now_str = datetime.utcnow().isoformat() + "Z"
    workers = []
    
    # Define zone mapping per scenario
    # Default/Normal layout: scattered safely
    zone_mapping = {
        1: "Zone-E", # John
        2: "Zone-F", # Alice
        3: "Zone-B", # Bob
        4: "Zone-C", # Charlie
        5: "Zone-D"  # Sarah
    }
    
    if scenario == "scenario_1":
        # Zone-A is active (Hot Work + Methane)
        # John and Bob are present in Zone-A (inside the danger zone!)
        zone_mapping[1] = "Zone-A"
        zone_mapping[3] = "Zone-A"
    elif scenario == "scenario_2":
        # Zone-B is active (Confined Space + CO)
        # John and Bob are present in Zone-B
        zone_mapping[1] = "Zone-B"
        zone_mapping[3] = "Zone-B"
    elif scenario == "scenario_3":
        # Zone-C is active (H2S leak + Valve repair)
        # Alice and Charlie are present in Zone-C
        zone_mapping[2] = "Zone-C"
        zone_mapping[4] = "Zone-C"
    elif scenario == "scenario_4":
        # Zone-D is active (Electrical + CH4)
        # John and Sarah are present in Zone-D
        zone_mapping[1] = "Zone-D"
        zone_mapping[5] = "Zone-D"
    elif scenario == "silent_failure":
        # Zone-E is active
        # John and Sarah are present in Zone-E
        zone_mapping[1] = "Zone-E"
        zone_mapping[5] = "Zone-E"
    elif scenario == "vizag_buildup":
        # Zone-C is active
        # Alice and Charlie are present in Zone-C
        zone_mapping[2] = "Zone-C"
        zone_mapping[4] = "Zone-C"

    # Compile the final list with calculated coordinates
    for profile in WORKERS_PROFILES:
        w_id = profile["id"]
        zone = zone_mapping.get(w_id, "Zone-F")
        base = ZONE_OFFSETS.get(zone, {"x": 40, "y": 40})
        
        workers.append({
            "id": w_id,
            "name": profile["name"],
            "role": profile["role"],
            "zone": zone,
            "x": base["x"] + profile["offset"]["x"],
            "y": base["y"] + profile["offset"]["y"],
            "last_update": now_str
        })
        
    return workers
