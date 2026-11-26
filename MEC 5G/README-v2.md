# Task Offloading & 5G MEC Host Selection Simulation

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![HTML5 Canvas](https://img.shields.io/badge/Simulation-HTML5%20Canvas-orange.svg)](#2-launching-the-interactive-html5-visualizers)
[![Standard](https://img.shields.io/badge/Architecture-ETSI%20GS%20MEC%20003%20%7C%203GPP%205G-green.svg)](#5g-mec-system-architecture)
[![Author](https://img.shields.io/badge/Author-Mai%20Cuong%20Tho-blueviolet.svg)](mailto:thomc@ntu.edu.vn)

A comprehensive academic simulation suite, interactive real-time web visualizer, and technical documentation package for **Load- and Latency-Aware Task Offloading** in general **Edge Computing** as well as **5G Multi-access Edge Computing (5G MEC)** environments compliant with **ETSI GS MEC 003** and **3GPP TS 23.501** specifications.

---

## Author & Attribution

* **Author:** Mai Cường Thọ
* **Email:** [thomc@ntu.edu.vn](mailto:thomc@ntu.edu.vn)
* **Affiliation:** Nha Trang University (NTU)

---

## Repository Structure

This repository is organized into two progressive modeling stages—from foundational **Edge Task Scheduling** to full **5G Core & ETSI MEC Host Selection**—with complete source code, interactive HTML5 animations, bilingual technical reports, and presentation slides:

```text
├── README.md                                              # Project documentation & quick-start guide
│
├── 1. Python Simulation Engines
│   ├── edge_offloading_simulation.py                      # Foundational Edge task offloading simulator
│   └── 5g_mec_host_selection_sim.py                       # 5G MEC Host selection simulator (5G NR, UPF, V2X Handover)
│
├── 2. Interactive Real-Time HTML5 Visualizers
│   ├── mo_phong_may_chu_bien-v5.html                      # Vietnamese end-to-end Edge offloading visualizer
│   ├── edge_server_simulation_v7_en.html                  # English end-to-end Edge offloading visualizer (v7)
│   └── 5g_mec_host_selection-v2.html                      # 5G MEC Control/User Plane & Handover visualizer (v2)
│
├── 3. Technical Reports (Microsoft Word)
│   ├── Bao_Cao_Mo_Phong_Phan_Phoi_Tac_Vu_May_Chu_Bien.docx # Vietnamese Report — General Edge Offloading
│   ├── Edge_Task_Offloading_Report_EN.docx                # English Report — General Edge Offloading
│   ├── Bao_Cao_Lua_Chon_MEC_Host_5G_VN.docx               # Vietnamese Report — 5G MEC Host Selection
│   └── 5G_MEC_Host_Selection_Report_EN.docx               # English Report — 5G MEC Host Selection
│
└── 4. Presentation Deck
    └── Edge_Task_Offloading_Algorithm_Presentation.pptx   # English algorithm & Python code walkthrough slides
```

---

## 5G MEC System Architecture

The 5G MEC model separates **Control Plane** orchestration from **User Plane** traffic forwarding via **5G Core UPF Local Breakout (UL CL)**:

```text
+---------------------------------------------------------------------------------------------------+
|                                      CONTROL PLANE (Top)                                          |
|                                                                                                   |
|      [MEC Orchestrator (MEO)]  --- (Select MEC Host & Policy) --->  [5G Core SMF]                 |
|                 ^                                                         |                       |
|                 | (Real-time Telemetry: CPU Load, Backhaul & Radio)       | (N4 Interface:        |
|                 |                                                         |  UL CL Routing Rule)  |
+-----------------|---------------------------------------------------------|-----------------------+
                  |                                                         v
+-----------------|---------------------------------------------------------|-----------------------+
|                 |                     USER PLANE (Bottom)                 v                       |
|                 |                                                                                 |
|   [5G UEs]      |        [5G gNBs]                    [5G Core UPF]             [ETSI MEC Hosts]  |
|  - Smartphone   |       - gNB-01 (Site 1)  <--N3-->  (Local Breakout) <--N6/N9--> - MEC Host 1     |
|  - V2X Vehicle ===5G NR==>                           (Uplink/Downlink)            - MEC Host 2    |
|  - Smart Camera |       - gNB-02 (Site 2)  <--N3-->                               - MEC Host 3    |
+---------------------------------------------------------------------------------------------------+
```

---

## Mathematical Formulation

### 1. General Edge Task Offloading Model
For a task $i$ with computational workload $C_i$ (Megacycles) arriving at time $t$, the scheduler selects edge server $j^*$ among $M$ heterogeneous servers ($f_j$ CPU capacity, $T_j^{\text{net}}$ network delay, $Q_j(t)$ queue backlog) to minimize total latency:

$$T_{\text{total}}(i, j) = T_j^{\text{net}} + \frac{Q_j(t)}{f_j} + \frac{C_i}{f_j}$$

### 2. Four-Component 5G MEC End-to-End Latency Model
In the 5G MEC environment (`5g_mec_host_selection_sim.py` & `5g_mec_host_selection-v2.html`), when UE $u$ attached to base station $g \in \{\text{gNB-01}, \text{gNB-02}\}$ generates task $i$ with payload $D_i$ (Mb) and computation $C_i$ (MCycles), MEO evaluates each candidate $\text{MEC Host } j$:

$$T_{\text{total}}^{5G}(i, j) = \underbrace{\frac{D_i}{R_{u,g}^{\text{5G\_NR}}}}_{\text{5G NR Radio Delay}} + \underbrace{T_{\text{backhaul}}(g, j)}_{\text{N3/N9 Backhaul Penalty}} + \underbrace{\frac{Q_j(t)}{f_j}}_{\text{Queue Wait Time}} + \underbrace{\frac{C_i}{f_j}}_{\text{MEC CPU Execution}}$$

$$j^* = \arg\min_{j \in \{1..M\}} \left( T_{\text{total}}^{5G}(i, j) \right)$$

---

## Quick Start

### 1. Running the Python Simulators
Ensure Python 3.8+ is installed along with `numpy` and `matplotlib`:

```bash
pip install numpy matplotlib
```

* **Run the 5G MEC Host Selection Simulator (with V2X Handover & Backhaul matrix):**
  ```bash
  python 5g_mec_host_selection_sim.py
  ```
* **Run the Foundational Edge Offloading Simulator:**
  ```bash
  python edge_offloading_simulation.py
  ```
Both scripts output quantitative benchmark tables in the terminal (mean latency, max latency, load standard deviation, and task distribution) and generate 3-panel comparative performance charts.

### 2. Launching the Interactive HTML5 Visualizers
No web server or build step is required:
1. Download `5g_mec_host_selection-v2.html` (for 5G MEC) or `edge_server_simulation_v7_en.html` (for General Edge).
2. Double-click the file to open it in any modern browser (Chrome, Edge, Firefox).
3. Use the top toolbar to:
   * Switch scheduling policies (**MEO Joint QoS & Load**, **Nearest Local MEC**, **Round Robin**, **Random**).
   * Trigger **5G Handover (`Switch UE gNB`)** to observe dynamic MEO re-routing during V2X mobility.
   * Adjust the **Animation Speed Slider (`0.1x` – `2.0x`)** and toggle **Fullscreen Mode**.

---

## Benchmark Summary (5G MEC Scenario)

Evaluated across **80 real-time tasks** with heterogeneous MEC hosts (`MEC-1` at `gNB-01`, `MEC-2` at `gNB-02`, and `MEC-3` at Regional Aggregation Site) including mid-simulation **V2X Handover**:

| Scheduling Policy | Mean Latency (s) | Max Latency (s) | Load Std. Dev. (s) | Key Operational Behavior |
| :--- | :---: | :---: | :---: | :--- |
| **Round Robin** | ~1.38s | ~3.45s | High | Ignores CPU heterogeneity & N9 backhaul penalty; overloads weak nodes |
| **Nearest Local MEC** | ~1.12s | ~2.90s | Moderate | Zero N9 backhaul delay, but causes severe local queue congestion at peak load |
| **MEO Joint QoS & Load (Proposed)** | **~0.68s** | **~1.25s** | **Low** | **Balances radio, N9 backhaul, and queue wait time; adapts seamlessly after V2X handover** |

---

## License

This project is developed for academic research and educational purposes. Feel free to cite or adapt with attribution to **Mai Cường Thọ (`thomc@ntu.edu.vn`)**.
