# Multi-Modal Counter-Drone Intelligence System (MCDIS)
**Technical Project Report**

---

## 1. Introduction to Anti-Drone Systems
With the rapid proliferation of Unmanned Aerial Vehicles (UAVs), both for commercial and military applications, the threat posed by malicious drone activity has increased exponentially. Anti-Drone systems are designed to detect, track, identify, and mitigate these threats. Modern solutions utilize a layered approach combining various sensors and countermeasures to ensure airspace security.

---

## 2. Core Countermeasure Systems

To fully protect an area, our counter-drone strategy is categorized into three primary systems:

### System 1: Attack & Interception System (Kinetic Hard-Kill)
This system relies on physically neutralizing the drone. It utilizes highly accurate **Visual Detectors** and tracking mechanisms.
*   **Target Locking:** The system actively detects the drone, locks onto it (Targeting), and maintains a persistent track.
*   **Interception Methods:** Once locked, the system issues a command to deploy a countermeasure. This could be:
    *   Launching a guided surface-to-air missile.
    *   Deploying an interceptor drone to cast a net over the target.
    *   Deploying a "Kamikaze" drone to ram the target in mid-air.
    *   Ground-based automated projectiles (e.g., CIWS or smart bullets).

### System 2: Jamming & Electronic Warfare System (Soft-Kill)
This system disables the drone by interfering with its communication and navigation operations at various levels:
*   **Level 1 (Encrypted Wireless Comms):** Disrupting specialized encrypted military links.
*   **Level 2 (Commercial RF Links):** Jamming the 2.4 GHz and 900 MHz frequencies used for Remote Control (RC) signals.
*   **Level 3 (Video Transmission):** Jamming 5.8 GHz and 1.x GHz bands used for FPV video feeds.
*   **Level 4 (GPS & Navigation):** GPS Spoofing or Jamming. 
    *   **Smart Drones:** We can overwrite the GPS coordinates and "hijack" the drone to land safely.
    *   **Suicide/FPV Drones:** Often lack GPS. In these cases, we jam the RC signal, causing the drone to lose control and crash. 
    *   **Fiber-Optic Drones:** To bypass all RF jamming, some new attack drones are tethered by fiber-optic wires. These are immune to Electronic Warfare, meaning they **must** be engaged by the **Attack System (Missile)** mentioned above.

### System 3: Early Warning Radar System
A powerful radar infrastructure serves as the first line of defense.
*   It provides long-range detection of incoming threats.
*   Upon detection, it triggers early warnings.
*   It immediately hands over the approximate coordinates to the **Visual/Attack System** and the **Jamming System** for pinpoint tracking and engagement.

---

## 3. Our Achievements and Implemented Technologies in MCDIS

In this project, we have successfully engineered a highly advanced, fully integrated **Multi-Modal Counter-Drone Intelligence System (MCDIS)**. 

### What We Have Built:
1.  **AI Vision Pipeline (YOLOv8 + SAHI):** 
    We implemented a state-of-the-art visual detector capable of identifying drones even at extreme distances by slicing 4K/1080p frames (SAHI).
2.  **Persistent Tracking & Target Locking (Fusion Engine):** 
    We combined **Kalman Filters** and **CSRT Hard Lock tracking**. This means once our AI spots the drone, the system locks onto it firmly and will not lose it, enabling the Attack System to target it effectively.
3.  **Kinematic Logic Engine (Threat Discrimination):**
    We engineered an advanced logic engine that tracks the speed, trajectory, and size of the object. It intelligently differentiates between:
    *   **Birds** (erratic flight, small size) -> Ignored.
    *   **Commercial Drones** -> Flagged.
    *   **Missiles/Fast Attack Drones** (high speed, straight trajectory) -> Marked as CRITICAL.
4.  **Auto-Thermal Night Vision Mode:**
    Our vision system automatically detects low-light environments and applies a thermal/CLAHE enhancement filter, allowing the system to detect threats seamlessly at night.
5.  **Multi-Sensor Fusion (Optical Flow & MOG2 Radar):**
    We developed a localized visual-radar system using Optical Flow and Background Subtraction to detect fast-moving anomalous pixels in the sky, serving as an Early Warning layer.
6.  **Automated Countermeasure Engine:**
    We programmed a rule-based AI that decides the best defense strategy (Jamming vs. Kinetic Attack) based on the threat classification (e.g., Swarm, Military Fixed-Wing, DJI Mini).
7.  **Tactical Command & Control Dashboard (C2):**
    A fully functional, military-grade localhost Web UI that displays real-time video feeds, radar blips, telemetry data (Speed, Heading), and system logs.

**System Status:** The MCDIS software architecture is **Complete and Mission-Ready** as an intelligent software backbone, ready to be connected to physical hardware (Cameras, Radars, SDR Jammers, and Missile Launchers).
