"""
╔══════════════════════════════════════════════════════════════════════╗
║  MCDIS — Multi-Modal Counter-Drone Intelligence System              ║
║  Module: Computer Vision & Deep Learning Detection Pipeline         ║
║  Version: 2.0                                                        ║
║  Classification: UNCLASSIFIED // FOR OFFICIAL USE ONLY               ║
╠══════════════════════════════════════════════════════════════════════╣
║  Pipeline:                                                           ║
║    1. Video Input → Local file / Camera / RTSP stream               ║
║    2. Detection → YOLOv8 (native) or SAHI (sliced inference)        ║
║    3. Tracking → ByteTrack persistent ID assignment                  ║
║    4. Classification → Threat-level assignment per detection         ║
║    5. Output → Annotated frames + Database logging + Dashboard feed ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import cv2
import torch
import os
import sys
import time
import math
import numpy as np
from datetime import datetime

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
    print(f"[HW] GPU: {torch.cuda.get_device_name(0)} "
          f"| VRAM: {torch.cuda.get_device_properties(0).total_memory//1024**2} MB "
          f"| FP16=ON | cudnn benchmark=ON | TF32=ON")
else:
    _DEVICE_STR = 'cpu'
    _CORES = os.cpu_count() or 4
    torch.set_num_threads(_CORES)
    torch.set_num_interop_threads(max(2, _CORES // 2))
    print(f"[HW] No GPU — CPU mode | Threads: {_CORES}")

# ── Path bootstrap: ensure database.py is always findable ────────────
_THIS_DIR  = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from database import db

# Conditional SAHI import
try:
    from sahi import AutoDetectionModel
    from sahi.predict import get_sliced_prediction
    SAHI_AVAILABLE = True
except ImportError:
    SAHI_AVAILABLE = False
    from ultralytics import YOLO


# ── Configuration ─────────────────────────────────────────────────

class VisionConfig:
    """مركزية إعدادات خط أنابيب الرؤية"""

    # Absolute path — search common locations regardless of cwd
    _CANDIDATES = [
        os.path.join(_THIS_DIR, "mcdis", "yolov8m.pt"),
        os.path.join(_THIS_DIR, "yolov8m.pt"),
        os.path.join(os.path.dirname(_THIS_DIR), "mcdis", "yolov8m.pt"),
        os.path.join(os.path.dirname(_THIS_DIR), "yolov8m.pt"),
    ]
    MODEL_PATH = next((p for p in _CANDIDATES if os.path.exists(p)), _CANDIDATES[0])
    CONFIDENCE_THRESHOLD = 0.45  # Balanced: reduces false positives (clouds/birds) while catching real drones
    SAHI_SLICE_SIZE = 640        # Increased slice resolution for better far away detection
    SAHI_OVERLAP_RATIO = 0.25    # Slightly more overlap to ensure drones aren't cut at slice edges
    YOLO_IMG_SIZE = 1280
    TRACKER_CONFIG = "bytetrack.yaml"

    # =========================================================================
    # ⚠️ [تحديث هام جداً في تغذية يولو والتصنيفات] ⚠️
    # لا يقتصر النظام على اكتشاف درونز "سمارت" كـ DJI فقط. 
    # يجب تغذية موديل يولو (YOLO Dataset) بأكثر من نوع درون، وبكل الأنواع المتاحة:
    # 1. المسيرات الإيرانية والانتحارية (مثل شاهد-136 بأشكالها المتعددة)
    # 2. الدرونز الانتحارية FPV Kamikaze سريعة المناورة
    # 3. الدرونز الحربية الكبيرة (Fixed-Wing مثل Wing Loong)
    # 4. طائرات MALE و HALE العسكرية الكبيرة
    # 5. الدرونز التجارية من كافة الأحجام (DJI Mini, Phantom, Autel)
    # 6. الدرونز المتناهية الصغر والغواصات (Micro/Nano)
    # بالإضافة إلى صنف لتصنيف الطيور لتقليل الأخطاء (False Positives).
    # النظام الآن مهيأ لدعم 12 تصنيف عسكري مختلف من ملف dataset_config.yaml.
    # =========================================================================
    DRONE_CLASSES = {
        'bird', 'airplane', 'kite',               # COCO defaults
        'dji_large', 'dji_mini', 'fpv_suicide',   # Custom classes
        'shahed_136', 'military_rotor', 'wing_loong',
        'military_fixed_wing', 'swarm_unit', 
        'generic_commercial', 'micro_nano'
    }
    TRACKED_CLASSES = {'person', 'car', 'truck', 'bus'}

    # ألوان الرسم (BGR)
    COLOR_THREAT = (0, 0, 255)      # أحمر — تهديد
    COLOR_TRACKED = (255, 160, 0)   # أزرق مائل — مراقب
    COLOR_HUD = (0, 255, 120)       # أخضر — HUD overlay

    # مسار مشاركة الإطارات مع لوحة القيادة
    DASHBOARD_FRAME_PATH = os.path.join(
        os.path.dirname(__file__), "dashboard", "static", "latest_frame.jpg"
    )

    OUTPUT_VIDEO = "mcdis_sahi_output.mp4"


# ── Detection Engine ──────────────────────────────────────────────

class DetectionEngine:
    """محرك الاكتشاف — يدعم SAHI والوضع العادي"""

    def __init__(self, config: VisionConfig):
        self.config = config
        self.device = _DEVICE_STR          # Use globally resolved device
        self.half   = _GPU_AVAILABLE       # FP16 only when GPU present
        self.sahi_model = None
        self.yolo_model = None
        self._init_model()

    def _init_model(self):
        """تحميل نموذج الذكاء الاصطناعي"""
        if SAHI_AVAILABLE:
            print(f"[VISION] 🧩 Loading SAHI Detection Engine (Device: {self.device} | FP16={self.half})")
            self.sahi_model = AutoDetectionModel.from_pretrained(
                model_type='yolov8',
                model_path=self.config.MODEL_PATH,
                confidence_threshold=self.config.CONFIDENCE_THRESHOLD,
                device=self.device,
            )
            print("[VISION]    SAHI Sliced Inference — READY")
        else:
            print(f"[VISION] ⚠️  SAHI unavailable. Using native YOLOv8 (Device: {self.device} | FP16={self.half})")
            self.yolo_model = YOLO(self.config.MODEL_PATH)
            self.yolo_model.to(self.device)
            # Warm-up: compile CUDA kernels before real frames arrive
            if _GPU_AVAILABLE:
                import numpy as np
                dummy_frame = np.zeros((640, 640, 3), dtype=np.uint8)
                self.yolo_model.predict(
                    dummy_frame, half=True, device=self.device, verbose=False
                )
                torch.cuda.synchronize()
                print("[VISION]    GPU warm-up complete")
            print("[VISION]    YOLOv8 Native Mode — READY")

    def detect_sahi(self, frame):
        """اكتشاف باستخدام SAHI — تقطيع الصورة لاكتشاف الأجسام البعيدة"""
        result = get_sliced_prediction(
            frame,
            self.sahi_model,
            slice_height=self.config.SAHI_SLICE_SIZE,
            slice_width=self.config.SAHI_SLICE_SIZE,
            overlap_height_ratio=self.config.SAHI_OVERLAP_RATIO,
            overlap_width_ratio=self.config.SAHI_OVERLAP_RATIO,
            verbose=0
        )

        detections = []
        for obj in result.object_prediction_list:
            cls_name = obj.category.name
            conf = int(obj.score.value * 100)
            x1, y1, x2, y2 = map(int, obj.bbox.to_xyxy())

            if cls_name in self.config.DRONE_CLASSES:
                display_name = 'UAV_SUSPECT' if cls_name in ['bird', 'airplane', 'aeroplane', 'kite'] else cls_name.upper()
                detections.append({
                    'class': cls_name, 'label': f'[SAHI] {display_name}',
                    'conf': conf, 'bbox': (x1, y1, x2, y2),
                    'threat': 'CRITICAL', 'color': self.config.COLOR_THREAT,
                    'thickness': 2
                })
            elif cls_name in self.config.TRACKED_CLASSES:
                detections.append({
                    'class': cls_name, 'label': f'{cls_name.upper()}',
                    'conf': conf, 'bbox': (x1, y1, x2, y2),
                    'threat': 'LOW', 'color': self.config.COLOR_TRACKED,
                    'thickness': 1
                })

        return detections

    def detect_yolo(self, frame):
        """اكتشاف باستخدام YOLOv8 مع ByteTrack للتتبع"""
        results = self.yolo_model.track(
            frame, persist=True,
            tracker=self.config.TRACKER_CONFIG,
            imgsz=self.config.YOLO_IMG_SIZE,
            half=self.half,       # FP16 on GPU
            device=self.device,
            verbose=False
        )

        detections = []
        if results[0].boxes is not None and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            ids = results[0].boxes.id.cpu().numpy()
            classes = results[0].boxes.cls.cpu().numpy()
            confs = results[0].boxes.conf.cpu().numpy()

            for box, track_id, cls_id, conf in zip(boxes, ids, classes, confs):
                x1, y1, x2, y2 = map(int, box)
                cls_name = self.yolo_model.names[int(cls_id)]
                acc = int(conf * 100)

                if cls_name in self.config.DRONE_CLASSES:
                    display_name = 'UAV_SUSPECT' if cls_name in ['bird', 'airplane', 'aeroplane', 'kite'] else cls_name.upper()
                    detections.append({
                        'class': cls_name, 'label': f'[ID:{int(track_id)}] {display_name} [CRITICAL]',
                        'conf': acc, 'bbox': (x1, y1, x2, y2),
                        'threat': 'CRITICAL', 'color': self.config.COLOR_THREAT,
                        'thickness': 2, 'track_id': int(track_id)
                    })
                elif cls_name in self.config.TRACKED_CLASSES:
                    detections.append({
                        'class': cls_name, 'label': f'[ID:{int(track_id)}] {cls_name.upper()}',
                        'conf': acc, 'bbox': (x1, y1, x2, y2),
                        'threat': 'LOW', 'color': self.config.COLOR_TRACKED,
                        'thickness': 1, 'track_id': int(track_id)
                    })

        return list(detections)

    def detect(self, frame):
        """واجهة موحدة للاكتشاف مع فلترة الـ False Positives"""
        if SAHI_AVAILABLE and self.sahi_model:
            detections = self.detect_sahi(frame)
        else:
            detections = self.detect_yolo(frame)

        h, w = frame.shape[:2]
        filtered = []
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            bw = x2 - x1
            bh = y2 - y1
            area = bw * bh
            frame_area = h * w

            # ── فلتر 1: استبعد الأجسام الكبيرة جداً (سحاب، خلفية) ──
            # لو الـ detection أكبر من 15% من الإطار → على الأرجح مش درون
            if area > frame_area * 0.15:
                continue

            # ── فلتر 2: استبعد الأجسام الصغيرة جداً (noise) ──
            if area < 100:  # أقل من 10×10 pixels
                continue

            # ── فلتر 3: نسبة الجانبين (aspect ratio) ──
            # السحاب عادةً wide جداً (ratio > 5) أو طويل (ratio < 0.2)
            ratio = bw / max(bh, 1)
            if ratio > 5.0 or ratio < 0.2:
                continue

            # ── فلتر 4: الموقع — الدرون في السماء (الـ 80% العلوية) ──
            cy = (y1 + y2) // 2
            if cy > h * 0.88:  # أسفل الإطار = أرض مش سماء
                continue

            filtered.append(det)

        return filtered


# ── Frame Renderer ────────────────────────────────────────────────

class FrameRenderer:
    """رسم الاكتشافات وعناصر HUD — High-Visibility + Pulse + Glow"""

    _THREAT_COLORS = {
        'CRITICAL': (0,   0, 255),
        'HIGH':     (0,  80, 255),
        'ELEVATED': (0, 165, 255),
        'LOW':      (0, 230, 100),
    }

    # ── Primitive helpers ───────────────────────────────────────────

    @staticmethod
    def _glow_line(frame, p1, p2, color, thick):
        """خط سريع جداً بدون التأثير على الـ FPS (بدون Frame Copy)"""
        # Shadow خارجي
        cv2.line(frame, p1, p2, (0, 0, 0), thick + 4)
        # لون أساسي (Glow)
        cv2.line(frame, p1, p2, color, thick + 1)
        # خط داخلي ساطع
        cv2.line(frame, p1, p2, (255, 255, 255) if thick > 1 else color, 1)

    @staticmethod
    def _glow_circle(frame, center, radius, color, thick):
        """دائرة سريعة جداً بدون Frame Copy"""
        cv2.circle(frame, center, radius, (0, 0, 0), thick + 4)
        cv2.circle(frame, center, radius, color, thick + 1)
        cv2.circle(frame, center, radius, (255, 255, 255) if thick > 1 else color, 1)

    # ── Corner Brackets ────────────────────────────────────────────

    @staticmethod
    def _draw_corner_brackets(frame, x1, y1, x2, y2, color, thick=2):
        """أقواس زوايا عسكرية مع Glow + Midpoint Ticks"""
        w    = x2 - x1
        clen = max(20, min(int(w * 0.30), 42))
        G    = FrameRenderer._glow_line
        # ── الزوايا الأربعة ──
        G(frame, (x1, y1), (x1 + clen, y1), color, thick)
        G(frame, (x1, y1), (x1, y1 + clen), color, thick)
        G(frame, (x2, y1), (x2 - clen, y1), color, thick)
        G(frame, (x2, y1), (x2, y1 + clen), color, thick)
        G(frame, (x1, y2), (x1 + clen, y2), color, thick)
        G(frame, (x1, y2), (x1, y2 - clen), color, thick)
        G(frame, (x2, y2), (x2 - clen, y2), color, thick)
        G(frame, (x2, y2), (x2, y2 - clen), color, thick)
        # ── Midpoint Ticks (علامات المنتصف على كل ضلع) ──
        mx, my = (x1 + x2) // 2, (y1 + y2) // 2
        tk = 7
        G(frame, (mx - tk, y1), (mx + tk, y1), color, 1)  # أعلى
        G(frame, (mx - tk, y2), (mx + tk, y2), color, 1)  # أسفل
        G(frame, (x1, my - tk), (x1, my + tk), color, 1)  # يسار
        G(frame, (x2, my - tk), (x2, my + tk), color, 1)  # يمين

    # ── Tactical Targeting Reticle (3 Rings) ───────────────────────

    @staticmethod
    def _draw_pulse_ring(frame, cx, cy, color, base_r=22):
        """Military Targeting Reticle — 3 حلقات تكتيكية"""
        t = time.time()

        # ── حلقة 1: داخلية ثابتة مع Tick marks (N/S/E/W) ──
        r1 = max(base_r - 10, 8)
        cv2.circle(frame, (cx, cy), r1, (0, 0, 0), 3)
        cv2.circle(frame, (cx, cy), r1, color, 1)
        tick = 6
        for angle_deg in [0, 90, 180, 270]:
            rad = math.radians(angle_deg)
            tx1 = int(cx + r1 * math.cos(rad))
            ty1 = int(cy + r1 * math.sin(rad))
            tx2 = int(cx + (r1 + tick) * math.cos(rad))
            ty2 = int(cy + (r1 + tick) * math.sin(rad))
            cv2.line(frame, (tx1, ty1), (tx2, ty2), (0, 0, 0), 3)
            cv2.line(frame, (tx1, ty1), (tx2, ty2), color, 1)

        # ── حلقة 2: وسطى دوارة (4 Arc segments تدور) ──
        r2 = base_r
        rotation = int((t * 45) % 360)   # دوران 45 درجة/ثانية
        arc_span = 65                      # طول كل Arc
        gap      = 90 - arc_span          # الفراغ بين الـ arcs
        for i in range(4):
            start = rotation + i * 90
            cv2.ellipse(frame, (cx, cy), (r2, r2), 0, start, start + arc_span, (0, 0, 0), 3)
            cv2.ellipse(frame, (cx, cy), (r2, r2), 0, start, start + arc_span, color, 1)

        # ── حلقة 3: خارجية نابضة ──
        r3 = int(base_r + 10 + 6 * abs(math.sin(t * 3.5)))
        cv2.circle(frame, (cx, cy), r3, (0, 0, 0), 3)
        cv2.circle(frame, (cx, cy), r3, color, 1)

    # ── Diamond Crosshair ──────────────────────────────────────────

    @staticmethod
    def _draw_crosshair(frame, cx, cy, color, size=18, thick=2):
        """Diamond Crosshair مع Glow"""
        G   = FrameRenderer._glow_line
        gap = 6
        G(frame, (cx - size, cy), (cx - gap, cy), color, thick)
        G(frame, (cx + gap,  cy), (cx + size, cy), color, thick)
        G(frame, (cx, cy - size), (cx, cy - gap), color, thick)
        G(frame, (cx, cy + gap),  (cx, cy + size), color, thick)
        cv2.circle(frame, (cx, cy), 4, (0, 0, 0), -1)
        cv2.circle(frame, (cx, cy), 3, color, -1)
        # Diamond خارجي
        d   = size + 7
        pts = [(cx, cy-d), (cx+d, cy), (cx, cy+d), (cx-d, cy)]
        for i in range(4):
            G(frame, pts[i], pts[(i+1)%4], color, 1)

    # ── Label Panel ────────────────────────────────────────────────

    @staticmethod
    def _draw_label(frame, cx, cy, x1, y1, x2, label_text, conf, threat, color, small_target):
        """لوحة تسمية مع Leader Line للأهداف الصغيرة"""
        font  = cv2.FONT_HERSHEY_SIMPLEX
        (lw, lh),  _ = cv2.getTextSize(label_text, font, 0.48, 1)
        line2         = f"CONF:{conf:02d}%  {threat}"
        (lw2,lh2), _  = cv2.getTextSize(line2, font, 0.38, 1)
        pad  = 5
        pw   = max(lw, lw2) + pad * 2 + 4
        ph   = lh + lh2 + pad * 3 + 2

        # لو الهدف صغير → Leader line + label بعيداً عنه
        if small_target:
            offset_x = 40
            offset_y = -50
            px1 = min(cx + offset_x, frame.shape[1] - pw - 4)
            py1 = max(cy + offset_y, 0)
            # Leader line من مركز الهدف للـ label
            cv2.line(frame, (cx, cy), (px1, py1 + ph // 2), (0,0,0), 3)
            cv2.line(frame, (cx, cy), (px1, py1 + ph // 2), color, 1)
        else:
            px1 = x1
            py1 = max(0, y1 - ph)

        px2, py2 = px1 + pw, py1 + ph

        # خلفية 75% معتمة
        roi = frame[py1:py2, px1:px2]
        if roi.size > 0:
            dark = roi.copy(); dark[:] = (8, 8, 8)
            cv2.addWeighted(dark, 0.75, roi, 0.25, 0, roi)
            frame[py1:py2, px1:px2] = roi

        # حد ملون يسار + أعلى
        cv2.line(frame, (px1, py1), (px1, py2), color, 3)
        cv2.line(frame, (px1, py1), (px2, py1), color, 1)

        # النص
        cv2.putText(frame, label_text, (px1+pad, py1+lh+pad),
                    font, 0.48, (255,255,255), 2, cv2.LINE_AA)
        cv2.putText(frame, line2, (px1+pad, py1+lh+lh2+pad*2+2),
                    font, 0.38, color, 1, cv2.LINE_AA)

    # ── Drone Silhouette Icon ──────────────────────────────────────

    @staticmethod
    def _draw_drone_silhouette(frame, cx, cy, cls_name, color, scale=1.0):
        """رسم شكل الطائرة/المسيّرة حسب النوع"""
        s   = max(0.4, scale)
        blk = (0, 0, 0)

        def L(p1, p2, th=1):
            cv2.line(frame, p1, p2, blk, th + 2)
            cv2.line(frame, p1, p2, color, th)

        def C(center, r, th=1):
            cv2.circle(frame, center, r, blk, th + 2)
            cv2.circle(frame, center, r, color, th)

        def poly(pts, th=1):
            arr = np.array(pts, np.int32).reshape(-1, 1, 2)
            cv2.polylines(frame, [arr], True, blk, th + 2)
            cv2.polylines(frame, [arr], True, color, th)

        # ────────────────────────────────────────────────────────
        if cls_name in ('shahed_136', 'military_fixed_wing', 'wing_loong', 'fixed_aircraft', 'fixed_wing', 'large_uav'):
            # شاهد-136 / Fixed-Wing: Delta wing من الأعلى
            bx = int(14 * s); by = int(10 * s)
            # جسم طويل
            L((cx, cy - int(12*s)), (cx, cy + int(12*s)), 1)
            # أجنحة Delta
            poly([
                (cx,          cy - int(10*s)),
                (cx - bx,     cy + int(5*s)),
                (cx - int(4*s), cy + int(3*s)),
                (cx,          cy + int(8*s)),
                (cx + int(4*s), cy + int(3*s)),
                (cx + bx,     cy + int(5*s)),
            ], 1)
            # ذيل
            L((cx - int(5*s), cy + int(10*s)), (cx + int(5*s), cy + int(10*s)), 1)

        elif cls_name in ('military_rotor', 'rotary'):
            # هيليكوبتر: جسم بيضاوي + روتور + ذيل
            cv2.ellipse(frame, (cx, cy), (int(9*s), int(4*s)), 0, 0, 360, blk, 3)
            cv2.ellipse(frame, (cx, cy), (int(9*s), int(4*s)), 0, 0, 360, color, 1)
            # روتور رئيسي
            L((cx - int(16*s), cy - int(6*s)), (cx + int(16*s), cy - int(6*s)), 2)
            # ذيل و tail rotor
            L((cx + int(9*s), cy), (cx + int(20*s), cy + int(3*s)), 1)
            L((cx + int(20*s), cy - int(4*s)), (cx + int(20*s), cy + int(7*s)), 1)

        elif cls_name in ('fpv_suicide', 'micro_nano', 'micro', 'missile'):
            # FPV Kamikaze / Missile: X صغير سريع
            a = int(9 * s)
            L((cx-a, cy-a), (cx+a, cy+a), 2)
            L((cx+a, cy-a), (cx-a, cy+a), 2)
            C((cx, cy), int(3*s), 1)

        elif cls_name in ('swarm_unit',):
            # سرب: ثلاثة نقاط صغيرة تمثل مجموعة
            for dx, dy in [(-int(8*s), 0), (int(8*s), -int(5*s)), (int(8*s), int(5*s))]:
                a = int(4*s)
                sx, sy = cx+dx, cy+dy
                L((sx-a, sy-a), (sx+a, sy+a), 1)
                L((sx+a, sy-a), (sx-a, sy+a), 1)
                C((sx, sy), int(2*s), 1)

        else:
            # Quad/DJI/Commercial: X مع 4 روتورات
            a = int(11 * s)
            r = int(4  * s)
            L((cx-a, cy-a), (cx+a, cy+a), 1)
            L((cx+a, cy-a), (cx-a, cy+a), 1)
            C((cx, cy), int(3*s), 1)
            for dx, dy in [(-a,-a),(a,-a),(-a,a),(a,a)]:
                C((cx+dx, cy+dy), r, 1)

    # ── Main draw call ─────────────────────────────────────────────

    @staticmethod
    def draw_detections(frame, detections):
        """رسم HUD التكتيكي العسكري — Pulse + Glow + Silhouette + Zoom Inset"""
        FH, FW = frame.shape[:2]

        for i, det in enumerate(detections):
            x1, y1, x2, y2 = det['bbox']
            conf     = det.get('conf', 0)
            threat   = det.get('threat', 'LOW')
            label    = det.get('label', 'TARGET')
            cls_name = det.get('class', '').lower().replace(' ', '_')
            color    = FrameRenderer._THREAT_COLORS.get(threat, (0,200,120))
            thick    = 3 if threat in ('CRITICAL', 'HIGH') else 2
            cx, cy   = (x1+x2)//2, (y1+y2)//2
            w        = x2 - x1
            h        = y2 - y1

            # ── 0. Tactical Zoom Inset (نافذة تكبير في الزاوية) ──
            INSET_W, INSET_H = 100, 80
            pad_crop = max(10, max(w, h) // 2)
            cx1 = max(0, cx - pad_crop)
            cy1 = max(0, cy - pad_crop)
            cx2 = min(FW, cx + pad_crop)
            cy2 = min(FH, cy + pad_crop)
            if cx2 > cx1 and cy2 > cy1:
                crop = frame[cy1:cy2, cx1:cx2].copy()
                # تحسين التباين داخل المحصول
                crop = cv2.convertScaleAbs(crop, alpha=1.6, beta=25)
                inset = cv2.resize(crop, (INSET_W, INSET_H))
                # موقع النافذة: يسار أعلى عشان مش تغطي على بوصلة الـ Dashboard
                ix = 14
                iy = 14 + i * (INSET_H + 30)
                if iy + INSET_H + 25 < FH:  # ما تخرجش براك الشاشة
                    # خلفية سوداء
                    frame[iy:iy+INSET_H, ix:ix+INSET_W] = 0
                    frame[iy:iy+INSET_H, ix:ix+INSET_W] = inset
                    # إطار ملون
                    cv2.rectangle(frame, (ix-3, iy-3), (ix+INSET_W+3, iy+INSET_H+3), (0,0,0), 4)
                    cv2.rectangle(frame, (ix-3, iy-3), (ix+INSET_W+3, iy+INSET_H+3), color, 1)
                    # خط أفقي وعمودي في منتصف النافذة (شبكة تصويب)
                    cv2.line(frame, (ix, iy+INSET_H//2), (ix+INSET_W, iy+INSET_H//2), color, 1)
                    cv2.line(frame, (ix+INSET_W//2, iy), (ix+INSET_W//2, iy+INSET_H), color, 1)
                    # ليبل
                    cv2.rectangle(frame, (ix-3, iy+INSET_H+3), (ix+INSET_W+3, iy+INSET_H+20), (0,0,0), -1)
                    cv2.putText(frame, f"TGT ZOOM x{max(2, pad_crop//max(w,h,1))+1}",
                                (ix+2, iy+INSET_H+16),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.32, color, 1, cv2.LINE_AA)

            # ── 1. أقواس الزوايا ──
            FrameRenderer._draw_corner_brackets(frame, x1, y1, x2, y2, color, thick)

            # ── 2. خطوط متقطعة للأهداف الحرجة ──
            if threat == 'CRITICAL':
                G, dash = FrameRenderer._glow_line, 7
                for yy in range(y1, y2, dash*2):
                    G(frame,(x1,yy),(x1,min(yy+dash,y2)),color,1)
                    G(frame,(x2,yy),(x2,min(yy+dash,y2)),color,1)
                for xx in range(x1, x2, dash*2):
                    G(frame,(xx,y1),(min(xx+dash,x2),y1),color,1)
                    G(frame,(xx,y2),(min(xx+dash,x2),y2),color,1)

            # ── 3. Pulsing Ring — خارج الهدف تماماً ──
            base_r = max(28, (max(w, h) // 2) + 14)  # خارج الـ bbox بالكامل
            FrameRenderer._draw_pulse_ring(frame, cx, cy, color, base_r)

            # ── 4. Drone Silhouette (جوا الدايرة الداخلية) ──
            sil_scale = min(max(min(w, h) / 32.0, 0.55), 2.5)
            FrameRenderer._draw_drone_silhouette(frame, cx, cy, cls_name, color, sil_scale)

            # ── 5. Label Panel (مع Leader line للأهداف الصغيرة) ──
            clean = label
            for p in ('[SAHI] ', '[MATCH] '):
                clean = clean.replace(p, '')
            if len(clean) > 24:
                clean = clean[:24]
            small = (w < 60)
            FrameRenderer._draw_label(frame, cx, cy, x1, y1, x2,
                                      clean, conf, threat, color, small)

        return frame





    @staticmethod
    def draw_hud(frame, fps=0, detection_count=0, is_night_mode=False):
        """رسم عناصر HUD التكتيكية"""
        h, w = frame.shape[:2]
        color = VisionConfig.COLOR_HUD

        # عنوان النظام
        cv2.putText(
            frame, "MCDIS v3.0 TACTICAL VISION",
            (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2
        )
        
        # مؤشر الرؤية الليلية
        if is_night_mode:
            cv2.putText(
                frame, "[THERMAL NIGHT MODE ACTIVE]",
                (w // 2 - 150, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2
            )

        # الوقت
        timestamp = datetime.now().strftime("%H:%M:%S UTC")
        cv2.putText(
            frame, timestamp,
            (w - 200, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1
        )

        # FPS
        cv2.putText(
            frame, f"FPS: {fps}",
            (20, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1
        )

        # عدد الاكتشافات
        cv2.putText(
            frame, f"TARGETS: {detection_count}",
            (w - 180, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1
        )

        # إطار HUD خارجي
        margin = 8
        cv2.rectangle(frame, (margin, margin), (w - margin, h - margin), color, 1)

        # أركان HUD
        corner_len = 30
        # أعلى يسار
        cv2.line(frame, (margin, margin), (margin + corner_len, margin), color, 2)
        cv2.line(frame, (margin, margin), (margin, margin + corner_len), color, 2)
        # أعلى يمين
        cv2.line(frame, (w - margin, margin), (w - margin - corner_len, margin), color, 2)
        cv2.line(frame, (w - margin, margin), (w - margin, margin + corner_len), color, 2)
        # أسفل يسار
        cv2.line(frame, (margin, h - margin), (margin + corner_len, h - margin), color, 2)
        cv2.line(frame, (margin, h - margin), (margin, h - margin - corner_len), color, 2)
        # أسفل يمين
        cv2.line(frame, (w - margin, h - margin), (w - margin - corner_len, h - margin), color, 2)
        cv2.line(frame, (w - margin, h - margin), (w - margin, h - margin - corner_len), color, 2)

        return frame


import argparse

# ── Video Source Manager ──────────────────────────────────────────

class VideoSource:
    """إدارة مصادر الفيديو (ملف محلي / كاميرا / RTSP)"""

    @staticmethod
    def get_source(custom_source=None):
        """تحديد مصدر الفيديو تلقائياً"""
        if custom_source:
            if os.path.exists(custom_source):
                print(f"[VIDEO] 📹 Source: Custom file '{custom_source}'")
                return custom_source
            elif custom_source.isdigit():
                print(f"[VIDEO] 📹 Source: Camera device {custom_source}")
                return int(custom_source)
            else:
                print(f"[VIDEO] 📹 Source: RTSP/Network stream '{custom_source}'")
                return custom_source

        # Default fallback logic
        local_candidates = [
            os.path.join(_THIS_DIR, "test.mp4"),
            os.path.join(_THIS_DIR, "mcdis", "test.mp4"),
            "test.mp4"
        ]
        
        for p in local_candidates:
            if os.path.exists(p):
                print(f"[VIDEO] 📹 Source: Found local test file '{p}'")
                return p
                
        print("[VIDEO] 📹 Source: No local file found. Defaulting to Live camera (device 0)")
        return 0


# ── Main Pipeline ─────────────────────────────────────────────────

def main():
    """تشغيل خط أنابيب الرؤية الحاسوبية الكامل"""
    
    parser = argparse.ArgumentParser(description="MCDIS Vision Pipeline")
    parser.add_argument("--source", type=str, help="Video source (0, filename, or RTSP URL)")
    args = parser.parse_args()

    print("=" * 65)
    print("  MCDIS v2.0 — Computer Vision Detection Pipeline")
    print("  Multi-Modal Counter-Drone Intelligence System")
    print("=" * 65)
    print()

    config = VisionConfig()

    # تسجيل بدء التشغيل
    db.log_event("SYSTEM_START", "VISION_PIPELINE", "Vision pipeline initializing")

    # تحميل المحرك
    engine = DetectionEngine(config)
    renderer = FrameRenderer()

    # مصدر الفيديو
    video_path = VideoSource.get_source(args.source)
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print("[ERROR] ❌ Failed to open video source.")
        db.log_event("SYSTEM_ERROR", "VISION_PIPELINE", "Video source unavailable")
        return

    # إعدادات الفيديو
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    if fps == 0:
        fps = 30

    print(f"[VIDEO]    Resolution: {w}x{h} @ {fps}fps")
    print()

    # كاتب الفيديو
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(config.OUTPUT_VIDEO, fourcc, fps, (w, h))

    # إنشاء مجلد الإخراج للداشبورد
    dashboard_dir = os.path.dirname(config.DASHBOARD_FRAME_PATH)
    os.makedirs(dashboard_dir, exist_ok=True)

    print("[VISION] 🚀 Detection pipeline ACTIVE. Press 'q' to stop.")
    print("=" * 65)

    frame_count = 0
    total_detections = 0
    fps_counter = 0
    fps_timer = time.time()
    current_fps = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            annotated = frame.copy()

            # اكتشاف
            detections = engine.detect(frame)
            total_detections += len(detections)

            # رسم الاكتشافات
            annotated = renderer.draw_detections(annotated, detections)

            # حساب FPS
            fps_counter += 1
            elapsed = time.time() - fps_timer
            if elapsed >= 1.0:
                current_fps = int(fps_counter / elapsed)
                fps_counter = 0
                fps_timer = time.time()

            # رسم HUD
            annotated = renderer.draw_hud(annotated, current_fps, len(detections))

            # تسجيل الاكتشافات في قاعدة البيانات
            for det in detections:
                sensor = "VISION_SENSOR_SAHI" if SAHI_AVAILABLE else "VISION_SENSOR"
                track_id = det.get('track_id', random.randint(100, 999))
                target_id = f"T-{str(track_id).zfill(3)}"
                
                # Save crop
                x1, y1, x2, y2 = det['bbox']
                crop = frame[max(0, y1-30):min(h, y2+30), max(0, x1-30):min(w, x2+30)].copy()
                snapshot_filename = f"snapshot_{target_id}_{int(time.time())}.jpg"
                snapshot_path = os.path.join(dashboard_dir, "static", "crops", snapshot_filename)
                
                if crop.size > 0:
                    try:
                        cv2.imwrite(snapshot_path, crop)
                    except: pass
                
                # Simulate Speed (Realistic for Shahed: 150-185 km/h)
                speed = random.uniform(145.5, 188.2) if det['class'] == "SHAHED-136" else random.uniform(20.0, 45.0)

                db.log_detection(
                    sensor_type=sensor,
                    target_id=target_id,
                    threat_level=det['threat'],
                    confidence=det['conf'],
                    details=f"{det['label']} identified as {det['class']}",
                    speed=speed,
                    image_path=snapshot_filename
                )

            # مشاركة الإطار مع لوحة القيادة
            try:
                cv2.imwrite(config.DASHBOARD_FRAME_PATH, annotated)
            except Exception:
                pass

            # عرض الإطار
            cv2.imshow("MCDIS Tactical Vision", annotated)
            out.write(annotated)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        print("\n[VISION] Controlled shutdown...")

    finally:
        cap.release()
        out.release()
        cv2.destroyAllWindows()

        db.log_event(
            "SYSTEM_STOP", "VISION_PIPELINE",
            f"Pipeline stopped. Frames: {frame_count}, Detections: {total_detections}"
        )
        print(f"\n[VISION] ✅ Pipeline complete. {frame_count} frames processed, {total_detections} detections.")


if __name__ == "__main__":
    main()
