# Athlete Dossier — Section 11 AI Coaching Protocol

## Identity

* Name: Paulo Pinto
* Age: 42
* Location: (not specified)
* Device: Garmin Venu Sq 2 → direct sync to Intervals.icu
* HRV Tracking: No (device does not broadcast raw RR intervals — DFA a1 protocol not applicable)

---

## Running Background

* Experience: Ran seriously 2015–2018, stopped 2019, returned gradually 2023–2025
* 2025 Annual Volume: 673 km
* Current Weekly Volume: ~30 km (as of April 2026, post-race recovery week)
* Training Days: Tuesday, Wednesday, Thursday, Saturday, Sunday
* Cross-training: None

---

## Race History & PRs

| Race               | Date           | Time    | Notes                                                  |
| ------------------ | -------------- | ------- | ------------------------------------------------------ |
| Half Marathon      | March 22, 2026 | 2:06:00 | Positive split — strong to 10k, significant fade after |
| Half Marathon (PR) | 2017           | 1:43:30 | Peak fitness era                                       |

---

## March 2026 Race Analysis

* Started at ~5:40/km (too aggressive for current fitness)
* Held pace to ~10 km, then faded to ~7:00/km
* Average HR: ~175 bpm
* Post-race: significant right calf soreness → 1 week full rest

**Conclusion:**
Undertrained for goal pace. Pacing error + insufficient aerobic base led to late-race fade.

---

## Current Goal

* Race: Half Marathon
* Date: October 25, 2026
* Goal: Sub 1:43:30 (beat 2017 PR)
* Target pace: ~4:56/km
* Timeline: ~27 weeks from April 2026
* Motivation: Return to peak fitness and validate performance potential

---

## Heart Rate Profile

* Resting HR: Unknown — use Intervals.icu data
* Max HR: Unknown — derive from Intervals.icu (estimated ~185–190)
* Lactate Threshold HR: Estimated ~170–175 bpm (based on race data)
* HRV: Not tracked
* Zone Preference: HR-based (no power meter)

### Estimated HR Zones (to refine)

| Zone | Name         | % Max HR | Approx BPM |
| ---- | ------------ | -------- | ---------- |
| Z1   | Recovery     | < 68%    | < 128      |
| Z2   | Aerobic Base | 68–83%   | 128–157    |
| Z3   | Tempo        | 83–94%   | 157–178    |
| Z4   | Threshold    | 94–105%  | 178–188    |
| Z5   | VO2 Max      | > 105%   | > 188      |

**Zone source:** Intervals.icu (auto-detected max HR preferred over estimates)

---

## Current Paces (April 2026)

* Easy pace: ~6:30/km
* 10K effort: ~6:00/km
* Half marathon (current): ~6:00/km
* Goal HM pace: 4:56/km

---

## Training Profile

* Current phase: Base rebuilding (post March 2026 HM)

* Biggest limiters:

  * Aerobic base depth
  * Pacing discipline
  * Muscular endurance late in long efforts

* Injury history:

  * Right calf — soreness post March 2026 HM (resolved)
  * Monitor closely during volume increases

* Sleep: Excellent

* Recovery: Good (Garmin Body Battery used as proxy)

---

## Coaching Directives

* **Pacing discipline is priority #1** — tendency to start too fast

* All workouts must include clear pace/HR targets

* Long runs strictly capped at Z2

* **Injury prevention:**

  * Monitor right calf closely
  * No intensity increases if tightness appears

* **Intensity distribution:**

  * 80/20 rule (Z1–Z2 dominant)
  * Avoid “grey zone” drift on easy days

* **Volume progression:**

  * Max +10% weekly increase
  * Every 4th week = cutback (~20% reduction)

* **Long run progression:**

  * Build from ~15 km → 19–20 km peak (weeks 11–13)

* **Race-specific work:**

  * Introduce race pace (~4:56/km) from week 8 onward

* **Fueling:**

  * Typically trains fasted in the morning
  * No caffeine use

* **Training structure:**

  * No cross-training
  * Strength work encouraged but not currently implemented

---

## 27-Week Plan Overview

| Phase         | Weeks | Focus                                             |
| ------------- | ----- | ------------------------------------------------- |
| Base Building | 1–6   | Consistency, easy volume, aerobic development     |
| Development   | 7–12  | Tempo work, extend long runs, introduce race pace |
| Peak          | 13–18 | Highest mileage, race-pace intervals              |
| Specific      | 19–24 | Race-specific sessions, possible tune-up races    |
| Taper         | 25–27 | Reduce volume, maintain sharpness                 |

---

## Data Sources

* Platform: Intervals.icu
* Sync: GitHub Actions (every 15 minutes)
* Protocol: Section 11 (SECTION_11.md)
* Data files:

  * latest.json
  * history.json
  * intervals.json (when applicable)
  * routes.json (when applicable)
