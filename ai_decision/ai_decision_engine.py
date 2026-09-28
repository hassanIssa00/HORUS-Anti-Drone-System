# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║  MCDIS — AI Tactical Decision Engine v1.0                           ║
║  طبقة اتخاذ القرار الذكية                                           ║
╠══════════════════════════════════════════════════════════════════════╣
║  Pipeline:                                                           ║
║    1. Feature Extraction  ← detection data (class, speed, conf...)  ║
║    2. ML Inference        ← Random Forest Classifier (trained)      ║
║    3. Decision Output     ← countermeasure mode + confidence        ║
║    4. Action Dispatch     ← fires command to countermeasure engine  ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import os, sys, time, json, threading, pickle, logging
import numpy as np
from datetime import datetime
from pathlib import Path
from collections import deque

# ── scikit-learn (ML backbone) ────────────────────────────────────────
try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.preprocessing import LabelEncoder, StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, accuracy_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("[AI-DECISION] WARNING: scikit-learn not installed — using rule-based fallback")

# ── Paths ─────────────────────────────────────────────────────────────
_THIS_DIR   = Path(__file__).parent
MODEL_PATH  = _THIS_DIR / "ai_decision_model.pkl"
SCALER_PATH = _THIS_DIR / "ai_decision_scaler.pkl"
LABEL_PATH  = _THIS_DIR / "ai_decision_labels.pkl"
LOG_PATH    = _THIS_DIR / "ai_decisions.jsonl"

logging.basicConfig(level=logging.INFO,
    format="[AI-DECISION] %(asctime)s %(message)s",
    datefmt="%H:%M:%S")
log = logging.getLogger("AI-DECISION")

# ══════════════════════════════════════════════════════════════════════
#  LABEL DEFINITIONS
#  What action should the AI pick?
# ══════════════════════════════════════════════════════════════════════
ACTIONS = [
    "MONITOR",          # Low threat — watch only
    "JAM_RF",           # RF jamming on control link
    "JAM_GPS",          # GPS denial
    "GPS_OVERRIDE",     # GPS spoofing → force RTH
    "ACOUSTIC_ATTACK",  # MEMS gyro disruption
    "INTERCEPT_DRONE",  # Launch interceptor
    "NET_PROJECTILE",   # Physical capture net
    "BROADBAND_JAM",    # Wide-spectrum (swarm)
    "MISSILE",          # Kinetic kill
    "NONE",             # False positive / bird
]

# ══════════════════════════════════════════════════════════════════════
#  SYNTHETIC TRAINING DATA GENERATOR
#  Builds realistic labeled dataset without needing real engagement logs
# ══════════════════════════════════════════════════════════════════════

CLASS_PROFILES = {
    # class_name: (priority, jammable, gps_dep, fiber, base_action)
    "shahed_136":         (100, 0, 0, 0, "MISSILE"),
    "fpv_suicide":        (98,  1, 0, 1, "MISSILE"),
    "military_fixed_wing":(90,  1, 0, 0, "MISSILE"),
    "wing_loong":         (88,  1, 0, 0, "MISSILE"),
    "military_rotor":     (85,  1, 0, 0, "INTERCEPT_DRONE"),
    "swarm_unit":         (80,  1, 1, 0, "BROADBAND_JAM"),
    "dji_large":          (70,  1, 1, 0, "GPS_OVERRIDE"),
    "dji_mini":           (60,  1, 1, 0, "JAM_RF"),
    "generic_commercial": (55,  1, 1, 0, "JAM_RF"),
    "micro_nano":         (40,  1, 0, 0, "ACOUSTIC_ATTACK"),
    "bird":               (0,   0, 0, 0, "NONE"),
    "fixed_aircraft":     (0,   0, 0, 0, "MONITOR"),
}

def _encode_class(class_name: str) -> list:
    """One-hot encode drone class."""
    classes = list(CLASS_PROFILES.keys())
    vec = [0] * len(classes)
    if class_name in classes:
        vec[classes.index(class_name)] = 1
    return vec

def generate_training_data(n_samples: int = 5000) -> tuple:
    """
    Generate synthetic training dataset.
    Each sample = feature vector describing a detected threat.
    Label = correct countermeasure action.
    """
    import random
    rng = random.Random(42)
    np_rng = np.random.default_rng(42)

    X, y = [], []

    for _ in range(n_samples):
        # Pick a random class
        cls = rng.choice(list(CLASS_PROFILES.keys()))
        priority, jammable, gps_dep, fiber, base_action = CLASS_PROFILES[cls]

        # Add realistic noise to features
        speed_ms    = float(np.clip(np_rng.normal(priority * 0.4, 10), 0, 200))
        confidence  = float(np.clip(np_rng.normal(75, 15), 10, 99))
        track_age   = float(np_rng.uniform(0.5, 120))
        straightness= float(np.clip(np_rng.normal(0.8 if priority > 70 else 0.5, 0.15), 0, 1))
        altitude_m  = float(np.clip(np_rng.normal(100 if priority > 70 else 50, 30), 5, 500))
        size_px     = float(np.clip(np_rng.normal(300 if priority > 70 else 150, 80), 20, 2000))
        night_mode  = int(np_rng.random() < 0.3)
        swarm_count = int(np_rng.poisson(3) if cls == "swarm_unit" else 1)
        missile_rdy = int(np_rng.random() < 0.8)
        intercept_rdy = int(np_rng.random() < 0.9)

        # Class encoding
        class_vec = _encode_class(cls)

        feature = [
            priority / 100.0,
            jammable,
            gps_dep,
            fiber,
            speed_ms / 200.0,
            confidence / 100.0,
            min(track_age / 60.0, 1.0),
            straightness,
            altitude_m / 500.0,
            size_px / 2000.0,
            night_mode,
            swarm_count / 10.0,
            missile_rdy,
            intercept_rdy,
        ] + class_vec

        # Determine correct action with logic
        action = base_action
        if fiber and action not in ("MISSILE", "NET_PROJECTILE"):
            action = "MISSILE"
        if not missile_rdy and action == "MISSILE":
            action = "INTERCEPT_DRONE" if intercept_rdy else "JAM_RF"
        if cls == "bird":
            action = "NONE"
        if cls == "swarm_unit" and swarm_count > 5:
            action = "BROADBAND_JAM"

        X.append(feature)
        y.append(action)

    return np.array(X, dtype=np.float32), np.array(y)


# ══════════════════════════════════════════════════════════════════════
#  AI DECISION ENGINE — CORE CLASS
# ══════════════════════════════════════════════════════════════════════

class AIDecisionEngine:
    """
    Trained Random Forest classifier that selects the optimal
    countermeasure for any given threat detection.

    Usage:
        engine = AIDecisionEngine()
        engine.train()   # one-time, saves model to disk
        decision = engine.decide(detection_dict)
    """

    def __init__(self, auto_train: bool = True):
        self.clf      = None
        self.scaler   = StandardScaler() if SKLEARN_AVAILABLE else None
        self.le       = LabelEncoder()   if SKLEARN_AVAILABLE else None
        self.trained  = False
        self._lock    = threading.Lock()

        # Decision history for dashboard
        self.history  = deque(maxlen=200)
        self.cycle    = 0

        if auto_train:
            if MODEL_PATH.exists():
                self._load_model()
            else:
                log.info("No saved model found — training from scratch...")
                self.train()

    # ── Training ──────────────────────────────────────────────────────

    def train(self, n_samples: int = 6000):
        if not SKLEARN_AVAILABLE:
            log.warning("scikit-learn not available — skipping training")
            return False

        log.info(f"Generating {n_samples} synthetic training samples...")
        X, y_raw = generate_training_data(n_samples)

        y = self.le.fit_transform(y_raw)
        X_scaled = self.scaler.fit_transform(X)

        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42, stratify=y
        )

        log.info("Training Random Forest classifier...")
        self.clf = RandomForestClassifier(
            n_estimators=200,
            max_depth=20,
            min_samples_leaf=2,
            class_weight='balanced',
            n_jobs=-1,
            random_state=42
        )
        self.clf.fit(X_train, y_train)

        # Evaluate
        y_pred = self.clf.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        log.info(f"Model accuracy: {acc*100:.1f}%")
        log.info("\n" + classification_report(
            y_test, y_pred,
            target_names=self.le.classes_,
            zero_division=0
        ))

        self._save_model()
        self.trained = True
        return True

    # ── Persistence ───────────────────────────────────────────────────

    def _save_model(self):
        with open(MODEL_PATH,  'wb') as f: pickle.dump(self.clf,    f)
        with open(SCALER_PATH, 'wb') as f: pickle.dump(self.scaler, f)
        with open(LABEL_PATH,  'wb') as f: pickle.dump(self.le,     f)
        log.info(f"Model saved → {MODEL_PATH}")

    def _load_model(self):
        try:
            with open(MODEL_PATH,  'rb') as f: self.clf    = pickle.load(f)
            with open(SCALER_PATH, 'rb') as f: self.scaler = pickle.load(f)
            with open(LABEL_PATH,  'rb') as f: self.le     = pickle.load(f)
            self.trained = True
            log.info("Trained model loaded from disk ✓")
        except Exception as e:
            log.error(f"Failed to load model: {e} — retraining...")
            self.train()

    # ── Feature Extraction ────────────────────────────────────────────

    def _extract_features(self, det: dict, env: dict = None) -> np.ndarray:
        """
        Convert a detection dictionary into the ML feature vector.

        det keys expected:
            class, conf, speed_kmh, bearing, speed_pxps,
            track_id, threat, bbox, coasting, ...
        """
        env = env or {}
        cls = det.get('class', 'generic_commercial').lower()

        # Lookup class profile
        profile = CLASS_PROFILES.get(cls, CLASS_PROFILES['generic_commercial'])
        priority, jammable, gps_dep, fiber, _ = profile

        speed_ms    = det.get('speed_kmh', 0) / 3.6          # km/h → m/s
        confidence  = det.get('conf', 50)
        track_age   = det.get('track_age_sec', 5.0)
        straightness= det.get('straightness', 0.8)

        bbox = det.get('bbox', [0, 0, 100, 100])
        w    = abs(bbox[2] - bbox[0])
        h    = abs(bbox[3] - bbox[1])
        size_px = w * h

        night_mode   = int(det.get('night_mode', False))
        swarm_count  = int(det.get('swarm_count', 1))
        missile_rdy  = int(env.get('missile_ready', True))
        intercept_rdy= int(env.get('interceptor_ready', True))

        class_vec = _encode_class(cls)

        features = [
            priority / 100.0,
            float(jammable),
            float(gps_dep),
            float(fiber),
            min(speed_ms / 200.0, 1.0),
            confidence / 100.0,
            min(track_age / 60.0, 1.0),
            float(straightness),
            0.2,                         # altitude placeholder (no radar)
            min(size_px / 2000.0, 1.0),
            float(night_mode),
            min(swarm_count / 10.0, 1.0),
            float(missile_rdy),
            float(intercept_rdy),
        ] + class_vec

        return np.array(features, dtype=np.float32).reshape(1, -1)

    # ── Inference ─────────────────────────────────────────────────────

    def decide(self, det: dict, env: dict = None) -> dict:
        """
        Main inference call.
        Returns dict with: action, confidence, probabilities, reasoning.
        """
        with self._lock:
            self.cycle += 1

        cls = det.get('class', 'unknown')
        threat = det.get('threat', 'LOW')

        # ── Rule-Based Fallback (no sklearn or not trained) ──────────
        if not SKLEARN_AVAILABLE or not self.trained or self.clf is None:
            return self._rule_based_decide(det, env)

        # ── ML Inference ─────────────────────────────────────────────
        try:
            feat     = self._extract_features(det, env)
            feat_sc  = self.scaler.transform(feat)
            proba    = self.clf.predict_proba(feat_sc)[0]
            pred_idx = int(np.argmax(proba))
            action   = self.le.inverse_transform([pred_idx])[0]
            ml_conf  = float(proba[pred_idx])

            # Build probability map
            prob_map = {
                self.le.inverse_transform([i])[0]: round(float(p), 3)
                for i, p in enumerate(proba)
            }

            result = {
                "action":         action,
                "confidence":     round(ml_conf * 100, 1),
                "method":         "ML_RANDOM_FOREST",
                "target_class":   cls,
                "threat_level":   threat,
                "cycle":          self.cycle,
                "timestamp":      datetime.now().isoformat(),
                "probabilities":  prob_map,
                "reasoning":      self._build_reasoning(det, action, ml_conf),
            }
        except Exception as e:
            log.warning(f"ML inference failed ({e}) — using rule-based fallback")
            result = self._rule_based_decide(det, env)

        # Persist to history & log file
        self._log_decision(result)
        return result

    # ── Rule-Based Fallback ───────────────────────────────────────────

    def _rule_based_decide(self, det: dict, env: dict = None) -> dict:
        """Deterministic decision tree — always available."""
        env = env or {}
        cls      = det.get('class', 'generic_commercial').lower()
        conf     = det.get('conf', 50)
        speed_ms = det.get('speed_kmh', 0) / 3.6

        profile  = CLASS_PROFILES.get(cls, CLASS_PROFILES['generic_commercial'])
        priority, jammable, gps_dep, fiber, base_action = profile

        action = base_action

        # Override rules
        if fiber and action not in ("MISSILE", "NET_PROJECTILE"):
            action = "MISSILE"
        if not env.get('missile_ready', True) and action == "MISSILE":
            action = "INTERCEPT_DRONE"
        if cls == "bird" or conf < 20:
            action = "NONE"
        if speed_ms > 80 and priority >= 95:
            action = "MISSILE"

        return {
            "action":       action,
            "confidence":   75.0,
            "method":       "RULE_BASED_FALLBACK",
            "target_class": cls,
            "threat_level": det.get('threat', 'LOW'),
            "cycle":        self.cycle,
            "timestamp":    datetime.now().isoformat(),
            "probabilities":{action: 0.75},
            "reasoning":    self._build_reasoning(det, action, 0.75),
        }

    # ── Reasoning Builder ─────────────────────────────────────────────

    def _build_reasoning(self, det: dict, action: str, conf: float) -> list:
        """Return human-readable reasons for the decision."""
        reasons = []
        cls      = det.get('class', 'unknown')
        speed    = det.get('speed_kmh', 0)
        threat   = det.get('threat', 'LOW')
        profile  = CLASS_PROFILES.get(cls, CLASS_PROFILES['generic_commercial'])
        priority, jammable, gps_dep, fiber, _ = profile

        reasons.append(f"Class '{cls.upper()}' — base priority {priority}/100")

        if priority >= 95:
            reasons.append("CRITICAL threat: loitering munition / FPV suicide drone")
        elif priority >= 70:
            reasons.append("HIGH threat: military or commercial UAS")
        elif priority >= 40:
            reasons.append("ELEVATED threat: commercial drone detected")
        else:
            reasons.append("LOW / FALSE POSITIVE — no engagement required")

        if fiber:
            reasons.append("Fiber-guided: RF jamming ineffective → kinetic only")
        if not jammable:
            reasons.append("Not jammable: inertial / pre-programmed navigation")
        if gps_dep:
            reasons.append("GPS-dependent: spoofing viable for RTH hijack")
        if speed > 150:
            reasons.append(f"High speed ({speed:.0f} km/h): rapid response required")

        ACTION_DESC = {
            "MISSILE":         "Kinetic missile engagement — maximum lethality",
            "INTERCEPT_DRONE": "Deploy interceptor drone — precision capture",
            "BROADBAND_JAM":   "Wide-spectrum jamming — effective vs swarms",
            "JAM_RF":          "RF control link jamming on 2.4/5.8 GHz",
            "GPS_OVERRIDE":    "GPS spoofing → force Return-to-Home",
            "ACOUSTIC_ATTACK": "Acoustic resonance attack on MEMS gyroscope",
            "NET_PROJECTILE":  "Net launcher — physical capture system",
            "JAM_GPS":         "GPS L1/L2 denial — navigation blackout",
            "MONITOR":         "Monitor only — insufficient threat level",
            "NONE":            "No action — false positive or friendly",
        }
        reasons.append(f"Selected: {action} — {ACTION_DESC.get(action, '')}")
        reasons.append(f"AI Confidence: {conf*100:.1f}%")
        return reasons

    # ── Logging ───────────────────────────────────────────────────────

    def _log_decision(self, result: dict):
        self.history.append(result)
        try:
            with open(LOG_PATH, 'a') as f:
                f.write(json.dumps(result) + "\n")
        except Exception:
            pass

    # ── Batch Analysis ────────────────────────────────────────────────

    def analyze_frame_detections(self, detections: list, env: dict = None) -> list:
        """
        Analyze all detections from a single frame.
        Returns list of (detection, decision) pairs sorted by priority.
        """
        results = []
        for det in detections:
            decision = self.decide(det, env)
            results.append({
                "detection": det,
                "decision":  decision,
            })

        # Sort: highest-confidence threats first
        results.sort(
            key=lambda r: r['decision']['confidence'],
            reverse=True
        )
        return results

    # ── Status ────────────────────────────────────────────────────────

    def status(self) -> dict:
        return {
            "trained":       self.trained,
            "method":        "ML_RANDOM_FOREST" if (SKLEARN_AVAILABLE and self.trained) else "RULE_BASED",
            "model_path":    str(MODEL_PATH),
            "model_exists":  MODEL_PATH.exists(),
            "decisions_made":self.cycle,
            "history_count": len(self.history),
            "actions":       ACTIONS,
        }

    def retrain(self):
        """Force retrain from fresh synthetic data."""
        log.info("Force retraining AI model...")
        if MODEL_PATH.exists(): MODEL_PATH.unlink()
        return self.train()


# ══════════════════════════════════════════════════════════════════════
#  SINGLETON INSTANCE (import and use directly)
# ══════════════════════════════════════════════════════════════════════

_engine_instance = None
_engine_lock     = threading.Lock()

def get_ai_engine() -> AIDecisionEngine:
    global _engine_instance
    if _engine_instance is None:
        with _engine_lock:
            if _engine_instance is None:
                _engine_instance = AIDecisionEngine(auto_train=True)
    return _engine_instance


# ══════════════════════════════════════════════════════════════════════
#  STANDALONE TEST
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 65)
    print("  MCDIS AI Decision Engine — Standalone Test")
    print("=" * 65)

    engine = AIDecisionEngine(auto_train=True)

    test_detections = [
        {"class": "shahed_136",          "conf": 92, "speed_kmh": 180, "threat": "CRITICAL", "bbox": [400,200,500,300]},
        {"class": "fpv_suicide",         "conf": 88, "speed_kmh": 120, "threat": "CRITICAL", "bbox": [300,100,380,180]},
        {"class": "swarm_unit",          "conf": 75, "speed_kmh": 60,  "threat": "HIGH",     "bbox": [200,150,260,210], "swarm_count": 8},
        {"class": "dji_large",           "conf": 81, "speed_kmh": 40,  "threat": "HIGH",     "bbox": [600,300,700,400]},
        {"class": "generic_commercial",  "conf": 65, "speed_kmh": 30,  "threat": "ELEVATED", "bbox": [100,200,150,250]},
        {"class": "bird",                "conf": 55, "speed_kmh": 20,  "threat": "LOW",      "bbox": [500,400,540,440]},
    ]

    env = {"missile_ready": True, "interceptor_ready": True, "gps_spoof_ready": True}

    print("[TEST] Running AI decisions on 6 test threats...\n")
    for det in test_detections:
        decision = engine.decide(det, env)
        print(f"  Target: {det['class']:25s} -> ACTION: {decision['action']:18s} | Confidence: {decision['confidence']}% | Method: {decision['method']}")
        for r in decision['reasoning']:
            print(f"           * {r}")
        print()

    print("\n[AI ENGINE STATUS]")
    for k, v in engine.status().items():
        print(f"  {k}: {v}")

    print("\n✅ AI Decision Engine test complete.")
