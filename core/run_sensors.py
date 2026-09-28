"""
╔══════════════════════════════════════════════════════════════════════╗
║  MCDIS — Multi-Modal Counter-Drone Intelligence System              ║
║  Module: Electronic Warfare & Signal Intelligence Suite              ║
║  Version: 2.0                                                        ║
║  Classification: UNCLASSIFIED // FOR OFFICIAL USE ONLY               ║
╠══════════════════════════════════════════════════════════════════════╣
║  Subsystems:                                                         ║
║    1. RF Scanner — Passive radio frequency spectrum surveillance     ║
║    2. Acoustic Detector — MFCC-based rotor noise classification      ║
║    3. GPS Spoof Monitor — Satellite position integrity validation    ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import numpy as np
import time
import threading
import sys
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from database import db

# ══════════════════════════════════════════════════════════════════════
#  CPU OPTIMISATION BLOCK  —  sensors are pure compute, no GPU needed.
#  Use all available CPU cores via a shared thread pool.
# ══════════════════════════════════════════════════════════════════════
_CPU_CORES  = os.cpu_count() or 4
_THREAD_POOL = ThreadPoolExecutor(
    max_workers=_CPU_CORES,
    thread_name_prefix="MCDIS-Sensor"
)
print(f"[SENSOR HW] CPU Cores: {_CPU_CORES} | ThreadPool workers: {_CPU_CORES}")

# Optional audio dependencies
try:
    import sounddevice as sd
    import librosa
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False


# ══════════════════════════════════════════════════════════════════════
#  RF SCANNER — Passive Radio Frequency Surveillance
# ══════════════════════════════════════════════════════════════════════

class RFScanner:
    """
    مسح طيف الترددات اللاسلكية بحثاً عن بروتوكولات التحكم في الدرونز.
    يستهدف النطاقات 2.4GHz و 5.8GHz وبروتوكولات FHSS/DSSS.

    في البيئة الحقيقية: يتم استبدال المحاكاة بـ SDR (Software Defined Radio)
    مثل RTL-SDR أو HackRF لالتقاط الإشارات الفعلية.
    """

    SCAN_INTERVAL = 15  # ثانية بين كل مسح
    FREQ_BANDS = [
        {"name": "2.4GHz ISM", "range": "2400-2483.5 MHz", "protocols": ["WiFi", "FHSS", "OcuSync"]},
        {"name": "5.8GHz ISM", "range": "5725-5875 MHz", "protocols": ["DJI V2", "Analog FPV"]},
        {"name": "900MHz",     "range": "902-928 MHz",     "protocols": ["LoRa", "ExpressLRS"]},
    ]

    def __init__(self):
        self._running = False
        self._thread = None
        self._detection_count = 0
        db.log_event("SENSOR_INIT", "RF_SCANNER", "RF spectrum surveillance initialized")
        print("[RF_SCANNER] 📡 Passive RF surveillance module initialized.")
        print(f"[RF_SCANNER]    Monitoring {len(self.FREQ_BANDS)} frequency bands")

    def start(self):
        """بدء المسح في Thread مستقل"""
        self._running = True
        self._thread = threading.Thread(target=self._scan_loop, daemon=True, name="RF-Scanner")
        self._thread.start()

    def stop(self):
        """إيقاف المسح"""
        self._running = False

    def _scan_loop(self):
        """حلقة المسح الرئيسية — كل نطاق يُمسح بالتوازي على core منفصل"""
        while self._running:
            time.sleep(self.SCAN_INTERVAL)
            # Submit each band scan to the global thread pool (parallel CPU cores)
            futures = [_THREAD_POOL.submit(self._scan_single_band, band)
                       for band in self.FREQ_BANDS]
            for f in futures:
                try:
                    f.result(timeout=5)
                except Exception:
                    pass

    def _scan_single_band(self, band):
        """Scan one frequency band — runs on a CPU thread pool worker."""
        if not self._running:
            return
        detection_probability = np.random.random()
        if detection_probability > 0.6:
            confidence = np.random.randint(72, 97)
            protocol = np.random.choice(band["protocols"])
            signal_strength = np.random.randint(-85, -30)  # dBm

            self._detection_count += 1
            threat_level = "CRITICAL" if confidence > 90 else "HIGH"

            details = (
                f"Protocol: {protocol} | "
                f"Band: {band['name']} | "
                f"Signal: {signal_strength}dBm | "
                f"Type: FHSS Hopping Pattern"
            )
            print(
                f"\n[\u26a0\ufe0f  RF ALERT] Hostile signal intercepted on {band['name']}"
                f"\n    Protocol: {protocol} | Confidence: {confidence}% | "
                f"Signal: {signal_strength}dBm"
            )
            db.log_detection(
                sensor_type="RF_SENSOR",
                target_id=f"RF_SIG_{self._detection_count:04d}",
                threat_level=threat_level,
                confidence=confidence,
                details=details
            )

    def _execute_scan(self):
        """Legacy sequential scan — kept for backward compatibility."""
        for band in self.FREQ_BANDS:
            self._scan_single_band(band)

    @property
    def is_running(self):
        return self._running


# ══════════════════════════════════════════════════════════════════════
#  ACOUSTIC DETECTOR — Rotor Noise Classification
# ══════════════════════════════════════════════════════════════════════

class AcousticDetector:
    """
    تحليل الصوت المحيط باستخدام خوارزميات MFCC لتمييز
    طنين محركات الدرونز من ضوضاء الخلفية.

    يعتمد على Mel-Frequency Cepstral Coefficients — نفس التقنية
    المستخدمة في أنظمة التعرف على الكلام ولكن مكيفة لاكتشاف
    التوقيعات الصوتية لمراوح الـ Quadcopter.
    """

    SAMPLE_RATE = 22050
    MFCC_COEFFICIENTS = 13
    VOLUME_THRESHOLD = 20.0
    SCORE_THRESHOLD = 0.3

    def __init__(self):
        self._running = False
        self._thread = None
        self._detection_count = 0
        db.log_event("SENSOR_INIT", "ACOUSTIC_ARRAY", "Acoustic detection array initialized")
        print("[ACOUSTIC] 🎙️  Acoustic intelligence array initialized.")
        print(f"[ACOUSTIC]    Sample rate: {self.SAMPLE_RATE}Hz | MFCC coefficients: {self.MFCC_COEFFICIENTS}")

    def start(self):
        """بدء الاستماع في Thread مستقل"""
        if not AUDIO_AVAILABLE:
            print("[ACOUSTIC] ⚠️  Audio libraries unavailable (sounddevice/librosa). Skipping.")
            db.log_event("SENSOR_ERROR", "ACOUSTIC_ARRAY", "Audio libraries not available")
            return

        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True, name="Acoustic-Detector")
        self._thread.start()

    def stop(self):
        """إيقاف الاستماع"""
        self._running = False

    def _listen_loop(self):
        """حلقة الاستماع الرئيسية"""
        try:
            with sd.InputStream(
                callback=self._process_audio,
                channels=1,
                samplerate=self.SAMPLE_RATE
            ):
                while self._running:
                    time.sleep(0.5)
        except Exception as e:
            print(f"[ACOUSTIC] ❌ Microphone access failed: {e}")
            db.log_event("SENSOR_ERROR", "ACOUSTIC_ARRAY", f"Microphone error: {e}")

    def _process_audio(self, indata, frames, time_info, status):
        """
        معالجة كل frame صوتي وارد.
        يتم استخراج MFCC ومقارنتها بالتوقيعات المعروفة.
        """
        if not self._running:
            return

        audio_data = indata.flatten()

        # استخراج معاملات MFCC
        mfccs = librosa.feature.mfcc(
            y=audio_data,
            sr=self.SAMPLE_RATE,
            n_mfcc=self.MFCC_COEFFICIENTS
        )
        mfcc_mean = np.mean(mfccs.T, axis=0)

        # حساب مستوى الصوت
        volume = np.linalg.norm(audio_data) * 10

        if volume > self.VOLUME_THRESHOLD:
            # خوارزمية مقارنة التوقيع الصوتي
            score = np.abs(mfcc_mean[1]) / (np.abs(mfcc_mean[0]) + 1e-6)

            if score > self.SCORE_THRESHOLD:
                self._detection_count += 1
                confidence = min(int((score * 100) + 40), 99)
                threat_level = "HIGH" if confidence > 80 else "MEDIUM"

                details = f"MFCC Score: {score:.3f} | Volume: {volume:.1f} | Freq Profile: Rotor Harmonic"

                print(
                    f"\n[🚨 ACOUSTIC MATCH] Drone rotor signature isolated"
                    f"\n    Confidence: {confidence}% | MFCC Score: {score:.3f}"
                )

                db.log_detection(
                    sensor_type="ACOUSTIC_ARRAY",
                    target_id=f"ACOUSTIC_{self._detection_count:04d}",
                    threat_level=threat_level,
                    confidence=confidence,
                    details=details
                )

    @property
    def is_running(self):
        return self._running


# ══════════════════════════════════════════════════════════════════════
#  GPS SPOOF DETECTOR — Satellite Position Integrity Monitor
# ══════════════════════════════════════════════════════════════════════

class GPSSpoofDetector:
    """
    مراقبة سلامة إحداثيات GPS بحثاً عن هجمات التزييف (Spoofing).
    يكتشف القفزات اللامنطقية في الموقع التي تشير إلى
    محاولة اختراق إلكتروني لنظام تحديد المواقع.

    المعايير العسكرية: قفزة > 50 متر خلال ثانية
    بدون سرعة فعلية = هجوم GPS Spoofing.
    """

    MONITOR_INTERVAL = 20  # ثانية بين كل فحص
    BASE_COORDS = (30.0444, 31.2357)  # إحداثيات المركز الدفاعي (القاهرة)
    SPOOF_PROBABILITY = 0.33  # احتمال محاكاة هجوم

    def __init__(self):
        self._running = False
        self._thread = None
        self._last_coords = self.BASE_COORDS
        self._last_time = time.time()
        self._alert_count = 0
        db.log_event("SENSOR_INIT", "GPS_MONITOR", "GPS integrity monitor activated")
        print("[GPS_SEC]  🛡️  Satellite position integrity monitor activated.")
        print(f"[GPS_SEC]     Base coordinates: {self.BASE_COORDS}")

    def start(self):
        """بدء المراقبة في Thread مستقل"""
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True, name="GPS-Monitor")
        self._thread.start()

    def stop(self):
        """إيقاف المراقبة"""
        self._running = False

    def _monitor_loop(self):
        """حلقة المراقبة الرئيسية"""
        while self._running:
            time.sleep(self.MONITOR_INTERVAL)
            self._check_integrity()

    def _check_integrity(self):
        """
        فحص سلامة الإحداثيات.
        المحاكاة: يتم إنشاء قفزة عشوائية لاختبار النظام.
        """
        is_spoofed = np.random.random() < self.SPOOF_PROBABILITY

        if is_spoofed:
            self._alert_count += 1
            distance_jump = np.random.randint(50, 1500)  # meters
            bearing = np.random.randint(0, 360)

            details = (
                f"GPS Jump: {distance_jump}m @ {bearing}° | "
                f"Base: {self.BASE_COORDS} | "
                f"Type: Position Manipulation Attack"
            )

            print(
                f"\n[🛑 GPS SECURITY BREACH] Spoofing attack detected!"
                f"\n    Position jump: {distance_jump}m at bearing {bearing}°"
                f"\n    Classification: ELECTRONIC WARFARE ATTACK"
            )

            db.log_detection(
                sensor_type="GPS_MONITOR",
                target_id=f"SPOOF_{self._alert_count:04d}",
                threat_level="CRITICAL",
                confidence=99,
                details=details
            )

    @property
    def is_running(self):
        return self._running


# ══════════════════════════════════════════════════════════════════════
#  MAIN ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════

def main():
    """تهيئة وتشغيل جميع وحدات الاستخبارات الإلكترونية"""

    print("=" * 65)
    print("  MCDIS v2.0 — Electronic Warfare & SIGINT Suite")
    print("  Multi-Modal Counter-Drone Intelligence System")
    print("=" * 65)
    print()

    # تسجيل حدث بدء التشغيل
    db.log_event("SYSTEM_START", "SENSOR_SUITE", "All sensor pipelines initializing")

    # تهيئة الوحدات
    rf_scanner = RFScanner()
    acoustic = AcousticDetector()
    gps_monitor = GPSSpoofDetector()

    # بدء جميع الوحدات
    rf_scanner.start()
    gps_monitor.start()
    acoustic.start()

    print()
    print("[SYSTEM] ✅ All sensor pipelines are ACTIVE.")
    print("[SYSTEM]    Press Ctrl+C to initiate controlled shutdown.")
    print("=" * 65)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n")
        print("=" * 65)
        print("[SYSTEM] ⚠️  Controlled shutdown initiated...")

        rf_scanner.stop()
        acoustic.stop()
        gps_monitor.stop()

        db.log_event("SYSTEM_STOP", "SENSOR_SUITE", "Controlled shutdown completed")
        db.close()

        print("[SYSTEM] ✅ All sensors stopped. Database synced.")
        print("=" * 65)


if __name__ == "__main__":
    main()
