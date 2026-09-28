"""
╔══════════════════════════════════════════════════════════════════════╗
║  MCDIS — Multi-Modal Counter-Drone Intelligence System              ║
║  Module: UNROCKER Acoustic Weapon System (MEMS IMU Attack)          ║
║  Classification: UNCLASSIFIED // FOR OFFICIAL USE ONLY               ║
╠══════════════════════════════════════════════════════════════════════╣
║  Description:                                                         ║
║    Based on KAIST's UNROCKER research (NDSS 2023).                   ║
║    Injects resonant acoustic waves (ultrasonic) directly into the     ║
║    target drone's MEMS Gyroscope to induce sampling jitter.           ║
║    Bypasses low-pass filters, destabilizing flight controller.        ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import time
import threading
import math
import random
import logging
from enum import Enum, auto

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("ACOUSTIC")

class EmitterState(Enum):
    STANDBY = auto()
    TARGETING = auto()
    INJECTING = auto()
    COOLING = auto()

class AcousticEmitter:
    """
    Directional acoustic emitter (e.g., LRAD or custom ultrasonic phased array).
    Targets specific resonant frequencies of common IMUs (e.g., InvenSense MPU-6000).
    """
    
    # Common MEMS Resonant Frequencies (kHz)
    IMU_PROFILES = {
        "dji_large": 27.3,       # Approx DJI resonant freq
        "dji_mini":  25.1,
        "fpv_suicide": 29.5,     # Often uses MPU-6000
        "generic_commercial": 26.0
    }

    def __init__(self, e_id: str):
        self.id = e_id
        self.state = EmitterState.STANDBY
        self.current_target = None
        self.target_freq_khz = 0.0
        self.azimuth = 0.0
        self.elevation = 0.0
        self._thread = None
        self._stop_event = threading.Event()
        
    def engage(self, target_id: str, drone_class: str, target_pos: tuple):
        if self.state not in (EmitterState.STANDBY, EmitterState.COOLING):
            log.warning(f"[🔊 ACOUSTIC {self.id}] Busy, cannot engage {target_id}.")
            return False
            
        self.current_target = target_id
        self.target_freq_khz = self.IMU_PROFILES.get(drone_class, 26.5)
        self.state = EmitterState.TARGETING
        self._stop_event.clear()
        
        # Calculate pointing angles
        x, y, z = target_pos
        self.azimuth = math.degrees(math.atan2(x, y))
        self.elevation = math.degrees(math.atan2(z, math.sqrt(x**2 + y**2)))
        
        log.info(f"[🔊 ACOUSTIC {self.id}] Targeting {target_id} ({drone_class}).")
        log.info(f"  └─ Azimuth: {self.azimuth:.1f}° | Elevation: {self.elevation:.1f}° | Freq: {self.target_freq_khz}kHz")
        
        self._thread = threading.Thread(target=self._injection_loop, daemon=True)
        self._thread.start()
        return True

    def _injection_loop(self):
        time.sleep(1.0) # Slew time to target
        self.state = EmitterState.INJECTING
        log.warning(f"[🔊 ACOUSTIC {self.id}] ⚡ INJECTING RESONANT WAVES at {self.target_freq_khz}kHz!")
        
        # Simulate acoustic attack over 5 seconds
        duration = 5
        for i in range(duration):
            if self._stop_event.is_set():
                break
            
            # Simulate sampling jitter increasing
            jitter = (i + 1) * random.uniform(10, 20)
            log.info(f"[🔊 ACOUSTIC {self.id}] Attacking... IMU sampling jitter: {jitter:.1f}% (Destabilizing)")
            time.sleep(1.0)
            
        if not self._stop_event.is_set():
            log.error(f"[🔊 ACOUSTIC {self.id}] Target {self.current_target} flight controller crashed. Target falling.")
            
        self.cease_fire()

    def cease_fire(self):
        self._stop_event.set()
        if self.state == EmitterState.INJECTING:
            log.info(f"[🔊 ACOUSTIC {self.id}] Ceasing acoustic injection. Cooling down.")
        self.state = EmitterState.COOLING
        time.sleep(2.0)
        self.state = EmitterState.STANDBY
        self.current_target = None


class AcousticWeaponSystem:
    """
    Manages acoustic emitters and connects to Countermeasure Engine.
    """
    def __init__(self, num_emitters: int = 2):
        self.emitters = [AcousticEmitter(f"LRAD-{i+1:02d}") for i in range(num_emitters)]
        log.info(f"[ACOUSTIC_SYS] Initialized {num_emitters} UNROCKER Acoustic Emitters.")
        
    def handle_engine_command(self, target, payload: dict):
        """Callback for the MCDIS Countermeasure Engine"""
        for e in self.emitters:
            if e.state == EmitterState.STANDBY:
                e.engage(target.id, target.best_class, target.position)
                return True
        log.warning("[ACOUSTIC_SYS] No acoustic emitters available.")
        return False

# Standalone Test
if __name__ == "__main__":
    aws = AcousticWeaponSystem(1)
    # Mock target object class
    class MockTarget:
        id = "T04"
        best_class = "fpv_suicide"
        position = (100, 50, 20)
        
    aws.handle_engine_command(MockTarget(), {})
    time.sleep(8)
