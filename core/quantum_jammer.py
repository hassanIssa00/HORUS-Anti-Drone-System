# -*- coding: utf-8 -*-
"""
MCDIS — Quantum Jammer System v1.0
تشويش كل الترددات في نفس الوقت — للدرونات العسكرية المتطورة
Based on: Quantum Radar Research — University of Birmingham
"""

import math, time, random, threading, logging
import numpy as np

log = logging.getLogger("QUANTUM-JAM")
log.setLevel(logging.INFO)

# ══════════════════════════════════════════════════════════════════════
#  FREQUENCY BANDS
# ══════════════════════════════════════════════════════════════════════

FREQUENCY_BANDS = {
    "UHF_433":    {"freq_mhz": 433,    "use": "LoRa/telemetry",    "power_w": 20},
    "UHF_900":    {"freq_mhz": 900,    "use": "LoRa/RC",           "power_w": 25},
    "L_1200":     {"freq_mhz": 1200,   "use": "RC long range",     "power_w": 30},
    "GPS_L1":     {"freq_mhz": 1575,   "use": "GPS L1",            "power_w": 15},
    "GPS_L2":     {"freq_mhz": 1227,   "use": "GPS L2",            "power_w": 15},
    "S_2400":     {"freq_mhz": 2400,   "use": "WiFi/DJI C2",       "power_w": 100},
    "S_2450":     {"freq_mhz": 2450,   "use": "Bluetooth/Zigbee",  "power_w": 50},
    "C_5800":     {"freq_mhz": 5800,   "use": "DJI video/5GHz",    "power_w": 80},
}

FHSS_PATTERNS = {
    "DJI_OCUSYNC": {
        "hop_rate_hz":    200,
        "channels":       100,
        "bandwidth_mhz":  20,
        "defeat_method":  "SWEEP_FOLLOW",
    },
    "MILITARY_FHSS": {
        "hop_rate_hz":    1000,
        "channels":       500,
        "bandwidth_mhz":  100,
        "defeat_method":  "BARRAGE",
    },
    "GENERIC_FHSS": {
        "hop_rate_hz":    50,
        "channels":       40,
        "bandwidth_mhz":  10,
        "defeat_method":  "SWEEP_FOLLOW",
    },
}


class QuantumJammer:
    """
    All-frequency sweep jammer.
    Defeats FHSS (Frequency Hopping Spread Spectrum) drones
    that evade conventional single-frequency jammers.

    Normal RF Jammer: blocks ONE frequency at a time
    Quantum Jammer  : sweeps ALL frequencies simultaneously
    """

    def __init__(self):
        self.total_power_w  = 500.0
        self.sweep_speed_ghz_per_sec = 12.0
        self.quantum_noise_enabled   = True
        log.info("Quantum Jammer initialized ✓")

    def _calculate_js_ratio(self, freq_mhz: float, distance_m: float, power_w: float) -> float:
        """J/S ratio at target (dB). >0 = effective jamming."""
        # Free-space path loss simplified (in dB)
        fspl = 20 * math.log10(max(distance_m, 1)) + 20 * math.log10(freq_mhz * 1e6) - 147.55
        # Jammer EIRP in dBm (assume 12 dBi antenna gain)
        jammer_eirp_dbm = 10 * math.log10(power_w * 1000) + 12
        # Drone receiver sensitivity assumed -90 dBm, signal at -70 dBm
        drone_signal_dbm = -70.0
        # J/S = jammer_received - drone_signal
        jammer_received = jammer_eirp_dbm - fspl
        return jammer_received - drone_signal_dbm

    def _defeat_fhss(self, pattern_name: str, distance_m: float) -> dict:
        profile    = FHSS_PATTERNS.get(pattern_name, FHSS_PATTERNS["GENERIC_FHSS"])
        hop_rate   = profile["hop_rate_hz"]
        channels   = profile["channels"]
        method     = profile["defeat_method"]

        sweep_time_per_ch = 1.0 / max(self.sweep_speed_ghz_per_sec * 1000 / channels, 0.001)

        if method == "SWEEP_FOLLOW":
            dwell_ms        = 1000.0 / hop_rate
            our_dwell_ms    = sweep_time_per_ch * 1000
            catch_prob      = min(dwell_ms / max(our_dwell_ms, 0.001), 1.0) * 0.9
        else:  # BARRAGE
            power_per_ch = self.total_power_w / channels
            js_each      = self._calculate_js_ratio(2400, distance_m, power_per_ch)
            catch_prob   = min(max((js_each + 10) / 30, 0), 0.85)

        return {
            "pattern":       pattern_name,
            "method":        method,
            "hop_rate_hz":   hop_rate,
            "channels":      channels,
            "catch_prob_pct": round(catch_prob * 100, 1),
            "effective":     catch_prob > 0.4,
        }

    def jam(self, target_id: str, distance_m: float,
            fhss_pattern: str = "GENERIC_FHSS",
            target_type: str = "commercial") -> dict:
        """
        Execute quantum jamming sweep.
        """
        t0 = time.time()

        if distance_m > 6000:
            return {
                "status":  "FAILED",
                "reason":  f"Target at {distance_m/1000:.1f}km — beyond effective range (6km)",
                "target":  target_id,
            }

        # Per-band jamming
        band_results = {}
        # Log-weighted power allocation: higher power to primary control bands
        weights = {"S_2400": 3, "C_5800": 3, "S_2450": 2, "GPS_L1": 1.5,
                   "GPS_L2": 1.5, "UHF_433": 1, "UHF_900": 1, "L_1200": 1}
        total_w = sum(weights.values())

        for band_name, band in FREQUENCY_BANDS.items():
            w = weights.get(band_name, 1)
            allocated_power = self.total_power_w * (w / total_w)
            js  = self._calculate_js_ratio(band["freq_mhz"], distance_m, allocated_power)
            # Effective if J/S > 6 dB (standard threshold)
            eff = js > 6.0
            band_results[band_name] = {
                "freq_mhz":      band["freq_mhz"],
                "power_w":       round(allocated_power, 1),
                "js_db":         round(js, 1),
                "effective":     eff,
                "use":           band["use"],
            }

        bands_jammed = sum(1 for b in band_results.values() if b["effective"])

        # FHSS defeat
        fhss_result = self._defeat_fhss(fhss_pattern, distance_m)

        # Military shielding factor
        shield = 15 if "military" in target_type.lower() else 0
        overall_eff = max(0, (bands_jammed / len(FREQUENCY_BANDS)) * 100 - shield)

        if self.quantum_noise_enabled:
            overall_eff = min(overall_eff + 8, 100)

        status = "SUCCESS" if overall_eff > 50 else ("PARTIAL" if overall_eff > 20 else "FAILED")

        effect = ""
        if status == "SUCCESS":
            effect = "All C2 links severed. Target in fail-safe / autonomous mode."
        elif status == "PARTIAL":
            effect = "Primary links disrupted. Target degraded — may continue on inertial."
        else:
            effect = "Target resisted quantum sweep — military-grade shielding confirmed."

        return {
            "status":          status,
            "weapon":          "QUANTUM_JAM",
            "target":          target_id,
            "distance_m":      distance_m,
            "bands_jammed":    bands_jammed,
            "total_bands":     len(FREQUENCY_BANDS),
            "effectiveness_pct": round(overall_eff, 1),
            "fhss_defeat":     fhss_result,
            "band_results":    band_results,
            "effect":          effect,
            "calc_time_ms":    round((time.time() - t0) * 1000, 1),
            "timestamp":       time.strftime("%H:%M:%S"),
        }

    def status(self) -> dict:
        return {
            "ready":             True,
            "total_power_w":     self.total_power_w,
            "bands_covered":     len(FREQUENCY_BANDS),
            "sweep_speed":       f"{self.sweep_speed_ghz_per_sec} GHz/s",
            "quantum_noise":     self.quantum_noise_enabled,
            "effective_range_km": 6.0,
        }


_qjam_instance = None

def get_quantum_jammer() -> QuantumJammer:
    global _qjam_instance
    if _qjam_instance is None:
        _qjam_instance = QuantumJammer()
    return _qjam_instance


if __name__ == "__main__":
    print("=" * 65)
    print("  MCDIS Quantum Jammer — Standalone Test")
    print("=" * 65)

    jammer = QuantumJammer()

    tests = [
        {"id": "T-001", "dist": 800,  "fhss": "DJI_OCUSYNC",   "type": "commercial", "label": "DJI FPV"},
        {"id": "T-002", "dist": 2500, "fhss": "MILITARY_FHSS",  "type": "military",   "label": "Military FHSS Drone"},
        {"id": "T-003", "dist": 5000, "fhss": "GENERIC_FHSS",   "type": "commercial", "label": "Long-Range Drone"},
        {"id": "T-004", "dist": 7000, "fhss": "GENERIC_FHSS",   "type": "commercial", "label": "Out of Range"},
    ]

    for t in tests:
        r = jammer.jam(t["id"], t["dist"], t["fhss"], t["type"])
        print(f"\n  {t['label']:30s} | Dist: {t['dist']/1000:.1f}km")
        print(f"    Status:        {r['status']}")
        print(f"    Effectiveness: {r.get('effectiveness_pct', 0):.0f}%")
        print(f"    Bands Jammed:  {r.get('bands_jammed', 0)}/{r.get('total_bands', 0)}")
        if "fhss_defeat" in r:
            fd = r["fhss_defeat"]
            print(f"    FHSS Defeat:   {fd['catch_prob_pct']:.0f}% ({fd['method']})")
        print(f"    Effect:        {r.get('effect', r.get('reason', ''))}")

    print("\n✅ Quantum Jammer test complete.")
