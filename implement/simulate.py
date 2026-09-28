"""
MCDIS — Scenario Simulator
============================
simulate.py  —  يشتغل مع app.py مباشرة

ScenarioSimulator class بالضبط اللي app.py بيستخدمه:
    sim = ScenarioSimulator(verbose=False)
    sim.run(scenario_id)
    sim.is_running        → bool
    sim.engine.targets    → dict of TargetState
"""

import time
import math
import threading
import sqlite3
import os
import random
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

log = logging.getLogger("mcdis.simulate")

# ── DB path (same as app.py uses) ────────────────────────────────────────────
_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "mcdis",
    "mcdis_logs.db"
)

def _get_conn():
    conn = sqlite3.connect(_DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS detections (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            sensor_type TEXT,
            target_id   TEXT,
            threat_level TEXT,
            confidence  REAL,
            timestamp   TEXT DEFAULT (datetime('now','utc')),
            details     TEXT,
            node_id     TEXT DEFAULT 'NODE-ALPHA',
            iff_status  TEXT DEFAULT 'UNKNOWN'
        )
    """)
    conn.commit()
    return conn


def _log(sensor_type, target_id, threat_level, confidence, details="", node_id="NODE-ALPHA", iff_status="UNKNOWN"):
    try:
        conn = _get_conn()
        conn.execute(
            "INSERT INTO detections (sensor_type,target_id,threat_level,confidence,details,node_id,iff_status) VALUES(?,?,?,?,?,?,?)",
            (sensor_type, str(target_id), threat_level, round(confidence, 1), details, node_id, iff_status)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        log.debug(f"DB log error: {e}")


# ── Target State ──────────────────────────────────────────────────────────────

@dataclass
class TargetState:
    """
    حالة هدف — app.py بيقرأ منه:
      target.position   → (x, y, z) بالمتر
      target.best_class → اسم الـ class
      target.priority   → int 0-100
    """
    track_id:   int
    best_class: str
    priority:   int
    model_name: str = "Unknown"
    category:   str = "DRONE"   # DRONE, BIRD, FIXED_WING
    position:   tuple = field(default_factory=lambda: (0.0, 0.0, 50.0))
    speed_kmh:  float = 60.0
    azimuth:    float = 0.0     # degrees
    range_m:    float = 2000.0
    threat:     str   = "MEDIUM"
    confidence: float = 0.85
    az_rate:    float = 0.3     # degrees/sec — للـ animation
    range_rate: float = 5.0     # m/sec — تقترب من المركز
    node_id:    str   = "NODE-ALPHA"
    iff_status: str   = "UNKNOWN" # UNKNOWN, FRIENDLY, HOSTILE

    def tick(self, dt: float = 1.0):
        """يحدث الموقع كل ثانية"""
        self.azimuth  = (self.azimuth + self.az_rate * dt) % 360
        self.range_m  = max(50, self.range_m - self.range_rate * dt)
        az_rad = math.radians(self.azimuth)
        self.position = (
            self.range_m * math.sin(az_rad),
            self.range_m * math.cos(az_rad),
            random.uniform(30, 150),
        )


# ── Engagement Engine ─────────────────────────────────────────────────────────

class EngagementEngine:
    """
    بيدير الأهداف النشطة.
    app.py بيقرأ: engine.targets → Dict[int, TargetState]
    """
    def __init__(self):
        self.targets: Dict[int, TargetState] = {}
        self._lock = threading.Lock()

    def add_target(self, t: TargetState):
        with self._lock:
            self.targets[t.track_id] = t

    def tick_all(self, dt: float = 1.0):
        with self._lock:
            for t in self.targets.values():
                t.tick(dt)

    def remove_target(self, track_id: int):
        with self._lock:
            self.targets.pop(track_id, None)

    def clear(self):
        with self._lock:
            self.targets.clear()


# ── Scenario Definitions ──────────────────────────────────────────────────────

SCENARIOS = {
    # ── Scenario 1: DJI Commercial Intrusion ─────────────────────────────────
    1: {
        "name": "COMMERCIAL DRONE INTRUSION",
        "description": "DJI Mavic Pro يخترق المنطقة المحمية",
        "duration": 30,
        "targets": [
            TargetState(101, "DJI Multirotor",   priority=30,
                        model_name="DJI Mavic 3", category="DRONE",
                        range_m=2500, azimuth=135, az_rate=0.4,
                        range_rate=8, threat="MEDIUM",  confidence=92,
                        speed_kmh=45.0),
        ],
        "events": [
            (0,  "VISION",   "CAM_TGT_101", "MEDIUM",   88, "DJI Multirotor detected"),
            (3,  "RF_SCAN",  "CAM_TGT_101", "MEDIUM",   91, "2.4GHz OcuSync signal locked"),
            (6,  "ACOUSTIC", "CAM_TGT_101", "MEDIUM",   75, "Rotor harmonic: DJI signature"),
            (10, "VISION",   "CAM_TGT_101", "HIGH",     94, "Target entering inner zone"),
            (15, "COMMAND",  "CMD_JAM_101",  "HIGH",     99, "RF Jamming Level-2 activated"),
            (20, "VISION",   "CAM_TGT_101", "ELEVATED", 88, "Target RTH initiated"),
            (28, "SYSTEM",   "SYS_CLEAR",   "MINIMAL",  100, "Airspace clear"),
        ],
    },

    # ── Scenario 2: FPV Suicide Attack ───────────────────────────────────────
    2: {
        "name": "FPV SUICIDE ATTACK",
        "description": "FPV drone انتحارية تهجم بسرعة عالية — لا GPS",
        "duration": 25,
        "targets": [
            TargetState(201, "FPV/Racing Drone", priority=90,
                        model_name="Custom FPV 7-inch", category="DRONE",
                        range_m=1800, azimuth=10, az_rate=0.1,
                        range_rate=25, threat="CRITICAL", confidence=78,
                        speed_kmh=130),
        ],
        "events": [
            (0,  "RADAR",    "RAD_TGT_201", "HIGH",     82, "Fast target detected — 130km/h"),
            (2,  "VISION",   "CAM_TGT_201", "HIGH",     79, "FPV drone confirmed — NO GPS"),
            (4,  "RF_SCAN",  "CAM_TGT_201", "CRITICAL", 85, "ELRS 900MHz control link"),
            (5,  "COMMAND",  "CMD_INT_201", "CRITICAL",  99, "INTERCEPTOR DRONE DEPLOYED"),
            (8,  "ACOUSTIC", "CAM_TGT_201", "CRITICAL", 88, "High-RPM motor signature"),
            (12, "COMMAND",  "CMD_KIN_201", "CRITICAL",  99, "KINETIC INTERCEPT AUTHORIZED"),
            (18, "SYSTEM",   "SYS_ENGAGE",  "CRITICAL", 100, "Target neutralized — zone clear"),
        ],
    },

    # ── Scenario 3: Shahed-136 ───────────────────────────────────────────────
    3: {
        "name": "SHAHED-136 APPROACH",
        "description": "طائرة شاهد-136 تقترب من الشمال — تصنيف CRITICAL",
        "duration": 45,
        "targets": [
            TargetState(301, "Shahed-136 Type",  priority=100,
                        model_name="Shahed-136/Geranium-2", category="DRONE",
                        range_m=4500, azimuth=15, az_rate=0.15,
                        range_rate=12, threat="CRITICAL", confidence=83,
                        speed_kmh=150),
        ],
        "events": [
            (0,  "RADAR",    "RAD_TGT_301", "ELEVATED", 74, "Large delta-wing target — N bearing"),
            (3,  "ACOUSTIC", "CAM_TGT_301", "HIGH",     81, "Piston engine signature — Shahed type"),
            (6,  "VISION",   "CAM_TGT_301", "CRITICAL", 83, "SHAHED-136 CONFIRMED — CRITICAL"),
            (8,  "COMMAND",  "CMD_JAM_301", "CRITICAL",  99, "Full-spectrum jamming Level-4"),
            (12, "RF_SCAN",  "CAM_TGT_301", "CRITICAL", 77, "GPS L1 disruption — target drifting"),
            (18, "COMMAND",  "CMD_KIN_301", "CRITICAL",  99, "MISSILE SYSTEM — ARMED"),
            (25, "COMMAND",  "CMD_ENG_301", "CRITICAL",  99, "ENGAGE TARGET AUTHORIZED"),
            (35, "SYSTEM",   "SYS_ENGAGE",  "CRITICAL", 100, "Target intercepted — zone clear"),
        ],
    },

    # ── Scenario 4: Swarm Attack ─────────────────────────────────────────────
    4: {
        "name": "SWARM ATTACK — 6 UNITS",
        "description": "سرب من 6 درونز من 3 اتجاهات مختلفة",
        "duration": 40,
        "targets": [
            TargetState(401+i, "Swarm Unit", priority=95,
                        model_name="Micro Swarm Drone", category="DRONE",
                        range_m=2000, azimuth=float(i*60),
                        az_rate=random.uniform(0.1, 0.4),
                        range_rate=15, threat="CRITICAL",
                        confidence=random.uniform(70, 88),
                        speed_kmh=80.0)
            for i in range(6)
        ],
        "events": [
            (0,  "RADAR",   "RAD_SWARM",   "HIGH",     80, "Multiple contacts — SWARM detected"),
            (3,  "VISION",  "CAM_SWARM",   "CRITICAL", 85, "6 swarm units confirmed"),
            (5,  "RF_SCAN", "CAM_SWARM",   "CRITICAL", 90, "Coordinated FHSS — swarm protocol"),
            (6,  "COMMAND", "CMD_JAM_ALL", "CRITICAL",  99, "WIDEBAND JAMMING — all frequencies"),
            (12, "COMMAND", "CMD_INT_ALL", "CRITICAL",  99, "3 interceptors deployed"),
            (20, "SYSTEM",  "SYS_ENGAGE",  "CRITICAL", 100, "Swarm neutralized: 6/6"),
        ],
    },

    # ── Scenario 5: Bird Flock (False Alarm) ──────────────────────────────────
    5: {
        "name": "BIRD FLOCK (FALSE ALARM TEST)",
        "description": "سرب من الطيور (Seagulls) يطير بالقرب من القاعدة لاختبار التمييز",
        "duration": 25,
        "targets": [
            TargetState(501, "Bird", priority=0,
                        model_name="Seagull", category="BIRD",
                        range_m=1200, azimuth=45, az_rate=1.5,
                        range_rate=-5, threat="NONE", confidence=95,
                        speed_kmh=35.0),
            TargetState(502, "Bird", priority=0,
                        model_name="Seagull", category="BIRD",
                        range_m=1210, azimuth=46, az_rate=1.4,
                        range_rate=-4, threat="NONE", confidence=92,
                        speed_kmh=34.0),
        ],
        "events": [
            (0,  "RADAR",    "RAD_TGT_501", "NONE",     82, "Small cross-section targets detected"),
            (3,  "VISION",   "CAM_TGT_501", "NONE",     98, "CLASSIFICATION: BIRD (Biological)"),
            (5,  "SYSTEM",   "SYS_IGNORE",  "NONE",     100, "Targets ignored by AI Engine — False Alarm"),
        ],
    },
    # ── Scenario 6: Friendly Police Drone (IFF Test) ─────────────────────────
    6: {
        "name": "FRIENDLY POLICE DRONE (IFF VERIFIED)",
        "description": "طائرة تابعة للشرطة (Friendly) يتم التعرف عليها تلقائياً عبر IFF",
        "duration": 25,
        "targets": [
            TargetState(601, "Police Drone", priority=0,
                        model_name="Matrice 300 RTK", category="DRONE",
                        range_m=1800, azimuth=270, az_rate=0.8,
                        range_rate=10, threat="NONE", confidence=99,
                        speed_kmh=40.0, iff_status="FRIENDLY"),
        ],
        "events": [
            (0,  "RADAR",   "RAD_TGT_601", "UNKNOWN", 80, "New target detected"),
            (2,  "IFF_SYS", "IFF_TGT_601", "NONE",    100, "IFF Handshake SUCCESS — Authorized MAC"),
            (5,  "VISION",  "CAM_TGT_601", "NONE",    98, "Friendly Drone visually confirmed"),
        ],
    },
}


# ── ScenarioSimulator ─────────────────────────────────────────────────────────

class ScenarioSimulator:
    """
    الـ class الرئيسي — app.py بيعمله instance ويشغله.
    
    Interface:
        sim = ScenarioSimulator(verbose=False)
        sim.run(scenario_id)        ← blocking (يُشغَّل في thread)
        sim.is_running              ← bool
        sim.engine.targets          ← dict للـ radar blips
    """

    def __init__(self, verbose: bool = True):
        self.verbose    = verbose
        self.is_running = False
        self.engine     = EngagementEngine()
        self._thread:   Optional[threading.Thread] = None

    def run(self, scenario_id: int):
        """يشغل السيناريو — يُستدعى من thread منفصل في app.py"""
        sc = SCENARIOS.get(int(scenario_id))
        if not sc:
            log.error(f"Scenario {scenario_id} not found")
            return

        self.is_running = True
        self.engine.clear()

        if self.verbose:
            print(f"\n[SIM] ══ SCENARIO {scenario_id}: {sc['name']} ══")
            print(f"[SIM] {sc['description']}")

        # Add targets
        for t in sc["targets"]:
            # Reset each target to fresh state
            t.range_m = t.__class__.__dataclass_fields__['range_m'].default
            self.engine.add_target(t)

        # Timeline events list
        events = list(sc["events"])
        start  = time.time()

        # ── Main simulation loop ──────────────────────────────────────
        while self.is_running:
            elapsed = time.time() - start

            # Tick all targets (move them)
            self.engine.tick_all(dt=1.0)

            # Fire events at their scheduled time
            fired = []
            for ev in events:
                # Add node_id and iff_status support if they exist in the event tuple
                if len(ev) == 6:
                    t_sec, sensor, tgt_id, threat, conf, details = ev
                    node_id = "NODE-ALPHA"
                    iff_status = "UNKNOWN"
                elif len(ev) == 8:
                    t_sec, sensor, tgt_id, threat, conf, details, node_id, iff_status = ev
                else:
                    t_sec, sensor, tgt_id, threat, conf, details = ev[0:6]
                    node_id = "NODE-ALPHA"
                    iff_status = "UNKNOWN"

                # Override IFF status for Scenario 6 if applicable
                for t in self.engine.targets.values():
                    if f"{t.track_id}" in tgt_id:
                        iff_status = t.iff_status

                if elapsed >= t_sec:
                    _log(sensor, tgt_id, threat, conf, details, node_id, iff_status)
                    if self.verbose:
                        print(f"[SIM {elapsed:5.1f}s] [{sensor}] {tgt_id} — {threat} (IFF: {iff_status}) — {details}")
                    fired.append(ev)

            for ev in fired:
                events.remove(ev)

            # Check if duration passed
            if elapsed >= sc["duration"]:
                if self.verbose:
                    print(f"[SIM] Scenario {scenario_id} complete")
                break

            time.sleep(1.0)

        self.is_running = False
        self.engine.clear()
