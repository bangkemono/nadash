from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import redis, json, os, socket, struct, threading
import numpy as np
from prometheus_api_client import PrometheusConnect
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from contextlib import asynccontextmanager
from pyod.models.copod import COPOD
from scipy.stats import entropy
from joblib import dump, load

# base config
MODEL_PATH = "/app/data/copod_model.joblib"
TARGET_INTERFACE = os.getenv("TARGET_INTERFACE", "enp1s0")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
PROM_URL = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
PROTOCOL_MAP = {"1": "ICMP", "6": "TCP", "17": "UDP", "58": "ICMPv6", "132": "SCTP"}

# service connections
r = redis.Redis(host=REDIS_HOST, port=6379, db=0, decode_responses=True)
prom = PrometheusConnect(url=PROM_URL, disable_ssl=True)

# baseline for input vectors
baseline_noise = np.array([
    [0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.50],
    [0.05, 0.01, 0.02, 0.10, 0.05, 0.50, 0.10, 0.60],
    [0.20, 0.10, 0.05, 0.05, 0.50, 0.20, 0.10, 0.40],
    [0.40, 0.30, 0.20, 0.20, 0.60, 0.80, 0.20, 0.90],
])

# model placeholder
model = None

def sigmoid(x):
    return 1 / (1 + np.exp(-x))

class NetFlowListener:
    def __init__(self, port=2055):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("0.0.0.0", port))
        self.running = True
        print(f"[NETFLOW] Listening on UDP {port} ...")

    def start(self):
        t = threading.Thread(target=self._listen_loop, daemon=True)
        t.start()

    def _listen_loop(self):
        while self.running:
            try:
                data, addr = self.sock.recvfrom(4096)
                self._process_packet(data)
            except Exception:
                pass

    def _process_packet(self, data):
        if len(data) < 24: return
        (version, count) = struct.unpack('!HH', data[:4])
        if version != 5: return

        offset = 24
        for _ in range(count):
            if offset + 48 > len(data): break
            record = data[offset : offset + 48]
            
            # extract field for netflow v5
            src_ip_int = struct.unpack('!I', record[0:4])[0]
            bytes_count = struct.unpack('!I', record[20:24])[0]
            dst_port = struct.unpack('!H', record[34:36])[0]
            protocol = record[38]

            src_ip = socket.inet_ntoa(struct.pack('!I', src_ip_int))
            proto_name = PROTOCOL_MAP.get(str(protocol), "Other")

            # update redis
            r.zincrby("top_talkers_src", bytes_count, src_ip)
            r.zincrby("protocol_usage", bytes_count, proto_name)
            r.sadd("active_ports", dst_port) # fan out unique ports

            offset += 48

def get_metric(query):
    try:
        data = prom.custom_query(query)
        if data and len(data) > 0:
            return float(data[0]['value'][1])
    except Exception:
        pass
    return 0.0

# lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    global model
    if os.path.exists(MODEL_PATH):
        print(f"[SYSTEM] Loading saved model from {MODEL_PATH}...")
        try:
            model = load(MODEL_PATH)
        except Exception:
            print("[SYSTEM] Model corrupt. Training fresh baseline.")
            model = COPOD(contamination=0.1)
            model.fit(baseline_noise)
    else:
        print("[SYSTEM] No model found. Training fresh baseline.")
        model = COPOD(contamination=0.1)
        model.fit(baseline_noise)
        dump(model, MODEL_PATH)

    scheduler.add_job(trigger_analysis, 'interval', seconds=1, max_instances=3)
    scheduler.start()
    nf_listener.start()
    yield
    scheduler.shutdown()
    dump(model, MODEL_PATH)

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

scheduler = BackgroundScheduler()
nf_listener = NetFlowListener(port=2055)

# routing
@app.get("/")
def read_root():
    return get_dashboard_data()

@app.get("/dashboard")
def get_dashboard_data():
    cached = r.get("system_health")
    current = json.loads(cached) if cached else {}
    return current

@app.post("/train/retrain-recent")
def retrain_model():
    global model
    try:
        print("[AI] Manual retrain triggered. Resetting to baseline.")
        model.fit(baseline_noise)
        dump(model, MODEL_PATH)
        return {"status": "success", "message": "Model reset and saved."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/run-inference")
def trigger_analysis():
    try:
        # prometheus metrics
        cpu_raw = get_metric('1 - avg(rate(node_cpu_seconds_total{mode="idle"}[1m]))')
        rx_mbps = get_metric(f'rate(node_network_receive_bytes_total{{device="{TARGET_INTERFACE}"}}[1m])') / 1024 / 1024
        tx_mbps = get_metric(f'rate(node_network_transmit_bytes_total{{device="{TARGET_INTERFACE}"}}[1m])') / 1024 / 1024
        pps_raw = get_metric(f'rate(node_network_receive_packets_total{{device="{TARGET_INTERFACE}"}}[1m])')

        # redis stats
        raw_top_ips = r.zrevrange("top_talkers_src", 0, 4, withscores=True)
        top_ips = [{"label": ip, "value": score} for ip, score in raw_top_ips]
        
        unique_ips = r.zcard("top_talkers_src") or 0
        unique_ports = r.scard("active_ports") or 0
        
        max_flow_score = top_ips[0]['value'] if top_ips else 0
        
        # entropy
        proto_data = r.zrange("protocol_usage", 0, -1, withscores=True)
        if proto_data:
            probs = [score / sum(s for _, s in proto_data) for _, score in proto_data]
            proto_entropy = entropy(probs)
        else:
            proto_entropy = 0.0

        # syn_ratio
        fan_out_ratio = unique_ports / (unique_ips + 1)
        if rx_mbps > 0:
            direction_ratio = min(tx_mbps / rx_mbps, 10.0) 
        else:
            direction_ratio = 0.0

        # norms
        norm_cpu = min(cpu_raw, 1.0)
        norm_mbps = min(rx_mbps / 100.0, 1.0)
        norm_pps = min(pps_raw / 10000.0, 1.0)
        norm_ips = min(unique_ips / 1000, 1.0)
        norm_dom = min(max_flow_score / 100000, 1.0)
        norm_ent = min(proto_entropy / 3.0, 1.0)
        norm_fan = min(fan_out_ratio / 10.0, 1.0)
        norm_dir = min(direction_ratio / 5.0, 1.0)

        # inference
        vector = np.array([[norm_cpu, norm_mbps, norm_pps, norm_ips, norm_dom, norm_ent, norm_fan, norm_dir]])
        raw_score = model.decision_function(vector)[0].item()
        final_score = sigmoid((raw_score - 7) / 1.11)

        status = "HEALTHY"
        alert_msg = "System Normal"
        if final_score > 0.75:
            status = "CRITICAL"
            total_traffic = sum(i['value'] for i in top_ips)
            suspect_score = top_ips[0]['value'] if top_ips else 0
            
            if total_traffic > 0 and (suspect_score / total_traffic) > 0.5:
                alert_msg = f"Intrusion Detected! Source: {top_ips[0]['label']}"
            elif fan_out_ratio > 5.0:
                 alert_msg = "Port Scanning Activity Detected"
            elif direction_ratio > 3.0:
                 alert_msg = "Potential Data Exfiltration"
            else:
                alert_msg = "High Anomalous Traffic (Distributed)"
                
        elif final_score > 0.50:
            status = "UNSTABLE"

        # cleanup & payload
        if r.exists("top_talkers_src"):
            r.zinterstore("top_talkers_src", {"top_talkers_src": 0.5})
            r.zremrangebyscore("top_talkers_src", "-inf", 1.0)
        if r.exists("active_ports"):
            r.delete("active_ports")
        raw_protos = r.zrevrange("protocol_usage", 0, -1, withscores=True)
        protocols = [{"label": p, "value": s} for p, s in raw_protos]

        payload = {
            "status": status,
            "score": final_score,
            "alert": alert_msg,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "interface": str(TARGET_INTERFACE),
            "model": "COPOD",
            "metrics": {
                "cpu": round(cpu_raw * 100, 1),
                "mbps": round(rx_mbps, 2),
                "pps": int(pps_raw)
            },
            "flow_data": {
                "top_ips": top_ips,
                "protocols": protocols
            }
        }

        # json history
        r.rpush("score_history", json.dumps({"timestamp": payload["timestamp"], "score": final_score}))
        r.ltrim("score_history", -60, -1)
        payload["history"] = [json.loads(x) for x in r.lrange("score_history", 0, -1)]

        r.set("system_health", json.dumps(payload), ex=60)
        return payload

    except Exception as e:
        print(f"[ERROR] {e}")
        return {"status": "ERROR", "score": 0.0}
