# general
import redis, json, os, socket, struct, threading
from datetime import datetime, timedelta, timezone

# web
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
import jwt
from pwdlib import PasswordHash 
from typing import Optional

# db
from prometheus_api_client import PrometheusConnect
from apscheduler.schedulers.background import BackgroundScheduler
from contextlib import asynccontextmanager

# od
import numpy as np
from pyod.models.copod import COPOD
from scipy.stats import entropy
from joblib import dump, load

# config
MODEL_PATH = "/app/data/copod_model.joblib"
USERS_DB = "/app/users.json"
TARGET_INTERFACE = os.getenv("TARGET_INTERFACE", "enp1s0")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
PROM_URL = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
PROTOCOL_MAP = {"1": "ICMP", "6": "TCP", "17": "UDP", "58": "ICMPv6", "132": "SCTP"}

# auth config
SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key-change-this")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# pwdlib hashin
password_hash = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

r = redis.Redis(host=REDIS_HOST, port=6379, db=0, decode_responses=True)
prom = PrometheusConnect(url=PROM_URL, disable_ssl=True)
baseline_noise = np.array([
    [0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.50],
    [0.05, 0.01, 0.02, 0.10, 0.05, 0.50, 0.10, 0.60],
    [0.20, 0.10, 0.05, 0.05, 0.50, 0.20, 0.10, 0.40],
    [0.40, 0.30, 0.20, 0.20, 0.60, 0.80, 0.20, 0.90],
])
model = None

# helpers
def verify_password(plain_password, hashed_password):
    return password_hash.verify(plain_password, hashed_password)

def get_password_hash(password):
    return password_hash.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    # PyJWT syntax
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        return username
    except jwt.InvalidTokenError: 
        raise credentials_exception

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
            bytes_count = struct.unpack('!I', record[20:24])[0]
            dst_port = struct.unpack('!H', record[34:36])[0]
            src_ip = socket.inet_ntoa(struct.pack('!I', struct.unpack('!I', record[0:4])[0]))
            proto_name = PROTOCOL_MAP.get(str(record[38]), "Other")
            
            r.zincrby("top_talkers_src", bytes_count, src_ip)
            r.zincrby("protocol_usage", bytes_count, proto_name)
            r.sadd("active_ports", dst_port)
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
        try:
            model = load(MODEL_PATH)
        except Exception:
            model = COPOD(contamination=0.1)
            model.fit(baseline_noise)
    else:
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
@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    if not os.path.exists(USERS_DB):
        raise HTTPException(status_code=500, detail="User DB missing")
    
    with open(USERS_DB, 'r') as f:
        users = json.load(f)
    
    user = next((u for u in users if u['username'] == form_data.username), None)
    
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    if user['password'] != form_data.password: 
         raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    access_token = create_access_token(
        data={"sub": user['username'], "name": user.get('name', 'User')},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/")
def read_root():
    return {"status": "AIOps Engine Online"}

@app.get("/dashboard")
def get_dashboard_data(current_user: str = Depends(get_current_user)):
    cached = r.get("system_health")
    current = json.loads(cached) if cached else {}
    return current

@app.post("/train/retrain-recent")
def retrain_model(current_user: str = Depends(get_current_user)):
    global model
    try:
        model.fit(baseline_noise)
        dump(model, MODEL_PATH)
        return {"status": "success", "message": "Model reset and saved."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/run-inference")
def trigger_analysis():
    try:
        cpu_raw = get_metric('1 - avg(rate(node_cpu_seconds_total{mode="idle"}[1m]))')
        rx_mbps = get_metric(f'rate(node_network_receive_bytes_total{{device="{TARGET_INTERFACE}"}}[1m])') / 1024 / 1024
        tx_mbps = get_metric(f'rate(node_network_transmit_bytes_total{{device="{TARGET_INTERFACE}"}}[1m])') / 1024 / 1024
        pps_raw = get_metric(f'rate(node_network_receive_packets_total{{device="{TARGET_INTERFACE}"}}[1m])')

        raw_top_ips = r.zrevrange("top_talkers_src", 0, 4, withscores=True)
        top_ips = [{"label": ip, "value": score} for ip, score in raw_top_ips]
        
        unique_ips = r.zcard("top_talkers_src") or 0
        unique_ports = r.scard("active_ports") or 0
        max_flow_score = top_ips[0]['value'] if top_ips else 0
        
        proto_data = r.zrange("protocol_usage", 0, -1, withscores=True)
        proto_entropy = entropy([s / sum(x for _, x in proto_data) for _, s in proto_data]) if proto_data else 0.0

        fan_out_ratio = unique_ports / (unique_ips + 1)
        direction_ratio = min(tx_mbps / rx_mbps, 10.0) if rx_mbps > 0 else 0.0

        vector = np.array([[
            min(cpu_raw, 1.0), min(rx_mbps / 100.0, 1.0), min(pps_raw / 10000.0, 1.0),
            min(unique_ips / 1000, 1.0), min(max_flow_score / 100000, 1.0),
            min(proto_entropy / 3.0, 1.0), min(fan_out_ratio / 10.0, 1.0), min(direction_ratio / 5.0, 1.0)
        ]])
        
        raw_score = model.decision_function(vector)[0].item()
        final_score = sigmoid((raw_score - 7) / 1.11)

        status = "HEALTHY"
        alert_msg = "System Normal"
        if final_score > 0.75:
            status = "CRITICAL"
            if top_ips and (top_ips[0]['value'] / sum(i['value'] for i in top_ips)) > 0.5:
                alert_msg = f"Intrusion Detected! Source: {top_ips[0]['label']}"
            elif fan_out_ratio > 5.0:
                 alert_msg = "Port Scanning Activity"
            else:
                alert_msg = "High Anomalous Traffic"
        elif final_score > 0.50:
            status = "UNSTABLE"

        if r.exists("top_talkers_src"):
            r.zinterstore("top_talkers_src", {"top_talkers_src": 0.5})
            r.zremrangebyscore("top_talkers_src", "-inf", 1.0)
        if r.exists("active_ports"): r.delete("active_ports")

        payload = {
            "status": status,
            "score": final_score,
            "alert": alert_msg,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "interface": str(TARGET_INTERFACE),
            "model": "COPOD",
            "metrics": {"cpu": round(cpu_raw * 100, 1), "mbps": round(rx_mbps, 2), "pps": int(pps_raw)},
            "flow_data": {"top_ips": top_ips, "protocols": [{"label": p, "value": s} for p, s in r.zrevrange("protocol_usage", 0, -1, withscores=True)]}
        }

        r.rpush("score_history", json.dumps({"timestamp": payload["timestamp"], "score": final_score}))
        r.ltrim("score_history", -60, -1)
        payload["history"] = [json.loads(x) for x in r.lrange("score_history", 0, -1)]
        r.set("system_health", json.dumps(payload), ex=60)
        return payload

    except Exception as e:
        print(f"[ERROR] {e}")
        return {"status": "ERROR", "score": 0.0}
