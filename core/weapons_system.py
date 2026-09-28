import time
import math
import random
import logging
from database import db

log = logging.getLogger("WEAPONS-ENGINE")

# ── New system imports (safe — each has its own fallback) ────────────
try:
    from cyber_takeover   import get_cyber_system
    _CYBER_READY = True
except ImportError:
    _CYBER_READY = False

try:
    from quantum_jammer   import get_quantum_jammer
    _QJAM_READY = True
except ImportError:
    _QJAM_READY = False

try:
    from interceptor_chain import get_interceptor_chain
    _CHAIN_READY = True
except ImportError:
    _CHAIN_READY = False

try:
    from isr_precheck import get_isr_engine
    _ISR_READY = True
except ImportError:
    _ISR_READY = False

# ════════════════════════════════════════════════════════════════════════════
# ADVANCED WEAPON SYSTEMS ENGINE
# This module simulates the complex physics, mathematics, and tactical logic
# of military-grade Counter-UAS effectors (Soft Kill & Hard Kill).
# ════════════════════════════════════════════════════════════════════════════

class GNSS_Spoofer:
    """
    Simulates Advanced GPS, GLONASS, and BEIDOU spoofing.
    Rather than just blocking the signal (Jamming), spoofing involves
    synthesizing fake satellite ephemeris data to trick the drone's receiver.
    """
    def __init__(self):
        self.active_constellations = ['GPS_L1', 'GLONASS_G1', 'BEIDOU_B1']
        self.power_dbm = 45.0  # Transmission power

    def calculate_doppler_shift(self, target_velocity, satellite_velocity=3000):
        """Simulates the Doppler shift required to match satellite signals."""
        c = 299792458  # Speed of light
        return (target_velocity / c) * 1.57542e9  # L1 Carrier Frequency

    def deploy_spoofing(self, target_id, target_speed_kmh, distance_m, mode="SPOOF_RTH"):
        if distance_m > 5000:
            return {"status": "FAILED", "reason": "Target out of effective spoofing range (>5km)"}
            
        # Time required to lock onto target receiver tracking loops (Pull-off)
        lock_time = random.uniform(2.5, 4.5) 
        
        if mode == "DENIAL":
            effect = "GNSS Denial - Satellites Blocked. Target relying on IMU drift."
        elif mode == "FORCE_LAND":
            effect = "GPS Hijacked - Forcing safe landing at designated capture zone."
        else:
            effect = "Navigation Hijacked - Forcing Return-to-Home (RTH)."

        return {
            "status": "SUCCESS",
            "weapon": "GNSS_SPOOFER",
            "target": target_id,
            "mode": mode,
            "constellations_hijacked": self.active_constellations,
            "time_to_lock_seconds": round(lock_time, 2),
            "effect": effect
        }

class RF_Jammer:
    """
    Simulates a Multi-Band Broadband RF Jammer.
    Covers Command & Control (C2) links, Video streams, and GNSS bands.
    Uses J/S (Jammer-to-Signal) ratio physics.
    """
    def __init__(self):
        self.bands = {
            "900MHz":  {"power_w": 100, "threshold_db": 0},  # Telemetry / LoRa
            "1.5GHz":  {"power_w": 50,  "threshold_db": -5}, # GNSS (L1/L2)
            "2.4GHz":  {"power_w": 150, "threshold_db": 5},  # WiFi / C2
            "5.8GHz":  {"power_w": 150, "threshold_db": 10}  # Video Feed (FPV)
        }

    def calculate_jamming(self, distance_m, drone_type):
        # Inverse square law for free-space path loss (simplified)
        path_loss = 20 * math.log10(distance_m) if distance_m > 0 else 1
        
        results = {}
        links_broken = 0
        for band, specs in self.bands.items():
            # Calculate J/S at target
            js_ratio = (10 * math.log10(specs["power_w"])) - path_loss + 100 # Simulated received J/S
            
            # FHSS (Frequency Hopping) drones have higher processing gain (resistance)
            resistance = 15 if drone_type in ["MILITARY", "SHAHED_136"] else 0
            
            if js_ratio > (specs["threshold_db"] + resistance):
                results[band] = "LINK BROKEN"
                links_broken += 1
            else:
                results[band] = "RESISTED"
                
        return results, links_broken

    def fire(self, target_id, distance_m, drone_type="COMMERCIAL"):
        band_results, broken_count = self.calculate_jamming(distance_m, drone_type)
        
        if broken_count == 0:
            return {"status": "FAILED", "reason": "Target resisted all jamming frequencies (Out of range or highly shielded FHSS)."}
        
        effect = "C2 & Video links severed. Drone in Fail-Safe mode (Hover/Land)."
        if drone_type == "SHAHED_136":
            effect = "Telemetry jammed, but pre-programmed target maintains inertial course."

        return {
            "status": "SUCCESS",
            "weapon": "BROADBAND_JAMMER",
            "target": target_id,
            "bands_status": band_results,
            "effect": effect
        }


class DirectedEnergyWeapon:
    """
    Simulates a 50kW High-Energy Laser (HEL) Hard Kill system.
    Thermal dynamics model to melt plastic/carbon-fiber or burn optical sensors.
    """
    def __init__(self):
        self.beam_power_watts = 50000 
        self.beam_divergence_mrad = 0.5 

    def fire(self, target_id, distance_m, target_material="CARBON_FIBER"):
        if distance_m > 3000:
            return {"status": "FAILED", "reason": "Atmospheric scattering severe at this range. Target safe."}
            
        # Calculate spot size at distance (d * divergence)
        spot_radius = distance_m * (self.beam_divergence_mrad / 1000.0)
        spot_area_cm2 = math.pi * ((spot_radius * 100)**2)
        
        # Intensity = Power / Area
        irradiance = self.beam_power_watts / spot_area_cm2
        
        # Time to burn through 2mm of carbon fiber
        # Simplified specific heat capacity model
        burn_time = 1500 / irradiance if irradiance > 0 else float('inf')
        
        if burn_time < 5.0:
            return {
                "status": "SUCCESS", 
                "weapon": "DEW_LASER",
                "target": target_id,
                "irradiance_w_cm2": round(irradiance, 2),
                "burn_time_sec": round(burn_time, 2),
                "effect": "Critical structural failure. Target destroyed."
            }
        else:
             return {"status": "FAILED", "reason": "Insufficient thermal dwell time on target."}


class HighPowerMicrowave:
    """
    Simulates an EMP/HPM Hard Kill system (e.g., Epirus Leonidas).
    Fries internal electronics (Flight controller, ESCs) instantly.
    """
    def __init__(self):
        self.peak_power_gw = 1.0  # 1 Gigawatt peak pulse
        self.pulse_width_ns = 50
        
    def fire(self, target_id, distance_m, drone_type="SHAHED_136"):
        # EMP effectiveness drops with inverse square law
        electric_field_v_m = (math.sqrt(30 * self.peak_power_gw * 1e9)) / distance_m
        
        # Military drones like Shahed have shielding (Faraday cages)
        shielding_factor = 1000 if drone_type == "SHAHED_136" else 100
        
        effective_field = electric_field_v_m / shielding_factor
        
        # Threshold to fry unshielded commercial electronics is ~5000 V/m
        # Threshold for military is ~20000 V/m
        threshold = 20000 if drone_type == "SHAHED_136" else 5000
        
        if effective_field > threshold:
            return {
                "status": "SUCCESS",
                "weapon": "HPM_EMP",
                "target": target_id,
                "electric_field": round(electric_field_v_m, 2),
                "effect": "Avionics destroyed instantly. Target falling."
            }
        else:
             return {"status": "FAILED", "reason": f"Target shielding resisted {round(effective_field, 2)} V/m pulse."}


class WeaponsSystemEngine:
    def __init__(self):
        self.gnss       = GNSS_Spoofer()
        self.rf_jammer  = RF_Jammer()
        self.dew        = DirectedEnergyWeapon()
        self.hpm        = HighPowerMicrowave()

        # New advanced systems
        self._cyber   = get_cyber_system()   if _CYBER_READY  else None
        self._qjam    = get_quantum_jammer() if _QJAM_READY   else None
        self._chain   = get_interceptor_chain() if _CHAIN_READY else None
        self._isr     = get_isr_engine()     if _ISR_READY    else None

    # ── ISR Pre-Check (call BEFORE any engagement) ───────────────────
    def isr_check(self, target_speed_kmh: float, target_distance_km: float,
                  target_bearing: float = 45, target_type: str = "commercial",
                  threat_level: str = "THREAT") -> dict:
        """Run ISR Pre-Check and return system recommendation."""
        if self._isr:
            return self._isr.evaluate(
                target_speed_kmh=target_speed_kmh,
                target_distance_km=target_distance_km,
                target_bearing_deg=target_bearing,
                target_type=target_type,
                threat_level=threat_level,
            )
        return {"go_nogo": "GO", "isr_pct": 50.0,
                "recommended": "RF_JAMMING", "alternative": "GPS_SPOOFING"}

    # ── Main engagement dispatcher ───────────────────────────────────
    def engage_target(self, weapon_type, target_id, distance_m, target_type,
                      rf_strength: float = 60, target_speed_kmh: float = 80,
                      target_bearing: float = 45, extra: dict = None):
        result = {}
        extra  = extra or {}

        # ── Original systems ─────────────────────────────────────────
        if weapon_type == "GPS_SPOOFING":
            result = self.gnss.deploy_spoofing(target_id, 100, distance_m, mode="FORCE_LAND")
        elif weapon_type == "GNSS_DENIAL":
            result = self.gnss.deploy_spoofing(target_id, 100, distance_m, mode="DENIAL")
        elif weapon_type == "RF_JAMMING":
            result = self.rf_jammer.fire(target_id, distance_m, target_type)
        elif weapon_type == "DEW_LASER":
            result = self.dew.fire(target_id, distance_m)
        elif weapon_type == "HPM_MICROWAVE":
            result = self.hpm.fire(target_id, distance_m, target_type)

        # ── Cyber Takeover ───────────────────────────────────────────
        elif weapon_type in ("CYBER_TAKEOVER", "CYBER"):
            if self._cyber:
                result = self._cyber.execute(
                    target_id=target_id,
                    rf_strength=rf_strength,
                    distance_m=distance_m,
                    capture_lat=extra.get("capture_lat", 30.15),
                    capture_lon=extra.get("capture_lon", 31.45),
                )
                result.setdefault("status",  result.get("overall_status", "FAILED"))
                result.setdefault("effect",  result.get("mode_desc", "Cyber takeover attempted"))
            else:
                result = {"status": "FAILED", "reason": "Cyber Takeover module not loaded"}

        # ── Quantum Jammer ───────────────────────────────────────────
        elif weapon_type in ("QUANTUM_JAM", "QUANTUM"):
            if self._qjam:
                fhss = extra.get("fhss_pattern", "GENERIC_FHSS")
                result = self._qjam.jam(target_id, distance_m, fhss, target_type)
                result.setdefault("status", "SUCCESS" if result.get("effectiveness_pct", 0) > 50 else "FAILED")
            else:
                result = {"status": "FAILED", "reason": "Quantum Jammer module not loaded"}

        # ── Interceptor Chain ────────────────────────────────────────
        elif weapon_type in ("INTERCEPTOR_CHAIN", "INTERCEPTOR"):
            if self._chain:
                chain_result = self._chain.run_chain(
                    target_id=target_id,
                    target_speed_kmh=target_speed_kmh,
                    target_distance_km=distance_m / 1000.0,
                    target_bearing_deg=target_bearing,
                    target_x=extra.get("target_x", distance_m * 0.7),
                    target_y=extra.get("target_y", distance_m * 0.3),
                    target_type=target_type,
                    async_dispatch=True,
                )
                result = {
                    "status":  "SUCCESS" if chain_result["final_status"] == "LAUNCHED" else "FAILED",
                    "weapon":  "INTERCEPTOR_CHAIN",
                    "target":  target_id,
                    "effect":  f"Chain status: {chain_result['final_status']}",
                    "chain":   chain_result,
                }
            else:
                result = {"status": "FAILED", "reason": "Interceptor Chain module not loaded"}

        # ── ISR Pre-Check (engagement info only) ─────────────────────
        elif weapon_type in ("ISR_PRECHECK", "ISR"):
            isr = self.isr_check(target_speed_kmh, distance_m / 1000.0,
                                 target_bearing, target_type)
            result = {
                "status":  "SUCCESS",
                "weapon":  "ISR_PRECHECK",
                "target":  target_id,
                "effect":  f"ISR: {isr['isr_pct']:.0f}% | Recommended: {isr['recommended']}",
                "isr":     isr,
            }

        else:
            result = {"status": "FAILED", "reason": f"Unknown Weapon System: {weapon_type}"}

        # ── Log to DB ────────────────────────────────────────────────
        try:
            db.log_command(weapon_type, target_id, result.get("status", "UNKNOWN"))
            db.log_event("WEAPON_ENGAGEMENT", weapon_type,
                         f"Target: {target_id} | Result: {result.get('effect', result.get('reason', ''))}")
        except Exception as e:
            log.warning(f"DB log failed: {e}")

        return result

    def system_status(self) -> dict:
        return {
            "cyber_takeover":    _CYBER_READY,
            "quantum_jammer":    _QJAM_READY,
            "interceptor_chain": _CHAIN_READY,
            "isr_precheck":      _ISR_READY,
            "classic_systems":   ["GPS_SPOOFING", "GNSS_DENIAL", "RF_JAMMING", "DEW_LASER", "HPM_MICROWAVE"],
        }


weapons_engine = WeaponsSystemEngine()

