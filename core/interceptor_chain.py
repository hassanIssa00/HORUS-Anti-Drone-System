# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║  MCDIS — Interceptor Chain Engine v1.0                              ║
║  سلسلة الاعتراض الذكي — 4 مراحل                                     ║
╠══════════════════════════════════════════════════════════════════════╣
║  Based on:                                                           ║
║    Phase 1 — ISR Check       (P2P Research)                         ║
║    Phase 2 — MIT Trajectory  (Lightweight LSTM-style prediction)    ║
║    Phase 3 — FRPN Approach   (Intercept Point Calculation)          ║
║    Phase 4 — Dispatch        (Launch command + status tracking)     ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import math
import time
import numpy as np
import threading
import logging
from typing import Optional, List, Tuple
from collections import deque

log = logging.getLogger("INTERCEPTOR-CHAIN")
log.setLevel(logging.INFO)


# ══════════════════════════════════════════════════════════════════════
#  PHASE 2 — TRAJECTORY PREDICTOR (MIT-style)
#  Lightweight sequence prediction without GPU requirement
# ══════════════════════════════════════════════════════════════════════

class TrajectoryPredictor:
    """
    Predicts future target position using position history.
    Uses weighted polynomial extrapolation (MIT-inspired, CPU-only).
    For real LSTM, GPU + training data would be needed.
    """

    def __init__(self, history_len: int = 10):
        self.history_len = history_len
        self._histories  = {}  # tid → deque of (x, y, t)

    def update(self, tid: int, x: float, y: float, t: float = None):
        """Add a new position observation."""
        if t is None:
            t = time.time()
        if tid not in self._histories:
            self._histories[tid] = deque(maxlen=self.history_len)
        self._histories[tid].append((x, y, t))

    def predict(self, tid: int, steps_ahead: int = 5, dt: float = 0.5) -> List[Tuple]:
        """
        Predict next N positions.
        Returns list of (x, y, t) tuples.
        """
        hist = self._histories.get(tid)
        if not hist or len(hist) < 3:
            return []

        xs = np.array([p[0] for p in hist])
        ys = np.array([p[1] for p in hist])
        ts = np.array([p[2] for p in hist])
        ts -= ts[0]  # normalize time

        # Fit degree-2 polynomial (parabolic) to x(t) and y(t)
        try:
            px = np.polyfit(ts, xs, min(2, len(hist) - 1))
            py = np.polyfit(ts, ys, min(2, len(hist) - 1))
        except np.linalg.LinAlgError:
            return []

        t_last = ts[-1]
        predictions = []
        for i in range(1, steps_ahead + 1):
            t_next = t_last + i * dt
            x_pred = float(np.polyval(px, t_next))
            y_pred = float(np.polyval(py, t_next))
            predictions.append((round(x_pred, 2), round(y_pred, 2),
                                 round(time.time() + i * dt, 2)))
        return predictions

    def get_velocity(self, tid: int) -> Tuple[float, float]:
        """Estimate current velocity (vx, vy) m/s from last 3 points."""
        hist = self._histories.get(tid)
        if not hist or len(hist) < 2:
            return 0.0, 0.0
        p1, p2 = hist[-2], hist[-1]
        dt = p2[2] - p1[2]
        if dt <= 0:
            return 0.0, 0.0
        return (p2[0] - p1[0]) / dt, (p2[1] - p1[1]) / dt


# ══════════════════════════════════════════════════════════════════════
#  PHASE 3 — FRPN (Final Run-up Point Navigation)
#  Calculates the intercept point — NOT a chase, but a cutoff!
# ══════════════════════════════════════════════════════════════════════

class FRPNCalculator:
    """
    Final Run-up Point Navigator.
    Calculates the optimal intercept point where our drone
    can arrive before or at the same time as the target.

    Key insight: Don't chase — predict where it'll be and go there.
    """

    def calculate_intercept_point(
        self,
        target_x: float, target_y: float,
        target_vx: float, target_vy: float,
        interceptor_x: float, interceptor_y: float,
        interceptor_speed: float,   # m/s
        max_iterations: int = 100,
    ) -> dict:
        """
        Iterative intercept point solver.

        Strategy:
        1. Guess intercept time T
        2. Compute where target will be at T
        3. Check if interceptor can reach that point in T
        4. Adjust T and repeat
        """
        # Initial guess: straight-line distance / interceptor speed
        dx = target_x - interceptor_x
        dy = target_y - interceptor_y
        dist0 = math.hypot(dx, dy)
        T = dist0 / max(interceptor_speed, 1.0)

        for _ in range(max_iterations):
            # Predicted target position at time T
            tx = target_x + target_vx * T
            ty = target_y + target_vy * T

            # Distance from interceptor to predicted position
            d_int = math.hypot(tx - interceptor_x, ty - interceptor_y)
            T_required = d_int / max(interceptor_speed, 1.0)

            # Convergence check
            if abs(T_required - T) < 0.1:
                break
            T = T_required

        # Final intercept point
        ix = target_x + target_vx * T
        iy = target_y + target_vy * T

        # Heading for interceptor
        hdg_rad = math.atan2(ix - interceptor_x, -(iy - interceptor_y))
        heading_deg = math.degrees(hdg_rad) % 360

        # Remaining distance for interceptor
        d_final = math.hypot(ix - interceptor_x, iy - interceptor_y)

        # Energy score (lower T and distance = more energy left = better)
        energy_score = max(0, 100 - T * 0.5 - d_final * 0.01)

        return {
            "intercept_x":       round(ix, 1),
            "intercept_y":       round(iy, 1),
            "time_to_intercept": round(T, 1),
            "interceptor_heading": round(heading_deg, 1),
            "distance_to_point": round(d_final, 1),
            "energy_score":      round(energy_score, 1),
            "feasible":          T < 300 and d_final < 8000,
        }


# ══════════════════════════════════════════════════════════════════════
#  INTERCEPTOR STATUS TRACKER
# ══════════════════════════════════════════════════════════════════════

class InterceptorUnit:
    """Represents a single interceptor drone unit."""

    STATES = ["STANDBY", "LAUNCHED", "APPROACHING", "INTERCEPTING", "SUCCESS", "FAILED", "RETURNED"]

    def __init__(self, unit_id: int):
        self.unit_id   = unit_id
        self.state     = "STANDBY"
        self.target_id = None
        self.launched_at    = None
        self.isr_pct        = 0.0
        self.phase          = 0
        self.phase_log      = []
        self._thread        = None

    def to_dict(self) -> dict:
        return {
            "unit_id":   self.unit_id,
            "state":     self.state,
            "target_id": self.target_id,
            "isr_pct":   self.isr_pct,
            "phase":     self.phase,
            "phase_log": self.phase_log,
        }


# ══════════════════════════════════════════════════════════════════════
#  INTERCEPTOR CHAIN ENGINE — MAIN
# ══════════════════════════════════════════════════════════════════════

class InterceptorChainEngine:
    """
    Full 4-phase interceptor chain:

    Phase 1: ISR Check     — is intercept feasible?
    Phase 2: MIT Trajectory— where will target be?
    Phase 3: FRPN Approach — compute intercept point
    Phase 4: Dispatch      — launch + track
    """

    def __init__(self, num_units: int = 3):
        self.num_units    = num_units
        self.units        = [InterceptorUnit(i + 1) for i in range(num_units)]
        self.predictor    = TrajectoryPredictor(history_len=15)
        self.frpn         = FRPNCalculator()
        self._lock        = threading.Lock()
        self.engagement_log = []
        log.info(f"Interceptor Chain Engine ready — {num_units} units ✓")

    # ── Public: update target position ──────────────────────────────
    def update_target_position(self, tid: int, x: float, y: float):
        """Feed live tracking data into trajectory predictor."""
        self.predictor.update(tid, x, y)

    # ── Get available unit ────────────────────────────────────────────
    def _get_available_unit(self) -> Optional[InterceptorUnit]:
        for unit in self.units:
            if unit.state == "STANDBY":
                return unit
        return None

    # ══════════════════════════════════════════════════════════════════
    #  MAIN: run_chain — executes all 4 phases
    # ══════════════════════════════════════════════════════════════════

    def run_chain(
        self,
        target_id: str,
        target_speed_kmh: float,
        target_distance_km: float,
        target_bearing_deg: float,
        target_x: float = 1000.0,    # meters from origin
        target_y: float = 500.0,
        target_type: str = "commercial",
        async_dispatch: bool = True,
        on_complete=None,            # callback(result_dict)
    ) -> dict:
        """
        Execute full interceptor chain.

        Returns phase-by-phase result dict immediately.
        If async_dispatch=True, Phase 4 runs in background thread.
        """
        chain_start = time.time()
        result = {
            "target_id":   target_id,
            "started_at":  time.strftime("%H:%M:%S"),
            "phases":      {},
            "final_status": "PENDING",
            "unit_id":     None,
        }

        # ── PHASE 1 — ISR Check ─────────────────────────────────────
        log.info(f"[CHAIN] Phase 1 — ISR Check for {target_id}")
        from isr_precheck import ISRCalculator
        isr_calc = ISRCalculator()
        isr_result = isr_calc.calculate_intercept_probability(
            target_speed_kmh=target_speed_kmh,
            target_distance_km=target_distance_km,
            target_bearing_deg=target_bearing_deg,
        )
        result['phases']['1_ISR'] = {
            "isr_pct":  isr_result['isr_pct'],
            "feasible": isr_result['feasible'],
            "reason":   isr_result['reason'],
            "status":   "PASS" if isr_result['feasible'] else "WARN",
        }

        if isr_result['isr_pct'] < 5:
            result['final_status'] = "ABORTED — ISR too low"
            result['abort_reason'] = isr_result['reason']
            self._log_engagement(result)
            return result

        # ── PHASE 2 — MIT Trajectory Prediction ─────────────────────
        log.info(f"[CHAIN] Phase 2 — Trajectory Prediction for {target_id}")

        # Derive velocity from speed + bearing
        bearing_rad = math.radians(target_bearing_deg)
        speed_ms    = target_speed_kmh / 3.6
        tvx = speed_ms * math.sin(bearing_rad)
        tvy = -speed_ms * math.cos(bearing_rad)

        predictions = self.predictor.predict(target_id.replace("T-", ""), steps_ahead=10)
        if not predictions:
            # No history — synthesise from current speed/bearing
            predictions = [
                (target_x + tvx * i * 0.5,
                 target_y + tvy * i * 0.5,
                 time.time() + i * 0.5)
                for i in range(1, 11)
            ]

        pred_pos_5s = predictions[min(9, len(predictions) - 1)]
        result['phases']['2_TRAJECTORY'] = {
            "predicted_x_5s":  round(pred_pos_5s[0], 1),
            "predicted_y_5s":  round(pred_pos_5s[1], 1),
            "velocity_vx":     round(tvx, 2),
            "velocity_vy":     round(tvy, 2),
            "prediction_steps": len(predictions),
            "status":          "PASS",
        }

        # ── PHASE 3 — FRPN Intercept Point ──────────────────────────
        log.info(f"[CHAIN] Phase 3 — FRPN Intercept Point for {target_id}")
        interceptor_speed_ms = 180 / 3.6   # 180 km/h interceptor
        frpn_result = self.frpn.calculate_intercept_point(
            target_x=target_x,
            target_y=target_y,
            target_vx=tvx,
            target_vy=tvy,
            interceptor_x=0.0,   # origin = our base
            interceptor_y=0.0,
            interceptor_speed=interceptor_speed_ms,
        )
        # Cap TTI for display — if target faster, use weapon-grade engagement
        tti_display = min(frpn_result['time_to_intercept'], 300)
        frpn_feasible = tti_display < 300 and target_distance_km <= 8.0

        result['phases']['3_FRPN'] = {
            "intercept_x":     frpn_result['intercept_x'],
            "intercept_y":     frpn_result['intercept_y'],
            "heading_deg":     frpn_result['interceptor_heading'],
            "tti_sec":         tti_display,
            "energy_score":    frpn_result['energy_score'],
            "feasible":        frpn_feasible,
            "status":          "PASS" if frpn_feasible else "WARN",
        }

        if not frpn_feasible:
            result['final_status'] = "ABORTED — FRPN infeasible (target out of range)"
            self._log_engagement(result)
            return result

        # ── PHASE 4 — Dispatch ───────────────────────────────────────
        unit = self._get_available_unit()
        if unit is None:
            result['final_status'] = "ABORTED — No units available"
            self._log_engagement(result)
            return result

        result['unit_id'] = unit.unit_id
        result['phases']['4_DISPATCH'] = {
            "unit_id":    unit.unit_id,
            "heading":    frpn_result['interceptor_heading'],
            "tti_sec":    frpn_result['time_to_intercept'],
            "status":     "LAUNCHED",
        }
        result['final_status'] = "LAUNCHED"

        # Launch (simulate engagement in background)
        if async_dispatch:
            t = threading.Thread(
                target=self._run_engagement_sim,
                args=(unit, target_id, isr_result['isr_pct'],
                      frpn_result['time_to_intercept'], result, on_complete),
                daemon=True,
            )
            unit.state     = "LAUNCHED"
            unit.target_id = target_id
            unit.launched_at = time.time()
            unit.isr_pct   = isr_result['isr_pct']
            unit.phase     = 4
            t.start()
        else:
            unit.state     = "LAUNCHED"
            unit.target_id = target_id

        result['calc_time_ms'] = round((time.time() - chain_start) * 1000, 1)
        self._log_engagement(result)
        log.info(f"[CHAIN] ✅ Unit-{unit.unit_id} dispatched → {target_id} "
                 f"(ISR: {isr_result['isr_pct']:.0f}%, TTI: {frpn_result['time_to_intercept']:.0f}s)")
        return result

    def _run_engagement_sim(self, unit, target_id, isr_pct, tti_sec, result, callback):
        """Background thread simulating the engagement."""
        sim_tti = min(tti_sec, 30.0)   # cap sim time at 30s
        unit.state = "APPROACHING"
        unit.phase_log.append(f"Approaching intercept point — ETA {tti_sec:.0f}s")
        time.sleep(sim_tti * 0.4)

        unit.state = "INTERCEPTING"
        unit.phase_log.append("Final approach — FRPN mode engaged")
        time.sleep(sim_tti * 0.3)

        # Outcome based on ISR probability
        success = np.random.random() < (isr_pct / 100.0)
        if success:
            unit.state = "SUCCESS"
            unit.phase_log.append(f"✅ TARGET {target_id} NEUTRALIZED")
            result['final_status'] = "SUCCESS"
        else:
            unit.state = "FAILED"
            unit.phase_log.append(f"❌ Intercept missed — returning")
            result['final_status'] = "FAILED"

        if callback:
            try:
                callback(result)
            except Exception:
                pass

        time.sleep(5.0)
        unit.state = "RETURNED"
        unit.target_id = None
        time.sleep(2.0)
        unit.state = "STANDBY"

    def _log_engagement(self, result):
        with self._lock:
            self.engagement_log.append(result)
            if len(self.engagement_log) > 100:
                self.engagement_log.pop(0)

    def status(self) -> dict:
        return {
            "units":          [u.to_dict() for u in self.units],
            "available":      sum(1 for u in self.units if u.state == "STANDBY"),
            "active":         sum(1 for u in self.units if u.state not in ("STANDBY", "RETURNED")),
            "engagements":    len(self.engagement_log),
        }


# ══════════════════════════════════════════════════════════════════════
#  SINGLETON
# ══════════════════════════════════════════════════════════════════════

_chain_instance = None

def get_interceptor_chain() -> InterceptorChainEngine:
    global _chain_instance
    if _chain_instance is None:
        _chain_instance = InterceptorChainEngine(num_units=3)
    return _chain_instance


# ══════════════════════════════════════════════════════════════════════
#  STANDALONE TEST
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 65)
    print("  MCDIS Interceptor Chain — Standalone Test")
    print("=" * 65)

    chain = InterceptorChainEngine(num_units=3)

    # Simulate some history for trajectory predictor
    import time
    base_t = time.time() - 5
    for i in range(10):
        chain.update_target_position(
            tid=1,
            x=200 + i * 30,
            y=150 + i * 15,
        )

    print("\n[TEST] Running Interceptor Chain on Shahed-136 simulation...\n")

    result = chain.run_chain(
        target_id="T-001",
        target_speed_kmh=185,
        target_distance_km=3.2,
        target_bearing_deg=42,
        target_x=1200,
        target_y=600,
        target_type="fixed_wing",
        async_dispatch=False,
    )

    print(f"  Target:       T-001 (Shahed-136)")
    print(f"  Final Status: {result['final_status']}")
    for phase_name, phase_data in result['phases'].items():
        print(f"\n  ── {phase_name} ──")
        for k, v in phase_data.items():
            print(f"    {k:25s}: {v}")

    print(f"\n  Unit Status:")
    for u in chain.status()['units']:
        print(f"    Unit-{u['unit_id']}: {u['state']}")

    print("\n✅ Interceptor Chain test complete.")
