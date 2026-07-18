# SentinelGrid: 5-Minute Pitch & Demo Script

This script outlines the exact click-by-click steps to deliver a high-impact, bug-free, 5-minute live demonstration of SentinelGrid for the hackathon judges.

---

## Pitch Structure: "Lead with the story, close with the numbers."
1. **Dashboard (Calm State)**: Establish baseline, nominal plant operations.
2. **Scenario Injection (The Incident)**: Simulate a compound threat in real-time, showing instantaneous AI safety summaries.
3. **Counterfactual Replay (The Emotional Beat)**: Show the historical Coke Oven battery disaster timeline and prove how SentinelGrid's correlation layer provides hours of early warning compared to legacy systems.
4. **Safety Scorecard (The Credibility Close)**: Deliver hard statistics on accuracy improvements, lead times, and compliance mapping.

---

## Live Click-by-Click Demo Flow

### Step 1: Baseline Dashboard (Time: 0:00 - 1:00)
- **Preparation**: Ensure the database is clean by clicking the **"Reset Demo DB"** button in the sidebar footer.
- **Action**: Navigate to the **Dashboard** (default home page).
- **Pitch Dialogue**:
  > *"Welcome to SentinelGrid. What you see here is a live visual floor plan of our facility. Under normal conditions (green), our six plant zones are safe. Sensor levels are normal, no safety rule violations are active, and our Risk Index is at 0. Traditional SCADA and DCS control rooms only watch individual gauges—waiting for a red line. SentinelGrid does something different. It correlates permits, maintenance databases, and gas sensors to catch problems before they happen."*

### Step 2: The Injected Incident (Time: 1:00 - 2:15)
- **Action**: Click the **"S1: Hot Work + Methane (Zone-A)"** button on the scenario control bar.
- **Visual Transition**: Zone-A immediately turns red (Danger/Tier 3) with a pulsing warning glow. The Risk Index dial shoots to 100.
- **Action**: Highlight the **Executive AI Briefing** speech bubble and the triggered rules below the map.
- **Pitch Dialogue**:
  > *"Let's simulate a live incident. With one click, we fast-forward our simulation clock. Instantly, Zone-A flashes red. Why? The SCADA gas sensor reads just 15 ppm methane—well below the static alarm threshold of 20 ppm. A legacy alarm system remains silent. But SentinelGrid's correlation engine catches that a Hot Work permit is active in Zone-A, and the ventilation system maintenance check is overdue. Our AI translation layer summarizes this for the safety officer instantly: active ignition sources are overlapping with gas accumulation in a compromised ventilation zone."*

### Step 3: The Replay & The Emotional Beat (Time: 2:15 - 3:45)
- **Action**: Click **"Counterfactual Replay"** in the sidebar. Keep the view on the **Incident Timeline Replay** tab.
- **Action**: Scroll horizontally to show the two parallel tracks: *"What actually happened"* vs *"What SentinelGrid would have flagged"*.
- **Pitch Dialogue**:
  > *"To show why this matters, let's step back and look at a real-world disaster. On this timeline, we reconstruct the Vizag Coke Oven battery gas buildup from public reports. On the top track is the actual timeline: a pressure regulator calibration check was overdue; CO gas started building up; workers started hot maintenance work; and finally, the gas crossed the critical 300 ppm lethal threshold.
  >
  > Now look at the bottom track. By correlating the work permit, gas telemetry, and overdue calibration check, SentinelGrid would have flagged a Tier 3 warning at Hour +10.0—providing an extra **155 minutes of warning** before the atmosphere became life-threatening. We lead with story: this margin is the difference between an orderly evacuation and a major industrial incident."*
- **Action** (Optional): Click the **"Mitigation Sandbox"** tab. Toggle off the active hot work permit. Show how the simulated risk score drops to green, proving how operators can run counterfactual "what-if" scenarios.

### Step 4: The Scorecard & Credibility Close (Time: 3:45 - 5:00)
- **Action**: Click **"Scorecard"** in the sidebar.
- **Visuals**: Highlight the large stat cards and the **Zone Compliance Audit** table.
- **Pitch Dialogue**:
  > *"We close with the numbers. Our performance scorecard compares SentinelGrid against standard single-sensor thresholds across the entire seeded 72-hour dataset.
  > 
  > First, our compound risk engine achieves **100% accuracy** in catching all major hazards in their early windows, compared to **0%** for single-sensor baselines. 
  > Second, we offer an average of **155 minutes of advance warning** before critical incident limits are crossed. 
  > Third, every single alert maintains **100% evidence quality**—correlating database IDs and zones. 
  > And fourth, our false negative count is exactly **0**.
  > 
  > SentinelGrid shifts industrial safety from reactive alarms to proactive, auditable compound intelligence. Thank you."*

---

## Troubleshooting & Verification Checklist

- [ ] **Reset Button**: If the database gets polluted or you want to restart a run, click **Reset Demo DB** in the sidebar. The page will reload in 1-2 seconds with a clean state.
- [ ] **API Failures**: If any backend endpoint fails, the frontend displays user-friendly warning banners instead of blanking out or throwing raw stack traces.
- [ ] **Instant Loading**: Replay timeline and scorecard data are highly optimized and cached on the backend, ensuring they load in less than 50 milliseconds with zero lag on stage.
