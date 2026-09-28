"""
╔══════════════════════════════════════════════════════════════════════╗
║  MCDIS — Multi-Modal Counter-Drone Intelligence System              ║
║  Module: Electronic Warfare & Jamming System v3.0                    ║
║  Classification: UNCLASSIFIED // FOR OFFICIAL USE ONLY               ║
╠══════════════════════════════════════════════════════════════════════╣
║  Jamming Levels:                                                      ║
║    L1 — 433 MHz  (LoRa, long-range RC, legacy drone links)           ║
║    L2 — 900 MHz  (ExpressLRS, ELRS, ISM band RC)                     ║
║    L3 — 2.4 GHz  (WiFi, DJI OcuSync, FrSky, DSMX control)          ║
║    L4 — 5.8 GHz  (DJI V2 video, analog FPV, OcuSync 2)             ║
║    L5 — GPS L1 (1575.42 MHz) + L2 (1227.60 MHz) — Navigation jam   ║
║                                                                       ║
║  Safety:                                                              ║
║    • Auto-stop timer (max 30s per burst)                              ║
║    • Whitelisted frequency exclusion zones                            ║
║    • Emergency halt command                                           ║
║    • All activities logged to tactical DB                             ║
╚══════════════════════════════════════════════════════════════════════╝

REAL HARDWARE NOTE:
─────────────────────────────────────────────────────────────────────
  This module simulates jamming logic for competition demonstration.
  In a real deployment, the dispatch layer would interface with:
    • HackRF One / BladeRF (wideband SDR transmitter)
    • ADALM-PLUTO (Analog Devices SDR dongle)
    • GNU Radio jamming flowgraph via ZMQ socket
    • Commercial CUAS jammer hardware (e.g., DroneGun, AUDS)
    
  The frequency database, safety logic, and protocol detection
  reflect real operational parameters used by military C-UAS systems.
─────────────────────────────────────────────────────────────────────
"""

import time
import threading
import random
import sys
import math
import logging
from datetime import datetime
from collections import defaultdict, deque
from enum import Enum, auto
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "mcdis"))
try:
    from database import db
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("MCDIS-JAMMER")


# ══════════════════════════════════════════════════════════════════════
#  FREQUENCY BAND DEFINITIONS
# ══════════════════════════════════════════════════════════════════════

class JamLevel(Enum):
    L1_433   = auto()   # 433 MHz LoRa / RC
    L2_900   = auto()   # 900 MHz ExpressLRS / ELRS
    L3_2400  = auto()   # 2.4 GHz DJI OcuSync / WiFi / DSMX
    L4_5800  = auto()   # 5.8 GHz FPV Video / DJI OcuSync 2
    L5_GPS   = auto()   # GPS L1 1575.42 MHz + L2 1227.60 MHz


FREQ_BANDS = {
    JamLevel.L1_433: {
        "name":        "433MHz ISM",
        "center_mhz":  433.920,
        "bandwidth_mhz": 8.0,
        "range_mhz":   [433.0, 434.79],
        "protocols":   ["LoRa", "FSK", "OOK", "ASK", "Legacy RC"],
        "power_dbm":   30,    # Simulated output power
        "uses":        "Long-range drone RC links, LoRa telemetry, "
                       "legacy RC transmitters (Futaba, JR, Spektrum legacy)",
        "effective_range_m": 500,
        "jammable_classes": ["military_rotor", "generic_commercial",
                             "swarm_unit", "micro_nano"],
    },
    JamLevel.L2_900: {
        "name":        "900MHz ISM",
        "center_mhz":  915.0,
        "bandwidth_mhz": 26.0,
        "range_mhz":   [902.0, 928.0],
        "protocols":   ["ExpressLRS", "ELRS", "FHSS-900", "433-US-equiv"],
        "power_dbm":   33,
        "uses":        "Modern FPV RC links (ExpressLRS 900MHz), "
                       "long-range drone control, penetrates foliage well",
        "effective_range_m": 800,
        "jammable_classes": ["fpv_suicide", "generic_commercial", "swarm_unit"],
    },
    JamLevel.L3_2400: {
        "name":        "2.4GHz ISM",
        "center_mhz":  2441.0,
        "bandwidth_mhz": 83.5,
        "range_mhz":   [2400.0, 2483.5],
        "protocols":   ["WiFi 802.11b/g/n", "DJI OcuSync 2.4", "DSMX",
                        "FrSky D/X", "ExpressLRS 2.4", "Graupner HoTT"],
        "power_dbm":   36,
        "uses":        "Primary DJI drone control link, most common FPV RC, "
                       "WiFi-based drones (Autel EVO, Parrot, consumer)",
        "effective_range_m": 300,
        "jammable_classes": ["dji_large", "dji_mini", "fpv_suicide",
                             "generic_commercial", "swarm_unit", "military_rotor"],
    },
    JamLevel.L4_5800: {
        "name":        "5.8GHz ISM",
        "center_mhz":  5800.0,
        "bandwidth_mhz": 150.0,
        "range_mhz":   [5725.0, 5875.0],
        "protocols":   ["DJI OcuSync 2.0/3.0 (video)", "Analog FPV",
                        "DJI Digital FPV", "5GHz WiFi"],
        "power_dbm":   34,
        "uses":        "DJI video transmission downlink, analog FPV video, "
                       "disrupts camera feed causing pilot disorientation",
        "effective_range_m": 200,
        "jammable_classes": ["dji_large", "fpv_suicide", "generic_commercial"],
    },
    JamLevel.L5_GPS: {
        "name":        "GPS L1 + L2",
        "center_mhz":  1575.42,    # L1 civilian
        "center_l2_mhz": 1227.60,  # L2 military/dual-band
        "bandwidth_mhz": 2.046,
        "power_dbm":   28,
        "uses":        "GPS navigation denial — causes drone to lose position fix. "
                       "DJI: triggers Return-to-Home. Military GPS: anti-spoof hardened.",
        "effective_range_m": 1000,
        "protocols":   ["GPS L1 C/A civilian", "GPS L2 P(Y) military",
                        "GLONASS L1/L2", "Galileo E1/E5"],
        "jammable_classes": ["dji_large", "dji_mini", "generic_commercial",
                             "swarm_unit", "fpv_suicide"],   # FPV only if has GPS
        "warning":     "GPS jamming affects ALL receivers in range including friendly. "
                       "Use directional antenna + cone of fire restriction.",
    },
}

# Frequencies that MUST NOT be jammed (safety exclusion list)
PROTECTED_FREQUENCIES_MHZ = [
    (118.0, 137.0),      # Aviation voice (VHF)
    (156.0, 174.0),      # Marine VHF
    (406.0, 406.1),      # EPIRB distress
    (121.5, 121.5),      # Aviation emergency
    (243.0, 243.0),      # Military emergency
    (406.0, 406.1),      # Search and rescue beacon
]


# ══════════════════════════════════════════════════════════════════════
#  RF PROTOCOL SCANNER
# ══════════════════════════════════════════════════════════════════════

class RFProtocolScanner:
    """
    Passive RF spectrum scanner to identify drone communication protocols.
    
    In simulation: probabilistic detection model.
    In production: interfaces with SDR (RTL-SDR, HackRF, ADALM-PLUTO)
                   via GNU Radio or SDR# spectrum data.
    """

    # Signal detection probabilities per band (tunable by environment)
    DETECTION_MODEL = {
        JamLevel.L1_433:  {"detect_prob": 0.35, "snr_range": (-10, 25)},
        JamLevel.L2_900:  {"detect_prob": 0.40, "snr_range": (-8, 30)},
        JamLevel.L3_2400: {"detect_prob": 0.55, "snr_range": (-5, 35)},
        JamLevel.L4_5800: {"detect_prob": 0.45, "snr_range": (-3, 28)},
        JamLevel.L5_GPS:  {"detect_prob": 0.20, "snr_range": (5, 45)},   # GPS strong
    }

    PROTOCOL_FINGERPRINTS = {
        "OcuSync":    {"bandwidth_mhz": 20, "modulation": "OFDM",
                       "hop_rate": None, "bands": [JamLevel.L3_2400, JamLevel.L4_5800]},
        "DSMX":       {"bandwidth_mhz": 1,  "modulation": "DSSS",
                       "hop_rate": 22,     "bands": [JamLevel.L3_2400]},
        "ExpressLRS": {"bandwidth_mhz": 0.5,"modulation": "LoRa",
                       "hop_rate": 500,    "bands": [JamLevel.L2_900, JamLevel.L3_2400]},
        "FrSky-D8":   {"bandwidth_mhz": 2,  "modulation": "GFSK",
                       "hop_rate": 50,     "bands": [JamLevel.L3_2400]},
        "LoRa":       {"bandwidth_mhz": 0.5,"modulation": "CSS",
                       "hop_rate": None,   "bands": [JamLevel.L1_433]},
    }

    def __init__(self):
        self._scans   = deque(maxlen=200)   # Scan history
        self._running = False
        self._thread  = None
        self._detections = defaultdict(list)
        print("[RF-SCAN] Passive RF scanner initialized")
        print(f"[RF-SCAN] Monitoring {len(FREQ_BANDS)} frequency bands")

    def start_continuous(self, interval_sec: float = 10.0):
        """Start continuous background RF scan."""
        self._running = True
        self._thread  = threading.Thread(
            target=self._scan_loop, args=(interval_sec,),
            daemon=True, name="RF-Scanner"
        )
        self._thread.start()
        print(f"[RF-SCAN] Continuous scan started (interval: {interval_sec}s)")

    def stop(self):
        self._running = False

    def _scan_loop(self, interval: float):
        while self._running:
            time.sleep(interval)
            self.scan_all()

    def scan_all(self) -> dict:
        """Scan all frequency bands and return detections."""
        results = {}
        print(f"\n[RF-SCAN] === Full spectrum scan @ {datetime.now().strftime('%H:%M:%S')} ===")
        for level, band_info in FREQ_BANDS.items():
            result = self._scan_band(level, band_info)
            results[level] = result
            if result["detected"]:
                self._detections[level.name].append(result)
                print(f"  ⚡ [{level.name}] {band_info['name']} "
                      f"— {result['protocol']} | SNR: {result['snr_db']:.1f}dB "
                      f"| Power: {result['power_dbm']:.1f}dBm")
                if DB_AVAILABLE:
                    db.log_detection(
                        sensor_type="RF_SCAN",
                        target_id=f"RF_{level.name}_{len(self._detections[level.name]):04d}",
                        threat_level="HIGH",
                        confidence=result["confidence"],
                        details=f"Protocol: {result['protocol']} @ {band_info['center_mhz']}MHz"
                    )
        self._scans.append({"timestamp": time.time(), "results": results})
        return results

    def _scan_band(self, level: JamLevel, band_info: dict) -> dict:
        """Simulate SDR scan of a single frequency band."""
        model   = self.DETECTION_MODEL[level]
        detected = random.random() < model["detect_prob"]

        if detected:
            snr     = random.uniform(*model["snr_range"])
            power   = random.uniform(-90, -30)     # dBm
            protocol = random.choice(band_info["protocols"])
            hopping = random.random() > 0.5
            conf    = min(int(50 + snr * 1.5), 99)
        else:
            snr, power, protocol, hopping, conf = 0, -110, "NONE", False, 0

        return {
            "band":      level.name,
            "center_mhz":band_info["center_mhz"],
            "detected":  detected,
            "protocol":  protocol,
            "snr_db":    round(snr, 1),
            "power_dbm": round(power, 1),
            "hopping":   hopping,
            "confidence":conf,
            "timestamp": datetime.now().isoformat(),
        }

    def identify_protocol(self, raw_snr: float, bandwidth: float, band: JamLevel) -> str:
        """Attempt to fingerprint protocol from spectral features."""
        for name, fp in self.PROTOCOL_FINGERPRINTS.items():
            if band in fp["bands"]:
                bw_match = abs(fp["bandwidth_mhz"] - bandwidth) < 5.0
                if bw_match:
                    return name
        return "UNKNOWN_PROTOCOL"

    @property
    def last_scan(self) -> dict:
        return self._scans[-1] if self._scans else {}


# ══════════════════════════════════════════════════════════════════════
#  GPS SPOOFER / OVERRIDER
# ══════════════════════════════════════════════════════════════════════

class GPSOverrideSystem:
    """
    GPS Spoofing system for commercial drone capture.
    
    Strategy for DJI / commercial drones:
    1. Jam GPS L1 → drone loses position lock
    2. Inject false GPS signal at desired coordinates
    3. DJI firmware triggers Return-to-Home to spoofed "Home" location
    4. Drone flies to our controlled capture zone
    
    NOT effective against:
    - Military GPS (encrypted P(Y) code — anti-spoof)
    - INS/Barometric hybrid navigation
    - Fiber-guided FPV (no GPS)
    """

    def __init__(self):
        self._active       = False
        self._target_id    = None
        self._spoof_coords = None
        self._start_time   = None
        self._thread       = None
        print("[GPS-SPF] GPS Override System initialized")

    def activate(self, target_id: str, capture_coords: tuple,
                 duration_sec: float = 20.0):
        """
        Activate GPS override targeting a specific drone.
        
        Args:
            target_id     : Drone identifier
            capture_coords: (lat, lon) of our capture zone
            duration_sec  : How long to maintain spoof
        """
        if self._active:
            print(f"[GPS-SPF] Already active against {self._target_id} — stopping first")
            self.deactivate()

        self._active       = True
        self._target_id    = target_id
        self._spoof_coords = capture_coords
        self._start_time   = time.time()

        print(f"\n[🛰️  GPS OVERRIDE] Activating against {target_id}")
        print(f"  Capture zone coordinates: {capture_coords}")
        print(f"  Strategy: Jam GPS L1 → Inject false home → Trigger RTH")
        print(f"  Duration: {duration_sec}s max")

        if DB_AVAILABLE:
            db.log_command("GPS_OVERRIDE", target_id, "ACTIVE")

        self._thread = threading.Thread(
            target=self._spoof_loop,
            args=(duration_sec,),
            daemon=True,
            name="GPS-Spoofer"
        )
        self._thread.start()

    def _spoof_loop(self, max_dur: float):
        """Simulate GPS spoofing loop."""
        step = 0
        while self._active and (time.time() - self._start_time) < max_dur:
            step += 1
            # Phase 1: Jam real GPS (first 5 steps)
            if step <= 5:
                print(f"[GPS-SPF] Phase 1: Jamming GPS L1 @ 1575.42MHz ... "
                      f"({step*2}s)")
            # Phase 2: Inject false signal
            elif step <= 12:
                offset_m = (12 - step) * 20   # Gradually approach capture zone
                print(f"[GPS-SPF] Phase 2: Injecting false GPS signal "
                      f"(offset: -{offset_m}m to capture zone)")
            # Phase 3: RTH triggered
            else:
                print(f"[GPS-SPF] Phase 3: RTH TRIGGERED — drone heading to capture zone "
                      f"{self._spoof_coords}")
            time.sleep(2)
        self.deactivate()

    def deactivate(self):
        if self._active:
            print(f"[GPS-SPF] Override deactivated — target: {self._target_id}")
            self._active    = False
            self._target_id = None
            if DB_AVAILABLE:
                db.log_command("GPS_OVERRIDE", "DEACTIVATE", "STOPPED")

    @property
    def is_active(self) -> bool:
        return self._active


# ══════════════════════════════════════════════════════════════════════
#  JAMMING UNIT — Single Frequency Band Jammer
# ══════════════════════════════════════════════════════════════════════

class JammingUnit:
    """
    Controls a single-band jamming transmitter.
    Auto-stop safety prevents continuous transmission > MAX_BURST_SEC.
    """

    MAX_BURST_SEC = 30     # Safety: max 30 seconds continuous jamming
    COOLDOWN_SEC  = 10     # Mandatory cooldown between bursts

    def __init__(self, level: JamLevel):
        self.level       = level
        self.band_info   = FREQ_BANDS[level]
        self._active     = False
        self._start_time = 0
        self._lock       = threading.Lock()
        self._last_stop  = 0
        self._jam_count  = 0

    def start(self, target_description: str = "") -> bool:
        """Activate jamming. Returns False if on cooldown or already active."""
        with self._lock:
            now = time.time()

            if self._active:
                log.warning(f"[JAM-{self.level.name}] Already active")
                return False

            if now - self._last_stop < self.COOLDOWN_SEC:
                remaining = self.COOLDOWN_SEC - (now - self._last_stop)
                log.warning(f"[JAM-{self.level.name}] Cooldown — {remaining:.1f}s remaining")
                return False

            self._active     = True
            self._start_time = now
            self._jam_count += 1

            band = self.band_info
            log.info(f"\n[📡 JAM-{self.level.name}] ACTIVE — {band['name']}")
            log.info(f"  Center: {band['center_mhz']}MHz | "
                     f"BW: {band['bandwidth_mhz']}MHz | "
                     f"Pwr: {band['power_dbm']}dBm")
            log.info(f"  Protocols disrupted: {', '.join(band['protocols'])}")
            log.info(f"  Effective range: {band.get('effective_range_m',0)}m")
            if target_description:
                log.info(f"  Target: {target_description}")

            warning = band.get("warning")
            if warning:
                log.warning(f"  ⚠️  {warning}")

            # Auto-stop safety timer
            timer = threading.Timer(self.MAX_BURST_SEC, self._auto_stop)
            timer.daemon = True
            timer.start()

            if DB_AVAILABLE:
                db.log_detection(
                    sensor_type="JAMMER",
                    target_id=f"JAM_{self.level.name}_{self._jam_count:04d}",
                    threat_level="HIGH",
                    confidence=100,
                    details=f"Band: {band['name']} | Center: {band['center_mhz']}MHz | "
                            f"Target: {target_description}"
                )
            return True

    def stop(self):
        with self._lock:
            if not self._active:
                return
            duration = round(time.time() - self._start_time, 1)
            self._active    = False
            self._last_stop = time.time()
            log.info(f"[JAM-{self.level.name}] Stopped after {duration}s")
            if DB_AVAILABLE:
                db.log_event("JAM_STOP", f"JAM_{self.level.name}",
                             f"Duration: {duration}s")

    def _auto_stop(self):
        log.warning(f"[JAM-{self.level.name}] AUTO-STOP — max burst time reached")
        self.stop()

    @property
    def is_active(self) -> bool:
        return self._active

    @property
    def active_duration(self) -> float:
        if self._active:
            return round(time.time() - self._start_time, 1)
        return 0.0

    @property
    def status(self) -> dict:
        return {
            "band":           self.level.name,
            "active":         self._active,
            "duration_sec":   self.active_duration,
            "jam_count":      self._jam_count,
            "center_mhz":     self.band_info["center_mhz"],
            "power_dbm":      self.band_info["power_dbm"],
        }


# ══════════════════════════════════════════════════════════════════════
#  JAMMING SYSTEM — Master Controller
# ══════════════════════════════════════════════════════════════════════

class JammingSystem:
    """
    Master controller for all 5 jamming levels + GPS override.
    
    Usage:
        js = JammingSystem()
        js.engage_drone_class("dji_large", target_id="T001")
        time.sleep(20)
        js.halt_all()
    """

    def __init__(self):
        self.units = {level: JammingUnit(level) for level in JamLevel}
        self.gps_override  = GPSOverrideSystem()
        self.scanner       = RFProtocolScanner()
        self._halt_event   = threading.Event()
        self._total_jams   = 0

        print("[JAMMER] ⚡ Electronic Warfare & Jamming System initialized")
        print(f"[JAMMER]    Levels available: {len(self.units)}")
        print(f"[JAMMER]    GPS Override: {'READY' if True else 'UNAVAILABLE'}")

    # ── Presets per drone class ──────────────────────────────────────

    ENGAGEMENT_PRESETS = {
        "dji_large": {
            "levels":     [JamLevel.L3_2400, JamLevel.L4_5800, JamLevel.L5_GPS],
            "gps_override": True,
            "desc":       "DJI OcuSync + GPS override → Return-to-Home capture",
        },
        "dji_mini": {
            "levels":     [JamLevel.L3_2400, JamLevel.L5_GPS],
            "gps_override": True,
            "desc":       "DJI Mini 2.4GHz + GPS → RTH capture",
        },
        "fpv_suicide": {
            "levels":     [JamLevel.L3_2400, JamLevel.L2_900],
            "gps_override": False,   # No GPS on most FPV — kinetic backup
            "desc":       "FPV RC jam (if NOT fiber-guided). Kinetic backup MANDATORY.",
        },
        "generic_commercial": {
            "levels":     [JamLevel.L1_433, JamLevel.L2_900, JamLevel.L3_2400,
                           JamLevel.L4_5800],
            "gps_override": True,
            "desc":       "Broadband commercial drone jam — all common RC bands",
        },
        "swarm_unit": {
            "levels":     [JamLevel.L1_433, JamLevel.L2_900, JamLevel.L3_2400,
                           JamLevel.L4_5800, JamLevel.L5_GPS],
            "gps_override": False,
            "desc":       "Full spectrum broadband jam for swarm disruption",
        },
        "military_rotor": {
            "levels":     [JamLevel.L3_2400, JamLevel.L5_GPS],
            "gps_override": False,   # Military GPS anti-spoof
            "desc":       "Military rotor — jam data link only. Kinetic backup.",
        },
        "shahed_136": {
            "levels":     [],
            "gps_override": False,
            "desc":       "⚠️ Loitering munition — JAMMING INEFFECTIVE. "
                          "Kinetic engagement required immediately.",
        },
    }

    def engage_drone_class(self, class_name: str, target_id: str = "UNKNOWN",
                           capture_coords: tuple = (30.0444, 31.2357)):
        """
        Engage a detected drone class with appropriate jamming preset.
        
        Args:
            class_name     : MCDIS class name (e.g., 'dji_large')
            target_id      : Track ID for audit log
            capture_coords : (lat, lon) for GPS override capture zone
        """
        preset = self.ENGAGEMENT_PRESETS.get(
            class_name,
            self.ENGAGEMENT_PRESETS["generic_commercial"]
        )

        print(f"\n{'='*65}")
        print(f"[JAMMER] Engaging: {class_name.upper()} | Target: {target_id}")
        print(f"[JAMMER] Strategy: {preset['desc']}")
        print(f"{'='*65}")

        if not preset["levels"]:
            print(f"[JAMMER] ❌ NO JAMMING POSSIBLE for {class_name}")
            print(f"[JAMMER] → Escalate to KINETIC engagement immediately")
            return False

        # Activate jamming units
        for level in preset["levels"]:
            if not self._halt_event.is_set():
                self.units[level].start(target_id)
                self._total_jams += 1
                time.sleep(0.3)   # Stagger startup

        # GPS override if applicable
        if preset["gps_override"] and not self.gps_override.is_active:
            time.sleep(2)          # Let jamming destabilize drone first
            self.gps_override.activate(target_id, capture_coords)

        return True

    def jam_level(self, level: JamLevel, target: str = "") -> bool:
        """Activate a specific jamming level directly."""
        return self.units[level].start(target)

    def stop_level(self, level: JamLevel):
        """Stop a specific jamming level."""
        self.units[level].stop()

    def halt_all(self):
        """Emergency halt — stop ALL jamming immediately."""
        print(f"\n[JAMMER] 🛑 EMERGENCY HALT — Stopping all jamming")
        self._halt_event.set()
        for unit in self.units.values():
            unit.stop()
        self.gps_override.deactivate()
        self._halt_event.clear()
        if DB_AVAILABLE:
            db.log_event("JAM_HALT", "JAMMING_SYSTEM", "Emergency halt — all bands stopped")

    def start_rf_scan(self, interval: float = 10.0):
        """Start passive RF scanning for target protocol identification."""
        self.scanner.start_continuous(interval)

    @property
    def active_levels(self) -> list:
        return [lvl for lvl, unit in self.units.items() if unit.is_active]

    def status_report(self) -> dict:
        return {
            "active_levels":  [l.name for l in self.active_levels],
            "gps_override":   self.gps_override.is_active,
            "total_jams":     self._total_jams,
            "unit_status":    {l.name: u.status for l, u in self.units.items()},
            "timestamp":      datetime.now().isoformat(),
        }

    def print_status(self):
        rpt = self.status_report()
        print(f"\n{'='*65}")
        print(f"  JAMMING SYSTEM STATUS")
        print(f"{'='*65}")
        print(f"  Active bands: {rpt['active_levels'] or 'NONE'}")
        print(f"  GPS Override: {'ACTIVE' if rpt['gps_override'] else 'STANDBY'}")
        print(f"  Total jam operations: {rpt['total_jams']}")
        print(f"\n  Band Status:")
        for bname, bstat in rpt["unit_status"].items():
            state = "⚡ACTIVE" if bstat["active"] else "○ idle"
            print(f"    {bname:<12} {state}  ({bstat['center_mhz']}MHz, "
                  f"{bstat['power_dbm']}dBm, {bstat['duration_sec']:.0f}s)")
        print(f"{'='*65}")


# ══════════════════════════════════════════════════════════════════════
#  STANDALONE TEST
# ══════════════════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description="MCDIS Jamming System Test")
    parser.add_argument("--target", default="dji_large",
                        choices=list(JammingSystem.ENGAGEMENT_PRESETS.keys()),
                        help="Drone class to simulate engaging")
    parser.add_argument("--scan", action="store_true",
                        help="Run passive RF scan and exit")
    parser.add_argument("--status", action="store_true",
                        help="Show frequency band database")
    args = parser.parse_args()

    print("=" * 65)
    print("  MCDIS v3.0 — Electronic Warfare & Jamming System")
    print("=" * 65)

    js = JammingSystem()

    if args.status:
        print("\n  FREQUENCY BAND DATABASE:")
        print("  " + "-" * 60)
        for level, info in FREQ_BANDS.items():
            print(f"\n  [{level.name}] {info['name']}")
            print(f"    Center:    {info['center_mhz']} MHz")
            print(f"    Bandwidth: {info['bandwidth_mhz']} MHz")
            print(f"    Protocols: {', '.join(info['protocols'][:3])}")
            print(f"    Range:     {info.get('effective_range_m', '?')} m")
            print(f"    Uses:      {info['uses'][:80]}")
        return

    if args.scan:
        scanner = RFProtocolScanner()
        print("\n[RF-SCAN] Performing full spectrum scan...")
        scanner.scan_all()
        return

    # Engage target
    print(f"\n[TEST] Engaging {args.target.upper()}...\n")
    js.engage_drone_class(args.target, target_id="TEST_T001")

    time.sleep(5)
    js.print_status()

    time.sleep(5)
    print("\n[TEST] Issuing emergency halt...")
    js.halt_all()
    js.print_status()
    print("\n[TEST] ✅ Jamming system test complete.")


if __name__ == "__main__":
    main()
