"""
╔══════════════════════════════════════════════════════════════════════╗
║  MCDIS — Multi-Modal Counter-Drone Intelligence System              ║
║  Module: Tactical Database Engine                                    ║
║  Version: 2.1 (Async Batch Optimized)                               ║
║  Classification: UNCLASSIFIED // FOR OFFICIAL USE ONLY               ║
╚══════════════════════════════════════════════════════════════════════╝

Centralized SQLite database for persistent storage of all sensor
detections, system events, and engagement actions. Designed for
high-frequency multi-threaded concurrent access.
"""

import sys
import sqlite3
import threading
import queue
import time
from datetime import datetime

# Fix Windows console encoding
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass


class MCDISDatabase:
    """Thread-safe tactical database engine for MCDIS sensor fusion."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, db_name="mcdis_logs.db"):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_name="mcdis_logs.db"):
        if self._initialized:
            return
        self._initialized = True
        self._db_name = db_name
        self._local = threading.local()
        self._write_lock = threading.Lock()
        
        # ── Async Batch Processing ──
        self._queue = queue.Queue()
        self._batch_thread = threading.Thread(target=self._batch_worker, daemon=True)
        self._batch_thread.start()
        
        self._init_schema()
        print(f"[DATABASE] ✅ Tactical database initialized (Async Batch Mode): {db_name}")

    def _get_conn(self):
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self._db_name, timeout=30)
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
        return self._local.conn

    def _init_schema(self):
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sensor_type TEXT NOT NULL,
                target_id TEXT NOT NULL,
                threat_level TEXT NOT NULL DEFAULT 'LOW',
                confidence INTEGER NOT NULL DEFAULT 0,
                timestamp DATETIME DEFAULT (datetime('now')),
                details TEXT DEFAULT '',
                node_id TEXT DEFAULT 'NODE-ALPHA',
                iff_status TEXT DEFAULT 'UNKNOWN',
                speed FLOAT DEFAULT 0.0,
                image_path TEXT DEFAULT ''
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS iff_whitelist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mac_address TEXT UNIQUE,
                rf_signature TEXT UNIQUE,
                entity_name TEXT NOT NULL,
                auth_level TEXT DEFAULT 'FRIENDLY'
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                pin_code TEXT NOT NULL,
                role TEXT NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                source TEXT NOT NULL,
                message TEXT,
                timestamp DATETIME DEFAULT (datetime('now'))
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tactical_commands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                command_type TEXT NOT NULL,
                target TEXT,
                status TEXT DEFAULT 'PENDING',
                operator TEXT DEFAULT 'C2_DASHBOARD',
                timestamp DATETIME DEFAULT (datetime('now'))
            )
        ''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_detections_timestamp ON detections(timestamp DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_detections_sensor ON detections(sensor_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_detections_threat ON detections(threat_level)')

        conn.commit()
        
        cursor.execute('DELETE FROM detections')
        cursor.execute('DELETE FROM tactical_commands')
        conn.commit()
        
        cursor.execute("SELECT COUNT(*) FROM user_roles")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO user_roles (username, pin_code, role) VALUES ('commander', '7777', 'COMMANDER')")
            cursor.execute("INSERT INTO user_roles (username, pin_code, role) VALUES ('operator', '1234', 'OPERATOR')")
            conn.commit()

    # ── High Frequency Logging ────────────────────────────────────

    def log_detection(self, sensor_type, target_id, threat_level, confidence, details="", node_id="NODE-ALPHA", iff_status="UNKNOWN", speed=0.0, image_path=""):
        """تسجيل اكتشاف جديد عبر إضافته لقائمة الانتظار (Async)"""
        try:
            self._queue.put({
                'sensor_type': str(sensor_type),
                'target_id': str(target_id),
                'threat_level': str(threat_level),
                'confidence': int(confidence),
                'details': str(details),
                'node_id': str(node_id),
                'iff_status': str(iff_status),
                'speed': float(speed),
                'image_path': str(image_path),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            return True
        except Exception as e:
            print(f"[DATABASE ERROR] log_detection: {e}")
            return False

    def _batch_worker(self):
        """خيط الخلفية لمعالجة الدفعات"""
        conn = sqlite3.connect(self._db_name, timeout=60)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        
        while True:
            batch = []
            try:
                # تجميع ما يصل لـ 50 عنصر أو الانتظار قليلاً
                while not self._queue.empty() and len(batch) < 50:
                    batch.append(self._queue.get_nowait())
            except:
                pass

            if batch:
                with self._write_lock:
                    try:
                        cursor = conn.cursor()
                        cursor.executemany('''
                            INSERT INTO detections 
                            (sensor_type, target_id, threat_level, confidence, timestamp, details, node_id, iff_status, speed, image_path)
                            VALUES (:sensor_type, :target_id, :threat_level, :confidence, :timestamp, :details, :node_id, :iff_status, :speed, :image_path)
                        ''', batch)
                        conn.commit()
                    except Exception as e:
                        print(f"[DATABASE ERROR] _batch_worker: {e}")
                        conn.rollback()
            
            time.sleep(1.0)

    # ── Standard Logging ──────────────────────────────────────────

    def log_event(self, event_type, source, message=""):
        with self._write_lock:
            try:
                conn = self._get_conn()
                conn.execute('INSERT INTO system_events (event_type, source, message) VALUES (?, ?, ?)', (event_type, source, message))
                conn.commit()
            except Exception as e:
                print(f"[DATABASE ERROR] log_event: {e}")

    def log_command(self, command_type, target="", status="EXECUTED"):
        with self._write_lock:
            try:
                conn = self._get_conn()
                conn.execute('INSERT INTO tactical_commands (command_type, target, status) VALUES (?, ?, ?)', (command_type, target, status))
                conn.commit()
            except Exception as e:
                print(f"[DATABASE ERROR] log_command: {e}")

    # ── Queries ───────────────────────────────────────────────────

    def fetch_all_logs(self, limit=50):
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM detections ORDER BY timestamp DESC LIMIT ?', (limit,))
            return cursor.fetchall()
        except:
            return []

    def get_stats(self):
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            stats = {}
            cursor.execute("SELECT COUNT(*) FROM detections")
            stats['total'] = cursor.fetchone()[0]
            cursor.execute("SELECT sensor_type, COUNT(*) FROM detections GROUP BY sensor_type")
            stats['by_sensor'] = dict(cursor.fetchall())
            cursor.execute("SELECT threat_level, COUNT(*) FROM detections GROUP BY threat_level")
            stats['by_threat'] = dict(cursor.fetchall())
            return stats
        except:
            return {'total': 0, 'by_sensor': {}, 'by_threat': {}}

    def close(self):
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None

# Global Instance
db = MCDISDatabase()
