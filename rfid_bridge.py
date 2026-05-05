# rfid_bridge.py (FINAL STABLE VERSION)

import socket
import threading
import json
import requests
from datetime import datetime, timezone
from collections import deque

# ================= CONFIG =================
POST_URL = "https://sorry-81tw.onrender.com/api/tags"

# ================= BUFFER =================
_TAG_BUFFER = deque(maxlen=2000)
_LATEST_TS = None
_LAST_SEEN = {}   # 🔥 ใช้กันยิงซ้ำ

# ================= UTIL =================
def _now_iso_utc():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def latest_ts():
    return _LATEST_TS


def clear_tags():
    global _LATEST_TS
    _TAG_BUFFER.clear()
    _LATEST_TS = None


def read_tags_since(since: str | None):
    if not since:
        return list(_TAG_BUFFER)
    return [t for t in _TAG_BUFFER if t.get("ts") and t["ts"] >= since]


def _append_item(item):
    global _LATEST_TS
    _TAG_BUFFER.append(item)

    ts = item.get("ts") or _now_iso_utc()
    item["ts"] = ts

    if (not _LATEST_TS) or (ts > _LATEST_TS):
        _LATEST_TS = ts


# ================= NETWORK =================
def send_to_web(epc, rssi):
    try:
        res = requests.post(
            POST_URL,
            json={"epc": epc, "rssi": rssi},
            timeout=5
        )
        print("✅ sent:", res.status_code)
    except Exception as e:
        print("❌ post fail:", e)


# ================= PARSER =================
def _parse_line(line: str):
    line = (line or "").strip()
    if not line:
        return None

    low = line.lower()

    # 🔥 กัน packet ขาด (line ยังไม่ครบ)
    if "tag:" in low and "," not in line:
        return None

    # -------- JSON --------
    if line.startswith("{") and line.endswith("}"):
        try:
            d = json.loads(line)

            epc = (d.get("epc") or d.get("tag") or "").strip()
            epc_clean = epc.replace(" ", "")

            if not epc_clean:
                return None

            return {
                "ts": _now_iso_utc(),
                "epc": epc_clean,
                "tag_id": epc_clean[-4:],
                "antenna": str(d.get("antenna") or ""),
                "rssi": str(d.get("rssi") or "")
            }
        except:
            return None

    # -------- TEXT (Alien) --------
    def get(key):
        i = low.find(key)
        if i == -1:
            return ""
        return line[i + len(key):].split(",")[0].strip()

    epc = get("tag:") or get("epc:")
    if not epc:
        return None

    epc_clean = epc.replace(" ", "")

    ant = get("ant:") or get("antenna:")
    rssi = get("rssi:")

    return {
        "ts": _now_iso_utc(),
        "epc": epc_clean,
        "tag_id": epc_clean[-4:],
        "antenna": ant,
        "rssi": rssi
    }


# ================= CLIENT =================
def _client_handler(conn, addr):
    print("📡 Connected from:", addr)

    try:
        with conn:
            buffer = ""

            while True:
                data = conn.recv(4096)
                if not data:
                    break

                chunk = data.decode("utf-8", errors="ignore")
                buffer += chunk

                lines = buffer.split("\n")
                buffer = lines.pop()

                for line in lines:
                    line = line.strip()
                    if not line:
                        continue

                    print("RAW:", line)

                    item = _parse_line(line)

                    if item:
                        print("🔥 PARSED:", item)

                        # 🔥 กันยิงซ้ำ (2 วินาที)
                        key = item["epc"]
                        now = datetime.now().timestamp()

                        if key in _LAST_SEEN and now - _LAST_SEEN[key] < 2:
                            continue

                        _LAST_SEEN[key] = now

                        _append_item(item)

                        try:
                            send_to_web(item.get("epc"), item.get("rssi"))
                        except Exception as e:
                            print("❌ send error:", e)

    except Exception as e:
        print("RFID client error:", e)


# ================= SERVER =================
def start_tagstream_in_background(host="0.0.0.0", port=4000):
    def _server():
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((host, port))
        srv.listen(8)

        print(f"🚀 RFID TagStream server listening on {host}:{port}", flush=True)

        while True:
            conn, addr = srv.accept()

            t = threading.Thread(
                target=_client_handler,
                args=(conn, addr),
                daemon=True
            )
            t.start()

    th = threading.Thread(target=_server, daemon=True)
    th.start()


# ================= MAIN =================
if __name__ == "__main__":
    start_tagstream_in_background()

    while True:
        pass
