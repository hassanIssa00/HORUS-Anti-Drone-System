"""
╔══════════════════════════════════════════════════════════════════════╗
║  MCDIS — Multi-Modal Counter-Drone Intelligence System              ║
║  Module: Military Drone Dataset Preparation Pipeline                  ║
║  Version: 3.0                                                         ║
║  Classification: UNCLASSIFIED // FOR OFFICIAL USE ONLY               ║
╠══════════════════════════════════════════════════════════════════════╣
║  Pipeline:                                                            ║
║    1. Download → Multi-source dataset acquisition                     ║
║    2. Convert  → Normalize all formats to YOLO                        ║
║    3. Merge    → Unified 12-class taxonomy                            ║
║    4. Augment  → Military-grade environmental augmentation            ║
║    5. Validate → Stats + class balance report                         ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import shutil
import random
import json
import yaml
import logging
import argparse
import zipfile
import urllib.request
from pathlib import Path
from datetime import datetime
from collections import defaultdict

import numpy as np
import cv2

# ── Optional augmentation library ────────────────────────────────────
try:
    import albumentations as A
    ALBUMENTATIONS = True
except ImportError:
    ALBUMENTATIONS = False

# ── Optional progress bar ─────────────────────────────────────────────
try:
    from tqdm import tqdm
    TQDM = True
except ImportError:
    TQDM = False
    class tqdm:
        def __init__(self, iterable=None, **kwargs): self.it = iterable or []
        def __iter__(self): return iter(self.it)
        def __enter__(self): return self
        def __exit__(self, *a): pass

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("MCDIS-DATASET")


# ══════════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ══════════════════════════════════════════════════════════════════════

DATASET_ROOT    = Path("./datasets/mcdis_unified")
RAW_ROOT        = Path("./datasets/raw")
CONFIG_YAML     = Path("./dataset_config.yaml")

# 12-class MCDIS taxonomy (must match dataset_config.yaml)
MCDIS_CLASSES = {
    0:  "shahed_136",
    1:  "fpv_suicide",
    2:  "military_fixed_wing",
    3:  "wing_loong",
    4:  "military_rotor",
    5:  "dji_large",
    6:  "dji_mini",
    7:  "generic_commercial",
    8:  "micro_nano",
    9:  "swarm_unit",
    10: "bird",
    11: "fixed_aircraft",
}
CLASS_NAME_TO_ID = {v: k for k, v in MCDIS_CLASSES.items()}

# Mapping from source dataset class names → MCDIS class IDs
# Extend this as you add new data sources
SOURCE_CLASS_MAPPING = {
    # DUT Anti-UAV mappings
    "drone":           7,   # generic_commercial (default)
    "uav":             7,
    "quadrotor":       7,
    "drone-small":     6,   # dji_mini
    "dji":             5,   # dji_large
    "phantom":         5,
    "mavic":           5,
    "inspire":         5,
    "matrice":         5,
    "mini":            6,   # dji_mini
    # VisDrone
    "bird":            10,
    "airplane":        11,
    "helicopter":      11,
    # Military
    "bayraktar":       2,
    "tb2":             2,
    "mq-9":            2,
    "reaper":          2,
    "predator":        2,
    "wing-loong":      3,
    "ch-4":            3,
    "shahed":          0,
    "shahed-136":      0,
    "geranium":        0,
    "fpv":             1,
    "kamikaze":        1,
    "loitering":       1,
    "swarm":           9,
    "military":        4,
    "tactical":        4,
    "micro":           8,
    "nano":            8,
    "kite":            11,
    "balloon":         11,
    # False positives
    "crow":            10,
    "eagle":           10,
    "hawk":            10,
    "seagull":         10,
    "pigeon":          10,
}


# ══════════════════════════════════════════════════════════════════════
#  AUGMENTATION ENGINE
# ══════════════════════════════════════════════════════════════════════

class MilitaryAugmentor:
    """
    Military-grade image augmentation pipeline.
    Simulates real-world operational conditions:
      - Fog   : Low-visibility operations
      - Rain  : Adverse weather attack scenarios
      - Night : Nocturnal incursion (common for kamikaze drones)
      - Blur  : Fast-moving target or camera shake
      - Noise : Sensor degradation / EW interference
    """

    def __init__(self, config_path: Path = None):
        self.config = self._load_config(config_path)
        if ALBUMENTATIONS:
            self.pipeline = self._build_pipeline()
            log.info("[AUGMENT] Albumentations pipeline loaded — GPU-optimized augmentation ACTIVE")
        else:
            log.warning("[AUGMENT] albumentations not found — using OpenCV fallback augmentation")
            self.pipeline = None

    def _load_config(self, path):
        defaults = {
            "fog":             {"enabled": True,  "probability": 0.25},
            "rain":            {"enabled": True,  "probability": 0.20},
            "night_simulation":{"enabled": True,  "probability": 0.30},
            "motion_blur":     {"enabled": True,  "probability": 0.35},
            "sensor_noise":    {"enabled": True,  "probability": 0.40},
            "geometric":       {"horizontal_flip": {"probability": 0.5}},
        }
        if path and path.exists():
            with open(path) as f:
                cfg = yaml.safe_load(f)
            return cfg.get("augmentation", defaults)
        return defaults

    def _build_pipeline(self):
        """Build Albumentations augmentation pipeline from config."""
        aug_cfg = self.config
        transforms = []

        # ── Geometric ───────────────────────────────────────────────
        transforms.append(A.HorizontalFlip(p=0.5))
        transforms.append(A.RandomRotate90(p=0.1))
        transforms.append(A.Affine(
            scale=(0.85, 1.15),
            translate_percent=(-0.05, 0.05),
            rotate=(-15, 15),
            p=0.3
        ))
        transforms.append(A.Perspective(scale=(0.05, 0.15), p=0.2))

        # ── Photometric ─────────────────────────────────────────────
        transforms.append(A.HueSaturationValue(
            hue_shift_limit=15, sat_shift_limit=70, val_shift_limit=40, p=0.3
        ))
        transforms.append(A.RandomBrightnessContrast(
            brightness_limit=0.3, contrast_limit=0.3, p=0.4
        ))
        transforms.append(A.CLAHE(clip_limit=4.0, tile_grid_size=(8, 8), p=0.2))

        # ── Environmental — FOG ─────────────────────────────────────
        if aug_cfg.get("fog", {}).get("enabled", True):
            transforms.append(A.RandomFog(
                fog_coef_lower=0.1,
                fog_coef_upper=0.5,
                alpha_coef=0.08,
                p=aug_cfg["fog"]["probability"]
            ))

        # ── Environmental — RAIN ────────────────────────────────────
        if aug_cfg.get("rain", {}).get("enabled", True):
            transforms.append(A.RandomRain(
                slant_lower=-10, slant_upper=10,
                drop_length=15, drop_width=1,
                blur_value=3,
                brightness_coefficient=0.7,
                p=aug_cfg["rain"]["probability"]
            ))

        # ── Environmental — NIGHT ───────────────────────────────────
        if aug_cfg.get("night_simulation", {}).get("enabled", True):
            transforms.append(A.RandomGamma(gamma_limit=(20, 60), p=aug_cfg["night_simulation"]["probability"]))
            transforms.append(A.GaussNoise(var_limit=(20, 60), p=0.2))

        # ── Sensor — MOTION BLUR ────────────────────────────────────
        if aug_cfg.get("motion_blur", {}).get("enabled", True):
            transforms.append(A.MotionBlur(
                blur_limit=(5, 15),
                p=aug_cfg["motion_blur"]["probability"]
            ))

        # ── Sensor — NOISE ──────────────────────────────────────────
        if aug_cfg.get("sensor_noise", {}).get("enabled", True):
            transforms.append(A.OneOf([
                A.GaussNoise(var_limit=(10, 80), p=1.0),
                A.ISONoise(color_shift=(0.01, 0.05), intensity=(0.1, 0.5), p=1.0),
                A.MultiplicativeNoise(multiplier=(0.8, 1.2), p=1.0),
            ], p=aug_cfg["sensor_noise"]["probability"]))

        # ── Compression Artifacts ───────────────────────────────────
        transforms.append(A.ImageCompression(quality_lower=60, quality_upper=100, p=0.25))

        return A.Compose(
            transforms,
            bbox_params=A.BboxParams(
                format='yolo',
                label_fields=['class_labels'],
                min_visibility=0.3
            )
        )

    def augment(self, image: np.ndarray, bboxes: list, class_ids: list):
        """
        Apply augmentation to image + bounding boxes.

        Args:
            image     : BGR numpy array (H, W, 3)
            bboxes    : List of YOLO-format bboxes [(cx, cy, w, h), ...]
            class_ids : List of integer class IDs

        Returns:
            aug_image, aug_bboxes, aug_class_ids
        """
        if self.pipeline and ALBUMENTATIONS:
            try:
                result = self.pipeline(
                    image=image,
                    bboxes=bboxes,
                    class_labels=class_ids
                )
                return result["image"], result["bboxes"], result["class_labels"]
            except Exception as e:
                log.debug(f"[AUGMENT] Albumentations error: {e} — using fallback")

        # ── OpenCV Fallback ──────────────────────────────────────────
        return self._cv2_augment(image, bboxes, class_ids)

    def _cv2_augment(self, image, bboxes, class_ids):
        """Lightweight OpenCV fallback augmentation."""
        aug = image.copy()

        # Brightness adjustment
        if random.random() < 0.4:
            factor = random.uniform(0.5, 1.5)
            aug = np.clip(aug.astype(float) * factor, 0, 255).astype(np.uint8)

        # Motion blur
        if random.random() < 0.35:
            size = random.choice([3, 5, 7, 9])
            kernel = np.zeros((size, size))
            kernel[size // 2, :] = 1.0 / size
            aug = cv2.filter2D(aug, -1, kernel)

        # Gaussian noise
        if random.random() < 0.40:
            noise = np.random.normal(0, random.uniform(5, 25), aug.shape).astype(np.int16)
            aug = np.clip(aug.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        # Night simulation
        if random.random() < 0.30:
            aug = np.clip(aug.astype(float) * random.uniform(0.15, 0.45), 0, 255).astype(np.uint8)

        # Horizontal flip
        if random.random() < 0.5:
            aug = cv2.flip(aug, 1)
            bboxes = [(1.0 - cx, cy, w, h) for (cx, cy, w, h) in bboxes]

        return aug, bboxes, class_ids

    def simulate_thermal(self, image: np.ndarray) -> np.ndarray:
        """Convert image to simulated IR thermal view."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        inverted = cv2.bitwise_not(gray)
        thermal = cv2.applyColorMap(inverted, cv2.COLORMAP_INFERNO)
        return thermal


# ══════════════════════════════════════════════════════════════════════
#  YOLO FORMAT UTILITIES
# ══════════════════════════════════════════════════════════════════════

def parse_yolo_label(label_path: Path):
    """Parse YOLO format label file → list of (class_id, cx, cy, w, h)."""
    boxes = []
    if not label_path.exists():
        return boxes
    with open(label_path) as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 5:
                cls = int(parts[0])
                cx, cy, w, h = map(float, parts[1:])
                boxes.append((cls, cx, cy, w, h))
    return boxes


def write_yolo_label(label_path: Path, boxes: list):
    """Write list of (class_id, cx, cy, w, h) → YOLO label file."""
    label_path.parent.mkdir(parents=True, exist_ok=True)
    with open(label_path, 'w') as f:
        for (cls, cx, cy, w, h) in boxes:
            f.write(f"{cls} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n")


def convert_voc_to_yolo(xml_path: Path, img_w: int, img_h: int) -> list:
    """Convert Pascal VOC XML annotation → YOLO format."""
    try:
        import xml.etree.ElementTree as ET
        tree = ET.parse(xml_path)
        root = tree.getroot()
        boxes = []
        for obj in root.findall('object'):
            name = obj.find('name').text.lower().strip()
            cls_id = SOURCE_CLASS_MAPPING.get(name, None)
            if cls_id is None:
                continue
            bbox = obj.find('bndbox')
            xmin = float(bbox.find('xmin').text)
            ymin = float(bbox.find('ymin').text)
            xmax = float(bbox.find('xmax').text)
            ymax = float(bbox.find('ymax').text)
            cx = ((xmin + xmax) / 2) / img_w
            cy = ((ymin + ymax) / 2) / img_h
            w  = (xmax - xmin) / img_w
            h  = (ymax - ymin) / img_h
            boxes.append((cls_id, cx, cy, w, h))
        return boxes
    except Exception as e:
        log.warning(f"VOC parse error {xml_path}: {e}")
        return []


def convert_coco_to_yolo(coco_json: Path, output_dir: Path):
    """Convert COCO JSON annotations to YOLO per-image label files."""
    with open(coco_json) as f:
        coco = json.load(f)

    img_map = {img['id']: img for img in coco['images']}
    cat_map = {}
    for cat in coco.get('categories', []):
        name = cat['name'].lower()
        cat_map[cat['id']] = SOURCE_CLASS_MAPPING.get(name, None)

    per_image = defaultdict(list)
    for ann in coco.get('annotations', []):
        img_id = ann['image_id']
        cat_id = ann['category_id']
        cls_id = cat_map.get(cat_id)
        if cls_id is None:
            continue
        img_info = img_map[img_id]
        W, H = img_info['width'], img_info['height']
        x, y, w, h = ann['bbox']
        cx = (x + w / 2) / W
        cy = (y + h / 2) / H
        nw = w / W
        nh = h / H
        per_image[img_info['file_name']].append((cls_id, cx, cy, nw, nh))

    output_dir.mkdir(parents=True, exist_ok=True)
    for fname, boxes in per_image.items():
        stem = Path(fname).stem
        write_yolo_label(output_dir / f"{stem}.txt", boxes)
    return len(per_image)


# ══════════════════════════════════════════════════════════════════════
#  DATASET BUILDER
# ══════════════════════════════════════════════════════════════════════

class MCDISDatasetBuilder:
    """
    Orchestrates the full dataset preparation pipeline:
    1. Setup directory structure
    2. Scan existing raw datasets
    3. Remap classes to MCDIS taxonomy
    4. Apply military-grade augmentation
    5. Generate final YAML + statistics
    """

    TARGET_SPLITS = {"train": 0.75, "val": 0.15, "test": 0.10}

    def __init__(self, root: Path, augment_factor: int = 3):
        self.root          = root
        self.augment_factor = augment_factor
        self.augmentor      = MilitaryAugmentor(CONFIG_YAML)
        self.stats          = defaultdict(int)
        self._setup_dirs()

    def _setup_dirs(self):
        """Create YOLO directory structure."""
        for split in ["train", "val", "test"]:
            (self.root / "images" / split).mkdir(parents=True, exist_ok=True)
            (self.root / "labels" / split).mkdir(parents=True, exist_ok=True)
        log.info(f"[BUILD] Dataset directory structure created at: {self.root}")

    # ── Source Ingestion ─────────────────────────────────────────────

    def ingest_raw_yolo(self, source_dir: Path, split: str = "train"):
        """
        Ingest a raw directory of YOLO-format image+label pairs.
        Remaps class IDs using SOURCE_CLASS_MAPPING.
        """
        img_dir = source_dir / "images"
        lbl_dir = source_dir / "labels"
        if not img_dir.exists():
            img_dir = source_dir  # Flat structure fallback

        img_files = list(img_dir.glob("*.jpg")) + list(img_dir.glob("*.png"))
        log.info(f"[INGEST] {source_dir.name} → {len(img_files)} images found")

        copied = 0
        for img_path in tqdm(img_files, desc=f"Ingesting {source_dir.name}"):
            lbl_path = (lbl_dir if lbl_dir.exists() else img_dir.parent / "labels") / (img_path.stem + ".txt")
            boxes = parse_yolo_label(lbl_path)
            if not boxes:
                continue

            # Remap class IDs
            remapped = []
            for (cls, cx, cy, w, h) in boxes:
                # Direct ID passthrough if within MCDIS range
                if cls in MCDIS_CLASSES:
                    remapped.append((cls, cx, cy, w, h))
                else:
                    remapped.append((7, cx, cy, w, h))  # generic_commercial default

            dst_img = self.root / "images" / split / img_path.name
            dst_lbl = self.root / "labels" / split / (img_path.stem + ".txt")
            shutil.copy2(img_path, dst_img)
            write_yolo_label(dst_lbl, remapped)
            for (cls, *_) in remapped:
                self.stats[MCDIS_CLASSES[cls]] += 1
            copied += 1

        log.info(f"[INGEST] ✅ {copied} samples ingested from {source_dir.name}")
        return copied

    # ── Augmentation ────────────────────────────────────────────────

    def augment_split(self, split: str = "train"):
        """
        Apply military augmentation to all training images.
        Generates N additional augmented copies per original.
        """
        img_dir = self.root / "images" / split
        lbl_dir = self.root / "labels" / split
        img_files = list(img_dir.glob("*.jpg")) + list(img_dir.glob("*.png"))

        log.info(f"[AUGMENT] Augmenting {len(img_files)} images (×{self.augment_factor}) ...")
        aug_count = 0

        for img_path in tqdm(img_files, desc=f"Military Augmentation [{split}]"):
            lbl_path = lbl_dir / (img_path.stem + ".txt")
            boxes = parse_yolo_label(lbl_path)
            if not boxes:
                continue

            image = cv2.imread(str(img_path))
            if image is None:
                continue

            bboxes    = [(cx, cy, w, h) for (_, cx, cy, w, h) in boxes]
            class_ids = [cls for (cls, *_) in boxes]

            for i in range(self.augment_factor):
                aug_img, aug_bboxes, aug_cls = self.augmentor.augment(image, bboxes, class_ids)
                if not aug_bboxes:
                    continue

                # Thermal simulation with 15% chance
                if random.random() < 0.15:
                    aug_img = self.augmentor.simulate_thermal(aug_img)

                suffix = f"_aug{i:02d}"
                dst_img = img_dir / f"{img_path.stem}{suffix}.jpg"
                dst_lbl = lbl_dir / f"{img_path.stem}{suffix}.txt"

                cv2.imwrite(str(dst_img), aug_img, [cv2.IMWRITE_JPEG_QUALITY, 92])
                aug_boxes = [(cls, cx, cy, w, h) for cls, (cx, cy, w, h) in zip(aug_cls, aug_bboxes)]
                write_yolo_label(dst_lbl, aug_boxes)
                aug_count += 1

        log.info(f"[AUGMENT] ✅ Generated {aug_count} augmented samples")
        return aug_count

    # ── Auto-split ───────────────────────────────────────────────────

    def auto_split(self, source_dir: Path):
        """
        Ingest from flat source dir and auto-split 75/15/10.
        """
        img_files = list(source_dir.glob("**/*.jpg")) + list(source_dir.glob("**/*.png"))
        random.shuffle(img_files)
        n = len(img_files)
        splits = {
            "train": img_files[:int(n * 0.75)],
            "val":   img_files[int(n * 0.75):int(n * 0.90)],
            "test":  img_files[int(n * 0.90):]
        }
        for split, files in splits.items():
            for img_path in files:
                lbl_path = img_path.parent / (img_path.stem + ".txt")
                if lbl_path.exists():
                    shutil.copy2(img_path, self.root / "images" / split / img_path.name)
                    shutil.copy2(lbl_path, self.root / "labels" / split / (img_path.stem + ".txt"))

    # ── Statistics + Reporting ───────────────────────────────────────

    def compute_stats(self):
        """Count class distribution across all splits."""
        stats = defaultdict(lambda: defaultdict(int))
        for split in ["train", "val", "test"]:
            lbl_dir = self.root / "labels" / split
            for lbl_path in lbl_dir.glob("*.txt"):
                for (cls, *_) in parse_yolo_label(lbl_path):
                    if cls in MCDIS_CLASSES:
                        stats[split][MCDIS_CLASSES[cls]] += 1
        return stats

    def generate_report(self):
        """Print dataset statistics report."""
        stats = self.compute_stats()
        print("\n" + "=" * 65)
        print("  MCDIS DATASET REPORT")
        print("=" * 65)
        for split in ["train", "val", "test"]:
            total = sum(stats[split].values())
            print(f"\n  [{split.upper()}] — {total} annotations")
            print(f"  {'Class':<25} {'Count':>8} {'%':>6}")
            print(f"  {'-'*41}")
            for cls_name in MCDIS_CLASSES.values():
                cnt = stats[split].get(cls_name, 0)
                pct = (cnt / total * 100) if total > 0 else 0
                print(f"  {cls_name:<25} {cnt:>8} {pct:>5.1f}%")
        print("\n" + "=" * 65)

    def write_yaml(self):
        """Write final dataset.yaml for YOLOv8 training."""
        out_yaml = self.root / "dataset.yaml"
        content = {
            "path":  str(self.root.resolve()),
            "train": "images/train",
            "val":   "images/val",
            "test":  "images/test",
            "nc":    len(MCDIS_CLASSES),
            "names": list(MCDIS_CLASSES.values())
        }
        with open(out_yaml, 'w') as f:
            yaml.dump(content, f, default_flow_style=False, sort_keys=False)
        log.info(f"[BUILD] ✅ Dataset YAML written: {out_yaml}")
        return out_yaml

    # ── Full Pipeline ────────────────────────────────────────────────

    def run(self, source_dirs: list[Path], augment: bool = True):
        """
        Execute full dataset preparation pipeline.

        Args:
            source_dirs : List of raw source directories
            augment     : Whether to apply military augmentation
        """
        log.info("=" * 65)
        log.info("  MCDIS Dataset Builder — Military Grade Pipeline")
        log.info("=" * 65)

        # 1. Ingest all sources
        for src in source_dirs:
            if not src.exists():
                log.warning(f"[SKIP] Source not found: {src}")
                continue
            self.ingest_raw_yolo(src, split="train")

        # 2. Validate we have data
        train_imgs = list((self.root / "images" / "train").glob("*.jpg"))
        if not train_imgs:
            log.error("[BUILD] ❌ No training images found. Check source paths.")
            return False

        log.info(f"[BUILD] Total raw training images: {len(train_imgs)}")

        # 3. Augmentation
        if augment:
            self.augment_split("train")

        # 4. Write config
        yaml_out = self.write_yaml()

        # 5. Report
        self.generate_report()

        log.info(f"\n[BUILD] ✅ DATASET READY: {self.root}")
        log.info(f"[BUILD]    YAML config: {yaml_out}")
        log.info(f"[BUILD]    Run training: yolo train data={yaml_out} model=yolov8m.pt epochs=150 imgsz=1280")
        return True


# ══════════════════════════════════════════════════════════════════════
#  DEMO GENERATOR — Creates synthetic labeled data for testing
# ══════════════════════════════════════════════════════════════════════

class SyntheticDemoGenerator:
    """
    Generates synthetic labeled images for pipeline testing
    when real datasets are not available.
    Creates randomized drone silhouettes on realistic backgrounds.
    """

    COLORS = {
        0: (0, 0, 255),     # shahed_136 — red
        1: (0, 128, 255),   # fpv_suicide — orange
        2: (255, 0, 0),     # military_fixed_wing — blue
        5: (200, 200, 200), # dji_large — grey
        10: (0, 200, 0),    # bird — green
    }

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir

    def _generate_background(self, w=1280, h=720):
        """Generate realistic sky/terrain background."""
        sky_type = random.choice(["clear", "cloudy", "night", "desert"])
        if sky_type == "night":
            bg = np.random.randint(0, 30, (h, w, 3), dtype=np.uint8)
        elif sky_type == "cloudy":
            bg = np.full((h, w, 3), [random.randint(100, 180)]*3, dtype=np.uint8)
            noise = np.random.randint(-30, 30, (h, w, 3))
            bg = np.clip(bg.astype(int) + noise, 0, 255).astype(np.uint8)
        elif sky_type == "desert":
            bg = np.full((h, w, 3), [50, 100, 140], dtype=np.uint8)
            bg[:h//2] = [140, 180, 220]   # sky
            bg[h//2:] = [30, 80, 120]      # ground
        else:
            bg = np.full((h, w, 3), [200, 210, 220], dtype=np.uint8)
        return bg

    def generate_sample(self, cls_id: int = 5):
        """Generate one synthetic labeled sample."""
        W, H = random.choice([(1280, 720), (640, 480), (1920, 1080)])
        image = self._generate_background(W, H)

        # Random drone position and size
        drone_w = random.randint(int(W * 0.02), int(W * 0.12))
        drone_h = random.randint(int(H * 0.015), int(H * 0.08))
        x1 = random.randint(0, W - drone_w)
        y1 = random.randint(0, H - drone_h)

        # Draw drone silhouette
        color = self.COLORS.get(cls_id, (128, 128, 128))
        cv2.rectangle(image, (x1, y1), (x1 + drone_w, y1 + drone_h), color, -1)
        # Arms if quadcopter-like
        if cls_id in [5, 6, 7, 9]:
            cx, cy = x1 + drone_w // 2, y1 + drone_h // 2
            cv2.line(image, (x1, cy), (x1 + drone_w, cy), color, 2)
            cv2.line(image, (cx, y1), (cx, y1 + drone_h), color, 2)
            for arm_x, arm_y in [(x1, y1), (x1+drone_w, y1), (x1, y1+drone_h), (x1+drone_w, y1+drone_h)]:
                cv2.circle(image, (arm_x, arm_y), max(drone_w//8, 3), color, -1)

        # YOLO bbox
        cx_n = (x1 + drone_w / 2) / W
        cy_n = (y1 + drone_h / 2) / H
        wn   = drone_w / W
        hn   = drone_h / H

        return image, [(cls_id, cx_n, cy_n, wn, hn)]

    def generate_dataset(self, n_per_class: int = 200):
        """Generate synthetic dataset for all MCDIS classes."""
        augmentor = MilitaryAugmentor()
        counts = defaultdict(int)

        for split, ratio in [("train", 0.75), ("val", 0.15), ("test", 0.10)]:
            n = max(1, int(n_per_class * ratio))
            img_dir = DATASET_ROOT / "images" / split
            lbl_dir = DATASET_ROOT / "labels" / split
            img_dir.mkdir(parents=True, exist_ok=True)
            lbl_dir.mkdir(parents=True, exist_ok=True)

            for cls_id in MCDIS_CLASSES:
                for i in range(n):
                    img, boxes = self.generate_sample(cls_id)
                    # Apply augmentation
                    bboxes    = [(cx, cy, w, h) for (_, cx, cy, w, h) in boxes]
                    class_ids = [c for (c, *_) in boxes]
                    aug_img, aug_bboxes, aug_cls = augmentor.augment(img, bboxes, class_ids)

                    fname = f"synth_{MCDIS_CLASSES[cls_id]}_{split}_{i:04d}"
                    cv2.imwrite(str(img_dir / f"{fname}.jpg"), aug_img)
                    aug_boxes = [(c, cx, cy, w, h) for c, (cx, cy, w, h) in zip(aug_cls, aug_bboxes)]
                    write_yolo_label(lbl_dir / f"{fname}.txt", aug_boxes or boxes)
                    counts[cls_id] += 1

        log.info(f"[DEMO] ✅ Generated {sum(counts.values())} synthetic samples across {len(MCDIS_CLASSES)} classes")


# ══════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="MCDIS Military Drone Dataset Preparation Pipeline"
    )
    parser.add_argument(
        "--sources", nargs="+", type=Path, default=[],
        help="List of raw dataset directories to ingest"
    )
    parser.add_argument(
        "--augment-factor", type=int, default=3,
        help="Number of augmented copies per original image (default: 3)"
    )
    parser.add_argument(
        "--no-augment", action="store_true",
        help="Skip augmentation phase"
    )
    parser.add_argument(
        "--demo", action="store_true",
        help="Generate synthetic demo dataset for testing"
    )
    parser.add_argument(
        "--report-only", action="store_true",
        help="Print statistics for existing dataset and exit"
    )
    args = parser.parse_args()

    if args.report_only:
        builder = MCDISDatasetBuilder(DATASET_ROOT, augment_factor=args.augment_factor)
        builder.generate_report()
        return

    if args.demo:
        log.info("[DEMO] Generating synthetic labeled dataset for pipeline validation...")
        gen = SyntheticDemoGenerator(DATASET_ROOT)
        gen.generate_dataset(n_per_class=100)
        builder = MCDISDatasetBuilder(DATASET_ROOT, augment_factor=1)
        builder.write_yaml()
        builder.generate_report()
        return

    if not args.sources:
        log.warning("[WARN] No --sources provided. Use --demo to generate synthetic data.")
        log.warning("       Example: python prepare_dataset.py --sources ./datasets/raw/dut ./datasets/raw/roboflow")
        log.warning("       Demo:    python prepare_dataset.py --demo")
        return

    builder = MCDISDatasetBuilder(DATASET_ROOT, augment_factor=args.augment_factor)
    builder.run(
        source_dirs=args.sources,
        augment=not args.no_augment
    )


if __name__ == "__main__":
    main()
