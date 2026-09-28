"""
╔══════════════════════════════════════════════════════════════════════╗
║  MCDIS — Multi-Modal Counter-Drone Intelligence System              ║
║  Module: Countermeasure Engine v3.0                                  ║
║  Classification: UNCLASSIFIED // FOR OFFICIAL USE ONLY               ║
╠══════════════════════════════════════════════════════════════════════╣
║  Functions:                                                           ║
║    1. ThreatEvaluator   — Priority 0-100 per class + confidence      ║
║    2. TargetTracker     — Position history, velocity, trajectory pred ║
║    3. CountermeasureSelector — Rules-based engagement decision        ║
║    4. CommandDispatcher — Fires simulated commands to subsystems      ║
║    5. EngagementLogger  — Full audit trail in tactical DB             ║
╚══════════════════════════════════════════════════════════════════════╝

Countermeasure Decision Tree:
─────────────────────────────────────────────────────────────────────
  Priority ≥ 95 (CRITICAL):
    → Fiber-guided / Loitering Munition detected
    → Jamming INEFFECTIVE
    → AUTO: Launch missile OR deploy interceptor drone
    → Notify: MISSILE BATTERY, INTERCEPTOR DRONE SQUADRON

  Priority 70-94 (HIGH):
    → Military UAS / Swarm detected
    → Try: Broadband RF Jamming + GPS Override
    → Fallback: Interceptor drone if jamming fails
    → Notify: JAMMING SYSTEM, INTERCEPTOR SQUADRON

  Priority 40-69 (ELEVATED):
    → Commercial drone (DJI/Generic) detected
    → Try: Protocol scan → 2.4/5.8GHz jam → GPS override
    → If DJI Smart: GPS spoofing → Return-to-Home hijack
    → Notify: JAMMING SYSTEM

  Priority < 40 (MONITOR/NONE):
    → Micro drone or false positive
    → Log + continue monitoring
    → No active countermeasure dispatched
─────────────────────────────────────────────────────────────────────
"""

import time
import math
import threading
import json
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from collections import deque, defaultdict
from pathlib import Path
from enum import Enum, auto

sys.path.insert(0, str(Path(__file__).parent.parent / "mcdis"))
try:
    from database import db
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

# ══════════════════════════════════════════════════════════════════════
#  CPU OPTIMISATION BLOCK
#  Threat scoring + command dispatch are I/O and float-compute bound.
#  Run them in parallel across all CPU cores.
# ══════════════════════════════════════════════════════════════════════
_CPU_CORES     = os.cpu_count() or 4
_ENGINE_POOL   = ThreadPoolExecutor(
    max_workers=_CPU_CORES,
    thread_name_prefix="MCDIS-CEngine"
)
print(f"[C-ENGINE HW] CPU cores: {_CPU_CORES} | Parallel threat scoring pool ready")

try:
    from interceptor_system import InterceptorSquadron
    from acoustic_weapon import AcousticWeaponSystem
    from adversarial_system import AdversarialSystem
    from swarm_decoy import SwarmDecoySystem
    ADVANCED_MODULES_AVAILABLE = True
except ImportError as e:
    ADVANCED_MODULES_AVAILABLE = False
    print(f"[C-ENGINE] Warning: Advanced AI modules not fully available ({e})")

# ══════════════════════════════════════════════════════════════════════
#  ENUMERATIONS
# ══════════════════════════════════════════════════════════════════════

class EngagementMode(Enum):
    NONE              = auto()   # No action
    MONITOR           = auto()   # Track only
    JAM_RF            = auto()   # RF control jamming
    JAM_GPS           = auto()   # GPS L1/L2 jamming
    GPS_OVERRIDE      = auto()   # GPS spoofing → Return-to-Home
    INTERCEPT_DRONE   = auto()   # Deploy interceptor drone
    NET_PROJECTILE    = auto()   # Launch net from ground
    MISSILE           = auto()   # Kinetic missile engagement
    BROADBAND_JAM     = auto()   # Wide-spectrum jamming (swarm)
    HPEM_PULSE        = auto()   # High-Power Electromagnetic Pulse
    IFF_CHECK         = auto()   # Identification Friend-or-Foe check
    ACOUSTIC_ATTACK   = auto()   # UNROCKER acoustic injection
    ADVERSARIAL_PATCH = auto()   # Visual AI blinding
    SWARM_DECOY       = auto()   # Flocking decoys

class TargetStatus(Enum):
    DETECTED          = auto()   # First detection
    TRACKING          = auto()   # Under stable tracking
    LOCK_CONFIRMED    = auto()   # Lock confirmed (N frames)
    ENGAGING          = auto()   # Countermeasure active
    NEUTRALIZED       = auto()   # No longer a threat
    LOST              = auto()   # Track lost


# ══════════════════════════════════════════════════════════════════════
#  THREAT PRIORITY DATABASE
# ══════════════════════════════════════════════════════════════════════

THREAT_DB = {
    # class_name: {
    #   priority        : 0-100 base score
    #   response_sec    : Required response time in seconds
    #   jammable        : Can RF/GPS jamming affect it?
    #   gps_overridable : Does it use GPS that can be spoofed?
    #   fiber_guided    : Fiber-optic connection (un-jammable)
    #   modes           : Ordered list of preferred engagement modes
    #   notes           : Operator guidance
    # }
    "shahed_136": {
        "priority":        100,
        "response_sec":    2,
        "jammable":        False,    # Uses inertial + pre-programmed route
        "gps_overridable": False,    # GPS not primary nav
        "fiber_guided":    False,
        "modes":           [EngagementMode.MISSILE,
                            EngagementMode.NET_PROJECTILE,
                            EngagementMode.INTERCEPT_DRONE],
        "notes":           "Loitering munition — delta-wing, ~36kg warhead. "
                           "Jamming ineffective. Kinetic engagement mandatory.",
    },
    "fpv_suicide": {
        "priority":        98,
        "response_sec":    1,
        "jammable":        True,     # RC signal on 2.4GHz if no fiber
        "gps_overridable": False,    # Typically no GPS
        "fiber_guided":    True,     # Modern FPV often fiber-guided
        "modes":           [EngagementMode.MISSILE,
                            EngagementMode.JAM_RF,      # if NOT fiber
                            EngagementMode.NET_PROJECTILE],
        "notes":           "Suicide FPV — if fiber-guided: MISSILE ONLY. "
                           "If RC: jam 2.4GHz. Fast reaction required (<1s).",
    },
    "military_fixed_wing": {
        "priority":        90,
        "response_sec":    30,
        "jammable":        True,     # Datalink jammable
        "gps_overridable": False,    # Military-grade anti-spoof GPS
        "fiber_guided":    False,
        "modes":           [EngagementMode.MISSILE,
                            EngagementMode.JAM_RF,
                            EngagementMode.INTERCEPT_DRONE],
        "notes":           "MALE/UCAV class — long range datalink. "
                           "Military GPS hardened. Kinetic preferred.",
    },
    "wing_loong": {
        "priority":        88,
        "response_sec":    30,
        "jammable":        True,
        "gps_overridable": False,
        "fiber_guided":    False,
        "modes":           [EngagementMode.MISSILE,
                            EngagementMode.JAM_RF],
        "notes":           "Export MALE (CH-4/Wing Loong). Similar to Predator.",
    },
    "military_rotor": {
        "priority":        85,
        "response_sec":    15,
        "jammable":        True,
        "gps_overridable": False,
        "fiber_guided":    False,
        "modes":           [EngagementMode.INTERCEPT_DRONE,
                            EngagementMode.JAM_RF,
                            EngagementMode.MISSILE],
        "notes":           "Tactical military rotor UAS. Encrypted link.",
    },
    "swarm_unit": {
        "priority":        80,
        "response_sec":    5,
        "jammable":        True,     # Swarm usually on unlicensed bands
        "gps_overridable": True,
        "fiber_guided":    False,
        "modes":           [EngagementMode.BROADBAND_JAM,
                            EngagementMode.HPEM_PULSE,
                            EngagementMode.JAM_GPS],
        "notes":           "Swarm — broadband jamming + HPEM. "
                           "Single-unit engagement inefficient.",
    },
    "dji_large": {
        "priority":        70,
        "response_sec":    10,
        "jammable":        True,     # OcuSync 2.4/5.8GHz
        "gps_overridable": True,     # DJI Return-to-Home exploitable
        "fiber_guided":    False,
        "modes":           [EngagementMode.GPS_OVERRIDE,
                            EngagementMode.JAM_RF,
                            EngagementMode.JAM_GPS,
                            EngagementMode.INTERCEPT_DRONE],
        "notes":           "DJI large — OcuSync on 2.4/5.8GHz. "
                           "GPS spoofing triggers Return-to-Home capture.",
    },
    "dji_mini": {
        "priority":        60,
        "response_sec":    15,
        "jammable":        True,
        "gps_overridable": True,
        "fiber_guided":    False,
        "modes":           [EngagementMode.JAM_RF,
                            EngagementMode.GPS_OVERRIDE],
        "notes":           "DJI Mini — 2.4GHz OcuSync. Light payload.",
    },
    "generic_commercial": {
        "priority":        55,
        "response_sec":    15,
        "jammable":        True,
        "gps_overridable": True,
        "fiber_guided":    False,
        "modes":           [EngagementMode.JAM_RF,
                            EngagementMode.JAM_GPS,
                            EngagementMode.INTERCEPT_DRONE],
        "notes":           "Generic commercial UAS. Run protocol scan first.",
    },
    "micro_nano": {
        "priority":        40,
        "response_sec":    30,
        "jammable":        True,
        "gps_overridable": False,
        "fiber_guided":    False,
        "modes":           [EngagementMode.MONITOR,
                            EngagementMode.NET_PROJECTILE],
        "notes":           "Micro/nano — acoustic+radar detection primary. "
                           "Limited payload but useful for surveillance.",
    },
    "bird": {
        "priority":        0,
        "response_sec":    999,
        "jammable":        False,
        "gps_overridable": False,
        "fiber_guided":    False,
        "modes":           [EngagementMode.NONE],
        "notes":           "FALSE POSITIVE — Bird. No action.",
    },
    "fixed_aircraft": {
        "priority":        0,
        "response_sec":    999,
        "jammable":        False,
        "gps_overridable": False,
        "fiber_guided":    False,
        "modes":           [EngagementMode.IFF_CHECK],
        "notes":           "IFF required — may be friendly aircraft.",
    },
}


# ══════════════════════════════════════════════════════════════════════
#  TARGET TRACKER
# ══════════════════════════════════════════════════════════════════════

class TrackedTarget:
    """
    State machine for a single tracked threat.
    Maintains:
    - Position history for velocity estimation
    - Classification votes (majority determines class)
    - Engagement status
    - Kill chain progress
    """

    SCALE_PX_TO_M = 0.05    # 1 pixel ≈ 5cm at 50m range (calibrate per deployment)
    HISTORY_LEN   = 30

    def __init__(self, target_id: str, initial_class: str, conf: float,
                 position: tuple = (0, 0, 0)):
        self.id             = target_id
        self.class_votes    = defaultdict(float)
        self.class_votes[initial_class] += conf
        self.first_seen     = datetime.now()
        self.last_seen      = datetime.now()
        self.status         = TargetStatus.DETECTED
        self.engagement_mode= EngagementMode.NONE

        # (x, y, z, timestamp) — z from radar/altitude estimate
        self.pos_history    = deque(maxlen=self.HISTORY_LEN)
        self.pos_history.append((*position, time.time()))

        self.lock_frames    = 0
        self.conf_avg       = conf
        self._conf_window   = deque([conf], maxlen=10)
        self.neutralized    = False
        self.command_count  = 0

    def update(self, class_name: str, conf: float, position: tuple):
        """Update state with new sensor report."""
        self.class_votes[class_name] += conf
        self._conf_window.append(conf)
        self.conf_avg  = sum(self._conf_window) / len(self._conf_window)
        self.last_seen = datetime.now()
        self.pos_history.append((*position, time.time()))

        if self.status == TargetStatus.DETECTED and len(self.pos_history) >= 3:
            self.status = TargetStatus.TRACKING

    @property
    def best_class(self) -> str:
        if not self.class_votes:
            return "generic_commercial"
        return max(self.class_votes, key=self.class_votes.get)

    @property
    def priority(self) -> int:
        return THREAT_DB.get(self.best_class, {}).get("priority", 0)

    @property
    def threat_info(self) -> dict:
        return THREAT_DB.get(self.best_class, THREAT_DB["generic_commercial"])

    @property
    def position(self) -> tuple:
        if self.pos_history:
            p = self.pos_history[-1]
            return (p[0], p[1], p[2])
        return (0, 0, 0)

    @property
    def velocity(self) -> tuple:
        """Returns (vx, vy, vz, speed) in m/s."""
        pts = list(self.pos_history)
        if len(pts) < 4:
            return (0.0, 0.0, 0.0, 0.0)
        new, old = pts[-1], pts[-4]
        dt = new[3] - old[3]
        if dt < 1e-6:
            return (0.0, 0.0, 0.0, 0.0)
        vx = (new[0] - old[0]) * self.SCALE_PX_TO_M / dt
        vy = (new[1] - old[1]) * self.SCALE_PX_TO_M / dt
        vz = (new[2] - old[2]) * self.SCALE_PX_TO_M / dt
        speed = math.sqrt(vx**2 + vy**2 + vz**2)
        return (round(vx,2), round(vy,2), round(vz,2), round(speed,2))

    def predict_position(self, dt_sec: float) -> tuple:
        """Predict position dt_sec seconds into future (linear model)."""
        x, y, z = self.position
        vx, vy, vz, _ = self.velocity
        px = x + vx * dt_sec / self.SCALE_PX_TO_M
        py = y + vy * dt_sec / self.SCALE_PX_TO_M
        pz = z + vz * dt_sec / self.SCALE_PX_TO_M
        return (round(px), round(py), round(pz))

    @property
    def heading_deg(self) -> float:
        vx, vy, _, _ = self.velocity
        if abs(vx) < 0.01 and abs(vy) < 0.01:
            return 0.0
        return round(math.degrees(math.atan2(vx, -vy)) % 360, 1)

    @property
    def age_sec(self) -> float:
        return (datetime.now() - self.first_seen).total_seconds()

    @property
    def stale_sec(self) -> float:
        return (datetime.now() - self.last_seen).total_seconds()

    def to_dict(self) -> dict:
        vx, vy, vz, speed = self.velocity
        return {
            "id":           self.id,
            "class":        self.best_class,
            "priority":     self.priority,
            "status":       self.status.name,
            "mode":         self.engagement_mode.name,
            "position":     self.position,
            "velocity_ms":  (vx, vy, vz, speed),
            "heading_deg":  self.heading_deg,
            "confidence":   round(self.conf_avg, 1),
            "age_sec":      round(self.age_sec, 1),
            "first_seen":   self.first_seen.isoformat(),
            "last_seen":    self.last_seen.isoformat(),
            "jammable":     self.threat_info.get("jammable", False),
            "fiber_guided": self.threat_info.get("fiber_guided", False),
            "notes":        self.threat_info.get("notes", ""),
        }


# ══════════════════════════════════════════════════════════════════════
#  THREAT EVALUATOR
# ══════════════════════════════════════════════════════════════════════

class ThreatEvaluator:
    """
    Assigns composite threat score to each target for prioritization.
    Score combines:
      - Class-based base priority (0-100 from THREAT_DB)
      - Track stability (how long has it been tracked)
      - Average detection confidence
      - Velocity (fast-moving targets get higher score)
      - Range bonus (closer = higher score — needs radar data)
    """

    WEIGHT_PRIORITY    = 0.50
    WEIGHT_STABILITY   = 0.15
    WEIGHT_CONFIDENCE  = 0.20
    WEIGHT_VELOCITY    = 0.15

    MAX_VELOCITY_MS    = 80.0    # Normalization: 80 m/s = max score

    @classmethod
    def score(cls, target: TrackedTarget) -> float:
        """Return composite threat score [0.0 – 100.0]."""
        # Base priority
        s_priority = target.priority

        # Track stability (asymptote at 60 frames)
        s_stability = min(target.age_sec / 60.0, 1.0) * 100.0

        # Confidence
        s_conf = min(target.conf_avg, 100.0)

        # Velocity (faster = more dangerous)
        _, _, _, speed = target.velocity
        s_velocity = min(speed / cls.MAX_VELOCITY_MS, 1.0) * 100.0

        composite = (
            cls.WEIGHT_PRIORITY   * s_priority +
            cls.WEIGHT_STABILITY  * s_stability +
            cls.WEIGHT_CONFIDENCE * s_conf +
            cls.WEIGHT_VELOCITY   * s_velocity
        )
        return round(composite, 2)

    @classmethod
    def rank(cls, targets: dict) -> list:
        """Return list of (score, target) sorted descending.
        Scoring runs in parallel on CPU cores for large target sets.
        """
        active = [(tid, t) for tid, t in targets.items() if not t.neutralized]
        if not active:
            return []

        # Parallel score computation
        futures = {_ENGINE_POOL.submit(cls.score, t): t for _, t in active}
        results = []
        for future in as_completed(futures):
            target = futures[future]
            try:
                s = future.result(timeout=1.0)
            except Exception:
                s = 0.0
            results.append((s, target))

        results.sort(key=lambda x: x[0], reverse=True)
        return results


# ══════════════════════════════════════════════════════════════════════
#  AI DECISION ENGINE
# ══════════════════════════════════════════════════════════════════════

class AIDecisionEngine:
    """
    AI/Deep Learning driven countermeasure selection matrix.
    Simulates a Deep Q-Network (DQN) evaluating the optimal engagement
    strategy based on a multi-dimensional state space with zero-error tolerance.
    """

    @staticmethod
    def select(target: TrackedTarget, environment: dict = None) -> EngagementMode:
        """
        Evaluate optimal countermeasure using simulated neural network inference.
        """
        env   = environment or {}
        info  = target.threat_info
        
        # 1. State Extraction (Input to Neural Net)
        priority = target.priority
        _, _, _, speed = target.velocity
        is_fiber = info.get("fiber_guided", False)
        is_jammable = info.get("jammable", False)
        is_gps_dep = info.get("gps_overridable", False)
        
        # Simulation of Neural Net Q-Value calculation for different modes
        q_values = {
            EngagementMode.MISSILE: 0.0,
            EngagementMode.INTERCEPT_DRONE: 0.0,
            EngagementMode.NET_PROJECTILE: 0.0,
            EngagementMode.BROADBAND_JAM: 0.0,
            EngagementMode.JAM_RF: 0.0,
            EngagementMode.GPS_OVERRIDE: 0.0,
            EngagementMode.ACOUSTIC_ATTACK: 0.0,
            EngagementMode.ADVERSARIAL_PATCH: 0.0,
            EngagementMode.SWARM_DECOY: 0.0,
            EngagementMode.MONITOR: 0.0,
            EngagementMode.NONE: 0.0
        }

        # --- Simulated Neural Weights & Bias ---
        if priority >= 95:
            # Critical Threats (Shahed, Suicide FPV)
            if is_fiber:
                q_values[EngagementMode.MISSILE] = 0.99
            else:
                q_values[EngagementMode.MISSILE] = 0.85
                q_values[EngagementMode.INTERCEPT_DRONE] = 0.92  # DQN prefers interceptor if fast enough
                q_values[EngagementMode.JAM_RF] = 0.75
                q_values[EngagementMode.SWARM_DECOY] = 0.80      # Good for confusing targeting systems
        
        elif priority >= 70:
            # High Threats (Military, Swarms, Large DJI)
            if target.best_class == "swarm_unit":
                q_values[EngagementMode.BROADBAND_JAM] = 0.95
                q_values[EngagementMode.SWARM_DECOY] = 0.90      # Fight swarm with swarm
            else:
                if is_jammable and not env.get("jamming_active"):
                    q_values[EngagementMode.JAM_RF] = 0.88
                q_values[EngagementMode.INTERCEPT_DRONE] = 0.90
                q_values[EngagementMode.ADVERSARIAL_PATCH] = 0.85 # Blind their cameras
                
        elif priority >= 40:
            # Commercial Threats
            if is_gps_dep and env.get("gps_spoof_ready", True):
                q_values[EngagementMode.GPS_OVERRIDE] = 0.94
            
            # UNROCKER Acoustic attack highly effective on commercial MEMS IMUs
            q_values[EngagementMode.ACOUSTIC_ATTACK] = 0.96
            
            if is_jammable:
                q_values[EngagementMode.JAM_RF] = 0.85
        else:
            if target.best_class in ("bird", "fixed_aircraft"):
                q_values[EngagementMode.IFF_CHECK if target.best_class == "fixed_aircraft" else EngagementMode.NONE] = 0.99
            else:
                q_values[EngagementMode.MONITOR] = 0.99

        # Filter out unavailable options based on environment constraints
        if not env.get("missile_ready", True):
            q_values[EngagementMode.MISSILE] = -1.0
        if not env.get("interceptor_ready", True):
            q_values[EngagementMode.INTERCEPT_DRONE] = -1.0
        if env.get("jamming_active"):
            q_values[EngagementMode.JAM_RF] = -1.0

        # Argmax selection (Zero-Error Tolerance Policy)
        best_mode = max(q_values, key=q_values.get)
        confidence = q_values[best_mode]
        
        # Log AI Decision metric
        target._ai_confidence = confidence
        return best_mode

    @staticmethod
    def get_jam_frequencies(target: TrackedTarget) -> list:
        """Return list of frequencies to jam for this target type."""
        class_name = target.best_class
        freq_map = {
            "shahed_136":          [],                  # Not jammable
            "fpv_suicide":         ["2400MHz"],          # RC only (no fiber assumed)
            "military_fixed_wing": ["GPS_L1", "GPS_L2", "DATALINK"],
            "wing_loong":          ["GPS_L1", "GPS_L2", "SATCOM"],
            "military_rotor":      ["2400MHz", "5800MHz", "GPS_L1"],
            "swarm_unit":          ["433MHz", "900MHz", "2400MHz",
                                    "5800MHz", "GPS_L1"],
            "dji_large":           ["2400MHz", "5800MHz", "GPS_L1"],
            "dji_mini":            ["2400MHz", "GPS_L1"],
            "generic_commercial":  ["433MHz", "900MHz", "2400MHz", "5800MHz"],
            "micro_nano":          ["2400MHz"],
        }
        return freq_map.get(class_name, [])


# ══════════════════════════════════════════════════════════════════════
#  COMMAND DISPATCHER
# ══════════════════════════════════════════════════════════════════════

class CommandDispatcher:
    """
    Dispatches engagement commands to hardware subsystems.
    In simulation: logs commands and calls registered callbacks.
    In production: sends serial/UDP/MQTT commands to real hardware.
    """

    def __init__(self):
        self._callbacks    = {}    # mode → callable
        self._history      = []    # Audit log
        self._lock         = threading.Lock()
        self._cooldowns    = {}    # target_id → last_cmd_time
        self.COOLDOWN_SEC  = 3.0

        # Register default simulation handlers
        self._register_defaults()

    def _register_defaults(self):
        """Register simulation print handlers for all modes."""
        for mode in EngagementMode:
            self._callbacks[mode] = self._sim_handler(mode)

    def _sim_handler(self, mode: EngagementMode):
        def handler(target: TrackedTarget, payload: dict):
            col = {
                EngagementMode.MISSILE:        "🚀",
                EngagementMode.INTERCEPT_DRONE:"🛸",
                EngagementMode.NET_PROJECTILE: "🕸️",
                EngagementMode.BROADBAND_JAM:  "📡",
                EngagementMode.JAM_RF:         "📡",
                EngagementMode.JAM_GPS:        "🛰️",
                EngagementMode.GPS_OVERRIDE:   "🛰️",
                EngagementMode.HPEM_PULSE:     "⚡",
                EngagementMode.MONITOR:        "👁️",
                EngagementMode.IFF_CHECK:      "❓",
                EngagementMode.NONE:           "✅",
                EngagementMode.ACOUSTIC_ATTACK:"🔊",
                EngagementMode.ADVERSARIAL_PATCH:"👁️‍🗨️",
                EngagementMode.SWARM_DECOY:    "🐝",
            }.get(mode, "▶")
            
            ai_conf = getattr(target, "_ai_confidence", 1.0)
            print(f"\n  {col}  [{mode.name}] → Target: {target.id} (AI Confidence: {ai_conf*100:.1f}%)")
            print(f"      Class: {target.best_class.upper()} | Priority: {target.priority}/100")
            print(f"      Position: {target.position} | Speed: {target.velocity[3]:.1f}m/s")
            if payload.get("frequencies"):
                print(f"      Jam Frequencies: {', '.join(payload['frequencies'])}")
            if payload.get("lead_point"):
                print(f"      Lead Point (0.5s): {payload['lead_point']}")
        return handler

    def register_callback(self, mode: EngagementMode, callback):
        """Register custom hardware callback for an engagement mode."""
        self._callbacks[mode] = callback

    def dispatch(self, mode: EngagementMode, target: TrackedTarget,
                 extra: dict = None) -> bool:
        """
        Fire engagement command for target.
        Returns True if dispatched, False if on cooldown.
        """
        with self._lock:
            now = time.time()
            # Cooldown check
            if target.id in self._cooldowns:
                if now - self._cooldowns[target.id] < self.COOLDOWN_SEC:
                    return False

            self._cooldowns[target.id] = now

            # Build payload
            freqs = AIDecisionEngine.get_jam_frequencies(target)
            pred  = target.predict_position(0.5)
            payload = {
                "mode":       mode.name,
                "target_id":  target.id,
                "class":      target.best_class,
                "priority":   target.priority,
                "position":   target.position,
                "lead_point": pred,
                "velocity_ms":target.velocity,
                "heading_deg":target.heading_deg,
                "frequencies":freqs,
                "timestamp":  datetime.now().isoformat(),
                **(extra or {}),
            }

            # Execute callback
            cb = self._callbacks.get(mode, self._sim_handler(mode))
            try:
                cb(target, payload)
            except Exception as e:
                print(f"[DISPATCH ERROR] {mode.name}: {e}")

            self._history.append(payload)
            target.command_count += 1
            target.engagement_mode = mode

            # Database log
            if DB_AVAILABLE:
                db.log_command(
                    command_type=mode.name,
                    target=f"{target.best_class}_{target.id}",
                    status="DISPATCHED"
                )
            return True

    @property
    def history(self) -> list:
        return list(self._history)


def CLASS_PRIORITY_LOOKUP(class_name: str) -> int:
    return THREAT_DB.get(class_name, {}).get("priority", 0)


# ══════════════════════════════════════════════════════════════════════
#  COUNTERMEASURE ENGINE — Main Orchestrator
# ══════════════════════════════════════════════════════════════════════

class CountermeasureEngine:
    """
    Main C-UAS countermeasure orchestration engine.
    Integrates: ThreatEvaluator + CountermeasureSelector + CommandDispatcher
    
    Usage:
        engine = CountermeasureEngine()
        engine.report_detection("T001", "dji_large", 87.5, position=(350, 200, 50))
        engine.run_cycle()   # Call once per second ideally
    """

    STALE_TIMEOUT   = 5.0    # Remove target if not seen for N seconds
    MIN_PRIORITY    = 40     # Minimum to engage (below = monitor only)
    MAX_TARGETS     = 20     # Maximum simultaneous tracked targets

    def __init__(self, environment: dict = None):
        self.targets    = {}
        self.evaluator  = ThreatEvaluator()
        self.selector   = AIDecisionEngine()
        self.dispatcher = CommandDispatcher()
        self.environment = environment or {
            "missile_ready":      True,
            "interceptor_ready":  True,
            "gps_spoof_ready":    True,
            "jamming_active":     False,
        }
        self._lock      = threading.Lock()
        self._cycle_cnt = 0
        
        # Initialize advanced subsystems
        if ADVANCED_MODULES_AVAILABLE:
            self.sys_interceptor = InterceptorSquadron(size=3)
            self.sys_acoustic = AcousticWeaponSystem(num_emitters=2)
            self.sys_adversarial = AdversarialSystem(num_projectors=2)
            self.sys_swarm = SwarmDecoySystem()
            
            # Register callbacks
            self.dispatcher.register_callback(EngagementMode.INTERCEPT_DRONE, self.sys_interceptor.handle_engine_command)
            self.dispatcher.register_callback(EngagementMode.ACOUSTIC_ATTACK, self.sys_acoustic.handle_engine_command)
            self.dispatcher.register_callback(EngagementMode.ADVERSARIAL_PATCH, self.sys_adversarial.handle_engine_command)
            self.dispatcher.register_callback(EngagementMode.SWARM_DECOY, self.sys_swarm.handle_engine_command)

        print("[C-ENGINE] Countermeasure Engine initialized.")
        print(f"[C-ENGINE] Operational environment: {self.environment}")

    def report_detection(self, target_id: str, class_name: str,
                         confidence: float, position: tuple = (0, 0, 0)):
        """
        Accept a detection report from any sensor.
        Position: (x_px, y_px, z_m) — z from radar or 0 if unknown.
        """
        with self._lock:
            if target_id not in self.targets:
                if len(self.targets) >= self.MAX_TARGETS:
                    self._prune_lowest_priority()
                self.targets[target_id] = TrackedTarget(
                    target_id, class_name, confidence, position
                )
                print(f"[C-ENGINE] New target: {target_id} — {class_name} (P:{CLASS_PRIORITY_LOOKUP(class_name)})")
                if DB_AVAILABLE:
                    db.log_event("NEW_TARGET", "COUNTERMEASURE_ENGINE",
                                 f"{class_name} detected | Priority: {CLASS_PRIORITY_LOOKUP(class_name)}")
            else:
                self.targets[target_id].update(class_name, confidence, position)

    def run_cycle(self):
        """Execute one evaluation cycle — call periodically (e.g., 1 Hz).
        Threat scoring is already parallel; top-5 dispatch runs concurrently.
        """
        with self._lock:
            self._cycle_cnt += 1
            self._cleanup_stale()

            if not self.targets:
                return

            ranked = self.evaluator.rank(self.targets)   # parallel scoring
            print(f"\n[C-ENGINE] === Engagement Cycle #{self._cycle_cnt} ===")
            print(f"[C-ENGINE] Active targets: {len(self.targets)}")

            top5 = ranked[:5]

            def _select_and_dispatch(score_target):
                """Runs on a CPU worker thread — one per top target."""
                score, target = score_target
                mode   = self.selector.select(target, self.environment)
                threat = THREAT_DB.get(target.best_class, {})
                print(f"\n  \u25b8 {target.id:>10} | {target.best_class:<22} | "
                      f"Score: {score:>5.1f} | Mode: {mode.name}")
                print(f"             Notes: {threat.get('notes','\u2014')[:70]}")
                if mode not in (EngagementMode.NONE, EngagementMode.MONITOR):
                    self.dispatcher.dispatch(mode, target)
                    target.status = TargetStatus.ENGAGING

            # Submit all top-5 decisions in parallel
            futs = [_ENGINE_POOL.submit(_select_and_dispatch, st) for st in top5]
            for f in as_completed(futs):
                try:
                    f.result(timeout=2.0)
                except Exception as exc:
                    print(f"[C-ENGINE] Dispatch error: {exc}")

    def _cleanup_stale(self):
        stale = [tid for tid, t in self.targets.items()
                 if t.stale_sec > self.STALE_TIMEOUT]
        for tid in stale:
            print(f"[C-ENGINE] Target {tid} stale — removing")
            del self.targets[tid]

    def _prune_lowest_priority(self):
        """Remove lowest-priority target to make room."""
        if not self.targets:
            return
        lowest = min(self.targets.values(), key=lambda t: t.priority)
        print(f"[C-ENGINE] Max targets reached — pruning {lowest.id}")
        del self.targets[lowest.id]

    def mark_neutralized(self, target_id: str):
        """Mark target as neutralized (removed from active engagement)."""
        if target_id in self.targets:
            self.targets[target_id].status     = TargetStatus.NEUTRALIZED
            self.targets[target_id].neutralized = True
            print(f"[C-ENGINE] ✅ Target {target_id} NEUTRALIZED")
            if DB_AVAILABLE:
                db.log_event("TARGET_NEUTRALIZED", "COUNTERMEASURE_ENGINE", target_id)

    def status_report(self) -> dict:
        ranked = self.evaluator.rank(self.targets)
        return {
            "cycle":        self._cycle_cnt,
            "active":       len([t for t in self.targets.values() if not t.neutralized]),
            "total_tracked":len(self.targets),
            "top_threat":   ranked[0][1].to_dict() if ranked else None,
            "all_targets":  [t.to_dict() for t in self.targets.values()],
            "timestamp":    datetime.now().isoformat(),
        }

    def print_status(self):
        report = self.status_report()
        print(f"\n{'='*65}")
        print(f"  COUNTERMEASURE ENGINE STATUS — Cycle #{report['cycle']}")
        print(f"{'='*65}")
        print(f"  Active targets: {report['active']} / {report['total_tracked']}")
        if report["top_threat"]:
            tt = report["top_threat"]
            print(f"  TOP THREAT: {tt['class'].upper()} "
                  f"| Priority: {tt['priority']} | Mode: {tt['mode']}")
        print(f"{'='*65}")


# CLASS_PRIORITY_LOOKUP is defined above CountermeasureEngine (moved to fix forward-reference).


# ══════════════════════════════════════════════════════════════════════
#  STANDALONE TEST
# ══════════════════════════════════════════════════════════════════════

def main():
    import random
    print("=" * 65)
    print("  MCDIS Countermeasure Engine — Standalone Test")
    print("=" * 65)

    engine = CountermeasureEngine()

    # Inject test detections
    test_detections = [
        ("T001", "shahed_136",         95.0, (640, 360, 200)),
        ("T002", "dji_large",           82.0, (320, 240, 50)),
        ("T003", "fpv_suicide",         91.0, (800, 450, 30)),
        ("T004", "swarm_unit",          75.0, (200, 100, 80)),
        ("T005", "bird",                60.0, (500, 300, 100)),
        ("T006", "generic_commercial",  70.0, (150, 200, 40)),
    ]

    print("\n[TEST] Injecting test detections...\n")
    for tid, cls, conf, pos in test_detections:
        engine.report_detection(tid, cls, conf, pos)
        time.sleep(0.1)

    # Simulate 3 cycles
    for cycle in range(3):
        print(f"\n[TEST] --- Cycle {cycle+1} ---")
        engine.run_cycle()
        time.sleep(1)

        # Update positions (simulate movement)
        for tid in engine.targets:
            t = engine.targets[tid]
            dx, dy = random.randint(-20, 20), random.randint(-20, 20)
            x, y, z = t.position
            t.update(t.best_class, random.uniform(70, 95), (x+dx, y+dy, z))

    engine.print_status()
    print("\n[TEST] ✅ Countermeasure Engine test complete.")


if __name__ == "__main__":
    main()
