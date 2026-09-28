# 🦅 HORUS (MCDIS) — Multi-Modal Counter-UAV Intelligence & Command & Control (C2) Defense Platform

<div align="center">

![HORUS Banner](https://img.shields.io/badge/HORUS-SYSTEM%20V2-00ffcc?style=for-the-badge&logo=shield&logoColor=black)
![Status](https://img.shields.io/badge/STATUS-OPERATIONAL%20%2F%20COMBAT--READY-brightgreen?style=for-the-badge)
![Classification](https://img.shields.io/badge/CLASSIFICATION-TOP%20SECRET%20%2F%20DEFENSE%20SIMULATION-red?style=for-the-badge)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-EE4C2C.svg?logo=pytorch&logoColor=white)](https://pytorch.org/)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-00ffff.svg)](https://ultralytics.com)
[![SAHI](https://img.shields.io/badge/SAHI-Sliced%20Inference-ff69b4.svg)](https://github.com/obss/sahi)
[![Flask-SocketIO](https://img.shields.io/badge/Flask--SocketIO-Realtime%20C2-black.svg?logo=flask&logoColor=white)](https://flask-socketio.readthedocs.io/)
[![Three.js](https://img.shields.io/badge/Three.js-3D%20Spatial%20Radar-049EF4.svg?logo=three.js&logoColor=white)](https://threejs.org/)
[![OpenCV](https://img.shields.io/badge/OpenCV-Computer%20Vision-5C3EE8.svg?logo=opencv&logoColor=white)](https://opencv.org/)

**Indigenous AI-Powered Multi-Domain Counter-Drone Airspace Defense & Tactical Command System**  
*Developed for ITC Egypt 2026 & Military Airspace Sovereignty against Tier 1, 2, and 3 UAV Incursions*

[English Documentation](#-system-architecture--engineering-specification) • [التقرير التقني الشامل بالعربية](#-ملخص-المشروع-والمنظومة-باللغة-العربية) • [Quick Start](#-quick-start--installation) • [Hardware Roadmap](#-hardware-integration-roadmap)

---

</div>

## 📑 جدول المحتويات / Table of Contents
- [🦅 ملخص المشروع والمنظومة باللغة العربية](#-ملخص-المشروع-والمنظومة-باللغة-العربية)
- [🛡️ System Architecture & Engineering Specification](#️-system-architecture--engineering-specification)
  - [Layer 1: Multi-Modal Sensing (The Eyes & Ears)](#layer-1-multi-modal-sensing-the-eyes--ears)
  - [Layer 2: Neural Intelligence & Fusion (The Brain)](#layer-2-neural-intelligence--fusion-the-brain)
  - [Layer 3: Tactical Command & Control (C2 Layer)](#layer-3-tactical-command--control-c2-layer)
  - [Layer 4: Multi-Tiered Response & Neutralization (The Sword)](#layer-4-multi-tiered-response--neutralization-the-sword)
- [📐 Mathematical & Physical Formulations](#-mathematical--physical-formulations)
- [📂 Repository Directory Structure](#-repository-directory-structure)
- [🚀 Quick Start & Installation](#-quick-start--installation)
- [🎮 Tactical C2 Dashboard Features](#-tactical-c2-dashboard-features)
- [📊 Version Evolution History](#-version-evolution-history-v10--v18--t2)
- [📡 Hardware Integration Roadmap](#-hardware-integration-roadmap)

---

## 🦅 ملخص المشروع والمنظومة باللغة العربية

### ما هي منظومة HORUS (MCDIS)؟
منظومة **HORUS** (المعروفة أيضاً باسم **MCDIS: Multi-Modal Counter-Drone Intelligence System**) هي منصة قيادة وسيطرة تكتيكية وبرمجية عسكرية متكاملة من الدرجة الأولى (**Military-Grade C2 Platform**) تم تصميمها وتطويرها لحماية المنشآت الحيوية والسيادة الجوية من تهديدات الطائرات المسيرة بكافة أصنافها (Tier 1 Small Commercial, Tier 2 FPV Kamikaze, Tier 3 Long-Range Loitering Munitions مثل Shahed-136).

تعمل المنظومة بنظام **البرمجيات المعرفة (Software-Defined C2 Ecosystem)**؛ بحيث تكون هي **"العقل المدبر"** المركزي الذي يستقبل بيانات المستشعرات المتعددة، يحللها بالذكاء الاصطناعي، يحدد هوية التهديد بدقة، ويصدر أوامر التحييد الآلية أو الموجهة عبر واجهة تكتيكية فائقة التطور.

---

### 🛡️ الأركان الدفاعية الثلاثة التي بنيت عليها المنظومة:

```mermaid
flowchart TD
    subgraph EarlyWarning["1️⃣ رادار الإنذار المبكر (Early Warning & Radar)"]
        R1[رادار دوبلر ميكروي] --> R2[مسح بصري MOG2]
        R2 --> R3[حساسات ترددات الراديو RF]
        R3 --> R4[مصفوفة رصد صوتية]
    end

    subgraph Fusion["🧠 عقل المنظومة (HORUS AI & Fusion Core)"]
        EarlyWarning --> F1[دمج بيانات المستشعرات Sensor Fusion]
        F1 --> F2[محرك المنطق الضبابي Fuzzy Logic Engine]
        F2 --> F3[تنبؤ المسار والحساب الفيزيائي FRPN]
        F3 --> F4[تقييم قواعد الاشتباك ROE & ISR]
    end

    subgraph DefenseActions["الرد التكتيكي المزدوج (Neutralization)"]
        F4 -->|تهديد قابل للاختراق اللاسلكي| S1["2️⃣ التحييد الإلكتروني (Soft-Kill)"]
        F4 -->|درون سلكية / صواريخ / أسراب حرجة| H1["3️⃣ الاعتراض الحركي (Hard-Kill)"]
        
        S1 --> S11[تشويش متعدد النطاقات 900MHz / 2.4 / 5.8GHz]
        S1 --> S12[تزييف إحداثيات GPS/GNSS Spoofing]
        S1 --> S13[اختراق بروتوكول التحكم Cyber Takeover]
        S1 --> S14[تعطيل الجيروسكوب بالرنين الصوتي]
        
        H1 --> H11[سلسلة صيد بالدرونز المقاتلة Interceptor Chain]
        H1 --> H12[سلاح الليزر الحراري الموجه DEW Laser]
        H1 --> H13[نبضات الميكروويف عالية القدرة HPM EMP]
    end
```

### 🎯 ما تم إنجازه وتطويره بالكامل في هذا المشروع:
1. **نظام الرؤية والذكاء الاصطناعي (AI Vision Pipeline):**
   - دمج نموذج **YOLOv8** مع تقنية **SAHI (Slicing Aided Hyper Inference)** لتقطيع الإطارات بدقة، مما مكن المنظومة من رصد الأهداف فائقة الصغر (Micro Drones) على مسافات بعيدة جداً وسط السحب والضوضاء البصرية.
   - خوارزميات التتبع المستمر المقفل (**Hard-Lock Tracking**) باستخدام **ByteTrack** و **CSRT Tracker** وفلاتر كالمان (**Kalman Filter**) لمنع فقدان الهدف عند المناورة أو الحجب اللحظي.
   - الرؤية الليلية والحرارية التلقائية (**Auto-Thermal FLIR**) التي تحول البث البصري في الإضاءة المنخفضة إلى نطاق حراري تكتيكي واضح.
2. **محرك تحليل الحركية والفيزياء (Kinematic Logic Engine):**
   - تحليل فيزيائي متقدم لسرعة الهدف، وتغير الارتفاع، واستقامة المسار لتمييز الطيور والأجسام العشوائية عن الدرونز والصواريخ، والقضاء على الإنذارات الكاذبة (**False Positives**).
3. **محرك القرار والمنطق الضبابي (Fuzzy Logic & AI Decision Engine):**
   - محرك قرار مبني على المنطق الضبابي يقيم 10 مدخلات متزامنة من الحساسات (المسافة، السرعة، المقطع الراداري RCS، قوة إشارة RF، بصمة الصوت، درجة ثقة الكاميرا) ليعطي مؤشر خطر من 0 إلى 100% مع مبررات منطقية واضحة للمشغل.
   - نموذج تصنيف آلي مدرب (**Random Forest / AdaBoost**) لاتخاذ قرارات التحييد الفورية.
4. **حسابات احتمالية الاعتراض ومسار النقطة المتقدمة (ISR & FRPN Physics):**
   - نظام **ISR Pre-Check** لحساب نسبة نجاح الاعتراض فيزيائياً قبل إطلاق أي سلاح.
   - خوارزمية **FRPN (Final Run-up Point Navigation)** لاعتراض الهدف عند نقطة مستقبلية (Cutoff Point) بدلاً من ملاحقته من الخلف، مما يوفر الطاقة ويقلل زمن التحييد.
5. **منظومة أسلحة متكاملة (Soft-Kill & Hard-Kill):**
   - محاكاة فيزيائية واقعية للتشويش الراديوي وتزييف الملاحة (GNSS Ephemeris)، واختراق بروتوكولات MAVLink، ونبضات EMP، وأسلحة الطاقة الموجهة DEW Laser.
6. **لوحة القيادة والسيطرة التكتيكية (C2 Command Dashboard):**
   - واجهة مستخدم فائقة التطور بتصميم عسكري زجاجي (**Military Glassmorphism HUD**) مع رادار ثلاثي الأبعاد تفاعلي (**Three.js / HTML5 Canvas**)، بث حي متعدد النوافذ (بصري، حراري، معالج بالذكاء الاصطناعي)، ومؤشرات لحالة جميع المنظومات الفرعية ونظام إنذار رئيسي (**Master Alarm**).
7. **نظام التقارير الاستخباراتية الآلي (Mission Intelligence Dossier):**
   - توليد تقارير رسمية بصيغة PDF فور انتهاء المهمة تشمل صور الأهداف الملتقطة حرارياً، إحداثيات الرادار، سجل زمني كامل للأوامر التكتيكية، ونوع السلاح المستخدم.

---

## 🛡️ System Architecture & Engineering Specification

MCDIS operates on a strictly modular **Four-Layer Architecture**, ensuring fault tolerance, zero latency bottlenecks, and deterministic mission execution:

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
│                 LAYER 3: TACTICAL C2 & OPERATOR HUD                    │
│  [3D Spatial Radar] [Multi-Feed Stream] [Rules of Engagement (ROE)]    │
│  [Real-Time Socket.IO] [Central SQLite WAL Audit] [Automated Reports]  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│             LAYER 4: RESPONSE EFFECTORS (COUNTERMEASURES)              │
│       NON-KINETIC (SOFT-KILL)         │       KINETIC (HARD-KILL)      │
│  • Cognitive Multi-Band RF Jammer     │  • 4-Phase Interceptor Chain   │
│  • Dynamic GNSS Ephemeris Spoofer     │  • Directed Energy Laser (DEW) │
│  • Cyber Protocol Takeover (MAVLink)  │  • High-Power Microwave (HPM)  │
│  • Acoustic Resonant Disruptor        │  • Collaborative Swarm Hunter  │
└────────────────────────────────────────────────────────────────────────┘
```

### Layer 1: Multi-Modal Sensing (The Eyes & Ears)
- **Multi-Spectral EO/IR**: High-resolution optical daylight feed coupled with an adaptive pseudo-thermal colormap enhancement engine for night operations, dense fog, and heat signature discrimination.
- **Active Micro-Doppler Radar**: Simulated 360° radar sweep tracking spatial azimuth, elevation, range, and rotor blade micro-Doppler signatures.
- **Passive RF Scanner**: Multi-band frequency scanning across 900 MHz (Telemetry/LoRa), 1.5 GHz (GNSS L1/L2), 2.4 GHz (Command & Control), and 5.8 GHz (FPV Video Link). Detects Frequency-Hopping Spread Spectrum (FHSS).
- **Passive Acoustic Harmonic Array**: Rotor harmonic signature detection using Mel-Frequency Cepstral Coefficients (MFCC) to classify acoustic drone profiles up to 500m.

### Layer 2: Neural Intelligence & Fusion (The Brain)
- **SAHI (Slicing Aided Hyper Inference)**: Overcomes the classical computer vision limitation where distant drones appear as 4–12 pixel blobs. By slicing 1080p/4K frames into overlapping windows, the YOLOv8 detector operates at native resolution on small regions.
- **Persistent Target Locking**: Combination of **CSRT (Discriminative Correlation Filter with Channel and Spatial Reliability)** and **ByteTrack** with a 6-state **Kalman Filter** ($\mathbf{x} = [x, y, z, \dot{x}, \dot{y}, \dot{z}]^T$) ensuring lock-on retention during high-g evasive maneuvers.
- **Hierarchical Fuzzy Decision Engine**: Multi-criteria inference system running on 10 sensor inputs:
  $$\text{Inputs} = \{\text{Distance}, \text{Speed}, \text{Altitude}, \text{RCS}, \text{Camera Conf}, \text{Size}, \text{RF Strength}, \text{RF Risk}, \text{Acoustic Match}, \text{Movement Directness}\}$$
- **ISR Pre-Check Engine**: Calculates intercept feasibility and ranks available effectors based on geometry, speed ratios, and target dependencies.

### Layer 3: Tactical Command & Control (C2 Layer)
- **Tactical C2 Interface**: Real-time glassmorphism tactical HUD displaying spatial radar, raw optical stream, AI annotated stream, thermal FLIR view, health monitors, threat ring, and active kill-chain.
- **Automated ROE Engine**: Autonomous evaluation of engagement authorization based on target identification, range threshold, and speed profile.
- **Cryptographic Audit Log**: Every detection, command, and effector firing is archived in a thread-safe SQLite database (WAL mode enabled).

### Layer 4: Multi-Tiered Response & Neutralization (The Sword)

| Effector | Class | Range | Target Focus | Operational Mechanism |
| :--- | :---: | :---: | :--- | :--- |
| **RF Multi-Band Jammer** | Soft-Kill | 5.0 km | Commercial, DJI, Analog FPV | Overwhelms C2 link via high Jammer-to-Signal ratio ($J/S$). |
| **Quantum / Cognitive Jammer** | Soft-Kill | 6.0 km | Military FHSS / Hopping Links | Real-time adaptive sweep countering frequency-hopping transmitters. |
| **GNSS Ephemeris Spoofer** | Soft-Kill | 5.0 km | GPS/GLONASS/BeiDou Drones | Synthesizes fake satellite constellation signals; forces Return-To-Home or capture-zone landing. |
| **Cyber Protocol Hijack** | Soft-Kill | 3.0 km | MAVLink, WiFi Drones | Injects malicious disarm / emergency-land packets into telemetry stream. |
| **Acoustic Gyro Disruptor** | Soft-Kill | 0.5 km | Micro-Drones, MEMS Gyros | Projects resonant acoustic frequencies matching MEMS sensor natural resonance to cause flight instability. |
| **4-Phase Interceptor Chain** | Hard-Kill | 8.0 km | Kamikaze, Shahed-136, Swarms | Autonomous interceptor drone launching with net capture or kinetic collision at FRPN cutoff coordinate. |
| **Directed Energy Laser (DEW)**| Hard-Kill | 3.0 km | Fixed-Wing, High-Speed Munitions | 50kW–100kW laser simulation calculating dwell time and thermal ablation for carbon fiber and aluminum airframes. |
| **High-Power Microwave (HPM)**| Hard-Kill | 1.5 km | Swarms, Unshielded Electronics | Intense electromagnetic radiation burst frying onboard flight controllers and motor ESCs. |

---

## 📐 Mathematical & Physical Formulations

### 1. Free-Space Path Loss & Jammer-to-Signal Ratio ($J/S$)
The system calculates the RF jamming efficiency using the radar Friis transmission equation:
$$FSPL(d, f) = 20 \log_{10}(d) + 20 \log_{10}(f) + 20 \log_{10}\left(\frac{4\pi}{c}\right)$$
The Jammer-to-Signal ratio at the target drone receiver is:
$$\left(\frac{J}{S}\right)_{\text{dB}} = P_J + G_J - FSPL(d_{\text{jammer}}, f) - \left( P_{\text{controller}} + G_{\text{controller}} - FSPL(d_{\text{controller}}, f) \right)$$
Jamming is successful when $(J/S)_{\text{dB}} \ge \text{Threshold}_{\text{band}}$.

### 2. GNSS Doppler Shift Compensation
To successfully capture a drone's GPS tracking loop (Pull-Off Spoofing), the synthesized ephemeris signal must match the Doppler frequency shift induced by the target velocity:
$$\Delta f_D = \frac{v_{\text{target}}}{c} \cdot f_{L1} \quad \text{where } f_{L1} = 1575.42\text{ MHz}$$

### 3. FRPN (Final Run-up Point Navigation) Intercept Solution
Rather than tail-chasing an incoming target (pure pursuit), the FRPN solver calculates the optimal cutoff intercept point $(x_I, y_I)$ iteratively:
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
├── README.md                          # Master bilingual system documentation
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
│   ├── MCDIS_Project_Report_AR.md     # تقرير المشروع التقني الشامل بالعربية
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
- NVIDIA GPU with CUDA support (Optional, for real-time YOLOv8 acceleration; CPU mode supported automatically)

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
Run the diagnostic script to ensure all libraries and modules are verified:
```cmd
DIAGNOSE_SYSTEM.bat
```

### 4. Launch the HORUS C2 Platform
Simply double-click `START_HORUS_SYSTEM.bat` or run:
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
- **Project Initiative**: ITC Egypt 2026 Counter-UAS Tactical Research & Development.
- **Libraries & Tools**: Ultralytics YOLOv8, SAHI, OpenCV, Flask, Three.js, PyTorch, Scikit-Learn.

---

<div align="center">

**🛡️ Airspace Sovereignty Guaranteed by Intelligent Automation 🛡️**

</div>
