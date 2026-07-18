# 🛡️ SentinelGrid: Data Sources & Credibility Matrix

This document maps the data sources used throughout SentinelGrid to verify compliance, train our Pattern Intelligence models, and configure risk thresholds. It details which elements of the system rely on **real-world regulatory limits and historical accident records** versus **synthetic/illustrative telemetry streams**.

---

## 1. Real-World Exposure Limits & Telemetry Thresholds

SentinelGrid's risk correlation thresholds align with exposure limits established by the United States Occupational Safety and Health Administration (OSHA), National Institute for Occupational Safety and Health (NIOSH), and the American Conference of Governmental Industrial Hygienists (ACGIH):

| Gas Type | System Baseline High Alarm | System Compound Risk Limit | Real-World Exposure Limit Baseline | Source Standard |
| :--- | :--- | :--- | :--- | :--- |
| **Carbon Monoxide (CO)** | **50.0 ppm** | **25.0 ppm** | 8-hour Time Weighted Average (TWA): **50 ppm** (OSHA)<br>8-hour TWA: **35 ppm** (NIOSH)<br>8-hour TWA: **25 ppm** (ACGIH) | [OSHA Carbon Monoxide Standards](https://www.osha.gov/chemicaldata/755)<br>[NIOSH Pocket Guide to CO](https://www.cdc.gov/niosh/npg/npgd0105.html) |
| **Hydrogen Sulfide ($H_2S$)** | **10.0 ppm** | **2.0 ppm** (Confined Space)<br>**5.0 ppm** (Hot Work) | 8-hour TWA: **10 ppm** (OSHA / NIOSH)<br>Ceiling (10 min): **10 ppm** (NIOSH)<br>Short-Term Exposure Limit (STEL): **5 ppm** (ACGIH) | [OSHA Hydrogen Sulfide Standards](https://www.osha.gov/hydrogen-sulfide/standards)<br>[NIOSH Pocket Guide to H2S](https://www.cdc.gov/niosh/npg/npgd0337.html) |
| **Methane ($CH_4$)** | **20.0% LEL** (10,005 ppm) | **10.0% LEL** (5,000 ppm) | Lower Explosive Limit (LEL) is **5.0% by volume** (50,000 ppm).<br>Mandated alarm limits: **10% LEL** and **20% LEL** for explosive atmospheres. | [OSHA Flammable Atmospheres](https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.146) |

*Note: In SentinelGrid, Methane ($CH_4$) values represent percent of Lower Explosive Limit (% LEL) rather than absolute ppm to remain physically compatible with standard industrial gas meters.*

---

## 2. Regulatory Compliance Clauses

SentinelGrid references specific safety clauses from Indian and international industrial regulations in both the Compliance Audit log and the Layer 3 AI Narration engine:

1. **OISD-STD-105 (Section 5.2) — Hot Work Permit:** 
   - *Requirement:* Governs authorization and control of hot work (welding, grinding, cutting) in explosive atmospheres. Mandates LEL testing before and during work.
   - *Source Link:* [Oil Industry Safety Directorate standards](https://oisd.gov.in/)
2. **OISD-STD-105 (Section 5.3) — Confined Space Entry Permit:** 
   - *Requirement:* Mandates physical isolation, purging, air monitoring (oxygen, flammables, toxics), and rescue watch protocols prior to entry.
   - *Source Link:* [Oil Industry Safety Directorate standards](https://oisd.gov.in/)
3. **Factories Act 1948 (Section 36) — Precautions against dangerous fumes:**
   - *Requirement:* Legally prohibits entry into confined spaces containing dangerous gas or fumes until testing proves the space is safe.
   - *Source Link:* [Factories Act 1948 full text](https://www.indiacode.nic.in/handle/123456789/1544)
4. **Factories Act 1948 (Section 37) — Explosive or inflammable dust, gas, etc.:**
   - *Requirement:* Requires all practical measures to prevent explosion or ignition of flammable gases in proximity to high-energy operations.
   - *Source Link:* [Factories Act 1948 full text](https://www.indiacode.nic.in/handle/123456789/1544)
5. **OISD-STD-137 — Inspection of Electrical Equipment:**
   - *Requirement:* Outlines strict inspection frequencies, testing protocols, and mechanical integrity requirements for electrical machinery operating in classified hazardous zones.
   - *Source Link:* [Oil Industry Safety Directorate standards](https://oisd.gov.in/)

---

## 3. Curated Real Incident Database (Pattern Intelligence)

The following real accidents have been compiled from public investigation records of the U.S. Chemical Safety and Hazard Investigation Board (CSB) and the Occupational Safety and Health Administration (OSHA). They are embedded in our RAG corpus (marked `source: "real_incident"`) and are used to detect systemic risk patterns:

| ID | Case / Source Citation | Incident Summary & Root Cause | Primary Rule Type |
| :--- | :--- | :--- | :--- |
| **18** | **CSB Report 2017-03-I-LA**<br>[View CSB Mill Investigation](https://www.csb.gov/packaging-corporation-of-america-hot-work-explosion/) | Hot work welding was authorized on piping connected to an un-isolated tank containing residual flammable chemicals, resulting in an explosion. Workers relied on verbal assumptions. Root cause: Permit approval without physical isolation or gas testing of connected vessels. | `RULE_HOT_WORK_NEAR_GAS_SPIKE` |
| **19** | **CSB Report 2008-01-I-CO**<br>[View CSB Cabin Creek Case](https://www.csb.gov/xcel-energy-cabin-creek-hydroelectric-plant-coal-fired-power-plant-fire/) | Five painters died in a flash fire inside a confined penstock tunnel due to flammable solvent buildup from epoxy. The space lacked ventilation. Root cause: Confined space entry permit authorized without air monitoring or rescue watch. | `RULE_CONFINED_SPACE_NEAR_GAS_SPIKE` |
| **20** | **CSB Report 2001-10-I-DE**<br>[View CSB Delaware Acid Case](https://www.csb.gov/motiva-enterprises-sulfuric-acid-tank-explosion/) | Sulfuric acid storage tank exploded during welding when hydrocarbons leaked from process vessels through degraded valves. Root cause: Hot work permit issued without testing tank roof atmosphere, despite known overdue repairs. | `RULE_HOT_WORK_NEAR_GAS_SPIKE` |
| **21** | **CSB Report 2006-07-I-MS**<br>[View CSB Mississippi Tank Case](https://www.csb.gov/partridge-raleigh-oilfield-explosion/) | Three contractors died when welding sparks ignited vapors inside oil production tanks. Root cause: Permit control failure due to lack of gas testing after breaks and absence of LEL monitors. | `RULE_HOT_WORK_NEAR_GAS_SPIKE` |
| **22** | **CSB Report 2006-01-I-FL**<br>[View CSB Bethune Case](https://www.csb.gov/bethune-point-wastewater-plant-explosion/) | Welders ignited methane gas venting from an adjacent sludge tank roof. Root cause: Hot work permit system failed to identify active atmospheric vents or mandate gas checks in the immediate area. | `RULE_HOT_WORK_NEAR_GAS_SPIKE` |
| **23** | **CSB Report 2015-02-I-CA**<br>[View CSB ExxonMobil Case](https://www.csb.gov/exxonmobil-refinery-explosion/) | Hydrocarbons backflowed into an electrostatic precipitator during maintenance due to a catalyst-jammed slide valve. Root cause: Operating and permitting repairs on equipment with overdue safety-critical valve maintenance. | `RULE_OVERDUE_MAINTENANCE_ACTIVE_PERMIT` |
| **24** | **CSB Report 2010-07-I-TX**<br>[View CSB DuPont Belle Case](https://www.csb.gov/dupont-belle-toxic-gas-releases/) | Fatal phosgene gas exposure caused by a ruptured transfer hose. Root cause: Degradation of critical phosgene transfer hoses that were overdue for replacement, and subsequent silent alarm failure. | `RULE_OVERDUE_MAINTENANCE_ACTIVE_PERMIT` |
| **25** | **CSB Report 2010-06-I-WA**<br>[View CSB Tesoro Case](https://www.csb.gov/tesoro-anacortes-refinery-heat-exchanger-rupture-/) | Catastrophic heat exchanger rupture during startup due to High Temperature Hydrogen Attack (HTHA). Root cause: Neglecting critical non-destructive inspections and delaying metallurgical upgrades. | `RULE_OVERDUE_MAINTENANCE_ACTIVE_PERMIT` |
| **26** | **CSB Report 2009-02-I-PR**<br>[View CSB CAPECO Case](https://www.csb.gov/caribbean-petroleum-refinery-explosion-and-fire/) | Marine fuel tank overflowed causing a massive vapor cloud explosion. Root cause: Overdue maintenance on level telemetry transmitter that went silent/uncalibrated, masking the rising level. | `RULE_SILENT_SENSOR_DURING_PERMIT` |
| **27** | **OSHA Inspection 315056708**<br>[View OSHA Valero Case](https://www.osha.gov/enforcement/dep/dep-investigations) | Two technicians asphyxiated inside a reactor vessel. Root cause: Confined space permit signed off without continuous oxygen/toxic monitoring, leading to entry into an immediately dangerous atmosphere. | `RULE_CONFINED_SPACE_NEAR_GAS_SPIKE` |
| **28** | **OSHA Inspection 310543781**<br>[View OSHA BP Texas Case](https://www.osha.gov/enforcement/dep/dep-investigations) | Hydrocarbon gas release during maintenance ignited, killing two. Root cause: Concurrent permit authorization for high-energy steam startup while isolation valves were still undergoing active repair. | `RULE_PERMIT_DURING_ACTIVE_REPAIR` |
| **29** | **CSB Report 2020-04-I-GA**<br>[View CSB Bio-Lab Case](https://www.csb.gov/bio-lab-chemical-fire-and-chlorine-release/) | Rainwater entered a chemical warehouse, reacting to cause a fire and toxic release. Root cause: Safety audits and building envelope maintenance were neglected, allowing moisture reaction. | `RULE_OVERDUE_MAINTENANCE_ACTIVE_PERMIT` |

---

## 4. Synthetic & Illustrative Data Components

For demonstration, training, and simulation purposes, the following parts of SentinelGrid are synthetic:

- **Zone Telemetry Readings:** Live sensor streams (`GasSensorReading`) are generated dynamically using random walks and noise around a realistic baseline, with injected anomalies representing the specific compound-risk scenarios.
- **Facility Floor Layout:** The spatial zones (`Zone-A` through `Zone-F`) are a representative layout modeling typical industrial layouts rather than mapping a specific physical refinery.
- **Pre-Seeded Incidents (1-17):** The original 17 incidents in the database represent hypothetical scenarios drafted to test specific risk rules (e.g., clerical error checks, routine safety walks) rather than real events. They remain marked as `source: "synthetic"`.
