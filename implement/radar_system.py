"""
╔══════════════════════════════════════════════════════════════════════╗
║  MCDIS — Multi-Modal Counter-Drone Intelligence System              ║
║  Module: Radar System v3.0                                            ║
║  Classification: UNCLASSIFIED // FOR OFFICIAL USE ONLY               ║
╠══════════════════════════════════════════════════════════════════════╣
║  Components:                                                          ║
║    1. RadarReturn      — Single target return with spherical coords  ║
║    2. MicroDopplerClassifier — Classify target by RCS + velocity     ║
║    3. TrackManager    — Nearest-neighbor multi-target association    ║
║    4. ThreatZoneMonitor — 3-ring threat zone alerting system         ║
║    5. RadarEngine     — Master orchestrator                           ║
║                                                                       ║
║  Threat Zones:                                                        ║
║    OUTER  — 5km radius : Long-range detection + EW prep              ║
║    MIDDLE — 2km radius : Engagement decision zone                    ║
║    INNER  — 500m radius: Immediate kinetic engagement                ║
╚══════════════════════════════════════════════════════════════════════╝

REAL HARDWARE NOTE:
─────────────────────────────────────────────────────────────────────
  In production, this module ingests real radar returns from:
    • FMCW Radar (e.g., InnoSent IVS-479, XeThru X4M200)
    • Pulse-Doppler radar (e.g., Robin Radar ELVIRA, DeTect HARRIER)
    • Phased array radar systems (academic/military grade)
    
  The physics models (RCS, Doppler, SNR) are calibrated to real-world
  values for each drone class. Replace _simulate_return() with your
  actual radar hardware interface (serial, UDP, custom SDK).
─────────────────────────────────────────────────────────────────────
"""

import math
import time
import random
import threading
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from collections import deque, defaultdict
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "mcdis"))
try:
    from database import db
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

# ══════════════════════════════════════════════════════════════════════
#  CPU OPTIMISATION BLOCK
#  Radar classification (MicroDoppler scoring) is pure float math —
#  parallelise across all available CPU cores.
# ══════════════════════════════════════════════════════════════════════
_CPU_CORES   = os.cpu_count() or 4
_RADAR_POOL  = ThreadPoolExecutor(
    max_workers=_CPU_CORES,
    thread_name_prefix="MCDIS-Radar"
)
print(f"[RADAR HW] CPU cores: {_CPU_CORES} | Parallel classification pool ready")


# ══════════════════════════════════════════════════════════════════════
#  CONSTANTS & PHYSICS
# ══════════════════════════════════════════════════════════════════════

# Speed of light (m/s)
C_LIGHT = 3e8

# Radar cross sections (m²) per target class — real-world estimates
DRONE_RCS = {
    "shahed_136":        0.5,    # Delta-wing, ~0.5m² face-on
    "fpv_suicide":       0.005,  # Tiny, H-frame, ~5cm²
    "military_fixed_wing": 1.5,  # Large, fuselage dominant
    "wing_loong":        2.0,    # Large MALE class
    "military_rotor":    0.2,    # Medium tactical rotor
    "swarm_unit":        0.003,  # Individual swarm drone (< bird)
    "dji_large":         0.02,   # DJI Phantom-class, ~20cm²
    "dji_mini":          0.004,  # DJI Mini, ~4cm²
    "generic_commercial":0.01,
    "micro_nano":        0.001,  # < 1cm²
    "bird":              0.01,   # Similar to DJI Mini (false positive risk)
    "fixed_aircraft":    5.0,
}

# Typical velocity ranges (m/s) per class [min, max]
DRONE_VELOCITY = {
    "shahed_136":        (10, 60),    # ~185 km/h typical
    "fpv_suicide":       (5, 40),     # Up to 150 km/h
    "military_fixed_wing":(30, 180),
    "wing_loong":        (25, 80),
    "military_rotor":    (5, 30),
    "swarm_unit":        (3, 15),
    "dji_large":         (2, 18),
    "dji_mini":          (2, 14),
    "generic_commercial":(2, 15),
    "micro_nano":        (1, 8),
    "bird":              (2, 20),
    "fixed_aircraft":    (50, 300),
}

# Micro-Doppler spectral features (normalized)
MICRO_DOPPLER_SIGNATURES = {
    # class: (blade_harmonics, flap_freq_hz, rotor_periodicity)
    "shahed_136":          (2, 0,    0.0),   # Fixed-wing: 2 harmonics, no flap
    "fpv_suicide":         (4, 0,    1.0),   # 4 motors, high periodicity
    "military_fixed_wing": (2, 0,    0.1),
    "wing_loong":          (2, 0,    0.1),
    "military_rotor":      (6, 0,    0.9),   # Hexacopter
    "swarm_unit":          (4, 0,    0.8),
    "dji_large":           (4, 0,    0.85),  # Quadcopter
    "dji_mini":            (4, 0,    0.9),
    "generic_commercial":  (4, 0,    0.7),
    "micro_nano":          (4, 0,    0.95),
    "bird":                (0, 4,    0.0),   # Wing flapping: 4Hz, no motors
    "fixed_aircraft":      (2, 0,    0.05),
}


# ══════════════════════════════════════════════════════════════════════
#  DATA STRUCTURES
# ══════════════════════════════════════════════════════════════════════

@dataclass
class RadarReturn:
    """
    Single radar target return — contains both spherical and Cartesian coords.
    
    Spherical: (range_m, azimuth_deg, elevation_deg) — natural radar format
    Cartesian: (x_m, y_m, z_m)                       — for fusing with vision
    """
    target_id:    str
    range_m:      float          # Slant range from radar antenna (m)
    azimuth_deg:  float          # Bearing from North, clockwise (0-360°)
    elevation_deg:float          # Elevation angle above horizon (-90 to +90°)
    radial_vel_ms:float          # Doppler radial velocity (m/s, +ve = moving away)
    rcs_m2:       float          # Measured radar cross section (m²)
    snr_db:       float          # Signal-to-noise ratio (dB)
    timestamp:    float = field(default_factory=time.time)
    class_hint:   str = ""       # Optional pre-classification hint

    # Derived Cartesian coordinates (auto-computed)
    x_m: float = field(init=False)
    y_m: float = field(init=False)
    z_m: float = field(init=False)

    def __post_init__(self):
        self._compute_cartesian()

    def _compute_cartesian(self):
        """Convert spherical → Cartesian (East-North-Up convention)."""
        r   = self.range_m
        az  = math.radians(self.azimuth_deg)
        el  = math.radians(self.elevation_deg)
        self.x_m = r * math.cos(el) * math.sin(az)   # East
        self.y_m = r * math.cos(el) * math.cos(az)   # North
        self.z_m = r * math.sin(el)                   # Up (altitude)

    @property
    def horizontal_range_m(self) -> float:
        return math.sqrt(self.x_m**2 + self.y_m**2)

    @property
    def speed_ms(self) -> float:
        return abs(self.radial_vel_ms)

    @property
    def heading_deg(self) -> float:
        """Estimated heading from velocity sign convention."""
        if self.radial_vel_ms < 0:
            return self.azimuth_deg   # Approaching
        return (self.azimuth_deg + 180) % 360   # Receding

    def to_dict(self) -> dict:
        return {
            "target_id":      self.target_id,
            "range_m":        round(self.range_m, 1),
            "azimuth_deg":    round(self.azimuth_deg, 2),
            "elevation_deg":  round(self.elevation_deg, 2),
            "radial_vel_ms":  round(self.radial_vel_ms, 2),
            "rcs_m2":         round(self.rcs_m2, 4),
            "snr_db":         round(self.snr_db, 1),
            "x_m":            round(self.x_m, 1),
            "y_m":            round(self.y_m, 1),
            "z_m":            round(self.z_m, 1),
            "horizontal_m":   round(self.horizontal_range_m, 1),
            "heading_deg":    round(self.heading_deg, 1),
            "class_hint":     self.class_hint,
            "timestamp":      self.timestamp,
        }


# ══════════════════════════════════════════════════════════════════════
#  MICRO-DOPPLER CLASSIFIER
# ══════════════════════════════════════════════════════════════════════

class MicroDopplerClassifier:
    """
    Classifies radar targets using Micro-Doppler signatures.
    
    Micro-Doppler effect: rotating parts (rotors, propellers, flapping wings)
    create characteristic spectral modulations around the main Doppler shift.
    
    Classification features:
    1. Number of blade/prop harmonics
    2. Harmonic frequency spacing
    3. Periodicity of modulation
    4. RCS magnitude and fluctuation
    5. Radial velocity range
    
    In production: replace with ML classifier (CNN on spectrogram images).
    """

    def classify(self, radar_return: RadarReturn, 
                 doppler_spectrum: list = None) -> dict:
        """
        Classify target from radar return features.
        
        Returns:
            dict with 'class', 'confidence', 'features', 'scores_per_class'
        """
        features = self._extract_features(radar_return, doppler_spectrum)
        scores   = self._score_all_classes(features)
        best_cls = max(scores, key=scores.get)
        conf     = scores[best_cls]

        return {
            "class":           best_cls,
            "confidence":      round(conf, 1),
            "features":        features,
            "scores_per_class":scores,
        }

    def _extract_features(self, ret: RadarReturn, spectrum: list) -> dict:
        """Extract classification features from radar return."""
        # Velocity-based features
        spd = ret.speed_ms
        rcs = ret.rcs_m2

        # Simulated Doppler spectrum analysis
        if spectrum and len(spectrum) > 8:
            harmonics = self._count_harmonics(spectrum)
            periodicity = self._estimate_periodicity(spectrum)
            flap_freq   = self._estimate_flap_frequency(spectrum)
        else:
            # Use RCS + velocity heuristics as fallback
            harmonics   = 4 if spd < 30 else 2
            periodicity = 0.8 if rcs < 0.05 else 0.1
            flap_freq   = 4.0 if (0.005 < rcs < 0.02 and 2 < spd < 20) else 0.0

        return {
            "radial_vel_ms": spd,
            "rcs_m2":        rcs,
            "harmonics":     harmonics,
            "periodicity":   periodicity,
            "flap_freq_hz":  flap_freq,
            "snr_db":        ret.snr_db,
        }

    def _score_all_classes(self, features: dict) -> dict:
        """Score each class against extracted features."""
        scores = {}
        rcs    = features["rcs_m2"]
        spd    = features["radial_vel_ms"]
        harm   = features["harmonics"]
        period = features["periodicity"]
        ffreq  = features["flap_freq_hz"]

        for cls, (ref_harm, ref_ffreq, ref_period) in MICRO_DOPPLER_SIGNATURES.items():
            expected_rcs = DRONE_RCS[cls]
            v_min, v_max = DRONE_VELOCITY[cls]

            # RCS score (log-space match, tolerance 1 order of magnitude)
            rcs_err = abs(math.log10(max(rcs, 1e-6)) - math.log10(expected_rcs))
            s_rcs   = max(0, 1.0 - rcs_err / 2.0)

            # Velocity score
            s_vel = 1.0 if v_min <= spd <= v_max else \
                    max(0, 1.0 - abs(spd - (v_min + v_max) / 2) / max(v_max, 1))

            # Harmonic score
            s_harm = 1.0 if harm == ref_harm else max(0, 1.0 - abs(harm - ref_harm) * 0.25)

            # Periodicity score
            s_period = 1.0 - abs(period - ref_period)

            # Flap frequency (bird detection)
            if ref_ffreq > 0:
                s_flap = max(0, 1.0 - abs(ffreq - ref_ffreq) / 4.0)
            else:
                s_flap = 0.8 if ffreq < 0.5 else 0.2

            # Composite
            score = (0.35 * s_rcs + 0.25 * s_vel + 0.20 * s_harm +
                     0.10 * s_period + 0.10 * s_flap) * 100
            scores[cls] = round(score, 1)

        return scores

    def _count_harmonics(self, spectrum: list) -> int:
        """Count dominant peaks in Doppler spectrum."""
        if not spectrum:
            return 0
        threshold = max(spectrum) * 0.3
        peaks = 0
        for i in range(1, len(spectrum) - 1):
            if spectrum[i] > threshold and spectrum[i] > spectrum[i-1] and spectrum[i] > spectrum[i+1]:
                peaks += 1
        return min(peaks, 6)

    def _estimate_periodicity(self, spectrum: list) -> float:
        """Estimate modulation periodicity [0-1]."""
        if len(spectrum) < 4:
            return 0.0
        variance = max(spectrum) - min(spectrum)
        mean     = sum(spectrum) / len(spectrum)
        return min(variance / max(mean, 0.01), 1.0)

    def _estimate_flap_frequency(self, spectrum: list) -> float:
        """Estimate wing-flap frequency from low-frequency content."""
        if len(spectrum) < 8:
            return 0.0
        low_power  = sum(spectrum[:4]) / 4
        high_power = sum(spectrum[4:]) / max(len(spectrum[4:]), 1)
        return 4.0 if low_power > high_power * 1.5 else 0.0


# ══════════════════════════════════════════════════════════════════════
#  RADAR TRACK MANAGER — Nearest-Neighbor Association
# ══════════════════════════════════════════════════════════════════════

@dataclass
class RadarTrack:
    """State of a single radar track (persistent across many returns)."""
    track_id:     str
    history:      deque = field(default_factory=lambda: deque(maxlen=50))
    class_name:   str = "unknown"
    confidence:   float = 0.0
    status:       str = "TENTATIVE"   # TENTATIVE → CONFIRMED → LOST
    confirm_count:int = 0
    miss_count:   int = 0
    first_seen:   float = field(default_factory=time.time)
    last_seen:    float = field(default_factory=time.time)

    CONFIRM_THRESHOLD = 3    # Returns needed to confirm track
    MISS_THRESHOLD    = 5    # Missed gates before track is dropped

    def update(self, ret: RadarReturn, cls_result: dict = None):
        self.history.append(ret)
        self.last_seen   = time.time()
        self.miss_count  = 0
        self.confirm_count += 1
        if self.confirm_count >= self.CONFIRM_THRESHOLD:
            self.status = "CONFIRMED"
        if cls_result:
            self.class_name  = cls_result["class"]
            self.confidence  = cls_result["confidence"]

    def gate_miss(self):
        """Record one scan with no association."""
        self.miss_count += 1
        if self.miss_count >= self.MISS_THRESHOLD:
            self.status = "LOST"

    @property
    def last_return(self) -> Optional[RadarReturn]:
        return self.history[-1] if self.history else None

    @property
    def velocity_3d(self) -> tuple:
        """Estimated 3D velocity (m/s) from track history."""
        pts = [(r.x_m, r.y_m, r.z_m, r.timestamp) for r in list(self.history)[-4:]]
        if len(pts) < 2:
            return (0.0, 0.0, 0.0, 0.0)
        new, old = pts[-1], pts[0]
        dt = new[3] - old[3]
        if dt < 1e-6:
            return (0.0, 0.0, 0.0, 0.0)
        vx = (new[0] - old[0]) / dt
        vy = (new[1] - old[1]) / dt
        vz = (new[2] - old[2]) / dt
        speed = math.sqrt(vx**2 + vy**2 + vz**2)
        return (round(vx,2), round(vy,2), round(vz,2), round(speed,2))

    @property
    def predicted_position(self) -> tuple:
        """Predict position 1 second ahead (linear extrapolation)."""
        r = self.last_return
        vx, vy, vz, _ = self.velocity_3d
        if r is None:
            return (0, 0, 0)
        return (round(r.x_m + vx, 1),
                round(r.y_m + vy, 1),
                round(r.z_m + vz, 1))


class TrackManager:
    """
    Multi-target track manager with nearest-neighbor gating and association.
    
    Algorithm:
    1. For each new radar return: compute distance to all existing tracks
    2. Associate return with nearest track inside gate distance
    3. Unassociated returns → initiate new tentative track
    4. No return in gate → increment miss, prune if max miss exceeded
    
    Reference: Singer-Ackermann-Bendor nearest-neighbor association.
    """

    GATE_DISTANCE_M = 150.0    # Max association distance (meters)
    MAX_TRACKS      = 30

    def __init__(self):
        self.tracks     = {}
        self._lock      = threading.Lock()
        self._tid_cnt   = 0
        self.classifier = MicroDopplerClassifier()

    def process_scan(self, returns: list) -> list:
        """
        Process a batch of radar returns from one scan.
        Classification of each return runs in parallel on CPU cores.
        """
        with self._lock:
            associated = set()
            unassociated = []

            # ── Parallel classify + associate ──────────────────────────────
            def _classify_return(ret):
                """Run MicroDoppler classification on a worker CPU core."""
                return ret, self.classifier.classify(ret)

            futures = {_RADAR_POOL.submit(_classify_return, ret): ret
                       for ret in returns}

            for future in as_completed(futures):
                try:
                    ret, cls_result = future.result(timeout=2.0)
                except Exception:
                    continue

                best_track = self._find_nearest_track(ret)
                if best_track:
                    best_track.update(ret, cls_result)
                    associated.add(best_track.track_id)
                else:
                    unassociated.append((ret, cls_result))

            # Mark misses for unassociated tracks
            for tid, track in list(self.tracks.items()):
                if tid not in associated:
                    track.gate_miss()
                    if track.status == "LOST":
                        del self.tracks[tid]

            # Initiate new tracks for unassociated returns
            for ret, cls_result in unassociated:
                self._initiate_track(ret, cls_result)

            return list(self.tracks.values())

    def _find_nearest_track(self, ret: RadarReturn) -> Optional[RadarTrack]:
        """Find nearest existing track within gate distance."""
        best_track = None
        best_dist  = float('inf')
        for track in self.tracks.values():
            if track.status == "LOST":
                continue
            last = track.last_return
            if last is None:
                continue
            dist = math.sqrt(
                (ret.x_m - last.x_m)**2 +
                (ret.y_m - last.y_m)**2 +
                (ret.z_m - last.z_m)**2
            )
            if dist < self.GATE_DISTANCE_M and dist < best_dist:
                best_dist  = dist
                best_track = track
        return best_track

    def _initiate_track(self, ret: RadarReturn, cls_result: dict = None):
        """Start new track from un-associated return (accepts pre-computed cls)."""
        if len(self.tracks) >= self.MAX_TRACKS:
            self._prune_lowest_snr()
        self._tid_cnt += 1
        tid   = f"RADAR_{self._tid_cnt:04d}"
        track = RadarTrack(track_id=tid)
        cls   = cls_result if cls_result else self.classifier.classify(ret)
        track.update(ret, cls)
        self.tracks[tid] = track

    def _prune_lowest_snr(self):
        """Remove weakest (lowest SNR) tentative track."""
        tentative = [(track.last_return.snr_db if track.last_return else -99, tid)
                     for tid, track in self.tracks.items()
                     if track.status == "TENTATIVE"]
        if tentative:
            _, tid = min(tentative)
            del self.tracks[tid]

    def confirmed_tracks(self) -> list:
        return [t for t in self.tracks.values() if t.status == "CONFIRMED"]


# ══════════════════════════════════════════════════════════════════════
#  THREAT ZONE MONITOR
# ══════════════════════════════════════════════════════════════════════

class ThreatZoneMonitor:
    """
    Monitors 3 concentric threat zones and generates alerts.
    
    Zones:
        ZONE_3 OUTER  — 5000m  : Long-range detection, prep countermeasures
        ZONE_2 MIDDLE — 2000m  : Engagement decision point
        ZONE_1 INNER  —  500m  : Immediate kinetic/jamming engagement
    """

    ZONES = {
        "INNER":  {"radius_m": 500,  "level": "CRITICAL", "action": "IMMEDIATE_ENGAGE"},
        "MIDDLE": {"radius_m": 2000, "level": "HIGH",      "action": "PREPARE_ENGAGE"},
        "OUTER":  {"radius_m": 5000, "level": "ELEVATED",  "action": "TRACK_AND_PREPARE"},
    }

    def __init__(self, alert_callback=None):
        self._callback   = alert_callback or self._default_alert
        self._zone_state = defaultdict(dict)   # track_id → {zone: timestamp}
        self._alerts     = deque(maxlen=100)

    def check_tracks(self, tracks: list) -> list:
        """Check all confirmed tracks against threat zones."""
        new_alerts = []
        for track in tracks:
            ret = track.last_return
            if not ret:
                continue
            r = ret.horizontal_range_m
            for zone_name, zone_info in sorted(
                self.ZONES.items(), key=lambda x: x[1]["radius_m"]
            ):
                if r <= zone_info["radius_m"]:
                    prev = self._zone_state[track.track_id].get(zone_name)
                    now  = time.time()
                    # Only alert on zone entry (not every scan)
                    if prev is None or (now - prev) > 30:
                        alert = self._build_alert(track, ret, zone_name, zone_info)
                        new_alerts.append(alert)
                        self._alerts.append(alert)
                        self._zone_state[track.track_id][zone_name] = now
                        self._callback(alert)
                    break   # Only report innermost zone
        return new_alerts

    def _build_alert(self, track, ret, zone_name, zone_info) -> dict:
        vx, vy, vz, speed = track.velocity_3d
        return {
            "zone":       zone_name,
            "level":      zone_info["level"],
            "action":     zone_info["action"],
            "track_id":   track.track_id,
            "class":      track.class_name,
            "confidence": track.confidence,
            "range_m":    round(ret.range_m, 1),
            "azimuth":    round(ret.azimuth_deg, 1),
            "altitude_m": round(ret.z_m, 1),
            "speed_ms":   round(speed, 1),
            "rcs_m2":     round(ret.rcs_m2, 4),
            "timestamp":  datetime.now().isoformat(),
        }

    @staticmethod
    def _default_alert(alert: dict):
        icons = {"INNER": "🔴", "MIDDLE": "🟠", "OUTER": "🟡"}
        icon  = icons.get(alert["zone"], "⚪")
        print(f"\n{icon} [{alert['zone']} ZONE BREACH] {alert['track_id']}")
        print(f"   Class: {alert['class'].upper()} | Confidence: {alert['confidence']:.0f}%")
        print(f"   Range: {alert['range_m']}m | Az: {alert['azimuth']}° | "
              f"Alt: {alert['altitude_m']}m | Speed: {alert['speed_ms']}m/s")
        print(f"   ACTION REQUIRED: {alert['action']}")


# ══════════════════════════════════════════════════════════════════════
#  RADAR ENGINE — Master Orchestrator
# ══════════════════════════════════════════════════════════════════════

class RadarEngine:
    """
    Master radar system orchestrator.
    Generates/ingests radar returns → associates tracks → classifies
    → checks threat zones → triggers countermeasure alerts.
    """

    SCAN_INTERVAL_SEC = 1.0      # Radar scan rate (1 Hz typical for ground radar)
    MAX_RANGE_M       = 8000.0   # Maximum radar range

    def __init__(self, alert_callback=None):
        self.track_manager = TrackManager()
        self.zone_monitor  = ThreatZoneMonitor(alert_callback)
        self.classifier    = MicroDopplerClassifier()
        self._running      = False
        self._thread       = None
        self._scan_count   = 0
        self._target_scene = []   # Simulated targets for demo
        self._lock         = threading.Lock()
        print("[RADAR] Radar Engine initialized")
        print(f"[RADAR] Max range: {self.MAX_RANGE_M}m | Scan rate: {1/self.SCAN_INTERVAL_SEC:.1f}Hz")

    def load_scenario(self, targets: list):
        """
        Load simulated target scenario.
        targets: list of dict with {class_name, range_m, azimuth_deg, elevation_deg, speed_ms}
        """
        self._target_scene = targets
        print(f"[RADAR] Scenario loaded: {len(targets)} targets")

    def start(self):
        self._running = True
        self._thread  = threading.Thread(
            target=self._scan_loop, daemon=True, name="Radar-Engine"
        )
        self._thread.start()
        print("[RADAR] ⚡ Radar scanning ACTIVE")

    def stop(self):
        self._running = False
        print("[RADAR] Radar scanning stopped")

    def _scan_loop(self):
        while self._running:
            time.sleep(self.SCAN_INTERVAL_SEC)
            returns  = self._generate_returns()
            tracks   = self.track_manager.process_scan(returns)
            confirmed = self.track_manager.confirmed_tracks()
            alerts   = self.zone_monitor.check_tracks(confirmed)

            self._scan_count += 1
            if self._scan_count % 5 == 0:
                self._print_picture(confirmed)

            # DB logging for confirmed tracks
            if DB_AVAILABLE and confirmed:
                for track in confirmed:
                    ret = track.last_return
                    if ret:
                        db.log_detection(
                            sensor_type="RADAR",
                            target_id=track.track_id,
                            threat_level="HIGH" if ret.horizontal_range_m < 2000 else "ELEVATED",
                            confidence=int(track.confidence),
                            details=f"class={track.class_name} "
                                    f"range={ret.range_m:.0f}m az={ret.azimuth_deg:.1f}° "
                                    f"rcs={ret.rcs_m2:.4f}m2"
                        )

    def _generate_returns(self) -> list:
        """
        Generate simulated radar returns from loaded scenario.
        In production: replace with real radar hardware data ingestion.
        """
        returns = []
        for i, tgt in enumerate(self._target_scene):
            # Simulate target movement
            tgt["range_m"]    = max(200, tgt["range_m"] - tgt.get("speed_ms", 15))
            tgt["azimuth_deg"] = (tgt["azimuth_deg"] + random.uniform(-2, 2)) % 360

            if tgt["range_m"] < 100:
                continue   # Target passed overhead

            # Simulate measurement noise
            rcs    = DRONE_RCS.get(tgt["class_name"], 0.01)
            rcs   *= random.uniform(0.5, 2.0)    # Fluctuation (Swerling model)
            range_noise  = random.gauss(0, 5)     # 5m range noise
            az_noise     = random.gauss(0, 0.5)   # 0.5deg azimuth noise
            el_noise     = random.gauss(0, 0.3)
            vel_noise    = random.gauss(0, 0.5)

            # SNR based on range (ranges: 4th power law)
            snr = 30 - 40 * math.log10(tgt["range_m"] / 1000 + 0.01)
            snr += 10 * math.log10(max(rcs / 0.01, 0.001))
            snr  = max(snr, -10)

            v_min, v_max = DRONE_VELOCITY.get(tgt["class_name"], (5, 30))
            speed = tgt.get("speed_ms", random.uniform(v_min, v_max))

            ret = RadarReturn(
                target_id    = f"T{i:02d}",
                range_m      = max(100, tgt["range_m"] + range_noise),
                azimuth_deg  = (tgt["azimuth_deg"] + az_noise) % 360,
                elevation_deg= tgt.get("elevation_deg", 5.0) + el_noise,
                radial_vel_ms= -(speed + vel_noise),  # Negative = approaching
                rcs_m2       = max(rcs, 0.0001),
                snr_db       = snr,
                class_hint   = tgt["class_name"],
            )
            returns.append(ret)

        return returns

    def ingest_return(self, ret: RadarReturn):
        """
        Accept a single radar return from external hardware.
        Call this from your real radar hardware interface.
        """
        tracks = self.track_manager.process_scan([ret])
        confirmed = self.track_manager.confirmed_tracks()
        self.zone_monitor.check_tracks(confirmed)

    def _print_picture(self, confirmed_tracks: list):
        """Print tactical radar picture (air picture)."""
        print(f"\n[RADAR] === Air Picture @ {datetime.now().strftime('%H:%M:%S')} "
              f"| Scan #{self._scan_count} ===")
        if not confirmed_tracks:
            print("  [RADAR] No confirmed tracks.")
            return
        print(f"  {'Track':<12} {'Class':<22} {'Range':>8} {'Az':>7} "
              f"{'Alt':>7} {'Speed':>8} {'RCS':>10} {'Conf':>6}")
        print("  " + "─" * 85)
        for t in confirmed_tracks:
            ret = t.last_return
            if not ret:
                continue
            _, _, _, spd = t.velocity_3d
            zone = self._get_zone(ret.horizontal_range_m)
            print(f"  {t.track_id:<12} {t.class_name:<22} "
                  f"{ret.range_m:>7.0f}m {ret.azimuth_deg:>6.1f}° "
                  f"{ret.z_m:>6.0f}m {spd:>7.1f}m/s "
                  f"{ret.rcs_m2:>9.4f}m² {t.confidence:>5.0f}%  [{zone}]")

    @staticmethod
    def _get_zone(h_range_m: float) -> str:
        if h_range_m <= 500:   return "INNER-CRITICAL"
        if h_range_m <= 2000:  return "MIDDLE-HIGH"
        if h_range_m <= 5000:  return "OUTER-ELEVATED"
        return "BEYOND-RANGE"

    def get_track_by_id(self, track_id: str) -> Optional[RadarTrack]:
        return self.track_manager.tracks.get(track_id)

    def status_report(self) -> dict:
        confirmed = self.track_manager.confirmed_tracks()
        return {
            "scanning":       self._running,
            "scan_count":     self._scan_count,
            "total_tracks":   len(self.track_manager.tracks),
            "confirmed":      len(confirmed),
            "critical_zone":  sum(1 for t in confirmed if t.last_return
                                  and t.last_return.horizontal_range_m <= 500),
            "tracks":         [
                {
                    "id":         t.track_id,
                    "class":      t.class_name,
                    "confidence": t.confidence,
                    "status":     t.status,
                    "range_m":    t.last_return.horizontal_range_m if t.last_return else 0,
                    "speed_ms":   t.velocity_3d[3],
                }
                for t in confirmed
            ],
        }


# ══════════════════════════════════════════════════════════════════════
#  STANDALONE TEST
# ══════════════════════════════════════════════════════════════════════

def main():
    import argparse

    parser = argparse.ArgumentParser(description="MCDIS Radar System Test")
    parser.add_argument("--duration", type=int, default=30,
                        help="Test duration in seconds")
    parser.add_argument("--targets", type=int, default=3,
                        help="Number of simulated targets")
    args = parser.parse_args()

    print("=" * 65)
    print("  MCDIS v3.0 — Radar System Standalone Test")
    print("=" * 65)

    # Simulated scenario
    scenario_templates = [
        {"class_name": "shahed_136",   "range_m": 5000, "azimuth_deg": 45,
         "elevation_deg": 3,   "speed_ms": 50},
        {"class_name": "dji_large",    "range_m": 1200, "azimuth_deg": 120,
         "elevation_deg": 8,   "speed_ms": 12},
        {"class_name": "fpv_suicide",  "range_m": 800,  "azimuth_deg": 270,
         "elevation_deg": 2,   "speed_ms": 35},
        {"class_name": "swarm_unit",   "range_m": 3000, "azimuth_deg": 350,
         "elevation_deg": 5,   "speed_ms": 10},
        {"class_name": "bird",         "range_m": 500,  "azimuth_deg": 200,
         "elevation_deg": 15,  "speed_ms": 8},
    ]
    selected = scenario_templates[:args.targets]

    def alert_handler(alert):
        if alert["zone"] == "INNER":
            print(f"\n  🚨 CRITICAL ALERT [{alert['track_id']}] — "
                  f"{alert['class'].upper()} at {alert['range_m']}m")
            print(f"     → ACTION: {alert['action']}")

    radar = RadarEngine(alert_callback=alert_handler)
    radar.load_scenario(selected)
    radar.start()

    print(f"\n[TEST] Radar running for {args.duration}s with {args.targets} targets...\n")

    try:
        duration = 0
        while duration < args.duration:
            time.sleep(1)
            duration += 1
    except KeyboardInterrupt:
        pass

    radar.stop()
    rpt = radar.status_report()
    print(f"\n[TEST] Final Status:")
    print(f"  Scans completed: {rpt['scan_count']}")
    print(f"  Confirmed tracks: {rpt['confirmed']}")
    print(f"  Critical zone targets: {rpt['critical_zone']}")
    print("\n[TEST] ✅ Radar system test complete.")


if __name__ == "__main__":
    main()
