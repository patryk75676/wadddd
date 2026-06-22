import threading
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
        # device_ids locked into 24/7 mode (mine forever, survive reboots)
        self.mode_247: set = set()

    def register(self, data: dict):
        with self._lock:
            did = data["device_id"]
            if did not in self.devices:
                self.devices[did] = {}
                self.history[did] = deque(maxlen=720)
            self.devices[did].update(data)
            self.devices[did]["status"] = "online"
            self.devices[did]["registered_at"] = datetime.utcnow().isoformat()
            # If 24/7 mode was set while machine was offline, push it now
            if did in self.mode_247:
                self.pending[did] = {"action": "set_247", "enabled": True}

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
                "mode_247": data.get("mode_247", False),
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
                out.append({**dev, "device_id": did, "mode_247": did in self.mode_247})
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
            self.mode_247.discard(device_id)

    # ── 24/7 mode ─────────────────────────────────────────────────────────

    def set_247(self, device_id: str, enabled: bool):
        """Enable/disable 24/7 mining on a device (or '_all' for broadcast)."""
        with self._lock:
            if device_id == "_all":
                targets = list(self.devices.keys())
                if enabled:
                    self.mode_247.update(targets)
                else:
                    self.mode_247.clear()
                for did in targets:
                    self.pending[did] = {"action": "set_247", "enabled": enabled}
            else:
                if enabled:
                    self.mode_247.add(device_id)
                else:
                    self.mode_247.discard(device_id)
                self.pending[device_id] = {"action": "set_247", "enabled": enabled}

    def get_247(self, device_id: str) -> bool:
        with self._lock:
            return device_id in self.mode_247


STATE = AppState()
