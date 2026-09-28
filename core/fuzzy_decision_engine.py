# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║  MCDIS — Fuzzy Logic Decision Engine v1.0                           ║
║  محرك اتخاذ القرار بالمنطق الضبابي                                   ║
╠══════════════════════════════════════════════════════════════════════╣
║  Inputs (10 sensors):                                                ║
║    Radar   : distance, speed, altitude, rcs                          ║
║    Camera  : camera_confidence, object_size                          ║
║    RF      : rf_signal_strength, rf_protocol_risk                    ║
║    Acoustic: acoustic_match                                          ║
║    Kinematic: movement_directedness                                  ║
║                                                                      ║
║  Outputs:                                                            ║
║    threat_level  : 0–100  (SAFE / SUSPICIOUS / THREAT / CRITICAL)   ║
║    action_score  : 0–100  (maps to best countermeasure)             ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import numpy as np
import logging
import time

log = logging.getLogger("FUZZY-ENGINE")
log.setLevel(logging.INFO)

# ── Try importing scikit-fuzzy ──────────────────────────────────────
try:
    import skfuzzy as fuzz
    from skfuzzy import control as ctrl
    SKFUZZY_AVAILABLE = True
except ImportError:
    SKFUZZY_AVAILABLE = False
    log.warning("[FUZZY] scikit-fuzzy not found — using NumPy fallback mode")


# ══════════════════════════════════════════════════════════════════════
#  THREAT & ACTION THRESHOLDS
# ══════════════════════════════════════════════════════════════════════

THREAT_LABELS = {
    (0,  25):  ("SAFE",       "#00FF88"),
    (25, 50):  ("SUSPICIOUS", "#FFCC00"),
    (50, 75):  ("THREAT",     "#FF6600"),
    (75, 101): ("CRITICAL",   "#FF0000"),
}

ACTION_MAP = {
    # threat_level → action
    (0,  20):  "NONE",
    (20, 35):  "MONITOR",
    (35, 50):  "JAM_RF",
    (50, 60):  "GPS_SPOOF",
    (60, 70):  "ACOUSTIC_ATTACK",
    (70, 80):  "INTERCEPTOR_CHAIN",
    (80, 90):  "LASER_DEW",
    (90, 101): "CRITICAL_ENGAGE",
}

RESPONSE_MAP = {
    "NONE":              "No action required",
    "MONITOR":           "Track and monitor — insufficient threat",
    "JAM_RF":            "RF control link jamming on 2.4/5.8 GHz",
    "GPS_SPOOF":         "GPS spoofing — force Return-to-Home",
    "ACOUSTIC_ATTACK":   "Acoustic resonance on MEMS gyroscope",
    "INTERCEPTOR_CHAIN": "Deploy interceptor drone — precision capture",
    "LASER_DEW":         "Directed energy laser — surgical strike",
    "CRITICAL_ENGAGE":   "CRITICAL: Multi-system simultaneous engagement",
}


# ══════════════════════════════════════════════════════════════════════
#  FUZZY SYSTEM BUILDER (scikit-fuzzy)
# ══════════════════════════════════════════════════════════════════════

def _build_fuzzy_system():
    """Build and return the compiled fuzzy control system."""

    # ── Antecedents (Inputs) ─────────────────────────────────────────
    distance    = ctrl.Antecedent(np.arange(0, 21,  0.1),  'distance')    # km
    speed       = ctrl.Antecedent(np.arange(0, 501, 1),    'speed')        # km/h
    altitude    = ctrl.Antecedent(np.arange(0, 3001, 1),   'altitude')     # m
    rcs         = ctrl.Antecedent(np.arange(0, 3,   0.01), 'rcs')          # 0=small,1=med,2=large
    cam_conf    = ctrl.Antecedent(np.arange(0, 101, 1),    'cam_conf')     # %
    rf_strength = ctrl.Antecedent(np.arange(0, 101, 1),    'rf_strength')  # 0=none,100=strong
    rf_risk     = ctrl.Antecedent(np.arange(0, 101, 1),    'rf_risk')      # 0=known,100=military
    acoustic    = ctrl.Antecedent(np.arange(0, 2,   0.01), 'acoustic')     # 0=no,1=yes
    movement    = ctrl.Antecedent(np.arange(0, 101, 1),    'movement')     # 0=random,100=directed
    obj_size    = ctrl.Antecedent(np.arange(0, 101, 1),    'obj_size')     # 0=tiny,100=large

    # ── Consequents (Outputs) ────────────────────────────────────────
    threat      = ctrl.Consequent(np.arange(0, 101, 1), 'threat',      defuzzify_method='centroid')
    action_sc   = ctrl.Consequent(np.arange(0, 101, 1), 'action_sc',   defuzzify_method='centroid')

    # ── Membership Functions — Distance ──────────────────────────────
    distance['close']  = fuzz.trapmf(distance.universe, [0, 0, 2, 4])
    distance['medium'] = fuzz.trimf(distance.universe,  [3, 8, 13])
    distance['far']    = fuzz.trapmf(distance.universe, [10, 15, 20, 20])

    # ── Speed ────────────────────────────────────────────────────────
    speed['slow']   = fuzz.trapmf(speed.universe, [0, 0, 40, 80])
    speed['medium'] = fuzz.trimf(speed.universe,  [60, 150, 250])
    speed['fast']   = fuzz.trimf(speed.universe,  [200, 350, 450])
    speed['hyper']  = fuzz.trapmf(speed.universe, [350, 430, 500, 500])

    # ── Altitude ─────────────────────────────────────────────────────
    altitude['low']    = fuzz.trapmf(altitude.universe, [0, 0, 100, 200])
    altitude['medium'] = fuzz.trimf(altitude.universe,  [150, 500, 1000])
    altitude['high']   = fuzz.trapmf(altitude.universe, [800, 1500, 3000, 3000])

    # ── RCS ──────────────────────────────────────────────────────────
    rcs['small']  = fuzz.trimf(rcs.universe, [0, 0, 0.8])
    rcs['medium'] = fuzz.trimf(rcs.universe, [0.5, 1.0, 1.5])
    rcs['large']  = fuzz.trimf(rcs.universe, [1.2, 2.0, 2.0])

    # ── Camera Confidence ────────────────────────────────────────────
    cam_conf['low']    = fuzz.trapmf(cam_conf.universe, [0, 0, 30, 50])
    cam_conf['medium'] = fuzz.trimf(cam_conf.universe,  [40, 65, 80])
    cam_conf['high']   = fuzz.trapmf(cam_conf.universe, [70, 85, 100, 100])

    # ── RF Signal Strength ───────────────────────────────────────────
    rf_strength['none']   = fuzz.trapmf(rf_strength.universe, [0, 0, 10, 20])
    rf_strength['weak']   = fuzz.trimf(rf_strength.universe,  [10, 35, 55])
    rf_strength['strong'] = fuzz.trapmf(rf_strength.universe, [45, 65, 100, 100])

    # ── RF Protocol Risk ─────────────────────────────────────────────
    rf_risk['known']    = fuzz.trapmf(rf_risk.universe, [0, 0, 20, 40])
    rf_risk['suspect']  = fuzz.trimf(rf_risk.universe,  [30, 55, 75])
    rf_risk['military'] = fuzz.trapmf(rf_risk.universe, [65, 80, 100, 100])

    # ── Acoustic Match ───────────────────────────────────────────────
    acoustic['no']  = fuzz.trimf(acoustic.universe, [0, 0, 0.5])
    acoustic['yes'] = fuzz.trimf(acoustic.universe, [0.5, 1, 1])

    # ── Movement (0=random/bird, 100=directed/kamikaze) ──────────────
    movement['random']   = fuzz.trapmf(movement.universe, [0, 0, 20, 40])
    movement['loiter']   = fuzz.trimf(movement.universe,  [30, 55, 70])
    movement['directed'] = fuzz.trapmf(movement.universe, [60, 80, 100, 100])

    # ── Object Size ──────────────────────────────────────────────────
    obj_size['tiny']   = fuzz.trapmf(obj_size.universe, [0, 0, 15, 30])
    obj_size['medium'] = fuzz.trimf(obj_size.universe,  [20, 50, 75])
    obj_size['large']  = fuzz.trapmf(obj_size.universe, [65, 80, 100, 100])

    # ── Threat MFs ───────────────────────────────────────────────────
    threat['safe']       = fuzz.trapmf(threat.universe, [0, 0, 15, 25])
    threat['suspicious'] = fuzz.trimf(threat.universe,  [20, 37, 52])
    threat['threat']     = fuzz.trimf(threat.universe,  [45, 62, 78])
    threat['critical']   = fuzz.trapmf(threat.universe, [72, 85, 100, 100])

    # ── Action Score MFs ─────────────────────────────────────────────
    action_sc['none']        = fuzz.trapmf(action_sc.universe, [0, 0, 15, 25])
    action_sc['soft_kill']   = fuzz.trimf(action_sc.universe,  [20, 42, 60])
    action_sc['hard_kill']   = fuzz.trimf(action_sc.universe,  [55, 72, 85])
    action_sc['critical']    = fuzz.trapmf(action_sc.universe, [80, 90, 100, 100])

    # ══════════════════════════════════════════════════════════════════
    #  FUZZY RULES
    # ══════════════════════════════════════════════════════════════════
    rules = [
        # ── SAFE rules ───────────────────────────────────────────────
        ctrl.Rule(movement['random'] & cam_conf['low'] & rf_strength['none'],
                  [threat['safe'], action_sc['none']]),

        ctrl.Rule(movement['random'] & acoustic['no'],
                  [threat['safe'], action_sc['none']]),

        ctrl.Rule(distance['far'] & speed['slow'] & rf_strength['none'],
                  [threat['safe'], action_sc['none']]),

        # ── SUSPICIOUS rules ──────────────────────────────────────────
        ctrl.Rule(distance['medium'] & rf_strength['weak'],
                  [threat['suspicious'], action_sc['soft_kill']]),

        ctrl.Rule(cam_conf['medium'] & movement['loiter'],
                  [threat['suspicious'], action_sc['soft_kill']]),

        ctrl.Rule(rf_risk['suspect'] & distance['medium'],
                  [threat['suspicious'], action_sc['soft_kill']]),

        ctrl.Rule(acoustic['yes'] & cam_conf['medium'],
                  [threat['suspicious'], action_sc['soft_kill']]),

        # ── THREAT rules ──────────────────────────────────────────────
        ctrl.Rule(distance['close'] & speed['medium'] & cam_conf['medium'],
                  [threat['threat'], action_sc['hard_kill']]),

        ctrl.Rule(rf_risk['military'] & rf_strength['strong'],
                  [threat['threat'], action_sc['hard_kill']]),

        ctrl.Rule(movement['directed'] & distance['medium'] & cam_conf['high'],
                  [threat['threat'], action_sc['hard_kill']]),

        ctrl.Rule(acoustic['yes'] & movement['directed'] & cam_conf['high'],
                  [threat['threat'], action_sc['hard_kill']]),

        ctrl.Rule(speed['fast'] & distance['close'],
                  [threat['threat'], action_sc['hard_kill']]),

        ctrl.Rule(rcs['small'] & rf_risk['military'] & movement['directed'],
                  [threat['threat'], action_sc['hard_kill']]),

        # ── CRITICAL rules ────────────────────────────────────────────
        ctrl.Rule(distance['close'] & speed['fast'] & movement['directed'],
                  [threat['critical'], action_sc['critical']]),

        ctrl.Rule(distance['close'] & speed['hyper'],
                  [threat['critical'], action_sc['critical']]),

        ctrl.Rule(rcs['small'] & speed['hyper'] & movement['directed'],
                  [threat['critical'], action_sc['critical']]),

        ctrl.Rule(rf_risk['military'] & movement['directed'] & distance['close'],
                  [threat['critical'], action_sc['critical']]),

        ctrl.Rule(cam_conf['high'] & speed['fast'] & movement['directed'] & distance['close'],
                  [threat['critical'], action_sc['critical']]),

        ctrl.Rule(acoustic['yes'] & rf_risk['military'] & movement['directed'],
                  [threat['critical'], action_sc['critical']]),
    ]

    system = ctrl.ControlSystem(rules)
    return ctrl.ControlSystemSimulation(system)


# ══════════════════════════════════════════════════════════════════════
#  NUMPY FALLBACK (no scikit-fuzzy)
# ══════════════════════════════════════════════════════════════════════

def _numpy_fallback(inputs: dict) -> dict:
    """Rule-based approximation of fuzzy logic using NumPy."""
    d  = inputs.get('distance', 10)          # km
    s  = inputs.get('speed', 50)             # km/h
    cc = inputs.get('cam_conf', 50)          # %
    rf = inputs.get('rf_strength', 0)        # 0-100
    rr = inputs.get('rf_risk', 0)            # 0-100
    mv = inputs.get('movement', 50)          # 0-100
    ac = inputs.get('acoustic', 0)           # 0-1

    score = 0.0

    # Distance contribution (closer = more threat)
    score += np.interp(d,  [0, 3, 10, 20], [40, 35, 10, 0])
    # Speed contribution
    score += np.interp(s,  [0, 80, 200, 400], [0, 5, 20, 35])
    # Camera confidence
    score += np.interp(cc, [0, 40, 70, 100], [0, 5, 15, 20])
    # RF signal
    score += np.interp(rf, [0, 20, 60, 100], [0, 3, 10, 15])
    # RF risk
    score += np.interp(rr, [0, 30, 70, 100], [0, 5, 15, 20])
    # Movement directedness
    score += np.interp(mv, [0, 30, 70, 100], [0, 2, 10, 15])
    # Acoustic
    score += ac * 10

    score = float(np.clip(score, 0, 100))
    return {"threat_score": score, "method": "NUMPY_FALLBACK"}


# ══════════════════════════════════════════════════════════════════════
#  MAIN FUZZY ENGINE CLASS
# ══════════════════════════════════════════════════════════════════════

class FuzzyDecisionEngine:
    """
    Fuzzy Logic inference engine for threat evaluation.

    Usage:
        engine = FuzzyDecisionEngine()
        result = engine.evaluate({
            'distance': 2.5,      # km
            'speed': 230,         # km/h
            'altitude': 150,      # m
            'rcs': 0.3,           # 0=small, 2=large
            'cam_conf': 92,       # %
            'obj_size': 65,       # 0-100
            'rf_strength': 80,    # 0-100
            'rf_risk': 90,        # 0=known, 100=military
            'acoustic': 1,        # 0/1
            'movement': 88,       # 0=random, 100=directed
        })
        # → {'threat_level': 'CRITICAL', 'threat_score': 91.2,
        #    'action': 'INTERCEPTOR_CHAIN', 'confidence': 0.91}
    """

    def __init__(self):
        self._sim = None
        self._ready = False
        if SKFUZZY_AVAILABLE:
            try:
                log.info("Building Fuzzy Control System...")
                t0 = time.time()
                self._sim = _build_fuzzy_system()
                log.info(f"Fuzzy system ready in {time.time()-t0:.2f}s ✓")
                self._ready = True
            except Exception as e:
                log.error(f"Failed to build fuzzy system: {e} — using fallback")
        else:
            log.warning("scikit-fuzzy not available — using NumPy fallback")

    # ── Input clipping helper ────────────────────────────────────────
    @staticmethod
    def _clip(val, lo, hi):
        return float(np.clip(val, lo, hi))

    # ── Label from score ─────────────────────────────────────────────
    @staticmethod
    def _score_to_label(score: float) -> tuple:
        for (lo, hi), (label, color) in THREAT_LABELS.items():
            if lo <= score < hi:
                return label, color
        return "CRITICAL", "#FF0000"

    # ── Action from score ────────────────────────────────────────────
    @staticmethod
    def _score_to_action(score: float) -> str:
        for (lo, hi), action in ACTION_MAP.items():
            if lo <= score < hi:
                return action
        return "CRITICAL_ENGAGE"

    # ── Main evaluate ────────────────────────────────────────────────
    def evaluate(self, inputs: dict) -> dict:
        """
        Evaluate threat level from multi-sensor inputs.
        Returns dict with threat_level, threat_score, action, reasoning.
        """
        # Clamp inputs to universe bounds
        d   = self._clip(inputs.get('distance', 10),      0, 20)
        s   = self._clip(inputs.get('speed', 50),          0, 500)
        alt = self._clip(inputs.get('altitude', 200),      0, 3000)
        rcs = self._clip(inputs.get('rcs', 1.0),           0, 1.99)
        cc  = self._clip(inputs.get('cam_conf', 50),       0, 100)
        sz  = self._clip(inputs.get('obj_size', 50),       0, 100)
        rfs = self._clip(inputs.get('rf_strength', 0),     0, 100)
        rfr = self._clip(inputs.get('rf_risk', 0),         0, 100)
        ac  = self._clip(inputs.get('acoustic', 0),        0, 1)
        mv  = self._clip(inputs.get('movement', 50),       0, 100)

        threat_score = 50.0
        action_score = 50.0
        method = "FUZZY_LOGIC"

        if self._ready and self._sim is not None:
            try:
                self._sim.input['distance']    = d
                self._sim.input['speed']       = s
                self._sim.input['altitude']    = alt
                self._sim.input['rcs']         = rcs
                self._sim.input['cam_conf']    = cc
                self._sim.input['obj_size']    = sz
                self._sim.input['rf_strength'] = rfs
                self._sim.input['rf_risk']     = rfr
                self._sim.input['acoustic']    = ac
                self._sim.input['movement']    = mv
                self._sim.compute()
                threat_score = float(self._sim.output['threat'])
                action_score = float(self._sim.output['action_sc'])
            except Exception as e:
                log.debug(f"Fuzzy compute error: {e} — fallback")
                fb = _numpy_fallback({'distance': d, 'speed': s, 'cam_conf': cc,
                                      'rf_strength': rfs, 'rf_risk': rfr,
                                      'movement': mv, 'acoustic': ac})
                threat_score = fb['threat_score']
                method = "NUMPY_FALLBACK"
        else:
            fb = _numpy_fallback({'distance': d, 'speed': s, 'cam_conf': cc,
                                  'rf_strength': rfs, 'rf_risk': rfr,
                                  'movement': mv, 'acoustic': ac})
            threat_score = fb['threat_score']
            method = "NUMPY_FALLBACK"

        label, color = self._score_to_label(threat_score)
        action = self._score_to_action(max(threat_score, action_score * 0.7 + threat_score * 0.3))

        reasoning = self._build_reasoning(inputs, threat_score, action, d, s, mv, rfs, rfr, ac, cc)

        return {
            "threat_score":   round(threat_score, 1),
            "action_score":   round(action_score, 1),
            "threat_level":   label,
            "threat_color":   color,
            "action":         action,
            "action_desc":    RESPONSE_MAP.get(action, ""),
            "confidence":     round(min(threat_score / 100.0 + 0.1, 1.0), 2),
            "method":         method,
            "reasoning":      reasoning,
        }

    # ── Human-readable reasoning ─────────────────────────────────────
    def _build_reasoning(self, raw, score, action, d, s, mv, rfs, rfr, ac, cc):
        r = []
        r.append(f"Fuzzy threat score: {score:.1f}/100")
        if d < 3:
            r.append(f"⚠ CLOSE RANGE: {d:.1f} km — immediate threat zone")
        if s > 200:
            r.append(f"⚠ HIGH SPEED: {s:.0f} km/h — time-critical")
        if mv > 70:
            r.append("⚠ DIRECTED MOVEMENT: target on purposeful course")
        if rfr > 70:
            r.append("⚠ MILITARY RF SIGNATURE detected")
        elif rfs > 50:
            r.append("RF control link active — jammable")
        if ac > 0.5:
            r.append("✓ Acoustic signature matched — drone confirmed")
        if cc > 80:
            r.append(f"✓ High camera confidence: {cc:.0f}%")
        r.append(f"→ Recommended: {action}")
        return r

    def status(self) -> dict:
        return {
            "ready":      self._ready,
            "backend":    "scikit-fuzzy" if SKFUZZY_AVAILABLE else "numpy",
            "rules":      18 if self._ready else 0,
            "inputs":     10,
        }


# ══════════════════════════════════════════════════════════════════════
#  SINGLETON
# ══════════════════════════════════════════════════════════════════════

_fuzzy_instance = None

def get_fuzzy_engine() -> FuzzyDecisionEngine:
    global _fuzzy_instance
    if _fuzzy_instance is None:
        _fuzzy_instance = FuzzyDecisionEngine()
    return _fuzzy_instance


# ══════════════════════════════════════════════════════════════════════
#  STANDALONE TEST
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    print("=" * 65)
    print("  MCDIS Fuzzy Decision Engine -- Standalone Test")
    print("=" * 65)

    engine = FuzzyDecisionEngine()

    scenarios = [
        {
            "name": "[SAFE]     Bird",
            "inputs": {"distance": 12, "speed": 25, "altitude": 80,
                       "rcs": 0.2, "cam_conf": 40, "obj_size": 15,
                       "rf_strength": 0, "rf_risk": 0,
                       "acoustic": 0, "movement": 15}
        },
        {
            "name": "[SUSPC]    Commercial Drone",
            "inputs": {"distance": 7, "speed": 55, "altitude": 120,
                       "rcs": 0.8, "cam_conf": 68, "obj_size": 45,
                       "rf_strength": 60, "rf_risk": 20,
                       "acoustic": 0, "movement": 50}
        },
        {
            "name": "[THREAT]   Military Drone",
            "inputs": {"distance": 4, "speed": 160, "altitude": 300,
                       "rcs": 1.2, "cam_conf": 85, "obj_size": 70,
                       "rf_strength": 75, "rf_risk": 80,
                       "acoustic": 1, "movement": 78}
        },
        {
            "name": "[CRITICAL] Shahed-136",
            "inputs": {"distance": 1.5, "speed": 230, "altitude": 150,
                       "rcs": 0.3, "cam_conf": 95, "obj_size": 80,
                       "rf_strength": 30, "rf_risk": 95,
                       "acoustic": 1, "movement": 97}
        },
    ]

    for sc in scenarios:
        result = engine.evaluate(sc['inputs'])
        print(f"\n  {sc['name']}")
        print(f"    Threat Score : {result['threat_score']}%")
        print(f"    Threat Level : {result['threat_level']}")
        print(f"    Action       : {result['action']}")
        print(f"    Method       : {result['method']}")
        for r in result['reasoning']:
            print(f"      * {r}")

    print(f"\n  Engine status: {engine.status()}")
    print("\n✅ Fuzzy Decision Engine test complete.")
