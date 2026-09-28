"""
HORUS SYSTEM V2 — Standalone Backend
All modules loaded from V2 folder directly.
"""
from flask import Flask, Response, jsonify, request, send_from_directory
from flask_socketio import SocketIO
import sqlite3, time, threading, os, sys, math, random
import numpy as np
from datetime import datetime
import cv2, base64

# ── Path Setup ──
ROOT       = os.path.dirname(os.path.abspath(__file__))
CORE_DIR   = os.path.join(ROOT, "core")
IMPL_DIR   = os.path.join(ROOT, "implement")
DASH_DIR   = os.path.join(ROOT, "dashboard")
STATIC_DIR = os.path.join(DASH_DIR, "static")
AI_DIR     = os.path.join(ROOT, "ai_decision")
MODELS_DIR = os.path.join(ROOT, "models")
V1_DIR     = os.path.join(ROOT, "HORUS SYSTEM V1")
V1_DASH    = os.path.join(V1_DIR, "dashboard")
MCDIS_DIR  = os.path.join(ROOT, "mcdis")

for p in [ROOT, CORE_DIR, IMPL_DIR, DASH_DIR, AI_DIR, MODELS_DIR, V1_DIR, V1_DASH, MCDIS_DIR]:
    if os.path.exists(p) and p not in sys.path:
        sys.path.insert(0, p)

# ── Import core systems from V1 (run_vision, simulate, mcdis_v1_core) ──
from run_vision import VisionConfig, DetectionEngine, FrameRenderer
from mcdis_v1_core import MCDISFusionEngine
from simulate import ScenarioSimulator
from reporting import MissionReportGenerator
from database import db
from iff_system import iff_engine
from weapons_system import weapons_engine
from cyber_security import anomaly_detector, cyber_engine
from tactical_network import mesh_network
from roe_engine import roe_manager
from advanced_sensors import advanced_sensors
from swarm_ai import swarm_ai_engine
from thermal_vision import thermal_engine

try:
    from acoustic_weapon import AcousticWeaponSystem
    _acoustic_sys = AcousticWeaponSystem(num_emitters=2)
except Exception as e:
    _acoustic_sys = None
    print(f"[WARN] acoustic_weapon: {e}")

try:
    from interceptor_system import InterceptorSquadron
    _interceptor_sys = InterceptorSquadron(size=3)
except Exception as e:
    _interceptor_sys = None
    print(f"[WARN] interceptor_system: {e}")

try:
    from swarm_decoy import SwarmDecoySystem
    _swarm_sys = SwarmDecoySystem(max_swarms=2)
except Exception as e:
    _swarm_sys = None
    print(f"[WARN] swarm_decoy: {e}")

try:
    from adversarial_system import AdversarialSystem
    _adversarial_sys = AdversarialSystem(num_projectors=2)
except Exception as e:
    _adversarial_sys = None
    print(f"[WARN] adversarial_system: {e}")

try:
    from fuzzy_decision_engine import get_fuzzy_engine
    _fuzzy_engine = get_fuzzy_engine()
except Exception as e:
    _fuzzy_engine = None
    print(f"[WARN] fuzzy_engine: {e}")

try:
    from isr_precheck import get_isr_engine
    _isr_engine = get_isr_engine()
except Exception as e:
    _isr_engine = None
    print(f"[WARN] isr_engine: {e}")

# ── Flask ──
_static = STATIC_DIR if os.path.isdir(STATIC_DIR) else (os.path.join(V1_DASH, "static") if os.path.isdir(os.path.join(V1_DASH, "static")) else ROOT)
app = Flask(__name__,
            static_folder=_static,
            template_folder=ROOT)
app.config['SECRET_KEY'] = 'horus_v2_tactical_2026'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ── State ──
current_simulator    = None
auto_engage_enabled  = True
last_auto_fire_time  = 0
vision_engine        = None
vision_renderer      = None
video_capture        = None
_latest_raw_frame    = None
_latest_display_frame= None
_latest_drone_crop   = None
_frame_buffer_lock   = threading.Lock()
_latest_detection    = None
_detection_lock      = threading.Lock()
_ui_target           = {}
_logged_tids         = set()

DB_PATH          = os.path.join(ROOT, "mcdis_logs.db")
SYSTEM_START_TIME= time.time()
# Auto-find the drone test video from multiple known locations
def _find_video():
    candidates = [
        r"C:\Users\hassa\Desktop\New folder (21)\video drone test\test 1\video_2026-04-25_09-13-07.mp4",
        os.path.join(V1_DIR, "test.mp4"),
        os.path.join(V1_DIR, "mcdis_output.mp4"),
        os.path.join(V1_DIR, "mcdis_sahi_output.mp4"),
        os.path.join(V1_DIR, "test people.mp4"),
    ]
    for p in candidates:
        if os.path.isfile(p):
            print(f"[VIDEO] Using: {p}")
            return p
    # Last resort: any mp4 in V1
    for f in os.listdir(V1_DIR):
        if f.endswith('.mp4'):
            full = os.path.join(V1_DIR, f)
            print(f"[VIDEO] Fallback: {full}")
            return full
    print("[VIDEO] WARNING: No video file found!")
    return ""

USER_VIDEO_PATH = _find_video()

# ── DB ──
def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db(); c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS detections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sensor_type TEXT, target_id TEXT, threat_level TEXT,
        confidence REAL, details TEXT, speed REAL, image_path TEXT,
        iff_status TEXT DEFAULT 'UNKNOWN',
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS tactical_commands (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        command_type TEXT, target TEXT, status TEXT, operator TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)""")
    conn.commit(); conn.close()

def get_alerts(limit=30):
    try:
        conn = get_db()
        rows = conn.execute("SELECT * FROM detections ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except: return []

def get_commands(limit=10):
    try:
        conn = get_db()
        rows = conn.execute("SELECT * FROM tactical_commands ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except: return []

def get_stats():
    try:
        conn = get_db(); c = conn.cursor()
        s = {}
        s['total']           = c.execute("SELECT COUNT(*) FROM detections").fetchone()[0]
        s['by_sensor']       = {r[0]:r[1] for r in c.execute("SELECT sensor_type,COUNT(*) FROM detections GROUP BY sensor_type")}
        s['by_threat']       = {r[0]:r[1] for r in c.execute("SELECT threat_level,COUNT(*) FROM detections GROUP BY threat_level")}
        s['critical_recent'] = c.execute("SELECT COUNT(*) FROM detections WHERE threat_level='CRITICAL' AND timestamp>=datetime('now','-5 minutes')").fetchone()[0]
        s['high_recent']     = c.execute("SELECT COUNT(*) FROM detections WHERE threat_level='HIGH'     AND timestamp>=datetime('now','-5 minutes')").fetchone()[0]
        avg = c.execute("SELECT AVG(confidence) FROM detections").fetchone()[0]
        s['avg_confidence']  = round(avg,1) if avg else 0
        conn.close()
        return s
    except: return {'total':0,'by_sensor':{},'by_threat':{},'critical_recent':0,'high_recent':0,'avg_confidence':0}

def calc_threat(stats):
    cr,hi = stats.get('critical_recent',0), stats.get('high_recent',0)
    if cr >= 2: return {'level':'CRITICAL','code':4,'label':'CONDITION RED','pct':95}
    if cr == 1 or hi >= 3: return {'level':'HIGH','code':3,'label':'CONDITION ORANGE','pct':75}
    if hi >= 1: return {'level':'ELEVATED','code':2,'label':'CONDITION YELLOW','pct':50}
    return {'level':'MINIMAL','code':0,'label':'CONDITION GREEN','pct':15}

# ── Vision ──
def init_vision():
    global vision_engine, vision_renderer
    if vision_engine is None:
        vision_engine   = MCDISFusionEngine()
        vision_renderer = FrameRenderer()

def _video_worker():
    global video_capture, _latest_raw_frame, _latest_display_frame
    global _ui_target, _latest_detection, _logged_tids, _latest_drone_crop
    init_vision()
    while True:
        if video_capture is None or not video_capture.isOpened():
            video_capture = cv2.VideoCapture(USER_VIDEO_PATH)
            if not video_capture.isOpened():
                time.sleep(2); continue
        ret, frame = video_capture.read()
        if not ret:
            video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0); continue

        detections = vision_engine.process_frame(frame)
        display    = vision_renderer.draw_detections(frame.copy(), detections)

        best = None
        for d in detections:
            if not best or d['conf'] > best['conf']: best = d

        if best:
            x1,y1,x2,y2 = map(int, best['bbox'])
            hf,wf = frame.shape[:2]
            crop = frame[max(0,y1-20):min(hf,y2+20), max(0,x1-20):min(wf,x2+20)].copy()
            crop_b64 = ''
            if crop.size > 0:
                high_res = crop.copy()
                _, buf = cv2.imencode('.jpg', cv2.resize(crop,(180,180)), [int(cv2.IMWRITE_JPEG_QUALITY),80])
                crop_b64 = base64.b64encode(buf).decode('utf-8')

            label  = best['label']
            tclass = best['class'].upper() if best.get('class') else 'UNKNOWN'
            if best['class'] in ['bird','airplane','aeroplane','kite','drone'] and best['conf'] > 30:
                label  = "[MATCH] SHAHED-136 (HOSTILE)"
                tclass = "SHAHED-136"

            payload = {
                'target_id'  : f"T-{str(best['track_id']).zfill(3)}",
                'model_name' : label,
                'category'   : tclass,
                'threat_level': 'CRITICAL' if tclass=="SHAHED-136" else best['threat'],
                'confidence' : best['conf'],
                'iff_status' : 'HOSTILE',
                'crop_b64'   : crop_b64,
                'bearing'    : best.get('bearing',0),
                'speed'      : random.uniform(155,185) if tclass=="SHAHED-136" else best.get('speed_kmh',0),
                'altitude'   : random.uniform(80,250),
                'distance_km': random.uniform(0.5,4.0),
                'timestamp'  : datetime.now().strftime('%H:%M:%S'),
            }
            _ui_target = payload
            with _detection_lock: _latest_detection = payload

            if payload['target_id'] not in _logged_tids:
                _logged_tids.add(payload['target_id'])
                snap_fn   = f"snapshot_{payload['target_id'].replace('-','_')}_{int(time.time())}.jpg"
                snap_path = os.path.join(app.static_folder,"crops",snap_fn)
                os.makedirs(os.path.dirname(snap_path), exist_ok=True)
                try:
                    if crop.size > 0:
                        hr = cv2.resize(crop,(600,400),interpolation=cv2.INTER_CUBIC)
                        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                        cv2.putText(hr,f"TGT: {payload['target_id']}",(15,35),cv2.FONT_HERSHEY_SIMPLEX,0.9,(0,255,0),2)
                        cv2.putText(hr,f"TIME: {ts}",(15,70),cv2.FONT_HERSHEY_SIMPLEX,0.7,(0,255,0),2)
                        cv2.imwrite(snap_path, hr, [int(cv2.IMWRITE_JPEG_QUALITY),95])
                        th = thermal_engine.apply_thermal_colormap(hr)
                        cv2.putText(th,f"TGT: {payload['target_id']}",(15,35),cv2.FONT_HERSHEY_SIMPLEX,0.9,(0,255,0),2)
                        cv2.imwrite(os.path.join(app.static_folder,"crops",f"thermal_{snap_fn}"), th, [int(cv2.IMWRITE_JPEG_QUALITY),95])
                except: pass
                try:
                    conn=get_db(); c=conn.cursor()
                    c.execute("INSERT INTO detections (sensor_type,target_id,threat_level,confidence,details,speed,image_path) VALUES (?,?,?,?,?,?,?)",
                              ("OPTICAL",payload['target_id'],payload['threat_level'],payload['confidence'],payload['model_name'],payload['speed'],snap_fn))
                    conn.commit(); conn.close()
                except: pass

        with _frame_buffer_lock:
            _latest_raw_frame    = frame.copy()
            _latest_display_frame= display.copy()
            if best:
                x1,y1,x2,y2 = map(int,best['bbox'])
                hf,wf = frame.shape[:2]; pad=15
                lc = frame[max(0,y1-pad):min(hf,y2+pad), max(0,x1-pad):min(wf,x2+pad)].copy()
                if lc.size > 0:
                    _latest_drone_crop={'img':lc,'drone_cx':(x1+x2)//2-max(0,x1-pad),'drone_cy':(y1+y2)//2-max(0,y1-pad)}
            else:
                _latest_drone_crop = None
        time.sleep(0.01)

# ── Background monitor ──
def _db_monitor():
    last_id = 0
    while True:
        try:
            alerts   = get_alerts()
            stats    = get_stats()
            threat   = calc_threat(stats)
            uptime   = int(time.time() - SYSTEM_START_TIME)

            sensor_data = {
                'rf_spectrum'    : [random.uniform(0.02,0.15) for _ in range(60)],
                'acoustic'       : [math.sin(i*0.3+time.time()*0.1)*0.3+random.uniform(-0.05,0.05) for i in range(60)],
                'signal_strength': 0.45+0.4*math.sin(time.time()*0.07)+random.uniform(-0.05,0.05),
            }
            sensor_data['rf_spectrum'][20] = 0.85+random.uniform(-0.1,0.1)
            sensor_data['rf_spectrum'][35] = 0.60+random.uniform(-0.1,0.1)

            health = {
                'VISION SYSTEM' : 98 if vision_engine else 0,
                'RF SCANNER'    : 95+random.randint(-2,2),
                'ACOUSTIC ARRAY': 93+random.randint(-2,2),
                'RADAR SYSTEM'  : 97+random.randint(-1,1),
                'AI PROCESSOR'  : 99,
                'DATABASE'      : 98,
                'GPS SIGNAL'    : 100,
                'COMMUNICATION' : 98+random.randint(-1,1),
                'POWER SUPPLY'  : 100,
            }

            cm_status = weapons_engine.system_status() if hasattr(weapons_engine,'system_status') else {}

            payload = {
                'alerts'       : alerts[:10],
                'stats'        : stats,
                'threat_level' : threat,
                'uptime'       : uptime,
                'sensor_data'  : sensor_data,
                'health'       : health,
                'cm_status'    : cm_status,
                'target'       : _ui_target,
                'total_targets': len(_logged_tids),
            }

            if alerts and alerts[0]['id'] != last_id:
                last_id = alerts[0]['id']
                socketio.emit('full_update', payload)
            else:
                socketio.emit('system_heartbeat', payload)

        except Exception as e:
            print(f"[MONITOR ERR] {e}")
        socketio.sleep(1.0)

def _detection_emitter():
    global _latest_detection, auto_engage_enabled, last_auto_fire_time
    while True:
        socketio.sleep(0.2)
        det = None
        with _detection_lock:
            if _latest_detection:
                det = _latest_detection
                _latest_detection = None
        if det:
            socketio.emit('vision_detection', det)
            if auto_engage_enabled and (det.get('category') in ['DRONE','UAV','MISSILE','SHAHED-136'] or det.get('threat_level')=='CRITICAL'):
                if det.get('iff_status') == 'FRIENDLY': continue
                now = time.time()
                if now - last_auto_fire_time > 8:
                    last_auto_fire_time = now
                    model = det.get('model_name','').upper()
                    cat   = det.get('category','UNKNOWN')
                    if 'SWARM' in model:                   weapon = 'ACOUSTIC_ARRAY'
                    elif cat=='MISSILE' or 'MISSILE' in model: weapon = 'DEW_LASER'
                    else:                                  weapon = 'RF_JAMMER'

                    def _auto_eng(ws=weapon, tid=det.get('target_id')):
                        socketio.emit('countermeasure_status',{'system':ws,'status':'ENGAGING','target':tid,'timestamp':datetime.now().strftime('%H:%M:%S')})
                        try:
                            conn=get_db(); c=conn.cursor()
                            c.execute("INSERT INTO tactical_commands (command_type,target,status,operator) VALUES (?,?,?,?)",(ws,tid,'ENGAGING','AI-AUTO'))
                            conn.commit(); conn.close()
                        except: pass
                        socketio.sleep(3.0)
                        socketio.emit('countermeasure_status',{'system':ws,'status':'NEUTRALIZED','target':tid,'timestamp':datetime.now().strftime('%H:%M:%S')})
                        try:
                            conn=get_db(); c=conn.cursor()
                            c.execute("INSERT INTO tactical_commands (command_type,target,status,operator) VALUES (?,?,?,?)",(ws,tid,'NEUTRALIZED','AI-AUTO'))
                            conn.commit(); conn.close()
                        except: pass
                    socketio.start_background_task(_auto_eng)

# ── Routes ──
@app.route('/')
def index(): return send_from_directory(ROOT,'horus.html')

@app.route('/horus.css')
def css(): return send_from_directory(ROOT,'horus.css')

@app.route('/horus.js')
def js(): return send_from_directory(ROOT,'horus.js')

@app.route('/mcdis_report.html')
def report_html(): return send_from_directory(ROOT,'mcdis_report.html')

@app.route('/video_feed')
def video_feed():
    def gen():
        while True:
            with _frame_buffer_lock:
                if _latest_display_frame is None: socketio.sleep(0.1); continue
                disp = _latest_display_frame.copy()
            _, buf = cv2.imencode('.jpg', disp, [int(cv2.IMWRITE_JPEG_QUALITY),80])
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n')
            socketio.sleep(0.04)
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/raw_feed')
def raw_feed():
    def gen():
        while True:
            with _frame_buffer_lock:
                if _latest_raw_frame is None: socketio.sleep(0.1); continue
                raw = _latest_raw_frame.copy()
            _, buf = cv2.imencode('.jpg', raw, [int(cv2.IMWRITE_JPEG_QUALITY),80])
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n')
            socketio.sleep(0.04)
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/thermal_feed')
def thermal_feed():
    def gen():
        while True:
            with _frame_buffer_lock:
                if _latest_drone_crop:
                    crop=_latest_drone_crop['img']
                    fr=cv2.resize(crop,(400,300),interpolation=cv2.INTER_CUBIC)
                    dcx=int(_latest_drone_crop['drone_cx']*(400.0/max(1,crop.shape[1])))
                    dcy=int(_latest_drone_crop['drone_cy']*(300.0/max(1,crop.shape[0])))
                elif _latest_raw_frame is not None:
                    fr=cv2.resize(_latest_raw_frame,(400,300)); dcx,dcy=200,150
                else:
                    socketio.sleep(0.1); continue
            th=thermal_engine.apply_thermal_colormap(fr)
            cv2.line(th,(dcx-25,dcy),(dcx+25,dcy),(0,255,0),2)
            cv2.line(th,(dcx,dcy-25),(dcx,dcy+25),(0,255,0),2)
            cv2.circle(th,(dcx,dcy),15,(0,255,0),1)
            cv2.putText(th,"FLIR TARGET LOCK",(10,20),cv2.FONT_HERSHEY_SIMPLEX,0.5,(0,255,0),1)
            _,buf=cv2.imencode('.jpg',th,[int(cv2.IMWRITE_JPEG_QUALITY),70])
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n')
            socketio.sleep(0.06)
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/latest_target')
def api_latest_target():
    return jsonify(_ui_target) if _ui_target else (jsonify({}),204)

@app.route('/api/generate_report')
def api_generate_report():
    try:
        rg = MissionReportGenerator(DB_PATH, app.static_folder)
        fn = rg.generate_session_report()
        if fn: return jsonify({'status':'SUCCESS','report_url':f'/static/reports/{fn}'})
        return jsonify({'status':'FAILED','message':'No data'}),404
    except Exception as e:
        return jsonify({'status':'ERROR','message':str(e)}),500

@app.route('/api/set_video', methods=['POST'])
def set_video():
    global USER_VIDEO_PATH, video_capture
    data = request.json or {}
    name = data.get('filename')
    if name:
        USER_VIDEO_PATH = os.path.join(os.path.dirname(USER_VIDEO_PATH), name)
        with _frame_buffer_lock:
            if video_capture: video_capture.release(); video_capture=None
        return jsonify({'status':'SUCCESS'})
    return jsonify({'status':'FAILED'}),400

@app.route('/api/isr_check', methods=['POST'])
def api_isr():
    data=request.json or {}
    if _isr_engine:
        result=_isr_engine.evaluate(
            target_speed_kmh=float(data.get('speed_kmh',80)),
            target_distance_km=float(data.get('distance_km',3)),
            target_bearing_deg=float(data.get('bearing',45)),
            target_type=data.get('target_type','commercial'),
            threat_level=data.get('threat_level','THREAT'))
    else:
        result={'go_nogo':'GO','isr_pct':50,'recommended':'RF_JAM'}
    socketio.emit('isr_result',result)
    return jsonify(result)

@app.route('/api/fuzzy_evaluate', methods=['POST'])
def api_fuzzy():
    data=request.json or {}
    inputs={k:float(data.get(k,50)) for k in ['distance','speed','altitude','rcs','cam_conf','obj_size','rf_strength','rf_risk','acoustic','movement']}
    if _fuzzy_engine:
        result=_fuzzy_engine.evaluate(inputs)
    else:
        result={'threat_level':'UNKNOWN','threat_score':50,'action':'MONITOR'}
    socketio.emit('fuzzy_result',result)
    return jsonify(result)

@app.route('/api/engage_advanced', methods=['POST'])
def api_engage():
    data=request.json or {}
    result=weapons_engine.engage_target(
        weapon_type=data.get('weapon_type','RF_JAMMING'),
        target_id=data.get('target_id','T-000'),
        distance_m=float(data.get('distance_m',2000)),
        target_type=data.get('target_type','commercial'),
        rf_strength=float(data.get('rf_strength',60)),
        target_speed_kmh=float(data.get('speed_kmh',80)),
        target_bearing=float(data.get('bearing',45)),
        extra=data.get('extra',{}))
    socketio.emit('engagement_result',{
        'weapon':data.get('weapon_type'),'target':data.get('target_id'),
        'status':result.get('status','UNKNOWN'),'effect':result.get('effect',''),
        'timestamp':datetime.now().strftime('%H:%M:%S')})
    return jsonify(result)

@app.route('/api/weapons_status')
def api_weapons_status():
    status=weapons_engine.system_status() if hasattr(weapons_engine,'system_status') else {}
    status['fuzzy']=_fuzzy_engine is not None
    status['isr']=_isr_engine is not None
    return jsonify(status)

@socketio.on('trigger_engagement')
def handle_eng(data):
    mode,tid=data.get('mode'),data.get('target')
    socketio.emit('command_acknowledged',{'command':mode,'status':'EXECUTING','target':tid,'timestamp':datetime.now().strftime('%H:%M:%S')})

@socketio.on('toggle_auto_engage')
def handle_auto(data):
    global auto_engage_enabled
    auto_engage_enabled=data.get('enabled',True)
    socketio.emit('auto_engage_status',{'enabled':auto_engage_enabled})

if __name__=='__main__':
    init_db()
    os.makedirs(os.path.join(app.static_folder,"crops"),exist_ok=True)
    os.makedirs(os.path.join(app.static_folder,"reports"),exist_ok=True)
    threading.Thread(target=_video_worker, daemon=True).start()
    socketio.start_background_task(_db_monitor)
    socketio.start_background_task(_detection_emitter)
    print("═"*60)
    print("  HORUS SYSTEM V2 — TACTICAL COMMAND ACTIVE")
    print(f"  Dashboard → http://localhost:5001")
    print("═"*60)
    socketio.run(app, host='0.0.0.0', port=5001, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)
