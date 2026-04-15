#!/usr/bin/env python3
"""
Intervals.icu → GitHub/Local JSON Export
Exports training data for LLM access.
Supports both automated GitHub sync and manual local export.

Version 3.102 - Phase detection fixes: corrected three independent bugs causing in-Build weeks
  to misclassify as Base on Mon/Tue after a deload→Build cycle. (1) ctl_slope was a 2-point chord
  divided by len(values) instead of (n-1) and included the in-progress current week's partial
  mid-day CTL — replaced with statistics.linear_regression over finalized weeks (chord-over-(n-1)
  fallback for Python <3.10). (2) Build/Base scorer used hard_sessions_planned (current week
  remainder only), never merging completed-so-far with planned-remaining — added
  current_week_hard_days_completed and current_week_hard_days_total on stream_2; scorer now
  reads the merged total. (3) plan_coverage_* denominator was hard-coded expected_sessions=5,
  producing values up to 2.6 for athletes training 12-17 sessions/week — now derives from rolling
  4-week mean activity_count over finalized weeks (fallback 5). New is_backfill flag on
  _phase_stream1_features and _detect_phase_v2 controls whether weekly_rows[-1] is sliced off
  (live, in-progress week excluded) or kept (backfill, target week sits at [-1]). History
  regen loop now skips the in-progress current week entirely. Live weekly_rows build extended
  to include activity_count per row (was history-only before).

Version 3.101 - has_dfa split + dfa_summary: new has_dfa boolean on recent_activities[] in
  latest.json, independent from has_intervals. has_intervals semantics narrowed to structured
  segments only — a steady Z2 ride with AlphaHRV now reports has_intervals: false, has_dfa: true
  (previously the latter overloaded the former). New compact dfa_summary block attached when
  has_dfa: true AND quality.sufficient: true — fields: avg, dominant_band (max-pct, alphabetical
  tiebreak), tiz_pct (4 bands), valid_pct, sufficient, plus optional drift_delta/drift_interpretable
  and lt1/lt2 watts/hr (omitted when underlying data absent — never null-filled). Lets the AI
  write post-workout DFA commentary from latest.json alone for the common case. quality.sufficient
  tightened: previously duration-only (>=20 min valid); now also requires valid_pct >= 70%. New
  constant DFA_SUFFICIENT_MIN_VALID_PCT = 70.0. Excludes noisy AlphaHRV sessions that previously
  passed the duration gate (pre-existing latent bug). New helper _build_dfa_summary() — pure
  extractor, no computation, single source of truth shared with capability summary.

Version 3.100 - DFA power calibration indoor/outdoor split: trailing_by_sport.cycling lt1/lt2
  estimates now split watts by environment (watts_outdoor, watts_indoor — always present, null
  when no qualifying sessions). HR stays pooled. Per-environment n_sessions for depth assessment.
  Shared _is_indoor_cycling() resolver (VirtualRide = indoor) replaces inline checks.
  Non-cycling sports unchanged. Activity name anonymization removed — names pass through as-is
  for coaching context (route identification, terrain association). athlete_id always redacted.
  
Version 3.99 - DFA a1 Protocol: per-session dfa block in intervals.json (artifact-filtered avg,
  4-zone TIZ split with HR/power cross-references, drift, LT1/LT2 crossing-band estimates,
  quality gates). New generic streams fetcher infrastructure (_fetch_activity_streams). dfa_a1_profile
  in latest.json capability block (latest_session + trailing_by_sport with confidence + validation
  flags). Always emits dfa block when streams fetched, even if quality.sufficient is False, so the
  AI can distinguish "no AlphaHRV" from "AlphaHRV ran but unusable". Intervals retention 8d → 14d
  to support drift analysis across multiple AlphaHRV sessions. Sport scope: all interval families;
  threshold mapping (1.0/0.5) cycling-validated, other sports flagged validated=False.
  Requires AlphaHRV Connect IQ data field, direct Garmin sync (Strava strips dev fields).

Version 3.98 - Schema rename: derived_metrics.polarisation_index → easy_time_ratio (and _note).
  Disambiguates from Seiler polarization_index (Treff PI). Rename only — no formula or value change.

Version 3.97 - Readiness signal hygiene: low-side ACWR removed from readiness_decision ambers
  and ACWR alerts — low ACWR is a load-state/undertraining context signal, not a fatigue signal,
  and already surfaces via acwr_interpretation. RI amber now requires 2-day persistence (ri<0.7
  today AND yesterday) to filter single-night noise; red still fires on any single day <0.6.
  New derived metric: recovery_index_yesterday. ACWR high-side boundary unified across code and
  docs: >=1.3 amber/caution, >=1.5 red/danger (replaces mixed >/>= usage).

Version 3.96 - Course character fix: elevation_per_km as sole density metric (total elevation
  is distance-blind); absolute elevation thresholds removed. Climb-category upgrade retained for
  "flat with one big climb" cases.

Version 3.95–3.88 — Polyline + event metadata; phase detection live weekly rows; Route & Terrain Intelligence (GPX/TCX → routes.json); local-sync auto-clear on script change; Sustainability Profile (per-sport power/HR for race estimation); sleep signal simplified to hours-only; phase detection current-week runtime overlay; HR Curve Delta (4 anchor durations, cross-sport).

Version 3.87–3.85 — Power curve delta, primary sport TSS filtering for phase detection, wellness field expansion
Version 3.84–3.80 — Activity description passthrough, per-sport zone preference, interval-level data, feel removed from readiness, orphan cleanup
Versions 3.7–3.79 — Phase detection v2, readiness decision, HRRc, week alignment, local sync pipeline, hash manifest, feel/RPE fix
Versions 3.3.0–3.6.5 — EF tracking, HR zone fallback, race calendar, durability, TID, alerts, history.json, smart fitness metrics
"""

import requests
import json
import os
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import base64
import math
import statistics
import hashlib
import zipfile
import tempfile
import shutil
import atexit
from collections import defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET


class IntervalsSync:
    """Sync Intervals.icu data to GitHub repository or local file"""
    
    INTERVALS_BASE_URL = "https://intervals.icu/api/v1"
    GITHUB_API_URL = "https://api.github.com"
    FTP_HISTORY_FILE = "ftp_history.json"
    HISTORY_FILE = "history.json"
    UPSTREAM_REPO = "CrankAddict/section-11"
    CHANGELOG_FILE = "changelog.json"
    VERSION = "3.102"
    INTERVALS_FILE = "intervals.json"
    ROUTES_FILE = "routes.json"

    # Sport families eligible for interval-level data extraction.
    # Only structured sessions in these families are worth fetching
    # per-interval detail for. Walk, strength, yoga, other excluded.
    INTERVAL_SPORT_FAMILIES = {"cycling", "run", "ski", "rowing", "swim"}
    INTERVAL_SCAN_HOURS = 72    # Only scan recent activities for new intervals
    INTERVAL_RETENTION_DAYS = 14  # Keep cached intervals for 14 days (DFA drift analysis window)

    # --- DFA a1 Protocol (v3.99) ---
    # Per-session DFA a1 rollups computed from streams when AlphaHRV Connect IQ field
    # has written to the FIT and Intervals.icu surfaces dfa_a1 + artifacts streams.
    # Threshold mapping (1.0 / 0.5) is cycling-validated (Rowlands 2017, Gronwald 2020,
    # Mateo-March 2023). Other sports get rollups but validated=False.
    DFA_LT1 = 1.0                       # DFA a1 above this = below LT1 (true aerobic)
    DFA_LT2 = 0.5                       # DFA a1 below this = above LT2 (supra-threshold)
    DFA_LT1_BAND = 0.05                 # crossing window for LT1 estimate: 0.95-1.05
    DFA_LT2_BAND = 0.05                 # crossing window for LT2 estimate: 0.45-0.55
    DFA_MIN_CROSSING_DWELL_SECS = 60    # min seconds in crossing band to emit threshold estimate
    DFA_ARTIFACT_MAX_PCT = 5.0          # drop seconds where artifacts % exceeds this
    DFA_MIN_VALID_VALUE = 0.01          # exclude AlphaHRV sentinel zeros
    DFA_MIN_DURATION_SECS = 1200        # 20 min minimum valid data for sufficient=True
    DFA_SUFFICIENT_MIN_VALID_PCT = 70.0 # min valid_pct for sufficient=True (excludes noisy AlphaHRV sessions)
    DFA_DRIFT_INTERPRETABLE_MAX_LT2_PCT = 15.0  # if >15% time above LT2, drift is structural noise
    DFA_TRAILING_WINDOW_N = 7           # latest N AlphaHRV sessions for trailing window (≥6 needed for 'high' confidence)
    DFA_VALIDATED_SPORTS = {"cycling"}  # sports where 1.0/0.5 mapping is literature-validated

    # Sport family mapping for per-sport monotony calculation
    # Multi-sport athletes get inflated total monotony when cross-training
    # adds a consistent TSS floor across days. Per-sport monotony isolates
    # the actual load variation within each modality.
    SPORT_FAMILIES = {
        "Ride": "cycling",
        "VirtualRide": "cycling",
        "MountainBikeRide": "cycling",
        "GravelRide": "cycling",
        "EBikeRide": "cycling",
        "VirtualSki": "ski",
        "NordicSki": "ski",
        "Walk": "walk",
        "Hike": "walk",
        "Run": "run",
        "VirtualRun": "run",
        "TrailRun": "run",
        "Swim": "swim",
        "Rowing": "rowing",
        "WeightTraining": "strength",
        "Yoga": "other",
        "Workout": "other",
    }
    
    # Activity types that may contain location data in their name
    OUTDOOR_TYPES = {"Ride", "MountainBikeRide", "GravelRide", "EBikeRide",
                     "Run", "TrailRun", "NordicSki", "Walk", "Hike"}
    
    # Indoor cycling detection — shared resolver for DFA profile, sustainability profile, etc.
    INDOOR_CYCLING_TYPES = {"VirtualRide"}

    @classmethod
    def _is_indoor_cycling(cls, activity_type: str) -> bool:
        """True when activity_type represents an indoor cycling session."""
        return activity_type in cls.INDOOR_CYCLING_TYPES

    # Training week start day (Python weekday: Mon=0, Tue=1, Wed=2, Thu=3, Fri=4, Sat=5, Sun=6)
    # Default Monday (ISO). Override via .sync_config.json, WEEK_START env var, or --week-start CLI arg.
    WEEK_START_DAY = 0
    
    # --- Sustainability Profile (v3.91) ---
    # Race estimation lookup table: what power/HR is sustainable at each duration?
    SUSTAINABILITY_WINDOW_DAYS = 42
    
    # Per-sport anchor durations (seconds). Cycling covers long events; SkiErg/rowing are shorter.
    SUSTAINABILITY_ANCHORS = {
        "cycling": {"300s": 300, "600s": 600, "1200s": 1200, "1800s": 1800, "3600s": 3600, "5400s": 5400, "7200s": 7200},
        "ski":     {"60s": 60, "120s": 120, "300s": 300, "600s": 600, "1200s": 1200, "1800s": 1800},
        "rowing":  {"60s": 60, "120s": 120, "300s": 300, "600s": 600, "1200s": 1200, "1800s": 1800},
    }
    
    # Coggan duration factors — midpoints of published ranges. Cycling only.
    # Source: Allen & Coggan, Training and Racing with a Power Meter (3rd ed.)
    # Sustainable power as fraction of FTP by duration.
    COGGAN_DURATION_FACTORS = {
        300:  1.06,   # 5min:  ~106% FTP (range 100-112%)
        600:  0.97,   # 10min: ~97% FTP (range 94-100%)
        1200: 0.93,   # 20min: ~93% FTP (range 91-95%)
        1800: 0.90,   # 30min: ~90% FTP (range 88-93%)
        3600: 0.86,   # 60min: ~86% FTP (range 83-90%)
        5400: 0.82,   # 90min: ~82% FTP (range 78-85%)
        7200: 0.78,   # 2h:    ~78% FTP (range 75-82%)
    }
    
    # Activity types for sport-filtered power-curves fetch
    SUSTAINABILITY_POWER_TYPES = {
        "cycling": ["Ride", "VirtualRide"],
        "ski":     ["NordicSki", "VirtualSki"],
        "rowing":  ["Rowing"],
    }
    
    # Activity types for sport-filtered hr-curves fetch
    SUSTAINABILITY_HR_TYPES = {
        "cycling": ["Ride", "VirtualRide"],
        "ski":     ["NordicSki", "VirtualSki"],
        "rowing":  ["Rowing"],
    }
    
    def __init__(self, athlete_id: str, intervals_api_key: str, github_token: str = None, 
                 github_repo: str = None, debug: bool = False, week_start_day: int = None,
                 zone_preference: dict = None):
        self.athlete_id = athlete_id
        self.intervals_auth = base64.b64encode(f"API_KEY:{intervals_api_key}".encode()).decode()
        self.github_token = github_token
        self.github_repo = github_repo
        self.debug = debug
        self.script_dir = Path(__file__).parent
        self.data_dir = Path.cwd()  # Data files (history.json, ftp_history.json) write to caller's working directory
        self.week_start_day = week_start_day if week_start_day is not None else self.WEEK_START_DAY
        self.zone_preference = zone_preference or {}  # {"run": "hr", "cycling": "power", ...}
        self._cached_script_hash = None  # lazy-computed
    
    @property
    def script_hash(self) -> str:
        """SHA256 of sync.py itself. Used to invalidate cached files on any code change."""
        if self._cached_script_hash is None:
            script_path = Path(__file__).resolve()
            h = hashlib.sha256()
            with open(script_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    h.update(chunk)
            self._cached_script_hash = h.hexdigest()[:12]  # short hash, sufficient for change detection
        return self._cached_script_hash
    
    def _intervals_get(self, endpoint: str, params: Dict = None) -> Dict:
        """Fetch from Intervals.icu API"""
        if endpoint:
            url = f"{self.INTERVALS_BASE_URL}/athlete/{self.athlete_id}/{endpoint}"
        else:
            url = f"{self.INTERVALS_BASE_URL}/athlete/{self.athlete_id}"
        headers = {
            "Authorization": f"Basic {self.intervals_auth}",
            "Accept": "application/json"
        }
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()

    def _get_activity_messages(self, activity_id: str) -> List[str]:
        """Fetch messages/notes for a completed activity. Returns list of text strings."""
        url = f"{self.INTERVALS_BASE_URL}/activity/{activity_id}/messages"
        headers = {
            "Authorization": f"Basic {self.intervals_auth}",
            "Accept": "application/json"
        }
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            messages = response.json()
            if isinstance(messages, list):
                return [m.get("content", m.get("text", "")) for m in messages if (m.get("content") or m.get("text", "")).strip()]
            return []
        except Exception:
            return []
    
    def _fetch_activity_intervals(self, activity_id: str) -> List[Dict]:
        """Fetch interval segments for a single activity. Returns icu_intervals list or empty list on failure."""
        url = f"{self.INTERVALS_BASE_URL}/activity/{activity_id}"
        headers = {
            "Authorization": f"Basic {self.intervals_auth}",
            "Accept": "application/json"
        }
        try:
            response = requests.get(url, headers=headers, params={"intervals": "true"})
            response.raise_for_status()
            data = response.json()
            intervals = data.get("icu_intervals", [])
            if isinstance(intervals, list):
                return intervals
            return []
        except Exception as e:
            if self.debug:
                print(f"    ⚠️  Could not fetch intervals for {activity_id}: {e}")
            return []

    def _fetch_activity_streams(self, activity_id: str, types: List[str]) -> Dict[str, List]:
        """
        Fetch per-second streams for a single activity.

        Generic streams fetcher for any rollup metric that needs second-by-second data.
        Returns a dict keyed by stream type, value is the data list. Streams not present
        in the response are simply absent from the returned dict.

        Returns empty dict on 404/exception. Many activities won't have AlphaHRV-derived
        streams (no Connect IQ field installed, sourced via Strava which strips dev fields,
        wrong sport, etc.) — that's expected and not an error.

        Note on cache invalidation: streams are fetched once per activity. If the underlying
        FIT is reprocessed in AlphaHRV's mobile app and re-uploaded, the cached rollup will
        be stale. Rare in practice; workaround is to delete intervals.json.
        """
        url = f"{self.INTERVALS_BASE_URL}/activity/{activity_id}/streams"
        headers = {
            "Authorization": f"Basic {self.intervals_auth}",
            "Accept": "application/json"
        }
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, list):
                return {}
            wanted = set(types)
            out = {}
            for s in data:
                stype = s.get("type")
                if stype in wanted:
                    sdata = s.get("data")
                    if isinstance(sdata, list):
                        out[stype] = sdata
            return out
        except Exception as e:
            if self.debug:
                print(f"    ⚠️  Could not fetch streams for {activity_id}: {e}")
            return {}

    def _compute_dfa_block(self, streams: Dict[str, List]) -> Optional[Dict]:
        """
        Compute per-session DFA a1 rollup from raw streams.

        Inputs: streams dict from _fetch_activity_streams, expected keys:
          dfa_a1, artifacts, heartrate, watts (heartrate/watts optional but degrade output)

        Returns the dfa block dict, or None if dfa_a1 stream is absent entirely
        (i.e. AlphaHRV did not record on this activity).

        When dfa_a1 IS present but data is insufficient to interpret (too short,
        too noisy), returns a block with quality.sufficient=False so the AI can
        distinguish "no AlphaHRV" (None → no dfa key in output) from "AlphaHRV
        ran but unusable" (block present, sufficient=False).

        Filtering rules (in order):
          1. Drop seconds where dfa_a1 < DFA_MIN_VALID_VALUE (AlphaHRV sentinel zeros)
          2. Drop seconds where artifacts > DFA_ARTIFACT_MAX_PCT (5%, Altini convention)
        Both filters applied jointly to dfa_a1, hr, watts so they stay aligned.
        """
        dfa_stream = streams.get("dfa_a1")
        if not dfa_stream:
            return None  # no AlphaHRV recording on this activity

        artifacts_stream = streams.get("artifacts") or [0.0] * len(dfa_stream)
        hr_stream = streams.get("heartrate") or [None] * len(dfa_stream)
        watts_stream = streams.get("watts") or [None] * len(dfa_stream)

        # Align all streams to dfa_a1 length (defensive — should already match)
        n = len(dfa_stream)
        if len(artifacts_stream) != n:
            artifacts_stream = (artifacts_stream + [0.0] * n)[:n]
        if len(hr_stream) != n:
            hr_stream = (hr_stream + [None] * n)[:n]
        if len(watts_stream) != n:
            watts_stream = (watts_stream + [None] * n)[:n]

        # Apply filters
        valid_dfa, valid_hr, valid_watts = [], [], []
        artifact_sum = 0.0
        artifact_count = 0
        for i in range(n):
            d = dfa_stream[i]
            a = artifacts_stream[i]
            if a is not None:
                artifact_sum += a
                artifact_count += 1
            if d is None or d < self.DFA_MIN_VALID_VALUE:
                continue
            if a is not None and a > self.DFA_ARTIFACT_MAX_PCT:
                continue
            valid_dfa.append(d)
            valid_hr.append(hr_stream[i])
            valid_watts.append(watts_stream[i])

        valid_secs = len(valid_dfa)
        total_secs = n
        valid_pct = round(100.0 * valid_secs / tota
