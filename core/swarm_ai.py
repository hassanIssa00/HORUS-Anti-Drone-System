import time
import math
from database import db

# ════════════════════════════════════════════════════════════════════════════
# MCDIS SWARM INTELLIGENCE ENGINE (Counter-Swarm Tactics)
# Implements "Collaborative Engagement" for Interceptor Drones.
# If attacked by a swarm (e.g., 10 Shaheds), this engine coordinates our 
# defensive interceptors to divide targets automatically without overlap.
# ════════════════════════════════════════════════════════════════════════════

class InterceptorUnit:
    def __init__(self, unit_id, status="IDLE"):
        self.unit_id = unit_id
        self.status = status # IDLE, ENGAGING, BINGO_FUEL, DESTROYED
        self.assigned_target = None
        self.ammo = 100 # percentage

class SwarmMeshNetwork:
    """
    Coordinates communication between interceptor drones using Stigmergy 
    (decentralized intelligence inspired by ants/bees).
    """
    def __init__(self):
        # We deploy 5 interceptor drones (e.g., Net-Guns or Kamikaze defenders)
        self.interceptors = [InterceptorUnit(f"DEFENDER-{i+1}") for i in range(5)]
        
    def get_available_units(self):
        return [u for u in self.interceptors if u.status == "IDLE" and u.ammo > 10]

    def coordinate_defense(self, hostile_targets):
        """
        Takes a list of hostile targets and optimally assigns them to available interceptors.
        Prevents two defenders from chasing the same target.
        """
        available_defenders = self.get_available_units()
        assignments = []
        
        # Sort targets by threat priority (assuming highest priority first)
        for target in hostile_targets:
            if not available_defenders:
                break # No more defenders available!
                
            # Assign the first available defender
            defender = available_defenders.pop(0)
            defender.status = "ENGAGING"
            defender.assigned_target = target['id']
            defender.ammo -= 20 # Using ammo/battery for the engagement
            
            assignments.append({
                "defender_id": defender.unit_id,
                "target_id": target['id'],
                "action": "INTERCEPT_VECTOR_LOCKED"
            })
            
            db.log_event(
                "SWARM_COLLABORATION", 
                "SWARM_ENGINE", 
                f"{defender.unit_id} locked onto {target['id']}. Avoiding overlap."
            )
            
        # If there are more targets than defenders, system must rely on DEW/HPM
        unassigned_count = len(hostile_targets) - len(assignments)
        
        return {
            "status": "ENGAGEMENT_PLANNED",
            "assignments": assignments,
            "unassigned_hostiles": unassigned_count,
            "recommendation": "FIRE HPM EMP" if unassigned_count > 0 else "MAINTAIN KINETIC INTERCEPT"
        }

swarm_ai_engine = SwarmMeshNetwork()
