# 🛡️ MCDIS: Multi-Modal Counter-Drone Intelligence System — Full Project Guide (A to Z)

## 📋 System Overview
**MCDIS** is a military-grade Anti-Drone (C-UAS) Command & Control (C2) platform designed for the **ITC Egypt 2026** competition. It integrates computer vision, RF signal analysis, and acoustic classification into a unified tactical dashboard for real-time threat detection, tracking, and automated countermeasure deployment.

---

## 📂 Project Structure (A-Z)

```text
/MCDIS_ROOT
│
├── mcdis/                          # CORE SYSTEM LOGIC
│   ├── dashboard/                  # C2 Web Interface (Flask + Socket.IO)
│   │   ├── static/                 # CSS, JS, and HUD frames
│   │   └── templates/              # HTML (Tactical Dashboard)
│   ├── database.py                 # SQLite Engine (Thread-safe, WAL mode)
│   ├── run_vision.py               # AI Vision Pipeline (YOLOv8 + SAHI)
│   ├── run_sensors.py              # Multi-Sensor Suite (RF, Acoustic, GPS)
│   └── yolov8m.pt                  # YOLOv8 Medium model weights
│
├── implement/                      # TACTICAL IMPLEMENTATIONS
│   ├── simulate.py                 # Scenario Simulation Engine
│   ├── countermeasure_engine.py    # Automated Response Logic
│   ├── radar_system.py             # Virtual Radar & Micro-Doppler
│   ├── jamming_system.py           # Electronic EW Simulation
│   └── prepare_dataset.py          # Data preparation & Augmentation
│
└── mcdis_logs.db                   # Centralized Tactical Database
```

---

## 🛠️ Installation & Setup

1.  **Environment Preparation**:
    ```powershell
    # Install core dependencies
    pip install flask flask-socketio ultralytics sahi opencv-python numpy sqlite3 requests
    ```

2.  **Dataset Preparation (Optional)**:
    If you want to train your own model on the 12-class MCDIS taxonomy:
    ```powershell
    python implement/prepare_dataset.py --demo  # Generates synthetic data for testing
    ```

---

## 🚀 How to Run the System

### 1. Launch the C2 Dashboard (Main Entry)
The dashboard orchestrates the entire system. Starting it will initialize the database monitor and the web server.
```powershell
python mcdis/dashboard/app.py
```
*   **Access**: `http://localhost:5000`

### 2. Monitoring the Tactical Feed
The vision pipeline initializes automatically when you view the dashboard. It will:
*   Load `mcdis/yolov8m.pt`.
*   Process the selected video from the `video drone test/` folder.
*   Apply SAHI (Sliced Inference) for long-range target detection.

### 3. Running Simulations
To test the system without real sensors, use the **Scenario Controls** at the bottom of the dashboard UI.
*   **Scenario 1**: Suicide FPV Incursion.
*   **Scenario 2**: Shahed-136 Loitering Munition.
*   **Scenario 3**: Multi-Drone Swarm Attack.

---

## 🔧 Maintenance & Debugging (The Audit Summary)

During the final system audit (April 2026), the following critical fixes were applied to ensure "A to Z" operational status:

| Component | Issue Resolved | Fix Impact |
| :--- | :--- | :--- |
| **Vision** | `track_id` NameError in SAHI mode | Fixed detection processing to handle sliced inference correctly. |
| **Vision** | Model Path Mismatch | Redirected config to `mcdis/yolov8m.pt` to ensure load success. |
| **C2 App** | Missing API Routes | Added `/api/scenario` to enable REST control of simulations. |
| **C2 App** | Path Buffering | Fixed double-parent path traversal in video file searching. |
| **Database** | Windows Encoding Crash | Fixed Unicode/Emoji crashes on CP1256 (Arabic Windows) terminals. |
| **Engine** | Forward Ref Error | Fixed `CLASS_PRIORITY_LOOKUP` in countermeasure logic. |
| **UI** | JS Data Mapping | Fixed threat level object parsing and sensor field names. |

---

## 📡 Tactical Operations Guide

### A. Threat Detection
*   **VISION**: Uses YOLOv8m. If SAHI is enabled, it slices the 4K/1080p frame into chunks to detect micro-drones at distance.
*   **RF SCAN**: Passively listens for hopping patterns (FHSS) on 2.4GHz and 5.8GHz.
*   **ACOUSTIC**: Analyzes rotor frequency signatures using MFCC.

### B. Automated Response
The **Countermeasure Engine** follows a rules-based matrix:
1.  **Commercial Drones**: Triggers GPS Spoofing + Frequency Jamming.
2.  **Military Fixed-Wing**: Escalates to Kinetic Interception (Hard Kill).
3.  **Swarms**: Activates Wideband Jamming across all levels.

---

## 🚧 Hardware Integration (Next Steps)
To move from simulation to reality:
1.  **Vision**: Connect `cv2.VideoCapture(0)` to a gimbal-mounted camera.
2.  **RF**: Replace `RFScanner` logic with `SoapySDR` or `GNU Radio` API calls.
3.  **Jamming**: Map the `JammingSystem.start()` method to a serial command for a physical SDR power amplifier.

---
**Status: MISSION READY** ✅  
**Version: 3.0 (April 22, 2026)**
