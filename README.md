# 🛡️ NADash : Network Analysis Dashboard

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Status](https://img.shields.io/badge/status-stable-green.svg)
![Stack](https://img.shields.io/badge/tech-FastAPI%20%7C%20SvelteKit%20%7C%20Docker%20%7C%20PyOD-orange.svg)

**A real-time, unsupervised Intrusion Detection System (IDS) that implements Anomaly Detection for identify security breaches on networks without prior training on attack data.**

## Overview

This project implements an **AIOps (Artificial Intelligence for IT Operations)** pipeline. It continuously monitors system metrics (CPU, Network Traffic, Packet Rate) and uses an **Distribution-based** model to detect anomalies.
Unlike traditional rule-based firewalls, this system is **unsupervised**. It learns the "baseline" of your network traffic in real-time and flags any deviations (like a SYN Flood) as anomalies.

### Key Features
* **Secure Architecture:** Uses Nginx to expose only Port 80, keeping backend services (API, DB, Metrics) isolated from the public network.
* **Real-Time Monitoring:** Scrapes metrics every second via Prometheus & Node Exporter.
* **Direct NetFlow Ingestion:** High-speed, custom UDP listener (Port 2055) to track Top IPs and Protocols in real-time without external collectors.
* **Unsupervised Learning:** Uses [PyOD](https://github.com/yzhao062/pyod) to detect unknown attack patterns.
* **Traffic Gate:** Automatically ignores statistical noise during idle periods to prevent false positives.
* **Modern Tech Stack:** Fully containerized with **Docker** for effortless deployment and features a reactive **Svelte** frontend for high-performance visualization.

---

## Architecture

The system is containerized using Docker and consists of these main microservices:

| Service | Technology | Description |
| :--- | :--- | :--- |
| **Nginx** | Alpine Linux | **Reverse Proxy.** The only public door (Port 80). Routes traffic to Frontend and API. |
| **Softflowd** | C (Alpine) | **Network Probe.** Sits on the host interface, generates NetFlow v5 packets, sends to Engine. |
| **AIOps Engine** | Python (FastAPI) | **Core Engine.** Ingests NetFlow UDP, scrapes Prometheus, runs AI inference. |
| **Frontend** | SvelteKit | **The Face.** Visualizes data. Accessed via Nginx. |
| **Prometheus** | Go | **Metrics DB.** Stores CPU/Packet data. |
| **Redis** | In-Memory DB | **Cache.** Stores flow stats and historical graphs. |

---

## Prerequisites

* **Docker** & **Docker Compose** installed.
* **Linux Environment** (Required for `node-exporter` to access host network interfaces).
* **Python 3.10+** (Only if running the attack scripts manually).
* **Root Privileges** (Required to put the network card into promiscuous mode).

---

## Project Structure

nadash/<br>
├── app/                 # Python Backend (FastAPI + PyOD)<br>
├── svelte-dashboard/    # Frontend (SvelteKit)<br>
├── nginx/               # Nginx Configuration<br>
├── softflowd/           # Network Probe Build Context<br>
├── docker-compose.yml   # Orchestration<br>
├── prometheus.yml       # Metrics Config<br>
└── .env                 # Local Secrets (GitIgnored)

---

## Installation & Setup

### 1. Cloning & Configuration File (.env)
Create a .env file in the project root to configure your network settings.
```bash
git clone [https://github.com/bangkemono/nadash.git](https://github.com/bangkemono/nadash.git)
cd nadash
cp .env.example .env
```

Open .env and set your Target Interface (run ip a to find yours, e.g., eth0, enp1s0, or wlan0).
```ini, TOML
# .env
TARGET_INTERFACE=enp1s0
NETFLOW_PORT=2055
```

### 2. Configure the Firewall
Docker network bridges often get blocked by default firewalls on Linux. Allow traffic from the Docker interface:
```bash
sudo ufw allow in on docker0
sudo ufw reload
```

### 3. Start the System

Run the entire stack in detached mode:
```bash
docker compose up -d --build
```

### 4. Verify Health

Check if the containers are running:

```bash
docker ps
```

If you had another instance of the given service then you must kill the service first before composing the project

---

## Usage
### 1. View the Dashboard Data

The AIOps Engine exposes a JSON endpoint for the dashboard:
- URL: http://localhost (or http://<TARGET_SERVER_IP>)
  - Note: You do not need to specify port 3000. Nginx handles the routing.

### 2. Simulate an Attack (DDoS)

To test the detection capabilities, use hping3 (or any packet generator) to flood the target interface.

**WARNING: Run this only on networks you own.**

```bash
# SYN Flood on Port 80
sudo hping3 -S -p 80 --flood <TARGET_SERVER_IP>
```

Expected Behavior:

```
Peace Time: Score stays near 0.00 - 0.10. Status: HEALTHY.
Attack Start: PPS (Packets Per Second) spike, Top Source IPs updates, and Protocol Mix shows a surge in TCP Traffic.
Detection: Probability score jumps to > 0.70. Status flips to CRITICAL.
```

---

## How it Works

The logic inside main.py is designed to filter noise and detect true threats.

- Reverse Proxy:
    - Nginx manages the port-routing, acting as a reverse proxy so that the server can be accessed on port 80
- Data Ingestion:
    - Metrics (Prometheus): The engine queries node_exporter for CPU Load and Packet Rate (PPS). This data feeds the AI model.
    - Flows (Direct UDP): softflowd captures traffic metadata on the host and sends NetFlow v5 packets to the engine's UDP port 2055. This data feeds the "Top IPs" and "Protocol Mix" charts.
- Normalization:
    - Inputs are scaled (0.0 to 1.0) to prevent one metric (like PPS) from dominating the calculation.
- Inference:
    - The core uses the COPOD (Copula-Based Outlier Detection) model from the PyOD library.
    - It predicts how "improbable" the current state is compared to the baseline noise.
    - **No Training Required**: The model fits itself to a small sample of baseline noise on startup and adapts.
- Traffic Noise Gate:
    - If traffic is negligible (< 10 PPS), the score is forcibly clamped to 0.00.

---

## Configuration
- .env (Environment Variables)
    - TARGET_INTERFACE: (Crucial) The network interface controller (NIC) to monitor (e.g., enp1s0, eth0).
    - NETFLOW_PORT: The UDP port for flow ingestion (Default: 2055).
    - ALLOWED_ORIGINS: Restrict which IPs can access the backend API (Default: *).
- docker-compose.yml
    - TZ: Set your timezone (e.g., Asia/Jakarta) to ensure logs and graphs match your wall clock.

- app/main.py
    - model = COPOD(contamination=0.1): Adjust the contamination parameter to change sensitivity.
    - if pps_raw < 10: The "Silence Gate" threshold. Increase this if your server normally handles constant low-level background traffic.

---

## Troubleshooting

- Prometheus Target is DOWN?
    - Check http://localhost:9090/targets.
    - If error is "No route to host," check the Firewall step above.
    - Ensure node-exporter is running in network_mode: host in the compose file.

- Top Source IPs are empty / "Waiting for flows..."
    - Ensure softflowd is running: docker logs softflowd.
    - Check if softflowd is watching the correct interface (enp1s0 vs eth0). Check your .env file.
    - Verify the backend is receiving packets: docker logs aiops-engine | grep NETFLOW. You should see [NETFLOW] Listening on UDP 2055....

---

## License
Distributed under the MIT License. See LICENSE for more information.
