# 🦅 HORUS (MCDIS) — Multi-Modal Counter-UAV Intelligence & Command & Control (C2) Defense Platform

<div align="center">

![HORUS Banner](https://img.shields.io/badge/HORUS-SYSTEM%20V2-00ffcc?style=for-the-badge&logo=shield&logoColor=black)
![Status](https://img.shields.io/badge/STATUS-OPERATIONAL%20%2F%20COMBAT--READY-brightgreen?style=for-the-badge)
![Classification](https://img.shields.io/badge/CLASSIFICATION-DEFENSE%20SIMULATION%20%26%20C2-red?style=for-the-badge)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-EE4C2C.svg?logo=pytorch&logoColor=white)](https://pytorch.org/)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-00ffff.svg)](https://ultralytics.com)
[![SAHI](https://img.shields.io/badge/SAHI-Sliced%20Inference-ff69b4.svg)](https://github.com/obss/sahi)
[![Flask-SocketIO](https://img.shields.io/badge/Flask--SocketIO-Realtime%20C2-black.svg?logo=flask&logoColor=white)](https://flask-socketio.readthedocs.io/)
[![Three.js](https://img.shields.io/badge/Three.js-3D%20Spatial%20Radar-049EF4.svg?logo=three.js&logoColor=white)](https://threejs.org/)
[![OpenCV](https://img.shields.io/badge/OpenCV-Computer%20Vision-5C3EE8.svg?logo=opencv&logoColor=white)](https://opencv.org/)

**AI-Powered Multi-Domain Counter-Drone Airspace Defense & Tactical Command System**  
*Engineered for Airspace Sovereignty against Tier 1, Tier 2, and Tier 3 UAV Incursions*

[System Architecture](#-system-architecture--engineering-specification) • [Mathematical Formulations](#-mathematical--physical-formulations) • [Directory Structure](#-repository-directory-structure) • [Quick Start](#-quick-start--installation) • [Hardware Roadmap](#-hardware-integration-roadmap)

---

</div>

## 📑 Table of Contents
- [Executive Summary](#-executive-summary)
- [System Architecture & Engineering Specification](#-system-architecture--engineering-specification)
  - [Layer 1: Multi-Modal Sensing (The Eyes & Ears)](#layer-1-multi-modal-sensing-the-eyes--ears)
  - [Layer 2: Neural Intelligence & Fusion (The Brain)](#layer-2-neural-intelligence--fusion-the-brain)
  - [Layer 3: Tactical Command & Control (C2 Layer)](#layer-3-tactical-command--control-c2-layer)
  - [Layer 4: Multi-Tiered Response & Neutralization (The Sword)](#layer-4-multi-tiered-response--neutralization-the-sword)
- [Mathematical & Physical Formulations](#-mathematical--physical-formulations)
  - [1. Free-Space Path Loss & Jammer-to-Signal Ratio ($J/S$)](#1-free-space-path-loss--jammer-to-signal-ratio-js)
  - [2. GNSS Doppler Shift Compensation](#2-gnss-doppler-shift-compensation)
  - [3. Final Run-up Point Navigation (FRPN) Cutoff Intercept](#3-final-run-up-point-navigation-frpn-cutoff-intercept)
  - [4. Intercept Success Rate (ISR) Probability](#4-intercept-success-rate-isr-probability)
- [Repository Directory Structure](#-repository-directory-structure)
- [Quick Start & Installation](#-quick-start--installation)
- [Tactical C2 Dashboard Features](#-tactical-c2-dashboard-features)
- [Version Evolution History (v1.0 → v1.8 → T2)](#-version-evolution-history-v10--v18--t2)
- [Hardware Integration Roadmap](#-hardware-integration-roadmap)
- [Authors & Acknowledgments](#-authors--acknowledgments)

---

## 📋 Executive Summary

The **HORUS System** (technically designated as **MCDIS: Multi-Modal Counter-Drone Intelligence System**) is an indigenous, military-grade Counter-Unmanned Aerial System (C-UAS) Command and Control (C2) simulation and operational platform. It was engineered to address the exponential rise of asymmetric low-altitude airspace threats across commercial, tactical, and military domains.

Unlike single-sensor commercial countermeasures, HORUS operates as a **Software-Defined Defense Ecosystem**. It serves as the unified intelligence hub bridging heterogeneous sensor feeds (optical, thermal, radar, acoustic, and RF signals) with an automated decision matrix and precision soft-kill/hard-kill effectors.

```mermaid
flowchart TD
    subgraph EarlyWarning["1️⃣ Early Warning & Detection Layer"]
        R1[Active Micro-Doppler Radar] --> R2[Visual Motion & Optical Flow]
        R2 --> R3[Passive RF Multi-Band Scanner]
        R3 --> R4[Harmonic Acoustic Array]
    end

    subgraph Fusion["🧠 HORUS Neural Fusion & Cognitive Core"]
        EarlyWarning --> F1[Multi-Sensor Data Fusion Engine]
        F1 --> F2[Hierarchical Fuzzy Decision Engine]
        F2 --> F3[MIT Trajectory Extrapolation & FRPN Cutoff]
        F3 --> F4[Automated Rules of Engagement ROE & ISR Check]
    end

    subgraph DefenseActions["Neutralization & Kill-Chain Execution"]
        F4 -->|RF Dependent / Commercial / Swarm| S1["2️⃣ Soft-Kill Neutralization"]
        F4 -->|Fiber-Optic / Guided Munition / Critical| H1["3️⃣ Hard-Kill Neutralization"]
        
        S1 --> S11[Broadband RF Jamming 900MHz / 2.4GHz / 5.8GHz]
        S1 --> S12[GNSS Ephemeris Spoofing & Doppler Pull-Off]
        S1 --> S13[MAVLink Cyber Protocol Takeover]
        S1 --> S14[Acoustic Gyroscope Resonance Disruption]
        
        H1 --> H11[4-Phase Interceptor Drone Squadron]
        H1 --> H12[Directed Energy Weapon DEW Thermal Laser]
        H1 --> H13[High-Power Microwave HPM EMP Burst]
    end
```

### Key Engineering Accomplishments:
1. **AI Vision Pipeline (YOLOv8 + SAHI)**: Integrated ultra-fast object detection with Slicing Aided Hyper Inference (SAHI) to detect ultra-small and distant targets ("Tiny Target Problem") across high-resolution frames against heavy sky clutter.
2. **Persistent Hard-Lock Tracking**: Coupled **CSRT**, **ByteTrack**, and a 6-state **Kalman Filter** to maintain target lock-on during sharp kinematic maneuvers and temporary occlusions.
3. **Kinematic False-Alarm Rejection**: Built-in trajectory linearity and velocity filters that distinguish birds and benign clutter from hostile kamikaze drones and loitering munitions.
4. **Cognitive Fuzzy Decision Matrix**: A 10-input multi-criteria Fuzzy Logic engine generating transparent threat scores ($0 - 100\%$) alongside human-readable military reasoning.
5. **Intercept Physics & Predictive Interception (ISR & FRPN)**: Calculated Intercept Success Rate (ISR) before effector dispatch, replacing tail-chasing pursuit with iterative cutoff navigation (Final Run-up Point Navigation).
6. **Tactical C2 Command Interface**: Fully interactive Glassmorphism HUD featuring real-time 3D spatial radar, multi-stream feeds (optical, thermal FLIR, AI bounding boxes), master condition-red alarms, and automated mission dossier generation (PDF).

---

## 🛡️ System Architecture & Engineering Specification

HORUS follows a strictly modular **Four-Layer Architecture**, ensuring zero latency bottlenecks, full subsystem decoupling, and deterministic operational execution:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   LAYER 1: MULTI-MODAL SENSING (INPUTS)                │
│  [EO/IR Visual]   [Micro-Doppler]   [RF Scanner]   [Acoustic Array]    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│             LAYER 2: NEURAL INTELLIGENCE & SENSOR FUSION               │
│  [YOLOv8 + SAHI] ──► [ByteTrack / Kalman] ──► [Fuzzy Logic Threat]    │
│  [Kinematic Filter] ──► [MIT Trajectory]  ──► [ISR Pre-Check Engine]  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                 LAYER 3: TACTICAL COMMAND & CONTROL (C2)               │
│  [3D Spatial Radar] [Multi-Feed Stream] [Rules of Engagement (ROE)]    │
│  [Real-Time Socket.IO] [Central SQLite WAL Audit] [Automated Reports]  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│             LAYER 4: RESPONSE EFFECTORS (COUNTERMEASURES)              │
│       NON-KINETIC (SOFT-KILL)         │       KINETIC (HARD-KILL)      │
│  • Multi-Band Broadband Jammer        │  • 4-Phase Interceptor Chain   │
│  • Dynamic GNSS Ephemeris Spoofer     │  • Directed Energy Laser (DEW) │
│  • Cyber Protocol Takeover (MAVLink)  │  • High-Power Microwave (HPM)  │
│  • Acoustic Gyro Resonant Disruptor   │  • Collaborative Swarm Hunter  │
└────────────────────────────────────────────────────────────────────────┘
```

### Layer 1: Multi-Modal Sensing (The Eyes & Ears)
*   **Multi-Spectral EO/IR Optical Feed**: Real-time daylight video combined with an automated pseudo-thermal FLIR colormap filter that enhances thermal contrast in low-light and nocturnal engagements.
*   **Active Micro-Doppler Radar Simulation**: Continuous 360° radar sweep computing azimuth, elevation, slant range, and propeller micro-Doppler signatures to isolate rotary blades from biological targets.
*   **Passive RF Spectrum Scanner**: Continuous monitoring of 4 mission-critical bands:
    *   **900 MHz**: Telemetry links, long-range LoRa communication.
    *   **1.5 GHz**: GNSS satellite navigation (GPS L1/L2, GLONASS, BeiDou).
    *   **2.4 GHz**: Command & Control (C2) channels and Wi-Fi control protocols.
    *   **5.8 GHz**: High-throughput analog and digital FPV video streams.
    *   *Frequency-Hopping Detection*: Identifies Frequency-Hopping Spread Spectrum (FHSS) profiles.
*   **Harmonic Acoustic Array**: Spectral feature extraction using Mel-Frequency Cepstral Coefficients (MFCC) to identify rotor harmonics up to 500 meters in urban canyons.

### Layer 2: Neural Intelligence & Fusion (The Brain)
*   **SAHI Sliced Hyper-Inference**: Slices 1080p and 4K optical frames into overlapping patches, running YOLOv8 at native crop resolution to detect micro-drones at standoff distances.
*   **CSRT + ByteTrack & Kalman Filter Tracking**: Implements continuous bounding-box tracking and 3D velocity vectors ($\mathbf{x} = [x, y, z, \dot{x}, \dot{y}, \dot{z}]^T$) to maintain a rigid lock even during erratic flight.
*   **Kinematic Logic Engine**: Evaluates trajectory linearity, velocity vectors, and altitude changes:
    *   *Avian / Clutter*: Low speed, random vector deviation $\rightarrow$ filtered out.
    *   *Commercial UAV*: Moderate speed, hovering capability $\rightarrow$ monitored and targeted.
    *   *Shahed-136 / Cruise Munition*: High speed ($>180$ km/h), strict straight-line vector $\rightarrow$ escalated to **CRITICAL 95%**.
*   **Hierarchical Fuzzy Decision Engine**: A multi-criteria inference engine receiving 10 concurrent sensor metrics:
    $$\text{Inputs} = \{\text{Distance}, \text{Speed}, \text{Altitude}, \text{RCS}, \text{Cam Conf}, \text{Size}, \text{RF Strength}, \text{RF Risk}, \text{Acoustic Match}, \text{Movement Directness}\}$$
    Outputs an actionable threat score ($0 - 100\%$) and automated kill-chain recommendations.
*   **Supervised Machine Learning Classifier (`ai_decision_engine.py`)**: Trained Random Forest model utilizing standard scalers and label encoders trained across engagement logs (`ai_decisions.jsonl`).
*   **FRPN & Predictive Cutoff Calculation**: Calculates the target's future spatial coordinates to vector interceptors for a cutoff interception rather than a tail-chase.
*   **ISR Pre-Check Engine**: Determines the mathematical probability of intercept before weapon activation (**GO / CAUTION / NO-GO**).

### Layer 3: Tactical Command & Control (C2 Layer)
*   **Tactical Glassmorphism HUD**: Military-inspired tactical user interface with high-contrast tactical styling, monospaced typography, and real-time responsiveness.
*   **Interactive 3D Spatial Radar (Three.js & Canvas)**: Visualizes azimuth bearings, target blips, range rings (1 km, 2 km, 3 km, 5 km), and elevation angles.
*   **Triple Concurrent Video Stream**: Displays raw optical feed, AI-processed telemetry HUD, and thermal FLIR imagery.
*   **Master Condition-Red Alarm**: Full-dashboard audio-visual alert pulsing upon detection of critical incursions.
*   **Automated Intelligence Dossier Generator**: Uses FPDF to compile mission reports with target crops, thermal captures, radar coordinates, and engagement timelines.

### Layer 4: Multi-Tiered Response & Neutralization (The Sword)

| Effector | Class | Effective Range | Target Profiles | Mechanism of Action |
| :--- | :---: | :---: | :--- | :--- |
| **Broadband RF Jammer** | Soft-Kill | 5.0 km | Commercial, DJI, Analog FPV | Overwhelms receiver antenna using optimal Jammer-to-Signal ($J/S$) ratios. |
| **Cognitive Quantum Jammer** | Soft-Kill | 6.0 km | Military FHSS / Agile Links | Sweeps hopping frequency slots dynamically based on active RF detection. |
| **GNSS Ephemeris Spoofer** | Soft-Kill | 5.0 km | GPS, GLONASS, BeiDou Receivers | Synthesizes authentic satellite ephemeris with Doppler offsets to force Return-To-Home or safe-zone landing. |
| **Cyber Protocol Hijack** | Soft-Kill | 3.0 km | MAVLink, WiFi Drones | Injects malicious telemetry packets commanding immediate disarm or emergency landing. |
| **Acoustic Gyro Disruptor** | Soft-Kill | 0.5 km | Micro-Drones, MEMS Gyros | Emits resonant sound waves matching MEMS sensor natural resonance to induce catastrophic roll/pitch loss. |
| **4-Phase Interceptor Chain** | Hard-Kill | 8.0 km | Kamikaze, Shahed-136, Fixed-Wing | Deploys autonomous interceptor drones to intercept targets at FRPN cutoff points using net guns or kinetic collision. |
| **Directed Energy Laser (DEW)**| Hard-Kill | 3.0 km | High-Speed Fixed-Wing Drones | 50kW–100kW laser simulation computing dwell time and thermal ablation for carbon fiber and aluminum airframes. |
| **High-Power Microwave (HPM)**| Hard-Kill | 1.5 km | Swarms, Unshielded Electronics | Projects high-energy electromagnetic pulses (EMP) burning out motor ESCs and microcontrollers. |

---

## 📐 Mathematical & Physical Formulations

### 1. Free-Space Path Loss & Jammer-to-Signal Ratio ($J/S$)
The efficiency of RF jamming is determined using the radar Friis transmission equation:
$$FSPL(d, f) = 20 \log_{10}(d) + 20 \log_{10}(f) + 20 \log_{10}\left(\frac{4\pi}{c}\right)$$
The Jammer-to-Signal ratio at the target drone receiver is calculated as:
$$\left(\frac{J}{S}\right)_{\text{dB}} = P_J + G_J - FSPL(d_{\text{jammer}}, f) - \left( P_{\text{controller}} + G_{\text{controller}} - FSPL(d_{\text{controller}}, f) \right)$$
Jamming succeeds when:
$$\left(\frac{J}{S}\right)_{\text{dB}} \ge \text{Threshold}_{\text{band}}$$

### 2. GNSS Doppler Shift Compensation
To successfully capture a drone's GPS receiver tracking loop (Pull-Off Spoofing), the synthetic ephemeris signal must match the Doppler shift caused by the target's relative velocity:
$$\Delta f_D = \frac{v_{\text{target}}}{c} \cdot f_{L1} \quad \text{where } f_{L1} = 1575.42\text{ MHz}$$

### 3. Final Run-up Point Navigation (FRPN) Cutoff Intercept
Rather than tail-chasing a moving target (pure pursuit), the FRPN solver computes the optimal future intercept point $(x_I, y_I)$ iteratively:
$$\vec{P}_{\text{target}}(T) = \vec{P}_0 + \vec{V}_{\text{target}} \cdot T$$
$$\|\vec{P}_{\text{target}}(T) - \vec{P}_{\text{interceptor}}\| = V_{\text{interceptor}} \cdot T$$
The equation is solved iteratively using Newton-Raphson until convergence:
$$|T_{k+1} - T_k| < 0.1 \text{ seconds}$$

### 4. Intercept Success Rate (ISR) Probability
$$\text{ISR} = \text{clip}\left( \left[ \min\left(\frac{V_i}{V_t}, 1.0\right) \cdot \cos(0.8 \cdot \theta) \cdot e^{-\frac{T_{\text{intercept}}}{120}} \cdot 1.2 \right] \times 100, \ 5\%, \ 98\% \right)$$

---

## 📂 Repository Directory Structure

```text
HORUS-Anti-Drone-System/
├── README.md                          # Master system technical documentation
├── requirements.txt                   # Production Python dependencies
├── environment.yml                    # Conda environment definition
├── .gitignore                         # Configured for clean git tracking
│
├── app.py                             # Main tactical C2 server (Flask + Socket.IO)
├── simulate.py                        # Multi-scenario tactical simulator
├── database.py                        # SQLite WAL centralized tactical telemetry
├── reporting.py                       # Automated intelligence mission report generator
│
├── START_HORUS_SYSTEM.bat             # 1-Click Launch: Server + Web C2 Interface
├── LAUNCH_FULL_HORUS_SYSTEM.bat       # Consolidated tactical launch script
├── DIAGNOSE_SYSTEM.bat                # Automated system diagnostic utility
├── KILL_ALL_PROCESSES.bat             # Clean process termination script
│
├── core/                              # Core Counter-UAS intelligence engines
│   ├── run_vision.py                  # Vision engine (YOLOv8 + SAHI + ByteTrack + CSRT)
│   ├── run_sensors.py                 # Multi-sensor suite (RF, Acoustic, Micro-Doppler, GPS)
│   ├── fusion_engine.py               # Hierarchical multi-sensor fusion
│   ├── fuzzy_decision_engine.py       # Multi-criteria Fuzzy Logic threat assessment
│   ├── isr_precheck.py                # Intercept Success Rate physics engine
│   ├── interceptor_chain.py           # 4-Phase smart interceptor guidance
│   ├── weapons_system.py              # Integrated soft/hard kill effectors
│   ├── quantum_jammer.py              # Cognitive dynamic frequency-sweep jammer
│   ├── cyber_takeover.py              # MAVLink telemetry protocol injection
│   ├── thermal_vision.py              # Adaptive pseudo-thermal FLIR engine
│   ├── iff_system.py                  # Identification Friend or Foe transponder logic
│   ├── roe_engine.py                  # Rules of Engagement decision engine
│   ├── swarm_ai.py                    # Swarm collective defense & area-denial
│   ├── tactical_network.py            # Encrypted mesh tactical networking
│   ├── advanced_sensors.py            # Micro-Doppler signature & optical flow
│   └── mcdis_v1_core.py               # Central orchestrator
│
├── implement/                         # Specialized tactical defense implementations
│   ├── acoustic_weapon.py             # Gyroscope resonant acoustic disruptor
│   ├── adversarial_system.py          # Optical perturbation projector
│   ├── countermeasure_engine.py       # Automated response matrix
│   ├── dataset_config.yaml            # 12-class MCDIS threat taxonomy
│   ├── interceptor_system.py          # Interceptor drone squadron manager
│   ├── jamming_system.py              # Broadband RF jammer simulation
│   ├── prepare_dataset.py             # Synthetic data generator & augmentation
│   ├── radar_system.py                # 360° virtual radar & Doppler processor
│   └── swarm_decoy.py                 # Swarm decoy deployment
│
├── ai_decision/                       # Machine learning decision classifier
│   ├── ai_decision_engine.py          # Scikit-Learn Random Forest threat classifier
│   ├── ai_decision_model.pkl          # Trained model weights (4.6 MB)
│   ├── ai_decision_scaler.pkl         # Feature standardizer
│   └── ai_decision_labels.pkl         # Threat class encoders
│
├── dashboard/                         # Tactical C2 Command Interface
│   ├── horus.html                     # Military-grade Glassmorphism HUD
│   ├── horus.css                      # HUD stylesheet & animations
│   ├── horus.js                       # Real-time WebSocket handlers & radar canvas
│   ├── templates/
│   │   └── index.html                 # Tactical dashboard template
│   └── static/
│       ├── style.css                  # Tactical HUD theme
│       ├── tactical_3d.js             # Three.js 3D spatial radar
│       ├── shahed_ref.png             # Target reference silhouette
│       └── target_data.json           # Target specifications database
│
├── models/                            # Trained weights & classifiers
│   ├── yolov8n.pt                     # YOLOv8 nano model (6.5 MB)
│   └── yolov8m.pt                     # YOLOv8 medium model (49.7 MB)
│
├── docs/                              # Comprehensive documentation & technical reports
│   ├── MCDIS_Project_Report_AR.md     # Full Project Technical Report (Arabic)
│   ├── MCDIS_Project_Report_EN.md     # Full English Technical Specification
│   ├── MCDIS_Full_Technical_Specification_v3.md # Unified Strategic Architecture
│   ├── MCDIS_Full_System_Guide.md     # A to Z System Guide
│   ├── MCDIS_Tech_Stack_DeepDive.md   # Technology Stack Deep Dive
│   ├── MCDIS_Executive_Summary_V3.md  # Executive Summary
│   ├── T2_DASHBOARD_DOCUMENTATION.md  # T2 Stable Release Field Manual
│   └── presentations/                 # HTML interactive presentations & proposals
│       ├── MCDIS_Presentation.html
│       ├── MCDIS_Competition_Proposal.html
│       ├── MCDIS_Final_Script_Printable.html
│       ├── mcdis_report.html
│       ├── MCDIS_Report_AR_Print.html
│       └── MCDIS_Report_EN_Print.html
│
└── tests/                             # Unit tests & verification scripts
    ├── test_integration.py            # End-to-end integration test suite
    ├── generate_sim_videos.py         # Synthetic video generator for offline testing
    └── fix_login.py                   # Authentication & credentials utility
```

---

## 🚀 Quick Start & Installation

### Prerequisites
- Python 3.10+ (64-bit recommended)
- Git
- NVIDIA GPU with CUDA support (Optional, for hardware-accelerated YOLOv8 inference; CPU mode operates automatically)

### 1. Clone the Repository
```bash
git clone https://github.com/hassanIssa00/HORUS-Anti-Drone-System.git
cd HORUS-Anti-Drone-System
```

### 2. Set Up Virtual Environment & Dependencies
```bash
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate      # On Windows
# source venv/bin/activate # On Linux/macOS

# Install required packages
pip install -r requirements.txt
```

### 3. Verify System Health
Run the diagnostic script to verify that all modules, drivers, and models load correctly:
```cmd
DIAGNOSE_SYSTEM.bat
```

### 4. Launch the HORUS C2 Platform
Double-click `START_HORUS_SYSTEM.bat` or run:
```bash
python app.py
```
- Open your browser at: **`http://localhost:5000`**
- The tactical command interface will initialize with the 3D spatial radar, sensor telemetry, and live camera feed.

---

## 🎮 Tactical C2 Dashboard Features

1. **360° Spatial Radar Canvas**: Interactive real-time radar sweep rendering target azimuth, elevation, distance rings (1km, 2km, 3km, 5km), and blip vector tracking.
2. **Multi-Stream Vision Feeds**:
   - **Raw Optical**: Direct high-definition camera stream.
   - **AI Processed**: Bounding box overlays, target ID labels, distance estimations, and hard-lock reticles.
   - **Thermal FLIR**: Low-light and night-vision simulation rendering thermal signatures.
3. **Dynamic Threat Ring**: Real-time risk percentage gauge (SAFE / SUSPICIOUS / THREAT / CRITICAL) with threat factor breakdown (Signal Intel, RF Scanner, Acoustic Array, Tracking Confidence).
4. **Subsystem Health Bars**: Visual status gauges for Vision, RF Scanner, Acoustic Array, Radar, AI Processor, Database, GPS, and Mesh Comm.
5. **Interactive Weapons Control Center**: Manual or autonomous firing triggers for RF Jammer, GNSS Spoofer, DEW Laser, Cyber Hijack, Acoustic Disruptor, and Interceptor Drone.
6. **Scenario Controls**: Instant scenario injection buttons:
   - **Scenario 1**: Suicide FPV Incursion (High-speed, low altitude, direct vector).
   - **Scenario 2**: Shahed-136 Loitering Munition (Fixed-wing, GPS dependent, high threat).
   - **Scenario 3**: Multi-Drone Swarm Incursion (Multiple simultaneous vectors, area denial response).

---

## 📊 Version Evolution History (v1.0 → v1.8 → T2)

- **v1.0 – v1.3 (Genesis)**: Initial YOLOv8 integration, baseline Flask dashboard, and synthetic video scenario prototypes.
- **v1.4 – v1.5 (Sensor Integration)**: Added SAHI sliced inference for small target detection, Kalman filter tracking, and initial RF/Acoustic multi-sensor telemetry.
- **v1.6 (Field Hardening)**: Thread-safe SQLite WAL database logging, CSRT hard-lock tracker, and Condition Red audio/visual master alarm.
- **v1.7 – v1.8 (Cognitive Decision Intelligence)**: Integration of Scikit-Learn ML classifier (`ai_decision_engine.py`), Fuzzy Logic threat evaluator, and automated dataset logging (`ai_decisions.jsonl`).
- **T1 & T2 (Combat Ready Deployment)**: Field-stabilized deployment architecture with standalone batch launchers (`LAUNCH_FULL_HORUS_SYSTEM.bat`), diagnostic utilities (`DIAGNOSE_SYSTEM.bat`), and Glassmorphism tactical HUD.
- **HORUS V2 (Unified Platform)**: Full integration of advanced effectors: Cognitive Quantum Jamming, MAVLink Cyber Takeover, DEW Laser thermal simulation, and 4-Phase Interceptor Chain with FRPN cutoff navigation.

---

## 📡 Hardware Integration Roadmap

To transition the HORUS system from software simulation to physical hardware deployment:

```mermaid
flowchart LR
    subgraph HW["Physical Hardware"]
        C[PTZ Optical & FLIR Camera]
        SDR[SDR: HackRF / USRP B210]
        MIC[Digital Acoustic Mic Array]
        PA[RF Power Amplifier 50W-100W]
        INT[Interceptor Quadcopter / Fixed-Wing]
    end

    subgraph Driver["Hardware Abstraction Layer"]
        C -->|RTSP / V4L2| CV[cv2.VideoCapture]
        SDR -->|SoapySDR / GNU Radio| RF[RFScanner & QuantumJammer]
        MIC -->|PyAudio / ALSA| AC[AcousticEngine]
        RF -->|Serial / GPIO Trigger| PA
        INT -->|MAVLink / DroneKit| IC[InterceptorChainEngine]
    end

    subgraph C2["HORUS Platform"]
        CV --> APP[app.py Core]
        RF --> APP
        AC --> APP
        IC --> APP
    end
```

1. **Optical & Thermal Sensors**: Map `cv2.VideoCapture(0)` or RTSP IP camera streams (`rtsp://user:pass@camera_ip:554/stream1`) directly to `run_vision.py`.
2. **RF Scanning & Jamming**: Replace simulation loops in `run_sensors.py` and `jamming_system.py` with `SoapySDR` or `GNU Radio` API bindings connected to a HackRF One, LimeSDR, or USRP B210.
3. **Acoustic Array**: Connect a multi-channel USB microphone array with `PyAudio` to stream real-time audio into the MFCC harmonic classifier.
4. **Effector Deployment**: Connect relay/serial outputs from `weapons_system.py` to trigger physical RF power amplifiers, GPS spoofing SDRs, or telemetry radio links to launch autonomous interceptor drones.

---

## 👥 Authors & Acknowledgments
- **Lead Developer & System Architect**: **Hassan Issa** ([@hassanIssa00](https://github.com/hassanIssa00))
- **Project Scope**: Autonomous Counter-UAS Multi-Modal Defense System Architecture.
- **Open-Source Technologies**: Ultralytics YOLOv8, SAHI, OpenCV, Flask, Three.js, PyTorch, Scikit-Learn.

---

<div align="center">

**🛡️ Airspace Sovereignty Guaranteed by Intelligent Automation 🛡️**

</div>
