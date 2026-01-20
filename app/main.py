from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import redis, json, os, socket, struct, threading
import numpy as np
from prometheus_api_client import PrometheusConnect
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from contextlib import asynccontextmanager
from pyod.models.copod import COPOD

# --- Config & Constants ---
model = COPOD(contamination=0.1)
baseline_noise = np.array([[0.0, 0.0, 0.0], [0.5, 0.5, 0.5], [0.1, 0.0, 0.0]])
model.fit(baseline_noise)

# Load config from Environment (Docker)
TARGET_INTERFACE = os.getenv("TARGET_INTERFACE", "enp1s0")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
PROM_URL = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

# IANA Protocol Numbers Mapping
PROTOCOL_MAP = {
    "1": "ICMP",
    "6": "TCP",
    "17": "UDP",
    "58": "ICMPv6",
    "132": "SCTP"
}

# Connect to Services
r = redis.Redis(host=REDIS_HOST, port=6379, db=0, decode_responses=True)
prom = PrometheusConnect(url=PROM_URL, disable_ssl=True)

# --- NetFlow v5 Listener ---
class NetFlowListener:
    def __init__(self, port=2055):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("0.0.0.0", port))
        self.running = True
        print(f"[NETFLOW] Listening on UDP {port} (v5 Mode)...")

    def start(self):
        t = threading.Thread(target=self._listen_loop, daemon=True)
        t.start()

    def _listen_loop(self):
        while self.running:
            try:
                data, addr = self.sock.recvfrom(4096)
                self._process_packet(data)
            except Exception as e:
                print(f"[NETFLOW] Error: {e}")

    def _process_packet(self, data):
        # NetFlow v5 Header is 24 bytes
        if len(data) < 24: return

        # Parse Header (version check)
        (version, count) = struct.unpack('!HH', data[:4])
        if version != 5: return

        offset = 24
        for _ in range(count):
            if offset + 48 > len(data): break

            # Parse Record (48 bytes)
            record = data[offset : offset + 48]

            # Extract fields
            src_ip_int = struct.unpack('!I', record[0:4])[0]
            bytes_count = struct.unpack('!I', record[20:24])[0]
            protocol = record[38]

            # Convert to readable format
            src_ip = socket.inet_ntoa(struct.pack('!I', src_ip_int))
            proto_name = PROTOCOL_MAP.get(str(protocol), "Other")

            # Update Redis (Sorted Sets for Top Lists)
            r.zincrby("top_talkers_src", bytes_count, src_ip)
            r.zincrby("protocol_usage", bytes_count, proto_name)

            offset += 48

# --- Helpers ---
def get_metric(query):
    try:
        data = prom.custom_query(query)
        if data and len(data) > 0:
            return float(data[0]['value'][1])
    except Exception:
        pass
    return 0.0

# --- Lifecycle ---
scheduler = BackgroundScheduler()
nf_listener = NetFlowListener(port=2055)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start Scheduler and NetFlow Listener
    scheduler.add_job(trigger_analysis, 'interval', seconds=1, max_instances=3)
    scheduler.start()
    nf_listener.start()

    print(f"[SYSTEM] Engine Online. Monitoring: {TARGET_INTERFACE}")
    yield
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routes ---

# 1. ROOT REDIRECT (Fixes the 404 error)
@app.get("/")
def read_root():
    return get_dashboard_data()

# 2. MAIN DASHBOARD ENDPOINT
@app.get("/dashboard")
def get_dashboard_data():
    cached = r.get("system_health")
    current = json.loads(cached) if cached else {}
    return current

# 3. INFERENCE JOB
@app.post("/run-inference")
def trigger_analysis():
    try:
        # --- 1. BASE METRICS (Prometheus) ---
        cpu_query = '1 - avg(rate(node_cpu_seconds_total{mode="idle"}[1m]))'
        cpu_raw = get_metric(cpu_query)

        mbps_query = f'rate(node_network_receive_bytes_total{{device="{TARGET_INTERFACE}"}}[1m])'
        mbps_raw = get_metric(mbps_query) / 1024 / 1024

        pps_query = f'rate(node_network_receive_packets_total{{device="{TARGET_INTERFACE}"}}[1m])'
        pps_raw = get_metric(pps_query)

        # --- 2. FLOW DATA (Redis Direct Ingest) ---

        # A. Protocols
        raw_protos = r.zrevrange("protocol_usage", 0, -1, withscores=True)
        protocols = [{"label": p, "value": s} for p, s in raw_protos]

        # B. Top Talkers
        raw_top_ips = r.zrevrange("top_talkers_src", 0, 4, withscores=True)
        top_ips = [{"label": ip, "value": score} for ip, score in raw_top_ips]

        # C. Decay (Fade old data)
        if r.exists("top_talkers_src"):
            r.zinterstore("top_talkers_src", {"top_talkers_src": 0.5})
        if r.exists("protocol_usage"):
            r.zinterstore("protocol_usage", {"protocol_usage": 0.5})

        # --- 3. ANOMALY LOGIC ---
        norm_cpu = min(cpu_raw, 1.0)
        norm_mbps = min(mbps_raw / 100.0, 1.0)
        norm_pps = min(pps_raw / 10000.0, 1.0)

        current_vector = np.array([[norm_cpu, norm_mbps, norm_pps]])
        anomaly_prob = model.predict_proba(current_vector)[0][1]
        final_score = round(anomaly_prob, 2)

        if pps_raw < 10: final_score = 0.00
        status = "CRITICAL" if final_score > 0.70 else "HEALTHY"

        # --- 4. PAYLOAD ---
        timestamp = datetime.now().strftime("%H:%M:%S")

        payload = {
            "status": status,
            "score": final_score,
            "timestamp": timestamp,
            "interface": TARGET_INTERFACE,
            "model": model.__class__.__name__,
            "metrics": {
                "cpu": round(cpu_raw * 100, 1),
                "mbps": round(mbps_raw, 2),
                "pps": int(pps_raw)
            },
            "flow_data": {
                "top_ips": top_ips,
                "protocols": protocols
            }
        }

        # History Management
        hist_entry = {"time": timestamp, "score": final_score}
        r.rpush("score_history", json.dumps(hist_entry))
        r.ltrim("score_history", -60, -1)
        raw_hist = r.lrange("score_history", 0, -1)
        payload["history"] = [json.loads(x) for x in raw_hist]

        r.set("system_health", json.dumps(payload), ex=60)
        return payload

    except Exception as e:
        print(f"[ERROR] Inference failed: {e}")
        return {"status": "ERROR", "score": 0.0}
