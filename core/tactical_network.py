import time
import math
from database import db

# ════════════════════════════════════════════════════════════════════════════
# MCDIS MULTI-SITE TACTICAL NETWORK
# Handles Mesh Communication, Node Redundancy, and Target Handoff Protocols.
# ════════════════════════════════════════════════════════════════════════════

class TacticalNode:
    def __init__(self, node_id, lat, lon, range_km):
        self.node_id = node_id
        self.lat = lat
        self.lon = lon
        self.range_km = range_km
        self.is_active = True
        self.tracked_targets = {}  # target_id -> last_seen_time

class NetworkController:
    """Manages the distributed Mesh Network of C2 nodes."""
    def __init__(self):
        # Default deployment: 3 nodes protecting a strategic perimeter (e.g., Airport)
        self.nodes = {
            "NODE-ALPHA": TacticalNode("NODE-ALPHA", 30.1234, 31.4567, 15.0), # HQ
            "NODE-BRAVO": TacticalNode("NODE-BRAVO", 30.1500, 31.4800, 10.0), # FWD
            "NODE-CHARLIE": TacticalNode("NODE-CHARLIE", 30.1000, 31.4900, 10.0) # SEA
        }
        self.primary_c2 = "NODE-ALPHA"
        
    def check_redundancy(self):
        """If the primary HQ node fails, seamlessly promote the next available node."""
        if not self.nodes[self.primary_c2].is_active:
            for n_id, node in self.nodes.items():
                if node.is_active:
                    db.log_event("NETWORK_FAILOVER", "MESH_CONTROLLER", f"Primary C2 down. Promoting {n_id} to Primary.")
                    self.primary_c2 = n_id
                    return
            db.log_event("SYSTEM_FAILURE", "MESH_CONTROLLER", "CRITICAL: All C2 Nodes Offline!")

    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """Haversine formula to calculate distance between two GPS coordinates."""
        R = 6371.0 # Earth radius in km
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def determine_best_node(self, target_lat, target_lon):
        """Finds the active node closest to the target."""
        best_node = None
        min_dist = float('inf')
        
        for n_id, node in self.nodes.items():
            if node.is_active:
                dist = self.calculate_distance(target_lat, target_lon, node.lat, node.lon)
                if dist < node.range_km and dist < min_dist:
                    min_dist = dist
                    best_node = n_id
                    
        return best_node

    def execute_handoff(self, target_id, current_node_id, target_lat, target_lon):
        """
        Handoff Protocol: When a target moves out of range of Node 1, 
        smoothly transfer tracking responsibility to Node 2.
        """
        best_node = self.determine_best_node(target_lat, target_lon)
        
        if best_node and best_node != current_node_id:
            # Transfer target data (simulated)
            self.nodes[best_node].tracked_targets[target_id] = time.time()
            if target_id in self.nodes[current_node_id].tracked_targets:
                del self.nodes[current_node_id].tracked_targets[target_id]
                
            db.log_event("TARGET_HANDOFF", "MESH_CONTROLLER", f"Target {target_id} transferred from {current_node_id} to {best_node}")
            return best_node
            
        return current_node_id

mesh_network = NetworkController()
