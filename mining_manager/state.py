import threading
import time
from collections import deque
from datetime import datetime


class AppState:
    def __init__(self):
        self._lock = threading.Lock()
        self.devices: dict = {}
        self.history: dict = {}
        self.pending: dict = {}
        self.pool_url = "pool.supportxmr.com:3333"
        self.wallet = ""
        self.coin = "xmr"
        # schedules: device_id -> {stop_at, hours, started_at}  ("_all" for broadcast)
        self.schedules: dict = {}
        self._sched_thread = threading.Thread(
            target=self._schedule_checker, daemon=True
        )
        self._sched_thread.start()

    def register(self, data: dict):
        with self._lock:
            did = data["device_id"]
            if did not in self.devices:
                self.devices[did] = {}
                self.history[did] = deque(maxlen=720)
            self.devices[did].update(data)
            self.devices[did]["status"] = "online"
            self.devices[did]["registered_at"] = datetime.utcnow().isoformat()

    def heartbeat(self, data: dict) -> dict:
        with self._lock:
            did = data["device_id"]
            if did not in self.devices:
                return {}
            now = datetime.utcnow()
            hw = data.get("hardware", {})
            mining = data.get("mining", {})
            self.devices[did].update({
                "last_seen": now.isoformat(),
                "status": "online",
                "mining": mining,
                "hardware": hw,
                "miner_active": data.get("miner_active", False),
            })
            gpu_t = max((g.get("temp_c", 0) for g in hw.get("gpus", [])), default=0)
            self.history[did].append({
                "t": now.strftime("%H:%M:%S"),
                "hr": mining.get("hashrate_hs", 0),
                "cpu": hw.get("cpu_percent", 0),
                "gpu_t": gpu_t,
            })
            return self.pending.pop(did, {})

    def get_devices(self):
        with self._lock:
            now = datetime.utcnow()
            out = []
            for did, dev in self.devices.items():
                ls = dev.get("last_seen")
                if ls and (now - datetime.fromisoformat(ls)).total_seconds() > 60:
                    dev["status"] = "offline"
                out.append({**dev, "device_id": did})
            return out

    def get_history(self, device_id: str, n: int = 60):
        with self._lock:
            return list(self.history.get(device_id, []))[-n:]

    def command(self, device_id: str, cmd: dict):
        with self._lock:
            self.pending[device_id] = cmd

    def broadcast(self, cmd: dict):
        with self._lock:
            for did in self.devices:
                self.pending[did] = dict(cmd)

    def summary(self):
        with self._lock:
            online = [d for d in self.devices.values() if d.get("status") == "online"]
            return {
                "total_hr": round(sum(d.get("mining", {}).get("hashrate_hs", 0) for d in online), 2),
                "online": len(online),
                "total": len(self.devices),
            }

    def delete_device(self, device_id: str):
        with self._lock:
            self.devices.pop(device_id, None)
            self.history.pop(device_id, None)
            self.pending.pop(device_id, None)
            self.schedules.pop(device_id, None)

    # ── Schedule support ──────────────────────────────────────────────────

    def set_schedule(self, device_id: str, hours: float):
        """Start mining and schedule automatic stop after `hours` (0 = indefinite)."""
        now = time.time()
        entry = {
            "started_at": now,
            "hours": hours,
            "stop_at": now + hours * 3600 if hours > 0 else None,
        }
        with self._lock:
            self.schedules[device_id] = entry
            if device_id == "_all":
                for did in self.devices:
                    self.pending[did] = {"action": "start"}
            else:
                self.pending[device_id] = {"action": "start"}

    def cancel_schedule(self, device_id: str):
        with self._lock:
            self.schedules.pop(device_id, None)

    def get_schedule(self, device_id: str) -> dict | None:
        with self._lock:
            return self.schedules.get(device_id) or self.schedules.get("_all")

    def _schedule_checker(self):
        while True:
            time.sleep(30)
            now = time.time()
            with self._lock:
                expired = [
                    did for did, s in self.schedules.items()
                    if s.get("stop_at") and now >= s["stop_at"]
                ]
                for did in expired:
                    del self.schedules[did]
                    if did == "_all":
                        for d in self.devices:
                            self.pending[d] = {"action": "stop"}
                    elif did in self.devices:
                        self.pending[did] = {"action": "stop"}


STATE = AppState()
