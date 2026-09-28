# -*- coding: utf-8 -*-
"""
MCDIS -- Cyber Takeover System v1.0
3-Phase drone hijacking: Signal Intercept -> Protocol Crack -> Command Inject
Based on: IET Cybersecurity 2025
"""

import math, time, random, threading, logging
import numpy as np

log = logging.getLogger("CYBER-TAKEOVER")
log.setLevel(logging.INFO)

PROTOCOL_PROFILES = {
    "DJI_OCUSYNC":     {"frequencies_mhz":[2400,5800], "encryption":"AES-128",  "crack_time_sec":(3.5,8.0),   "success_rate":0.82, "takeover_mode":"GPS_REDIRECT", "notes":"OcuSync 2.0/3.0 partial vuln"},
    "DJI_LIGHTBRIDGE": {"frequencies_mhz":[2400],       "encryption":"AES-256",  "crack_time_sec":(8.0,18.0),  "success_rate":0.61, "takeover_mode":"FORCE_LAND",   "notes":"LightBridge replay attack"},
    "MAVLINK_V1":      {"frequencies_mhz":[433,915,2400],"encryption":"NONE",    "crack_time_sec":(0.5,2.0),   "success_rate":0.97, "takeover_mode":"FULL_CONTROL", "notes":"No auth -- trivial takeover"},
    "MAVLINK_V2":      {"frequencies_mhz":[433,915,2400],"encryption":"MAVLink", "crack_time_sec":(4.0,10.0),  "success_rate":0.74, "takeover_mode":"FULL_CONTROL", "notes":"Signing key timing attack"},
    "CUSTOM_MILITARY": {"frequencies_mhz":[433,1200,2400],"encryption":"MIL",    "crack_time_sec":(30.0,90.0), "success_rate":0.18, "takeover_mode":"PARTIAL",      "notes":"Military-grade, low success"},
    "UNKNOWN":         {"frequencies_mhz":[2400,5800],   "encryption":"UNKNOWN", "crack_time_sec":(5.0,20.0),  "success_rate":0.45, "takeover_mode":"FORCE_LAND",   "notes":"Protocol fingerprinting needed"},
}

TAKEOVER_MODES = {
    "FULL_CONTROL":  "Complete takeover -- we are the pilot",
    "GPS_REDIRECT":  "Override GPS -- redirect to capture zone",
    "FORCE_LAND":    "Send immediate land command",
    "PARTIAL":       "Partial injection -- disrupt navigation",
}


class SignalInterceptor:
    def __init__(self):
        self.sensitivity_dbm = -95.0

    def intercept(self, target_id, rf_strength, distance_m):
        fspl = 20 * math.log10(max(distance_m, 1)) + 20 * math.log10(2400e6) - 147.55
        received_dbm = -30 + rf_strength * 0.6 - fspl * 0.01
        locked = received_dbm > self.sensitivity_dbm and rf_strength > 15

        if not locked:
            return {"phase":1, "status":"FAILED", "reason": f"Signal too weak ({received_dbm:.1f} dBm)",
                    "snr_db": round(received_dbm - self.sensitivity_dbm, 1)}

        protocol = "DJI_OCUSYNC" if rf_strength > 80 else ("MAVLINK_V1" if rf_strength > 50 else "UNKNOWN")
        snr = round(received_dbm - self.sensitivity_dbm, 1)
        return {
            "phase":1, "status":"SUCCESS", "target_id":target_id, "protocol":protocol,
            "received_dbm":round(received_dbm,1), "snr_db":snr,
            "frequencies":PROTOCOL_PROFILES[protocol]["frequencies_mhz"],
            "encryption":PROTOCOL_PROFILES[protocol]["encryption"],
            "lock_time_sec":round(random.uniform(0.3,1.5),2),
        }


class ProtocolCracker:
    ATTACK_METHODS = {
        "NONE":    "Direct injection (no encryption)",
        "AES-128": "Timing side-channel on AES key",
        "AES-256": "Replay attack + nonce prediction",
        "MAVLink": "HMAC-SHA256 timing attack",
        "MIL":     "FPGA brute-force (low success)",
        "UNKNOWN": "Protocol fuzzing + replay",
    }

    def crack(self, intercept_result):
        if intercept_result.get("status") != "SUCCESS":
            return {"phase":2, "status":"SKIPPED", "reason":"Phase 1 failed"}

        protocol = intercept_result["protocol"]
        profile  = PROTOCOL_PROFILES[protocol]
        enc      = profile["encryption"]
        t_min, t_max = profile["crack_time_sec"]
        success  = random.random() < profile["success_rate"]

        return {
            "phase":2, "status":"SUCCESS" if success else "PARTIAL",
            "protocol":protocol, "encryption":enc,
            "attack_method":self.ATTACK_METHODS.get(enc,"Unknown"),
            "crack_time_sec":round(random.uniform(t_min,t_max),2),
            "success_rate":f"{profile['success_rate']*100:.0f}%",
            "takeover_mode":profile["takeover_mode"],
            "notes":profile["notes"],
        }


class CommandInjector:
    COMMANDS = {
        "FULL_CONTROL":  ["SET_PILOT_ME","DISABLE_RTH","ACCEPT_WAYPOINTS"],
        "GPS_REDIRECT":  ["OVERRIDE_WAYPOINT","SET_DESTINATION_CAPTURE"],
        "FORCE_LAND":    ["SEND_LAND_CMD","DISABLE_MOTORS_SOFT"],
        "PARTIAL":       ["CORRUPT_NAV_DATA","INJECT_NOISE"],
    }

    def inject(self, crack_result, target_id, capture_lat=30.0, capture_lon=31.0):
        if crack_result.get("status") == "SKIPPED":
            return {"phase":3, "status":"SKIPPED"}

        mode     = crack_result.get("takeover_mode","FORCE_LAND")
        success  = crack_result["status"] == "SUCCESS"
        if not success:
            mode = "PARTIAL"

        commands = self.COMMANDS.get(mode, ["SEND_LAND_CMD"])
        hijack_conf = round(random.uniform(0.7,0.98) if success else random.uniform(0.1,0.4), 2)

        return {
            "phase":3, "status":"SUCCESS" if success else "PARTIAL",
            "target_id":target_id, "mode":mode,
            "mode_desc":TAKEOVER_MODES.get(mode,""),
            "commands_sent":commands,
            "inject_time_sec":round(random.uniform(0.2,1.8),2),
            "hijack_confidence":hijack_conf,
            "capture_zone":{"lat":capture_lat,"lon":capture_lon},
            "drone_response":"COMPLYING" if success else "RESISTING",
        }


class CyberTakeoverSystem:
    def __init__(self):
        self.interceptor = SignalInterceptor()
        self.cracker     = ProtocolCracker()
        self.injector    = CommandInjector()
        self._active     = {}
        self._lock       = threading.Lock()
        log.info("Cyber Takeover System ready")

    def execute(self, target_id, rf_strength, distance_m,
                capture_lat=30.0, capture_lon=31.0,
                async_mode=False, on_complete=None):
        t0 = time.time()
        p1 = self.interceptor.intercept(target_id, rf_strength, distance_m)
        p2 = self.cracker.crack(p1)
        p3 = self.injector.inject(p2, target_id, capture_lat, capture_lon)

        overall = "SUCCESS"
        if p1['status'] == "FAILED":        overall = "FAILED"
        elif p2['status'] == "PARTIAL" or p3.get('status') == "PARTIAL": overall = "PARTIAL"

        hijack_conf = p3.get("hijack_confidence", 0)
        result = {
            "target_id":target_id, "overall_status":overall,
            "hijack_confidence":hijack_conf,
            "takeover_mode":p3.get("mode","NONE"),
            "mode_desc":p3.get("mode_desc",""),
            "phases":{"1_INTERCEPT":p1,"2_CRACK":p2,"3_INJECT":p3},
            "total_time_sec":round(time.time()-t0 + p2.get("crack_time_sec",0) + p3.get("inject_time_sec",0),2),
            "timestamp":time.strftime("%H:%M:%S"),
        }
        with self._lock:
            self._active[target_id] = result
        if on_complete:
            on_complete(result)
        log.info(f"[CYBER] {target_id} -> {overall} | Mode: {p3.get('mode')} | Conf: {hijack_conf:.0%}")
        return result

    def get_status(self, target_id=None):
        with self._lock:
            if target_id: return self._active.get(target_id, {})
            return dict(self._active)


_cyber_instance = None

def get_cyber_system():
    global _cyber_instance
    if _cyber_instance is None:
        _cyber_instance = CyberTakeoverSystem()
    return _cyber_instance


if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    print("=" * 65)
    print("  MCDIS Cyber Takeover -- Standalone Test")
    print("=" * 65)
    sys_ = CyberTakeoverSystem()
    tests = [
        {"id":"T-001","rf":85,"dist":800,  "label":"DJI Mavic (close)"},
        {"id":"T-002","rf":55,"dist":2000, "label":"Unknown (medium)"},
        {"id":"T-003","rf":5, "dist":6000, "label":"Out of range"},
    ]
    for tc in tests:
        r = sys_.execute(tc['id'], tc['rf'], tc['dist'])
        print(f"\n  {tc['label']}")
        print(f"    Overall:    {r['overall_status']}")
        print(f"    Mode:       {r['takeover_mode']}")
        print(f"    Confidence: {r['hijack_confidence']:.0%}")
    print("\n[OK] Cyber Takeover test complete.")
