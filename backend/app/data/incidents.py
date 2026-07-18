# Corpus of 17 synthetic incidents/near-misses and 12 real incidents distributed across the fleet
INCIDENT_CORPUS = [
    # 8 reports echoing existing compound-risk rules (Synthetic)
    {
        "id": 1,
        "text": "Flash fire occurred at the ventilation stack when hot work grinding was performed while methane gas levels were rising. Standard gas sniffers were active but the correlation with the active permit was not flagged in time.",
        "rule_type": "RULE_HOT_WORK_NEAR_GAS_SPIKE",
        "regulatory_clause": "OISD 105",
        "zone": "Zone-A",
        "plant_id": "Plant-C",
        "time_offset_desc": "four months ago",
        "source": "synthetic"
    },
    {
        "id": 2,
        "text": "A welder suffered minor burns during piping alterations. Methane vented from an adjacent relief valve pooled near the hot work site, causing a brief localized flare-up due to lagging inter-zone correlation.",
        "rule_type": "RULE_HOT_WORK_NEAR_GAS_SPIKE",
        "regulatory_clause": "OISD 105",
        "zone": "Zone-A",
        "plant_id": "Plant-B",
        "time_offset_desc": "six months ago",
        "source": "synthetic"
    },
    {
        "id": 3,
        "text": "During tank cleanout, two technicians lost consciousness due to carbon monoxide accumulation in the confined storage tank. The gas detector alarm was overdue for calibration and failed to sound at the safe threshold.",
        "rule_type": "RULE_CONFINED_SPACE_NEAR_GAS_SPIKE",
        "regulatory_clause": "OSHA 1910.146",
        "zone": "Zone-B",
        "plant_id": "Plant-C",
        "time_offset_desc": "three months ago",
        "source": "synthetic"
    },
    {
        "id": 4,
        "text": "Contractor team entered confined storage chamber for valve inspection. Slow buildup of CO went undetected until post-incident review because the portable multi-gas monitor was offline and overdue for annual service.",
        "rule_type": "RULE_CONFINED_SPACE_NEAR_GAS_SPIKE",
        "regulatory_clause": "OSHA 1910.146",
        "zone": "Zone-B",
        "plant_id": "Plant-A",
        "time_offset_desc": "eight months ago",
        "source": "synthetic"
    },
    {
        "id": 5,
        "text": "A hot work permit was active for Zone-D while the emergency exhaust fan calibration and maintenance was flagged as overdue. Welders experienced respiratory discomfort due to localized smoke accumulation.",
        "rule_type": "RULE_OVERDUE_MAINTENANCE_ACTIVE_PERMIT",
        "regulatory_clause": "OISD 105",
        "zone": "Zone-D",
        "plant_id": "Plant-B",
        "time_offset_desc": "one month ago",
        "source": "synthetic"
    },
    {
        "id": 6,
        "text": "Safety sensor in refinery tank went silent for 90 minutes. Confined space permit was active, but monitoring dashboard failed to alert operators that the telemetry connection had dropped, masking a concurrent H2S rise.",
        "rule_type": "RULE_SILENT_SENSOR_DURING_PERMIT",
        "regulatory_clause": "OSHA 1910.146",
        "zone": "Zone-E",
        "plant_id": "Plant-C",
        "time_offset_desc": "five months ago",
        "source": "synthetic"
    },
    {
        "id": 7,
        "text": "Refinery zone escalated to danger level when active routine permit overlapped with ongoing valve leak repair. Heavy maintenance was conducted simultaneously without cross-system safety verification, violating isolation protocols.",
        "rule_type": "RULE_PERMIT_DURING_ACTIVE_REPAIR",
        "regulatory_clause": "OISD 105",
        "zone": "Zone-C",
        "plant_id": "Plant-A",
        "time_offset_desc": "two months ago",
        "source": "synthetic"
    },
    {
        "id": 8,
        "text": "Simultaneous low levels of CO and H2S in routine loading area caused synergistic toxicity symptoms in two operators. Neither gas reached its standalone alarm limit, demonstrating compound toxicological exposure danger.",
        "rule_type": "RULE_MULTI_GAS_COMPOUND_TOXICITY",
        "regulatory_clause": "OSHA 1910.1000",
        "zone": "Zone-F",
        "plant_id": "Plant-B",
        "time_offset_desc": "nine months ago",
        "source": "synthetic"
    },
    # 5 reports describing incidents NOT caught by single-sensor systems (Synthetic)
    {
        "id": 9,
        "text": "Toxic gas pooling was detected only after the fact following a joint safety audit. Individual H2S and CO sensors showed sub-alarm levels, but the combination caused acute respiratory issues in workers.",
        "rule_type": "RULE_MULTI_GAS_COMPOUND_TOXICITY",
        "regulatory_clause": "OSHA 1910.1000",
        "zone": "Zone-F",
        "plant_id": "Plant-C",
        "time_offset_desc": "seven months ago",
        "source": "synthetic"
    },
    {
        "id": 10,
        "text": "Hydrocarbon leak in the process bay was detected only after the fact when a pipeline inspector noticed structural corrosion. The gas detector did not trigger because levels remained flat and below the alarm limit.",
        "rule_type": "UNSUPPORTED_RULE",
        "regulatory_clause": "OISD 137",
        "zone": "Zone-C",
        "plant_id": "Plant-A",
        "time_offset_desc": "ten months ago",
        "source": "synthetic"
    },
    {
        "id": 11,
        "text": "Methane accumulation in the switch room was detected only after the fact when thermal cameras showed abnormal temperatures. Individual sensors did not trigger because pooling occurred in a dead zone.",
        "rule_type": "UNSUPPORTED_RULE",
        "regulatory_clause": "IE Rule 1956",
        "zone": "Zone-D",
        "plant_id": "Plant-B",
        "time_offset_desc": "eleven months ago",
        "source": "synthetic"
    },
    {
        "id": 12,
        "text": "A valve packing failure released minor toxic vapors, detected only after the fact by a manual sniffer patrol. Local static sensors did not register any gas because the wind dispersed it immediately.",
        "rule_type": "UNSUPPORTED_RULE",
        "regulatory_clause": "OISD 137",
        "zone": "Zone-A",
        "plant_id": "Plant-C",
        "time_offset_desc": "one year ago",
        "source": "synthetic"
    },
    {
        "id": 13,
        "text": "A small pipeline flange leak of carbon monoxide was detected only after the fact when routine soil inspection showed localized plant degradation. The sensor was positioned too high to capture the low-density ground leak.",
        "rule_type": "UNSUPPORTED_RULE",
        "regulatory_clause": "OSHA 1910.146",
        "zone": "Zone-B",
        "plant_id": "Plant-A",
        "time_offset_desc": "one year ago",
        "source": "synthetic"
    },
    # 4 reports topically similar but NOT actually related (Synthetic)
    {
        "id": 14,
        "text": "Hot work permit was audited for clerical errors. The permit issuer had incorrect spelling on the safety officer name, but no hot work was actually performed and no gas was present.",
        "rule_type": "CLERICAL_ERROR",
        "regulatory_clause": "OISD 105",
        "zone": "Zone-A",
        "plant_id": "Plant-B",
        "time_offset_desc": "three weeks ago",
        "source": "synthetic"
    },
    {
        "id": 15,
        "text": "Confined space entry training certificates were audited for compliance. Several operator badges were expired, prompting a refresher course, but no environmental gas issues or active permits were involved.",
        "rule_type": "COMPLIANCE_AUDIT",
        "regulatory_clause": "OSHA 1910.146",
        "zone": "Zone-B",
        "plant_id": "Plant-C",
        "time_offset_desc": "five weeks ago",
        "source": "synthetic"
    },
    {
        "id": 16,
        "text": "Annual recalibration of methane sensors was completed ahead of schedule. The calibration team verified all limits are correct and baseline noise levels are normal.",
        "rule_type": "ROUTINE_CALIBRATION",
        "regulatory_clause": "OISD 137",
        "zone": "Zone-D",
        "plant_id": "Plant-A",
        "time_offset_desc": "two weeks ago",
        "source": "synthetic"
    },
    {
        "id": 17,
        "text": "A routine safety walk in the loading bay flagged missing fire extinguisher tags. Inspection records were updated online, but no active refinery permits or telemetry anomalies were detected.",
        "rule_type": "ROUTINE_SAFETY",
        "regulatory_clause": "OISD 105",
        "zone": "Zone-F",
        "plant_id": "Plant-B",
        "time_offset_desc": "one week ago",
        "source": "synthetic"
    },
    # 12 Real Incidents curated from CSB and OSHA databases
    {
        "id": 18,
        "text": "Hot work welding was authorized on piping connected to an un-isolated tank containing residual flammable chemicals, resulting in a flash fire and explosion. The safety management failed to perform a hazard analysis and workers relied on verbal assumptions. CSB investigation stated the root cause was permit approval without isolation or gas testing of connected vessels (CSB Report 2017-03-I-LA).",
        "rule_type": "RULE_HOT_WORK_NEAR_GAS_SPIKE",
        "regulatory_clause": "OISD 105",
        "zone": "Zone-A",
        "plant_id": "Plant-A",
        "time_offset_desc": "one year ago",
        "source": "real_incident"
    },
    {
        "id": 19,
        "text": "Five contractors died in a flash fire while coating a confined penstock tunnel with flammable epoxy solvents. The workspace had inadequate mechanical ventilation and lacked air monitoring or emergency rescue equipment. The investigation determined the root cause was confined space permit failure due to absence of atmospheric monitoring and planning (CSB Report 2008-01-I-CO).",
        "rule_type": "RULE_CONFINED_SPACE_NEAR_GAS_SPIKE",
        "regulatory_clause": "OSHA 1910.146",
        "zone": "Zone-B",
        "plant_id": "Plant-A",
        "time_offset_desc": "one year ago",
        "source": "real_incident"
    },
    {
        "id": 20,
        "text": "An acid storage tank exploded during welding repair due to flammable hydrocarbon vapors leaking from a nearby process vessel into the deteriorated tank. Corrosion and valve degradation allowed cross-contamination to go undetected. The investigation cited the root cause as hot work permit issuance without proper gas monitoring on a tank with overdue structural integrity maintenance (CSB Report 2001-10-I-DE).",
        "rule_type": "RULE_HOT_WORK_NEAR_GAS_SPIKE",
        "regulatory_clause": "OISD 105",
        "zone": "Zone-A",
        "plant_id": "Plant-B",
        "time_offset_desc": "one year ago",
        "source": "real_incident"
    },
    {
        "id": 21,
        "text": "Three contract workers were killed when welding sparks ignited flammable vapors inside oil production tanks during piping installation. The facility failed to perform gas testing after work breaks and lacked portable LEL monitors on site. The stated root cause was permit control failure due to inadequate gas monitoring procedures for active welding operations (CSB Report 2006-07-I-MS).",
        "rule_type": "RULE_HOT_WORK_NEAR_GAS_SPIKE",
        "regulatory_clause": "OISD 105",
        "zone": "Zone-A",
        "plant_id": "Plant-C",
        "time_offset_desc": "one year ago",
        "source": "real_incident"
    },
    {
        "id": 22,
        "text": "An explosion occurred during hot work welding near a methane-venting wastewater sludge tank, causing two contractor fatalities. The permit was issued without inspecting the area for atmospheric vents or potential gas accumulation. The investigation concluded the root cause was hot work permit process failure that ignored active gas vents in the immediate vicinity (CSB Report 2006-01-I-FL).",
        "rule_type": "RULE_HOT_WORK_NEAR_GAS_SPIKE",
        "regulatory_clause": "OISD 105",
        "zone": "Zone-A",
        "plant_id": "Plant-A",
        "time_offset_desc": "one year ago",
        "source": "real_incident"
    },
    {
        "id": 23,
        "text": "A massive explosion occurred at the electrostatic precipitator (ESP) during a shutdown when flammable hydrocarbons flowed back through a leaking slide valve. The slide valve was jammed with catalyst particles and was overdue for maintenance and inspection. The investigation stated the root cause was issuing maintenance permits while running equipment with overdue safety-critical valve maintenance (CSB Report 2015-02-I-CA).",
        "rule_type": "RULE_OVERDUE_MAINTENANCE_ACTIVE_PERMIT",
        "regulatory_clause": "OISD 105",
        "zone": "Zone-D",
        "plant_id": "Plant-B",
        "time_offset_desc": "one year ago",
        "source": "real_incident"
    },
    {
        "id": 24,
        "text": "A worker was fatally exposed to toxic phosgene gas when a phosgene transfer hose burst during operation. The hose was degraded and overdue for replacement, and the local gas detector alarm failed to alert the control room in time. The CSB investigation cited the root cause as systemic failure in mechanical integrity and inspection programs for safety-critical toxic gas systems (CSB Report 2010-07-I-TX).",
        "rule_type": "RULE_OVERDUE_MAINTENANCE_ACTIVE_PERMIT",
        "regulatory_clause": "OSHA 1910.146",
        "zone": "Zone-E",
        "plant_id": "Plant-C",
        "time_offset_desc": "one year ago",
        "source": "real_incident"
    },
    {
        "id": 25,
        "text": "A carbon steel heat exchanger ruptured catastrophically during refinery startup, releasing high-pressure hydrocarbons that exploded and killed seven. The vessel suffered from long-term High Temperature Hydrogen Attack (HTHA) which was undetected due to lack of advanced inspection testing. The root cause was identified as neglecting critical integrity testing and delaying upgrades to safer alloy materials (CSB Report 2010-06-I-WA).",
        "rule_type": "RULE_OVERDUE_MAINTENANCE_ACTIVE_PERMIT",
        "regulatory_clause": "OISD 105",
        "zone": "Zone-D",
        "plant_id": "Plant-A",
        "time_offset_desc": "one year ago",
        "source": "real_incident"
    },
    {
        "id": 26,
        "text": "A major fuel storage tank overflowed during marine delivery, causing a massive vapor cloud explosion. The tank level telemetry transmitter was uncalibrated and failed to alert operators that the tank had exceeded its capacity. The investigation concluded the root cause was the lack of functional level alarms and safety sensor systems on the primary storage tanks (CSB Report 2009-02-I-PR).",
        "rule_type": "RULE_SILENT_SENSOR_DURING_PERMIT",
        "regulatory_clause": "OISD 137",
        "zone": "Zone-E",
        "plant_id": "Plant-B",
        "time_offset_desc": "one year ago",
        "source": "real_incident"
    },
    {
        "id": 27,
        "text": "Two technicians entered a reactor vessel for catalyst removal and were asphyxiated by nitrogen and hydrogen sulfide gas. The entry was authorized without verifying isolation or maintaining continuous atmospheric monitoring. OSHA cited the root cause as confined space entry permit sign-off without conducting gas testing in an immediately dangerous atmosphere (OSHA Inspection 315056708).",
        "rule_type": "RULE_CONFINED_SPACE_NEAR_GAS_SPIKE",
        "regulatory_clause": "OSHA 1910.146",
        "zone": "Zone-B",
        "plant_id": "Plant-A",
        "time_offset_desc": "one year ago",
        "source": "real_incident"
    },
    {
        "id": 28,
        "text": "A release of highly flammable hydrocarbon gas during piping maintenance ignited and killed two refinery workers. The facility permitted concurrent operations: a high-energy steam startup overlapped with active valve repair in the same piping line. OSHA cited the root cause as failure to coordinate permits and isolate active repair lines, violating standard permit-to-work protocols (OSHA Inspection 310543781).",
        "rule_type": "RULE_PERMIT_DURING_ACTIVE_REPAIR",
        "regulatory_clause": "OISD 105",
        "zone": "Zone-C",
        "plant_id": "Plant-B",
        "time_offset_desc": "one year ago",
        "source": "real_incident"
    },
    {
        "id": 29,
        "text": "A severe warehouse fire released toxic chlorine gas when rainwater leaked through a damaged roof and reacted with stored chemicals. The building's roof integrity was degraded and building inspections were overdue. The CSB cited the root cause as failure to maintain structural integrity and safety detection systems in chemical storage zones, ignoring potential moisture reactions (CSB Report 2020-04-I-GA).",
        "rule_type": "RULE_OVERDUE_MAINTENANCE_ACTIVE_PERMIT",
        "regulatory_clause": "OSHA 1910.146",
        "zone": "Zone-F",
        "plant_id": "Plant-A",
        "time_offset_desc": "one year ago",
        "source": "real_incident"
    }
]
