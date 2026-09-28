"""
╔══════════════════════════════════════════════════════════════════════╗
║  MCDIS — Multi-Modal Counter-Drone Intelligence System              ║
║  Module: Swarm Decoy System (Flocking Algorithm)                    ║
║  Classification: UNCLASSIFIED // FOR OFFICIAL USE ONLY               ║
╠══════════════════════════════════════════════════════════════════════╣
║  Description:                                                         ║
║    Deploys a swarm of autonomous mini-drones to act as decoys.        ║
║    Uses Reynolds-inspired flocking algorithms (Separation, Alignment, ║
║    Cohesion) based on EPFL's vswarm research to confuse enemy sensors.║
╚══════════════════════════════════════════════════════════════════════╝
"""

import time
import threading
import math
import random
import logging
from enum import Enum, auto

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("SWARM_DECOY")

class SwarmState(Enum):
    STANDBY = auto()
    DEPLOYING = auto()
    FLOCKING = auto()
    RECALLING = auto()

class Boid:
    """A single decoy drone within the swarm."""
    def __init__(self, x: float, y: float, z: float):
        self.pos = [x, y, z]
        self.vel = [random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-0.1, 0.1)]
        self.max_speed = 15.0

    def update(self):
        self.pos[0] += self.vel[0]
        self.pos[1] += self.vel[1]
        self.pos[2] += self.vel[2]

class SwarmDecoySystem:
    """
    Manages the deployment and kinematic simulation of a decoy swarm.
    """
    def __init__(self, max_swarms: int = 2):
        self.max_swarms = max_swarms
        self.active_swarms = {} # target_id -> list of Boids
        self.state = SwarmState.STANDBY
        self._threads = {}
        log.info(f"[🐝 SWARM_SYS] Initialized Swarm Decoy Controller. Capacity: {max_swarms} concurrent swarms.")

    def deploy_swarm(self, target_id: str, intercept_vector: tuple, num_boids: int = 15):
        if len(self.active_swarms) >= self.max_swarms:
            log.warning(f"[🐝 SWARM_SYS] Cannot deploy for {target_id}. Max swarms reached.")
            return False

        self.state = SwarmState.DEPLOYING
        log.info(f"[🐝 SWARM_SYS] Deploying swarm of {num_boids} decoys towards {intercept_vector} to confuse {target_id}...")
        
        # Initialize swarm around the base
        base_x, base_y, base_z = 0, 0, 0
        boids = [Boid(base_x + random.uniform(-5,5), base_y + random.uniform(-5,5), base_z) for _ in range(num_boids)]
        self.active_swarms[target_id] = boids
        
        t = threading.Thread(target=self._flocking_loop, args=(target_id, boids, intercept_vector), daemon=True)
        self._threads[target_id] = t
        t.start()
        return True

    def _flocking_loop(self, target_id: str, boids: list, target_vector: tuple):
        time.sleep(1.0)
        self.state = SwarmState.FLOCKING
        log.info(f"[🐝 SWARM_SYS] Swarm for {target_id} active. Flocking towards enemy vector.")
        
        tx, ty, tz = target_vector
        
        for step in range(10): # Simulate 10 seconds of active flocking
            if target_id not in self.active_swarms:
                break
                
            # Simulate Reynolds' Cohesion/Alignment towards target
            center_x = sum(b.pos[0] for b in boids) / len(boids)
            center_y = sum(b.pos[1] for b in boids) / len(boids)
            
            log.info(f"[🐝 SWARM_SYS] Swarm {target_id} flocking... Center of mass: ({center_x:.1f}, {center_y:.1f})")
            
            # Move boids
            for b in boids:
                # Steer towards target vector
                dx = tx - b.pos[0]
                dy = ty - b.pos[1]
                mag = math.sqrt(dx**2 + dy**2) + 0.001
                
                b.vel[0] += (dx/mag) * 2.0
                b.vel[1] += (dy/mag) * 2.0
                
                # Speed limit
                speed = math.sqrt(b.vel[0]**2 + b.vel[1]**2)
                if speed > b.max_speed:
                    b.vel[0] = (b.vel[0]/speed) * b.max_speed
                    b.vel[1] = (b.vel[1]/speed) * b.max_speed
                    
                b.update()
                
            time.sleep(1.0)

        self.recall_swarm(target_id)

    def recall_swarm(self, target_id: str):
        if target_id in self.active_swarms:
            log.info(f"[🐝 SWARM_SYS] Recalling swarm from {target_id}...")
            del self.active_swarms[target_id]
            self.state = SwarmState.RECALLING
            time.sleep(2.0)
            self.state = SwarmState.STANDBY
            log.info(f"[🐝 SWARM_SYS] Swarm returned and docked.")

    def handle_engine_command(self, target, payload: dict):
        """Callback for the MCDIS Countermeasure Engine"""
        return self.deploy_swarm(target.id, target.position)

# Standalone Test
if __name__ == "__main__":
    swarm = SwarmDecoySystem()
    class MockTarget:
        id = "HOSTILE-SWARM"
        position = (300, 400, 100)
        
    swarm.handle_engine_command(MockTarget(), {})
    time.sleep(15)
