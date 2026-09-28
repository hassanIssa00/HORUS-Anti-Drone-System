import cv2
import numpy as np
import os
import math

OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "video drone test"))
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# 1280x720, 30fps, 10 seconds = 300 frames
WIDTH = 1280
HEIGHT = 720
FPS = 30
FRAMES = 300

def create_video(filename, draw_func):
    path = os.path.join(OUTPUT_DIR, filename)
    out = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*'mp4v'), FPS, (WIDTH, HEIGHT))
    
    for i in range(FRAMES):
        # Gray cloudy sky background
        bg_intensity = int(140 + 20 * math.sin(i / 20.0))
        frame = np.full((HEIGHT, WIDTH, 3), (bg_intensity, bg_intensity + 5, bg_intensity + 10), dtype=np.uint8)
        
        # Add some noise for realism
        noise = np.random.randint(0, 15, (HEIGHT, WIDTH, 3), dtype=np.uint8)
        frame = cv2.add(frame, noise)
        
        # Draw target
        draw_func(frame, i)
        
        out.write(frame)
        
    out.release()
    print(f"Created: {filename}")

# 1. DJI (Slow moving, steady)
def draw_dji(frame, i):
    x = int(WIDTH * 0.2 + (i / FRAMES) * WIDTH * 0.6)
    y = int(HEIGHT * 0.4 + math.sin(i / 10.0) * 20)
    cv2.circle(frame, (x, y), 8, (50, 50, 50), -1)
    # Propeller blur
    cv2.ellipse(frame, (x-10, y-5), (12, 3), 0, 0, 360, (200, 200, 200), -1)
    cv2.ellipse(frame, (x+10, y-5), (12, 3), 0, 0, 360, (200, 200, 200), -1)

# 2. FPV (Fast, erratic, zooming in)
def draw_fpv(frame, i):
    progress = i / FRAMES
    x = int(WIDTH * 0.8 - progress * WIDTH * 0.6 + math.sin(i / 3.0) * 50 * (1 - progress))
    y = int(HEIGHT * 0.2 + progress * HEIGHT * 0.6 + math.cos(i / 4.0) * 40 * (1 - progress))
    size = int(5 + progress * 20)
    cv2.rectangle(frame, (x-size, y-size), (x+size, y+size), (30, 30, 30), -1)
    if i % 4 < 2:
        cv2.circle(frame, (x, y), int(size/2), (0, 0, 255), -1) # red LED blink

# 3. SHAHED (Fixed wing, delta shape, linear path)
def draw_shahed(frame, i):
    x = int(WIDTH * 0.1 + (i / FRAMES) * WIDTH * 0.8)
    y = int(HEIGHT * 0.3 + (i / FRAMES) * HEIGHT * 0.4)
    # Delta wing triangle
    pts = np.array([[x+20, y+20], [x-15, y-15], [x-25, y+5]], np.int32)
    pts = pts.reshape((-1, 1, 2))
    cv2.fillPoly(frame, [pts], (20, 25, 20))

# 4. SWARM (Multiple small dots moving together but with individual jitter)
def draw_swarm(frame, i):
    center_x = int(WIDTH * 0.5 + math.sin(i / 30.0) * WIDTH * 0.3)
    center_y = int(HEIGHT * 0.5 + math.cos(i / 20.0) * HEIGHT * 0.2)
    
    np.random.seed(42) # fixed seed so they don't jump around randomly each frame
    for j in range(8):
        offset_x = int(math.sin(i/10.0 + j) * 40 + np.random.randint(-10, 10))
        offset_y = int(math.cos(i/12.0 + j) * 40 + np.random.randint(-10, 10))
        cv2.circle(frame, (center_x + offset_x, center_y + offset_y), 4, (40, 40, 40), -1)

# 5. BIRD (Flapping motion, curved path)
def draw_bird(frame, i):
    x = int(WIDTH * 0.9 - (i / FRAMES) * WIDTH * 0.8)
    y = int(HEIGHT * 0.6 - math.sin(i / 15.0) * HEIGHT * 0.3)
    # Flapping wings
    wing_offset = int(math.sin(i / 2.0) * 15)
    cv2.line(frame, (x, y), (x-15, y-wing_offset), (10, 10, 10), 3)
    cv2.line(frame, (x, y), (x+15, y-wing_offset), (10, 10, 10), 3)

# 6. POLICE IFF (Helicopter-like, with green/blue flashing strobe)
def draw_police(frame, i):
    x = int(WIDTH * 0.3 + math.sin(i / 50.0) * WIDTH * 0.4)
    y = int(HEIGHT * 0.5)
    cv2.ellipse(frame, (x, y), (25, 10), 0, 0, 360, (50, 60, 80), -1)
    cv2.ellipse(frame, (x-15, y-10), (10, 10), 0, 0, 360, (50, 60, 80), -1)
    
    # Blue/Red strobe
    if i % 10 < 5:
        cv2.circle(frame, (x, y+5), 6, (255, 0, 0), -1) # Blue
    else:
        cv2.circle(frame, (x, y+5), 6, (0, 0, 255), -1) # Red

if __name__ == "__main__":
    print(f"Generating simulation videos in: {OUTPUT_DIR}")
    create_video("sim_dji.mp4", draw_dji)
    create_video("sim_fpv.mp4", draw_fpv)
    create_video("sim_shahed.mp4", draw_shahed)
    create_video("sim_swarm.mp4", draw_swarm)
    create_video("sim_bird.mp4", draw_bird)
    create_video("sim_police.mp4", draw_police)
    print("Done!")
