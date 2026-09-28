# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║  MCDIS — ISR Pre-Check Engine v1.0                                  ║
║  نظام تقييم احتمال الاعتراض قبل أي engagement                       ║
╠══════════════════════════════════════════════════════════════════════╣
║  Based on: P2P Intercept Success Rate Research                       ║
║                                                                      ║
║  Formula:                                                            ║
║    ISR = f(speed_ratio, angle, distance, time_to_intercept)         ║
║                                                                      ║
║  Output:                                                             ║
║    isr_pct         : 0–100%                                          ║
║    recommended_sys : best system for this scenario                   ║
║    alternatives    : ranked list of other options                    ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import math
import time
import numpy as np
import logging
from typing import Optional

log = logging.getLogger("ISR-PRECHECK")
log.setLevel(logging.INFO)


# ══════════════════════════════════════════════════════════════════════
#  SYSTEM CAPABILITIES
#  Each system has: max_range_km, max_speed_kmh, effectiveness profile
# ══════════════════════════════════════════════════════════════════════

SYSTEM_PROFILES = {
    "INTERCEPTOR_CHAIN": {
        "max_range_km":   8.0,
        "speed_kmh":      180,
        "max_target_speed": 400,
        "soft_kill":      False,
        "effective_against": ["commercial", "military", "suicide", "fixed_wing"],
        "description":    "Interceptor drone — precision capture/collision",
    },
    "RF_JAM": {
        "max_range_km":   5.0,
        "speed_kmh":      0,    # instantaneous (EW)
        "max_target_speed": 500,
        "soft_kill":      True,
        "effective_against": ["commercial", "dji"],
        "description":    "RF jamming — C2 link disruption",
    },
    "GPS_SPOOF": {
        "max_range_km":   5.0,
        "speed_kmh":      0,
        "max_target_speed": 500,
        "soft_kill":      True,
        "effective_against": ["commercial", "dji", "civilian"],
        "description":    "GPS spoofing — force RTH",
    },
    "LASER_DEW": {
        "max_range_km":   3.0,
        "speed_kmh":      0,    # speed of light
        "max_target_speed": 500,
        "soft_kill":      False,
        "effective_against": ["commercial", "military", "fixed_wing"],
        "description":    "Directed energy laser — thermal kill",
    },
    "HPM_EMP": {
        "max_range_km":   1.5,
        "speed_kmh":      0,
        "max_target_speed": 500,
        "soft_kill":      False,
        "effective_against": ["commercial", "dji"],
        "description":    "High-power microwave — electronics fry",
    },
    "ACOUSTIC_ATTACK": {
        "max_range_km":   0.5,
        "speed_kmh":      0,
        "max_target_speed": 200,
        "soft_kill":      True,
        "effective_against": ["commercial", "dji", "micro"],
        "description":    "Acoustic resonance — MEMS gyro disruption",
    },
    "NET_GUN": {
        "max_range_km":   0.05,
        "speed_kmh":      0,
        "max_target_speed": 80,
        "soft_kill":      True,
        "effective_against": ["commercial", "dji", "micro"],
        "description":    "Net launcher — physical capture",
    },
    "CYBER_TAKEOVER": {
        "max_range_km":   3.0,
        "speed_kmh":      0,
        "max_target_speed": 500,
        "soft_kill":      True,
        "effective_against": ["dji", "commercial", "mavlink"],
        "description":    "Protocol hijack — drone takeover",
    },
    "QUANTUM_JAM": {
        "max_range_km":   6.0,
        "speed_kmh":      0,
        "max_target_speed": 500,
        "soft_kill":      True,
        "effective_against": ["military", "fhss", "hopping"],
        "description":    "Quantum jamming — all-frequency sweep",
    },
    "COLLAB_SWARM": {
        "max_range_km":   10.0,
        "speed_kmh":      120,
        "max_target_speed": 300,
        "soft_kill":      False,
        "effective_against": ["swarm", "military", "commercial"],
        "description":    "Collaborative swarm — area denial",
    },
}


# ══════════════════════════════════════════════════════════════════════
#  ISR CALCULATOR
# ══════════════════════════════════════════════════════════════════════

class ISRCalculator:
    """
    Intercept Success Rate calculator.

    Physics model:
    1. Time-to-Intercept (TTI) — based on geometry
    2. Closure Rate — relative speed
    3. Angle Penalty — large angles reduce success
    4. Speed Ratio — if interceptor slower than target, hard to catch
    """

    def calculate_intercept_probability(
        self,
        target_speed_kmh: float,
        target_distance_km: float,
        target_bearing_deg: float,
        interceptor_speed_kmh: float = 180,
        interceptor_range_km: float = 8.0,
    ) -> dict:
        """
        Calculate probability that an interceptor can catch the target.

        Returns:
            isr_pct          : 0-100
            time_to_intercept: seconds
            intercept_point  : estimated km from origin
            feasible         : bool
        """
        # Out of range
        if target_distance_km > interceptor_range_km:
            return {
                "isr_pct": 5.0,
                "feasible": False,
                "reason": f"Target at {target_distance_km:.1f}km — beyond interceptor range ({interceptor_range_km:.1f}km)",
                "time_to_intercept_sec": 9999,
                "intercept_distance_km": None,
            }

        # Convert to m/s
        v_t = target_speed_kmh / 3.6
        v_i = interceptor_speed_kmh / 3.6
        d   = target_distance_km * 1000  # meters

        # Angle in radians (angle between target heading and intercept vector)
        angle_rad = math.radians(abs(target_bearing_deg) % 180)

        # ── Intercept geometry ───────────────────────────────────────
        # Pure pursuit: t_intercept = d / (v_i - v_t * cos(angle))
        # Predictive intercept: find meeting point
        cosA = math.cos(angle_rad)
        relative_approach = v_i - v_t * cosA

        if relative_approach <= 0:
            # Target moving away faster than interceptor can close
            return {
                "isr_pct": max(2.0, 30.0 - target_speed_kmh * 0.05),
                "feasible": False,
                "reason": f"Target escaping — approach rate negative ({relative_approach:.1f} m/s)",
                "time_to_intercept_sec": 9999,
                "intercept_distance_km": None,
            }

        tti_sec = d / relative_approach  # seconds
        intercept_km = target_distance_km + (v_t * tti_sec / 1000)

        # ── Base probability from physics ────────────────────────────
        speed_ratio = min(v_i / max(v_t, 1.0), 2.0)   # 1.0 = same speed
        angle_penalty = math.cos(angle_rad * 0.8)       # penalize large angles

        # Time penalty (longer = more uncertainty)
        time_factor = math.exp(-tti_sec / 120.0)        # decay over 2 min

        # Speed bonus
        speed_factor = min(speed_ratio / 1.0, 1.0)      # caps at 1.0

        raw_prob = speed_factor * angle_penalty * time_factor * 1.2
        isr_pct = float(np.clip(raw_prob * 100, 5, 98))

        # ── Feasibility check ────────────────────────────────────────
        feasible = (isr_pct >= 25) and (tti_sec < 300)

        reason = ""
        if not feasible:
            if tti_sec >= 300:
                reason = "TTI too long — target will escape zone"
            else:
                reason = f"Low intercept probability ({isr_pct:.0f}%)"
        else:
            reason = f"Intercept feasible in {tti_sec:.0f}s at {intercept_km:.1f}km"

        return {
            "isr_pct":               round(isr_pct, 1),
            "feasible":              feasible,
            "reason":                reason,
            "time_to_intercept_sec": round(tti_sec, 1),
            "intercept_distance_km": round(intercept_km, 2),
            "speed_ratio":           round(speed_ratio, 2),
            "angle_penalty":         round(angle_penalty, 2),
        }


# ══════════════════════════════════════════════════════════════════════
#  SYSTEM RANKER — finds best countermeasure for situation
# ══════════════════════════════════════════════════════════════════════

class SystemRanker:
    """Ranks available countermeasure systems for a given target scenario."""

    def rank_systems(
        self,
        target_speed_kmh: float,
        target_distance_km: float,
        target_bearing_deg: float,
        target_type: str = "commercial",
        rf_controlled: bool = True,
        gps_dependent: bool = True,
        threat_level: str = "THREAT",
        available_systems: Optional[list] = None,
    ) -> list:
        """
        Returns list of systems sorted by effectiveness (best first).
        """
        if available_systems is None:
            available_systems = list(SYSTEM_PROFILES.keys())

        isr_calc = ISRCalculator()
        scores = []

        for sys_name in available_systems:
            profile = SYSTEM_PROFILES.get(sys_name)
            if not profile:
                continue

            score = 0.0
            notes = []

            # ── Range check ───────────────────────────────────────────
            if target_distance_km > profile['max_range_km']:
                notes.append(f"Out of range ({target_distance_km:.1f}>{profile['max_range_km']}km)")
                score -= 50

            # ── Speed check ───────────────────────────────────────────
            if target_speed_kmh > profile['max_target_speed']:
                notes.append("Target too fast for this system")
                score -= 30

            # ── Effectiveness against target type ─────────────────────
            if any(t in target_type.lower() for t in profile['effective_against']):
                score += 30
                notes.append(f"Effective vs {target_type}")
            else:
                score -= 10

            # ── Soft kill suitability ─────────────────────────────────
            if not rf_controlled and sys_name == "RF_JAM":
                score -= 40
                notes.append("Target not RF-controlled — jamming ineffective")
            if not gps_dependent and sys_name == "GPS_SPOOF":
                score -= 40
                notes.append("Target not GPS-dependent — spoofing ineffective")

            # ── Threat level matching ─────────────────────────────────
            if threat_level in ("CRITICAL", "THREAT") and profile['soft_kill']:
                score += 10  # still valid, but lower than kinetic
            if threat_level == "CRITICAL" and not profile['soft_kill']:
                score += 25  # prefer hard kill on critical

            # ── ISR specific calc for INTERCEPTOR_CHAIN ───────────────
            isr_result = None
            if sys_name == "INTERCEPTOR_CHAIN":
                isr_result = isr_calc.calculate_intercept_probability(
                    target_speed_kmh, target_distance_km, target_bearing_deg,
                    interceptor_speed_kmh=profile['speed_kmh'],
                    interceptor_range_km=profile['max_range_km'],
                )
                score += isr_result['isr_pct'] * 0.5
                if not isr_result['feasible']:
                    score -= 30

            # ── COLLAB_SWARM speed limit ──────────────────────────────
            if sys_name == "COLLAB_SWARM":
                isr_result = isr_calc.calculate_intercept_probability(
                    target_speed_kmh, target_distance_km, target_bearing_deg,
                    interceptor_speed_kmh=profile['speed_kmh'],
                    interceptor_range_km=profile['max_range_km'],
                )
                score += isr_result['isr_pct'] * 0.4

            # Base score from range closeness (closer target = more options)
            range_bonus = max(0, (profile['max_range_km'] - target_distance_km) /
                              profile['max_range_km'] * 20)
            score += range_bonus

            scores.append({
                "system":      sys_name,
                "score":       round(score, 1),
                "description": profile['description'],
                "soft_kill":   profile['soft_kill'],
                "in_range":    target_distance_km <= profile['max_range_km'],
                "notes":       notes,
                "isr_result":  isr_result,
            })

        scores.sort(key=lambda x: x['score'], reverse=True)
        return scores


# ══════════════════════════════════════════════════════════════════════
#  ISR PRE-CHECK — MAIN ENGINE
# ══════════════════════════════════════════════════════════════════════

class ISRPreCheck:
    """
    Full ISR Pre-Check system.
    Call evaluate() before any engagement to get:
    - ISR % for interceptor
    - Best system recommendation
    - Alternative systems
    - Go/NoGo decision
    """

    def __init__(self):
        self.isr_calc = ISRCalculator()
        self.ranker   = SystemRanker()
        log.info("ISR Pre-Check Engine ready ✓")

    def evaluate(
        self,
        target_speed_kmh: float,
        target_distance_km: float,
        target_bearing_deg: float = 45.0,
        target_type: str = "commercial",
        threat_level: str = "THREAT",
        rf_controlled: bool = True,
        gps_dependent: bool = True,
        available_systems: Optional[list] = None,
    ) -> dict:
        """
        Run full ISR Pre-Check.

        Returns:
        {
          "go_nogo": "GO" | "CAUTION" | "NO-GO",
          "isr_pct": 73.2,
          "recommended": "INTERCEPTOR_CHAIN",
          "alternative": "GPS_SPOOF",
          "ranked_systems": [...],
          "intercept_calc": {...},
          "timestamp": "...",
        }
        """
        t0 = time.time()

        # Full intercept probability for interceptor drone
        intercept_calc = self.isr_calc.calculate_intercept_probability(
            target_speed_kmh=target_speed_kmh,
            target_distance_km=target_distance_km,
            target_bearing_deg=target_bearing_deg,
        )

        # Rank all systems
        ranked = self.ranker.rank_systems(
            target_speed_kmh=target_speed_kmh,
            target_distance_km=target_distance_km,
            target_bearing_deg=target_bearing_deg,
            target_type=target_type,
            rf_controlled=rf_controlled,
            gps_dependent=gps_dependent,
            threat_level=threat_level,
            available_systems=available_systems,
        )

        # Extract top 2
        recommended  = ranked[0] if ranked else None
        alternative  = ranked[1] if len(ranked) > 1 else None

        # Go/NoGo decision
        if not recommended or recommended['score'] < 0:
            go_nogo = "NO-GO"
        elif recommended['score'] < 20:
            go_nogo = "CAUTION"
        else:
            go_nogo = "GO"

        isr_pct = intercept_calc.get('isr_pct', 0)

        return {
            "go_nogo":         go_nogo,
            "isr_pct":         isr_pct,
            "isr_feasible":    intercept_calc.get('feasible', False),
            "recommended":     recommended['system'] if recommended else "NONE",
            "recommended_desc":recommended['description'] if recommended else "",
            "alternative":     alternative['system'] if alternative else "NONE",
            "ranked_systems":  ranked[:5],          # top 5 only
            "intercept_calc":  intercept_calc,
            "calc_time_ms":    round((time.time() - t0) * 1000, 1),
            "timestamp":       time.strftime("%H:%M:%S"),
        }

    def quick_isr(self, speed_kmh: float, distance_km: float, bearing: float = 45) -> float:
        """Fast ISR % only — for real-time display."""
        r = self.isr_calc.calculate_intercept_probability(speed_kmh, distance_km, bearing)
        return r['isr_pct']


# ══════════════════════════════════════════════════════════════════════
#  SINGLETON
# ══════════════════════════════════════════════════════════════════════

_isr_instance = None

def get_isr_engine() -> ISRPreCheck:
    global _isr_instance
    if _isr_instance is None:
        _isr_instance = ISRPreCheck()
    return _isr_instance


# ══════════════════════════════════════════════════════════════════════
#  STANDALONE TEST
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 65)
    print("  MCDIS ISR Pre-Check — Standalone Test")
    print("=" * 65)

    engine = ISRPreCheck()

    test_cases = [
        {"speed": 230,  "dist": 2.5, "bearing": 45,  "type": "fixed_wing",  "label": "Shahed-136"},
        {"speed": 60,   "dist": 1.2, "bearing": 20,  "type": "dji",         "label": "DJI Mini Pro"},
        {"speed": 350,  "dist": 8.0, "bearing": 90,  "type": "military",    "label": "Military Drone"},
        {"speed": 25,   "dist": 0.8, "bearing": 10,  "type": "commercial",  "label": "Slow Drone"},
    ]

    for tc in test_cases:
        result = engine.evaluate(
            target_speed_kmh=tc['speed'],
            target_distance_km=tc['dist'],
            target_bearing_deg=tc['bearing'],
            target_type=tc['type'],
        )
        print(f"\n  Target: {tc['label']:20s} | Speed: {tc['speed']} km/h | Dist: {tc['dist']} km")
        print(f"    ┌─────────────────────────────────────────────┐")
        print(f"    │ ISR: {result['isr_pct']:5.1f}%  {('✅' if result['isr_feasible'] else '❌')}              │")
        print(f"    │ RECOMMENDED: {result['recommended']:20s}    │")
        print(f"    │ ALTERNATIVE: {result['alternative']:20s}    │")
        print(f"    │ GO/NO-GO: {result['go_nogo']:10s}                 │")
        print(f"    └─────────────────────────────────────────────┘")
        if result['intercept_calc'].get('time_to_intercept_sec'):
            tti = result['intercept_calc']['time_to_intercept_sec']
            if tti < 9999:
                print(f"    → Time to intercept: {tti:.0f}s")

    print("\n✅ ISR Pre-Check test complete.")
