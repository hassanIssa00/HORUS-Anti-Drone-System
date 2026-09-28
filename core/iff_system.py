import hashlib
import time
import os
import sqlite3

# This module simulates a cryptographic Transponder-based IFF (Identification Friend or Foe)
# It uses Challenge-Response authentication to verify friendly units.

class IFFSystem:
    def __init__(self, db_path="mcdis_logs.db"):
        self.db_path = db_path
        self._ensure_table()

    def _get_conn(self):
        return sqlite3.connect(self.db_path, timeout=10)

    def _ensure_table(self):
        """Ensure the IFF table supports crypto keys."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            # Upgrade existing table if needed
            cursor.execute("ALTER TABLE iff_whitelist ADD COLUMN crypto_key TEXT")
            conn.commit()
        except Exception:
            pass # Column already exists
        finally:
            if 'conn' in locals():
                conn.close()

    def register_friendly_unit(self, entity_name, mac_address, rf_signature):
        """Registers a friendly unit with an auto-generated cryptographic key."""
        # Generate a secure random key for the transponder
        crypto_key = hashlib.sha256(os.urandom(32)).hexdigest()
        
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO iff_whitelist (mac_address, rf_signature, entity_name, auth_level, crypto_key)
                VALUES (?, ?, ?, 'FRIENDLY', ?)
            ''', (mac_address, rf_signature, entity_name, crypto_key))
            conn.commit()
            return {"status": "success", "entity": entity_name, "crypto_key": crypto_key}
        except sqlite3.IntegrityError:
            return {"status": "error", "message": "Unit MAC or RF already registered."}
        except Exception as e:
            return {"status": "error", "message": str(e)}
        finally:
            conn.close()

    def generate_challenge(self):
        """Generates a time-based challenge string sent to the target."""
        return hashlib.md5(str(time.time()).encode()).hexdigest()

    def verify_target(self, mac_address, rf_signature, challenge, encrypted_response):
        """
        Cryptographic handshake verification.
        The target must respond with SHA256(Challenge + Target_Secret_Key).
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Check if the unit's hardware signature is in the whitelist
        cursor.execute("SELECT entity_name, crypto_key FROM iff_whitelist WHERE mac_address=? OR rf_signature=?", (mac_address, rf_signature))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return {"iff_status": "HOSTILE", "reason": "Not in whitelist"}
            
        entity_name, secret_key = row
        
        if not secret_key:
             return {"iff_status": "UNKNOWN", "reason": "No crypto key configured"}

        # Validate the cryptographic response
        expected_hash = hashlib.sha256((challenge + secret_key).encode()).hexdigest()
        
        if expected_hash == encrypted_response:
            return {"iff_status": "FRIENDLY", "entity": entity_name}
        else:
            return {"iff_status": "HOSTILE", "reason": "Cryptographic Handshake Failed (Spoofing Detected)"}

# Singleton instance
iff_engine = IFFSystem()
