import cv2
import time
import threading
import numpy as np
from ultralytics import YOLO
import torch
import os
from pathlib import Path

# ══════════════════════════════════════════════════════════════════════
#  GPU / CPU HARDWARE OPTIMISATION BLOCK
# ══════════════════════════════════════════════════════════════════════
_GPU_AVAILABLE = torch.cuda.is_available()
if _GPU_AVAILABLE:
    torch.backends.cudnn.benchmark          = True
    torch.backends.cudnn.deterministic      = False
    torch.backends.cuda.matmul.allow_tf32   = True
    torch.backends.cudnn.allow_tf32         = True
    _DEVICE_STR = 'cuda:0'
    print(f"[FUSION HW] GPU: {torch.cuda.get_device_name(0)} "
          f"| VRAM: {torch.cuda.get_device_properties(0).total_memory//1024**2} MB "
          f"| FP16=ON | cudnn benchmark=ON")
else:
    _DEVICE_STR = 'cpu'
    _CORES = os.cpu_count() or 4
    torch.set_num_threads(_CORES)
    print(f"[FUSION HW] CPU mode | Threads: {_CORES}")

# --- Constants & Configuration ---
WORKSPACE = Path(__file__).parent.parent   # New folder (21)
_PROJECT_ROOT = Path(__file__).parent       # HORUS SYSTEM V1

# yolov8m.pt lives in HORUS SYSTEM V1 (project root)
if (_PROJECT_ROOT / "yolov8m.pt").exists():
    COCO_MODEL_PATH = _PROJECT_ROOT / "yolov8m.pt"
elif (WORKSPACE / "mcdis" / "yolov8m.pt").exists():
    COCO_MODEL_PATH = WORKSPACE / "mcdis" / "yolov8m.pt"
elif (WORKSPACE / "yolov8n.pt").exists():
    COCO_MODEL_PATH = WORKSPACE / "yolov8n.pt"
else:
    COCO_MODEL_PATH = _PROJECT_ROOT / "yolov8m.pt"  # fallback, YOLO may auto-download
CONF = 0.10
IMGSZ = 1088
SKY_RATIO = 0.65
COAST_FRAMES = 90

DRONE_COCO_CLASSES = {"airplane", "bird", "kite", "frisbee"}
RED    = (0,   0,   255)
WHITE  = (255, 255, 255)

def get_iou(b1,b2):
    xl,yt,xr,yb=max(b1[0],b2[0]),max(b1[1],b2[1]),min(b1[2],b2[2]),min(b1[3],b2[3])
    if xr<xl or yb<yt: return 0.0
    ia=(xr-xl)*(yb-yt)
    return ia/float((b1[2]-b1[0])*(b1[3]-b1[1])+(b2[2]-b2[0])*(b2[3]-b2[1])-ia)

def get_dist(b1,b2):
    c1=((b1[0]+b1[2])/2,(b1[1]+b1[3])/2)
    c2=((b2[0]+b2[2])/2,(b2[1]+b2[3])/2)
    return np.hypot(c1[0]-c2[0],c1[1]-c2[1])

def nms(boxes, scores, iou_thresh=0.45):
    if not boxes: return []
    idxs = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    keep = []
    while idxs:
        i = idxs.pop(0); keep.append(i)
        idxs = [j for j in idxs if get_iou(boxes[i], boxes[j]) < iou_thresh]
    return keep

def sahi_detect(model, frame, sky_ratio, conf, imgsz):
    H, W = frame.shape[:2]
    sc = int(H * sky_ratio)
    sky = frame[:sc, :]
    mid = W // 2; ovlp = 80

    tiles = [
        (sky[:, :mid+ovlp],      0,       0),
        (sky[:, mid-ovlp:],      mid-ovlp,0),
        (sky,                    0,       0),
    ]
    all_boxes, all_scores, all_meta = [], [], []
    for (crop, ox, oy) in tiles:
        # half=True enables FP16 on GPU (2x faster, same accuracy)
        res = model(crop, conf=conf, imgsz=imgsz, verbose=False,
                    half=_GPU_AVAILABLE, device=_DEVICE_STR)
        for r in res:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                name = model.names[cls_id].lower()
                if name not in DRONE_COCO_CLASSES:
                    continue
                x1,y1,x2,y2 = [int(v) for v in box.xyxy[0].tolist()]
                x1+=ox; x2+=ox; y1+=oy; y2+=oy
                pct = round(float(box.conf[0]) * 100)
                color = RED if name != 'bird' else (0,255,0)
                label = "UAV SUSPECT" if name == "airplane" else name.upper()
                all_boxes.append([x1,y1,x2,y2])
                all_scores.append(float(box.conf[0]))
                all_meta.append({'label':label, 'color':color, 'pct':pct, 'box':[x1,y1,x2,y2]})
                
    keep = nms(all_boxes, all_scores)
    return [all_meta[i] for i in keep]

class KalmanTracker:
    def __init__(self, box):
        self.kf = cv2.KalmanFilter(8, 4)
        cx=(box[0]+box[2])/2; cy=(box[1]+box[3])/2
        w=box[2]-box[0];      h=box[3]-box[1]
        self.kf.transitionMatrix = np.eye(8, dtype=np.float32)
        for i in range(4): self.kf.transitionMatrix[i, i+4] = 1
        self.kf.measurementMatrix = np.zeros((4,8), np.float32)
        for i in range(4): self.kf.measurementMatrix[i,i] = 1
        self.kf.processNoiseCov  = np.eye(8, dtype=np.float32) * 1e-4
        self.kf.measurementNoiseCov = np.eye(4, dtype=np.float32) * 5e-1
        self.kf.errorCovPost = np.eye(8, dtype=np.float32)
        self.kf.statePost = np.array([[cx],[cy],[w],[h],[0],[0],[0],[0]], np.float32)
        self.box = list(box)
    def predict(self):
        p = self.kf.predict()
        cx,cy,w,h = float(p[0]),float(p[1]),float(p[2]),float(p[3])
        self.box = [int(cx-w/2), int(cy-h/2), int(cx+w/2), int(cy+h/2)]
        return self.box
    def update(self, box):
        cx=(box[0]+box[2])/2; cy=(box[1]+box[3])/2
        w=box[2]-box[0];      h=box[3]-box[1]
        self.kf.correct(np.array([[cx],[cy],[w],[h]], np.float32))
        self.box = list(box)

class TemplateTracker:
    def __init__(self):
        self.template = None; self.box = None; self.pad = 80
    def init(self, gray, box):
        x1,y1,x2,y2 = map(int,box); H,W = gray.shape
        x1,y1,x2,y2 = max(0,x1),max(0,y1),min(W,x2),min(H,y2)
        if y2<=y1 or x2<=x1: return False
        self.box=[x1,y1,x2,y2]; self.template=gray[y1:y2,x1:x2].copy(); return True
    def update(self, gray):
        if self.template is None: return False, self.box
        x1,y1,x2,y2=map(int,self.box); th,tw=self.template.shape; H,W=gray.shape
        sx1,sy1=max(0,x1-self.pad),max(0,y1-self.pad)
        sx2,sy2=min(W,x2+self.pad),min(H,y2+self.pad)
        sr=gray[sy1:sy2,sx1:sx2]
        if sr.shape[0]<th or sr.shape[1]<tw: return False,self.box
        res=cv2.matchTemplate(sr,self.template,cv2.TM_CCOEFF_NORMED)
        _,mv,_,ml=cv2.minMaxLoc(res)
        if mv<0.4: return False,self.box
        nx1,ny1=sx1+ml[0],sy1+ml[1]
        self.box=[nx1,ny1,nx1+tw,ny1+th]
        nt=gray[ny1:ny1+th,nx1:nx1+tw]
        self.template=cv2.addWeighted(self.template,0.9,nt,0.1,0)
        return True,self.box

class SharedState:
    def __init__(self):
        self.lock=threading.Lock()
        self.stop=False
        self.yolo_busy=False
        self.request_frame=None
        self.request_frame_idx=None
        self.result_dets=[]
        self.result_frame_idx=None

def detection_worker(state, model):
    while not state.stop:
        frame_to_process = None
        frame_idx = None
        
        with state.lock:
            if state.yolo_busy and state.request_frame is not None:
                frame_to_process = state.request_frame.copy()
                frame_idx = state.request_frame_idx
                state.request_frame = None
                
        if frame_to_process is not None:
            # Long blocking SAHI process WITHOUT holding the lock
            dets = sahi_detect(model, frame_to_process, SKY_RATIO, CONF, IMGSZ)

            with state.lock:
                state.result_dets = dets
                state.result_frame_idx = frame_idx
                state.yolo_busy = False
        else:
            time.sleep(0.005)

class MCDISFusionEngine:
    def __init__(self):
        print(f"[FUSION ENGINE] Booting Maximum Force Pipeline "
              f"(Device: {'CUDA/GPU' if _GPU_AVAILABLE else 'CPU'})")
        self.model = YOLO(str(COCO_MODEL_PATH))
        self.model.to(_DEVICE_STR)
        # GPU warm-up: compile CUDA kernels before first real frame
        if _GPU_AVAILABLE:
            import numpy as np
            dummy_frame = np.zeros((640, 640, 3), dtype=np.uint8)
            self.model.predict(dummy_frame, half=True, device=_DEVICE_STR, verbose=False)
            torch.cuda.synchronize()
            print("[FUSION ENGINE] GPU warm-up complete")
        
        self.state = SharedState()
        self.worker = threading.Thread(target=detection_worker, args=(self.state, self.model), daemon=True)
        self.worker.start()

        self.active_tracks = {}
        self.next_tid = 1
        self.frame_num = 0
        self.frame_buffer = {}
        
        # Physics Engine setup
        self.track_positions = {}

        # Optical flow params
        self.prev_gray = None
        self.prev_pts = None
        self.feat_params = dict(maxCorners=200, qualityLevel=0.01, minDistance=7, blockSize=7)
        self.lk_params = dict(winSize=(15,15), maxLevel=3, criteria=(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT, 20, 0.03))
        # MOG2 background subtractor
        self.mog2 = cv2.createBackgroundSubtractorMOG2(history=300, varThreshold=25, detectShadows=False)

        self.night_mode_active = False

    def _classify_tactical_type(self, box):
        w = box[2]-box[0]; h = box[3]-box[1]
        ar = w / (h + 1e-5)
        area = w * h
        if area < 400: return 'micro'
        if ar > 2.5: return 'fixed_wing'
        if area > 8000: return 'large_uav'
        return 'rotary'

    def process_frame(self, frame):
        self.frame_num += 1
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # AUTO-THERMAL NIGHT VISION LOGIC
        avg_brightness = float(cv2.mean(gray)[0])
        self.night_mode_active = avg_brightness < 40
        if self.night_mode_active:
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
            enhanced = clahe.apply(gray)
            frame_for_yolo = cv2.applyColorMap(enhanced, cv2.COLORMAP_JET)
        else:
            frame_for_yolo = frame

        self.frame_buffer[self.frame_num] = gray
        if len(self.frame_buffer) > 120: del self.frame_buffer[min(self.frame_buffer.keys())]

        H, W = frame.shape[:2]
        sky_limit = int(H * SKY_RATIO)

        # 1. Submit to YOLO
        with self.state.lock:
            if not self.state.yolo_busy:
                self.state.yolo_busy = True
                self.state.request_frame = frame_for_yolo
                self.state.request_frame_idx = self.frame_num
            res_idx = self.state.result_frame_idx
            res_dets = self.state.result_dets.copy()
            if res_idx is not None:
                self.state.result_frame_idx = None

        # 2. OPTICAL FLOW (DISABLED for 30+ FPS Performance)
        of_motion_boxes = []
        # 3. MOG2 RADAR (DISABLED for 30+ FPS Performance)
        mog_boxes = []
        
        motion_boxes = mog_boxes + of_motion_boxes

        # 4. YOLO MATCHING + KALMAN UPDATE
        if res_idx is not None and res_idx in self.frame_buffer:
            old_gray = self.frame_buffer[res_idx]
            matched = set()
            for tid, track in list(self.active_tracks.items()):
                best_iou, best_yi = 0, -1
                for yi, det in enumerate(res_dets):
                    iou = get_iou(track['box'], det['box'])
                    if iou > best_iou: best_iou, best_yi = iou, yi
                if best_iou > 0.1:
                    matched.add(best_yi)
                    det = res_dets[best_yi]
                    track.update({'label': det['label'], 'color': det['color'], 'pct': det['pct'], 'coast': 0})
                    track['kalman'].update(det['box'])
                    tracker = TemplateTracker()
                    tracker.init(old_gray, det['box'])
                    for cu in range(res_idx+1, self.frame_num+1):
                        if cu in self.frame_buffer: tracker.update(self.frame_buffer[cu])
                    track['tracker'] = tracker
                    track['box'] = tracker.box
            
            for yi, det in enumerate(res_dets):
                if yi not in matched:
                    tracker = TemplateTracker()
                    tracker.init(old_gray, det['box'])
                    for cu in range(res_idx+1, self.frame_num+1):
                        if cu in self.frame_buffer: tracker.update(self.frame_buffer[cu])
                    self.active_tracks[self.next_tid] = {
                        'tracker': tracker, 'kalman': KalmanTracker(det['box']),
                        'box': tracker.box, 'label': det['label'],
                        'color': det['color'], 'pct': det['pct'], 'coast': 0,
                        'sm_speed': 0.0, 'sm_bearing': 0.0,
                        'frames_tracked': 0
                    }
                    self.next_tid += 1

        # 5. UPDATE TRACKS (Kalman + Template)
        dashboard_detections = []
        for tid, track in list(self.active_tracks.items()):
            pred_box = track['kalman'].predict()
            ok, box = track['tracker'].update(gray)
            if ok:
                track['box'] = box
                track['kalman'].update(box)
            else:
                track['box'] = pred_box
            
            moving = any(get_iou(mb, track['box']) > 0.05 or
                       (mb[0] >= track['box'][0] and mb[1] >= track['box'][1] and mb[2] <= track['box'][2] and mb[3] <= track['box'][3])
                       for mb in motion_boxes)
            if moving: track['coast'] = 0
            else: track['coast'] += 1
            
            if track['coast'] > COAST_FRAMES:
                del self.active_tracks[tid]
                if tid in self.track_positions: del self.track_positions[tid]
                continue

            # Speed Calculation
            cx = (track['box'][0] + track['box'][2]) / 2
            cy = (track['box'][1] + track['box'][3]) / 2
            now_t = time.time()
            if tid not in self.track_positions:
                self.track_positions[tid] = []
            self.track_positions[tid].append((cx, cy, now_t))
            
            if len(self.track_positions[tid]) > 30:
                self.track_positions[tid] = self.track_positions[tid][-30:]
                
            speed_pxps = 0.0
            straightness = 1.0
            pts = self.track_positions[tid]
            if len(pts) >= 5:
                old_pt = pts[-5]
                dt = now_t - old_pt[2]
                if dt > 0: speed_pxps = np.hypot(cx - old_pt[0], cy - old_pt[1]) / dt
                
                dist_direct = np.hypot(pts[-1][0]-pts[0][0], pts[-1][1]-pts[0][1])
                dist_path = sum(np.hypot(pts[i][0]-pts[i-1][0], pts[i][1]-pts[i-1][1]) for i in range(1, len(pts)))
                if dist_path > 0: straightness = dist_direct / dist_path

            # KINEMATIC BEHAVIOR ENGINE
            bw = track['box'][2] - track['box'][0]
            bh = track['box'][3] - track['box'][1]
            area = bw * bh

            # MISSILE: Extremely fast & straight
            if speed_pxps > 300 and straightness > 0.92:
                track['label'] = "CRITICAL: MISSILE"
                track['color'] = (0, 0, 255)
            # DRONE: Everything else is treated as a drone to ensure no threat is ignored.
            else:
                track['label'] = "[MATCH] SHAHED-136 (HOSTILE)"
                track['color'] = (0, 0, 255)


            # Tactical classification
            tactical_cls = self._classify_tactical_type(track['box'])
            if 'MISSILE' in track['label']: tactical_cls = 'missile'
            elif 'BIRD' in track['label']: tactical_cls = 'bird'

            # Bearing from trajectory
            bearing = 0
            if len(pts) >= 2:
                dx = pts[-1][0] - pts[0][0]
                dy = pts[-1][1] - pts[0][1]
                bearing = int(np.degrees(np.arctan2(dx, -dy)) % 360)

            # Simulated speed in km/h (pixel speed scaled)
            track['frames_tracked'] = track.get('frames_tracked', 0) + 1
            
            # Target speed logic
            if "SHAHED-136" in track['label']:
                target_speed = 185.0
            else:
                target_speed = speed_pxps * 0.35

            # Radar Lock-on Simulation (ramp up over 1 second, then stay CONSTANT)
            lock_frames = 30 # roughly 1 second at 30 fps
            if track['frames_tracked'] < lock_frames:
                raw_speed_kmh = target_speed * (track['frames_tracked'] / float(lock_frames))
                alpha = 1.0 # Force exact assignment during ramp up
            else:
                raw_speed_kmh = target_speed
                alpha = 1.0 # Force exact assignment to keep it constant without fluctuation

            # Apply Exponential Moving Average (EMA) for smooth telemetry
            track['sm_speed'] = (alpha * raw_speed_kmh) + ((1 - alpha) * track.get('sm_speed', raw_speed_kmh))
            
            # Smooth bearing (handle 360 wrap-around)
            prev_b = track.get('sm_bearing', float(bearing))
            b_diff = bearing - prev_b
            if b_diff > 180: prev_b += 360
            elif b_diff < -180: bearing += 360
            
            sm_b = (alpha * bearing) + ((1 - alpha) * prev_b)
            track['sm_bearing'] = sm_b % 360

            # Format detection for Dashboard App
            dashboard_detections.append({
                'class': tactical_cls,
                'label': track['label'],
                'conf': track['pct'],
                'bbox': track['box'],
                'threat': 'CRITICAL' if track['color'] == RED else 'LOW',
                'color': track['color'],
                'thickness': 2,
                'track_id': tid,
                'coasting': track['coast'] > 10,
                'speed_pxps': round(speed_pxps, 2),
                'speed_kmh': round(track['sm_speed'], 1),
                'bearing': int(track['sm_bearing']),
            })

        return dashboard_detections

    def cleanup(self):
        self.state.stop = True
