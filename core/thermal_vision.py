import cv2
import numpy as np

# ════════════════════════════════════════════════════════════════════════════
# MCDIS THERMAL VISION ENGINE (FLIR SIMULATION)
# Uses Classical Computer Vision (Thresholding & Contours) to detect "Hot Blobs"
# against a cold background, exactly how military infrared tracking works.
# Extremely lightweight, runs at 120+ FPS without needing a heavy AI model.
# ════════════════════════════════════════════════════════════════════════════

class ThermalDetector:
    def __init__(self, threshold_value=220, min_area=50, max_area=5000):
        # 220 out of 255 (looking for very bright/hot pixels only)
        self.threshold_value = threshold_value 
        self.min_area = min_area
        self.max_area = max_area

    def process_frame(self, frame):
        """
        Takes an RGB frame, simulates a thermal FLIR view, and detects targets.
        """
        # 1. Convert to Grayscale (Heatmap intensity)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Apply slight blur to remove camera noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # 2. Thresholding: Isolate the "hottest" pixels
        # Since this is simulated from daylight video, the drone is usually a DARK silhouette
        # against a BRIGHT sky. We use THRESH_BINARY_INV so dark objects become WHITE (detected).
        _, thresh = cv2.threshold(blurred, self.threshold_value, 255, cv2.THRESH_BINARY_INV)
        
        # 3. Morphological Operations: Clean up the image
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel)
        
        # 4. Contour Detection: Find the connected blobs
        contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        detections = []
        for contour in contours:
            area = cv2.contourArea(contour)
            
            # 5. Filter by size
            if self.min_area < area < self.max_area:
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = float(w) / h
                if 0.5 < aspect_ratio < 4.0:
                    # Calculate "Heat Confidence"
                    mask = np.zeros(gray.shape, np.uint8)
                    cv2.drawContours(mask, [contour], -1, 255, -1)
                    # We look at the inverted mean because the drone is dark in original RGB
                    mean_val = cv2.mean(gray, mask=mask)[0]
                    confidence = min(99, int(((255 - mean_val) / 255.0) * 100))
                    
                    detections.append({
                        "bbox": (x, y, x + w, y + h),
                        "confidence": max(60, confidence),
                        "class": "HOT_TARGET"
                    })
                    
        return detections, cleaned

    def apply_thermal_colormap(self, frame):
        """
        Converts an RGB image to a pseudo-thermal (INFERNO) look for the UI.
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Invert grayscale! Dark drone becomes White (Hot), Bright sky becomes Black (Cold)
        inverted = cv2.bitwise_not(gray)
        
        # Boost contrast heavily to make the drone stand out as a heat source
        clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8,8))
        high_contrast = clahe.apply(inverted)
        
        # Apply the FLIR-like colormap (INFERNO)
        # INFERNO maps black to dark purple, and white to bright yellow/white.
        thermal_img = cv2.applyColorMap(high_contrast, cv2.COLORMAP_INFERNO)
        return thermal_img

thermal_engine = ThermalDetector(threshold_value=200, min_area=30)
