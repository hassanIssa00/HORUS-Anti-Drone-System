import math
from database import db

# ════════════════════════════════════════════════════════════════════════════
# MCDIS RULES OF ENGAGEMENT (ROE) ENGINE
# Enforces tactical boundaries, geofencing (no-fire zones), and the 
# Kill Chain Confirmation protocol for lethal Hard Kill weapons.
# ════════════════════════════════════════════════════════════════════════════

class GeofenceZone:
    def __init__(self, name, lat, lon, radius_km, zone_type="NO_FIRE"):
        self.name = name
        self.lat = lat
        self.lon = lon
        self.radius_km = radius_km
        self.zone_type = zone_type # "NO_FIRE" (Civilian/Hospital) or "FREE_FIRE" (Military Base)

class ROE_Engine:
    def __init__(self):
        # Lethal weapons that require secondary Kill Chain Confirmation
        self.hard_kill_weapons = ["DEW_LASER", "HPM_MICROWAVE", "NET_GUN"]
        
        # Geofenced zones
        self.restricted_zones = [
            GeofenceZone("City Hospital", 30.1300, 31.4600, 2.0),
            GeofenceZone("Residential District 5", 30.1100, 31.4400, 3.5)
        ]
        
    def _calculate_distance(self, lat1, lon1, lat2, lon2):
        """Haversine distance in km."""
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def check_geofence(self, target_lat, target_lon, weapon_type):
        """Checks if firing a specific weapon at the target's location violates international/tactical law."""
        # Non-lethal EW (Soft Kill) is generally permitted anywhere, but Hard Kill is restricted.
        if weapon_type not in self.hard_kill_weapons:
            return {"allowed": True, "reason": "Soft Kill permitted"}
            
        for zone in self.restricted_zones:
            dist = self._calculate_distance(target_lat, target_lon, zone.lat, zone.lon)
            if dist <= zone.radius_km:
                return {
                    "allowed": False, 
                    "reason": f"ROE VIOLATION: Target inside restricted Geofence ({zone.name}). Hard Kill prohibited."
                }
                
        return {"allowed": True, "reason": "Target in clear airspace."}

    def evaluate_kill_chain(self, target_lat, target_lon, weapon_type, is_human_confirmed=False):
        """
        The core of the ROE Engine. Evaluates whether an engagement is legal and authorized.
        Prevents AI from going rogue with lethal weapons.
        """
        # Step 1: Check Geofencing Laws
        geo_check = self.check_geofence(target_lat, target_lon, weapon_type)
        if not geo_check["allowed"]:
            db.log_event("ROE_VIOLATION_BLOCKED", "ROE_ENGINE", f"Weapon: {weapon_type} blocked. {geo_check['reason']}")
            return {"authorized": False, "status": "ABORTED", "reason": geo_check["reason"]}
            
        # Step 2: Kill Chain Confirmation (Human-in-the-loop for Lethal Force)
        if weapon_type in self.hard_kill_weapons and not is_human_confirmed:
            db.log_event("KILL_CHAIN_HALTED", "ROE_ENGINE", f"AI attempted to use {weapon_type}. Awaiting human authorization.")
            return {
                "authorized": False, 
                "status": "PENDING_CONFIRMATION", 
                "reason": f"{weapon_type} requires explicit Operator Authorization."
            }
            
        # If all checks pass
        return {"authorized": True, "status": "AUTHORIZED", "reason": "All ROE criteria met."}

roe_manager = ROE_Engine()
