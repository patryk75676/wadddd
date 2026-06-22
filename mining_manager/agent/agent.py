"""
Mining Farm Agent v2.0 — Auto-konfiguracja sprzętu
====================================================
Nowe w v2.0:
  - Auto-detekcja CPU, RAM, GPU (NVIDIA/AMD)
  - Generuje optymalny xmrig_config.json per maszyna
  - XMRig uruchamiany przez --config zamiast flag
  - Raportuje pełne info o sprzęcie do dashboardu
"""

import psutil, time, platform, socket, uuid
import subprocess, threading, requests, json, os, sys, logging
from datetime import datetime
from pathlib import Path
from wol_setup import WolConfigurator
from hardware_detect import auto_detect_and_configure

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("agent.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("agent")

CONFIG_PATH = Path("xmrig_config.json")


# ── XMRig Manager ──────────────────────────────────────────────────────────
class XMRigManager:
    API_PORT    = 4048
    CRASH_WAIT  = 15

    def __init__(self, xmrig_path: str = "xmrig"):
        self.xmrig_path = xmrig_path
        self._proc: subprocess.Popen | None = None
        self._lock      = threading.Lock()
        self._running   = False

    def apply_config(self, config: dict):
        """Zapisz wygenerowany config na dysk."""
        CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False))
        log.info(f"Config zapisany: {CONFIG_PATH.resolve()}")

    def start(self):
        with self._lock:
            if self._proc and self._proc.poll() is None:
                return
            cmd = [self.xmrig_path, "--config", str(CONFIG_PATH)]
            try:
                self._proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                log.info(f"XMRig uruchomiony (PID {self._proc.pid}) z {CONFIG_PATH}")
            except FileNotFoundError:
                log.error(f"XMRig nie znaleziony: '{self.xmrig_path}'")
            except Exception as e:
                log.error(f"Błąd startu XMRig: {e}")

    def stop(self):
        with self._lock:
            if self._proc:
                self._proc.terminate()
                try:   self._proc.wait(timeout=10)
                except subprocess.TimeoutExpired: self._proc.kill()
                self._proc = None
                log.info("XMRig zatrzymany")

    def is_running(self) -> bool:
        with self._lock:
            return self._proc is not None and self._proc.poll() is None

    def start_watchdog(self):
        self._running = True
        def _watch():
            time.sleep(20)
            while self._running:
                if not self.is_running():
                    log.warning(f"XMRig crashował — restart za {self.CRASH_WAIT}s")
                    time.sleep(self.CRASH_WAIT)
                    if self._running:
                        self.start()
                time.sleep(5)
        threading.Thread(target=_watch, daemon=True).start()

    def stop_watchdog(self):
        self._running = False

    def get_stats(self) -> dict:
        try:
            r = requests.get(
                f"http://127.0.0.1:{self.API_PORT}/2/summary",
                timeout=3,
            )
            if r.ok:
                d  = r.json()
                hr = d.get("hashrate", {}).get("total", [0, 0, 0])
                rs = d.get("results", {})
                return {
                    "hashrate_hs":   hr[0] or 0,
                    "hashrate_1m":   hr[1] or 0,
                    "hashrate_15m":  hr[2] or 0,
                    "accepted":      rs.get("shares_good", 0),
                    "rejected":      rs.get("shares_total", 0) - rs.get("shares_good", 0),
                    "uptime_sec":    d.get("uptime", 0),
                    "algo":          d.get("algo", ""),
                    "pool":          d.get("connection", {}).get("pool", ""),
                    "hugepages":     d.get("hugepages", False),
                    "donate_level":  d.get("donate_level", 0),
                    "cuda_enabled":  d.get("cuda", {}).get("enabled", False),
                    "opencl_enabled": d.get("opencl", {}).get("enabled", False),
                }
        except requests.ConnectionError:
            pass
        except Exception as e:
            log.debug(f"XMRig API: {e}")
        return {"hashrate_hs": 0, "hashrate_1m": 0, "hashrate_15m": 0,
                "accepted": 0, "rejected": 0, "uptime_sec": 0}

    def reconfigure(self, pool: str, wallet: str):
        """Zmień pool/portfel — przepisz config i zrestartuj."""
        if CONFIG_PATH.exists():
            cfg = json.loads(CONFIG_PATH.read_text())
            if cfg.get("pools"):
                cfg["pools"][0]["url"]  = pool
                cfg["pools"][0]["user"] = wallet
                CONFIG_PATH.write_text(json.dumps(cfg, indent=2))
        self.stop()
        time.sleep(3)
        self.start()


# ── Hardware Stats ──────────────────────────────────────────────────────────
class HardwareStats:
    def collect(self) -> dict:
        mem  = psutil.virtual_memory()
        data = {
            "cpu_percent":  psutil.cpu_percent(interval=0.5),
            "ram_percent":  mem.percent,
            "ram_total_gb": round(mem.total / 1e9, 1),
            "gpus":         [],
        }
        try:
            import GPUtil
            for g in GPUtil.getGPUs():
                data["gpus"].append({
                    "id":        g.id,
                    "name":      g.name,
                    "load":      round(g.load * 100, 1),
                    "mem_used":  g.memoryUsed,
                    "mem_total": g.memoryTotal,
                    "temp_c":    g.temperature,
                })
        except Exception:
            pass
        return data


# ── Uninstall ───────────────────────────────────────────────────────────────
def uninstall_agent():
    log.warning("=" * 50)
    log.warning("  ODINSTALOWYWANIE — polecenie z serwera")
    log.warning("=" * 50)
    os_type = platform.system()
    if os_type == "Windows":
        for cmd in [["sc","stop","MiningAgent"],["sc","delete","MiningAgent"]]:
            subprocess.run(cmd, capture_output=True)
    elif os_type == "Linux":
        for cmd in [["systemctl","stop","mining-agent"],
                    ["systemctl","disable","mining-agent"]]:
            subprocess.run(cmd, capture_output=True)
        import glob
        for path in ["/etc/systemd/system/mining-agent.service",
                     "/opt/mining-agent/agent.py",
                     "/opt/mining-agent/wol_setup.py",
                     "/opt/mining-agent/hardware_detect.py",
                     str(CONFIG_PATH)] + \
                    glob.glob("/etc/systemd/system/wol-*.service"):
            try: os.remove(path)
            except FileNotFoundError: pass
        subprocess.run(["systemctl","daemon-reload"], capture_output=True)
        try: os.rmdir("/opt/mining-agent")
        except Exception: pass
    log.info("Odinstalowanie zakończone.")


# ── Główny Agent ────────────────────────────────────────────────────────────
class MiningAgent:
    INTERVAL        = 10
    MAX_HB_FAILS    = 6

    def __init__(self, server_url, pool, wallet,
                 xmrig_path="xmrig", smart_plug_ip="", smart_plug_type=""):
        self.server_url   = server_url.rstrip("/")
        self.pool         = pool
        self.wallet       = wallet
        self.device_id    = hex(uuid.getnode())
        self.hostname     = socket.gethostname()
        self.xmrig        = XMRigManager(xmrig_path)
        self.hw           = HardwareStats()
        self.wol_cfg      = WolConfigurator(smart_plug_ip, smart_plug_type)
        self.wol_result   = None
        self.hw_summary   = {}
        self._hb_fails    = 0
        self._quit        = False

    # ── WoL ─────────────────────────────────────────────────────────────────
    def _setup_wol(self):
        log.info(f"[WoL] {platform.system()} — sprawdzam...")
        status = self.wol_cfg.check_status()
        if status.get("active"):
            self.wol_result = {"method":"wol","success":True,"detail":"aktywny","fallback":False}
            log.info("[WoL] ✓ Już aktywny")
        else:
            r = self.wol_cfg.configure()
            self.wol_result = r.to_dict()
            log.info(f"[WoL] {'✓' if r.success else '✗'} [{r.method}] {r.detail}")

    # ── Auto-konfiguracja sprzętu ────────────────────────────────────────────
    def _setup_hardware(self):
        log.info("[HW] Auto-detekcja sprzętu...")
        try:
            result = auto_detect_and_configure(
                pool     = self.pool,
                wallet   = self.wallet,
                api_port = XMRigManager.API_PORT,
            )
            self.hw_summary = result["summary"]
            self.xmrig.apply_config(result["config"])

            s = result["summary"]
            log.info(
                f"[HW] CPU: {s['cpu_model']} | "
                f"{s['cpu_threads']} wątki | "
                f"RandomX: {s['rx_mode'].upper()} | "
                f"GPU: {s['gpu_count']} szt."
            )
            if s["nvidia_count"]:
                log.info(f"[HW] NVIDIA: {s['nvidia_count']} kart — CUDA ✓")
            if s["amd_count"]:
                log.info(f"[HW] AMD: {s['amd_count']} kart — OpenCL ✓")
        except Exception as e:
            log.error(f"[HW] Detekcja nieudana: {e} — używam domyślnego config")
            # Fallback: podstawowy config bez GPU
            fallback = {
                "autosave": True, "background": False, "colors": False,
                "donate-level": 1, "log-file": "xmrig.log", "print-time": 60,
                "cpu": {"enabled":True,"huge-pages":True,"priority":5,"max-threads-hint":100},
                "randomx": {"mode":"auto","1gb-pages":False,"rdmsr":True,"wrmsr":True},
                "opencl": {"enabled": False},
                "cuda":   {"enabled": False},
                "pools": [{"url":self.pool,"user":self.wallet,"pass":"x","keepalive":True}],
                "http":  {"enabled":True,"host":"127.0.0.1","port":XMRigManager.API_PORT},
            }
            self.xmrig.apply_config(fallback)

    # ── Rejestracja ──────────────────────────────────────────────────────────
    def _register(self) -> bool:
        mac_n = uuid.getnode()
        mac   = ":".join(f"{(mac_n>>(5-i)*8)&0xff:02x}" for i in range(6))
        try:    ip = socket.gethostbyname(socket.gethostname())
        except: ip = ""

        payload = {
            "device_id":   self.device_id,
            "hostname":    self.hostname,
            "platform":    platform.system(),
            "cpu_count":   psutil.cpu_count(logical=True),
            "ram_gb":      round(psutil.virtual_memory().total/1e9, 1),
            "mac_address": mac,
            "ip_address":  ip,
            "wol_status":  self.wol_result or {},
            "hw_summary":  self.hw_summary,
        }
        try:
            r = requests.post(f"{self.server_url}/api/register", json=payload, timeout=10)
            if r.ok:
                log.info(f"[Server] Zarejestrowano ✓")
                return True
        except requests.ConnectionError:
            log.warning(f"[Server] Brak połączenia")
        except Exception as e:
            log.warning(f"[Server] {e}")
        return False

    # ── Heartbeat ─────────────────────────────────────────────────────────────
    def _heartbeat(self, mining, hw) -> dict:
        try:
            r = requests.post(f"{self.server_url}/api/heartbeat", json={
                "device_id": self.device_id,
                "timestamp": datetime.utcnow().isoformat(),
                "mining": mining, "hardware": hw,
                "miner_active": self.xmrig.is_running(),
            }, timeout=5)
            if r.ok:
                self._hb_fails = 0
                return r.json()
        except Exception:
            self._hb_fails += 1
            if self._hb_fails == self.MAX_HB_FAILS:
                log.warning("[Server] Utracono połączenie")
            if self._hb_fails % 30 == 0:
                self._register()
        return {}

    # ── Komendy ───────────────────────────────────────────────────────────────
    def _handle(self, cmd: dict):
        action = cmd.get("action")
        if not action: return
        log.info(f"[CMD] {action}")
        if action == "start":
            self.xmrig.start()
        elif action == "stop":
            self.xmrig.stop_watchdog(); self.xmrig.stop()
        elif action == "restart":
            self.xmrig.stop(); time.sleep(3); self.xmrig.start()
        elif action == "reconfigure":
            self.xmrig.reconfigure(
                cmd.get("pool",   self.pool),
                cmd.get("wallet", self.wallet),
            )
        elif action == "redetect":
            # Ponowna detekcja sprzętu i restart
            log.info("[CMD] Ponowna detekcja sprzętu...")
            self.xmrig.stop_watchdog()
            self.xmrig.stop()
            self._setup_hardware()
            time.sleep(2)
            self.xmrig.start()
            self.xmrig.start_watchdog()
        elif action == "uninstall":
            self.xmrig.stop_watchdog(); self.xmrig.stop(); time.sleep(2)
            try:
                requests.post(f"{self.server_url}/api/devices/{self.device_id}/unregistered",
                              timeout=5)
            except Exception: pass
            uninstall_agent()
            self._quit = True

    # ── Run ───────────────────────────────────────────────────────────────────
    def run(self):
        log.info("=" * 55)
        log.info(f"  Mining Agent v2.0  |  {self.hostname}  |  {platform.system()}")
        log.info("=" * 55)

        self._setup_wol()
        self._setup_hardware()

        while not self._register():
            log.info("Ponowna próba za 30s..."); time.sleep(30)

        self.xmrig.start()
        self.xmrig.start_watchdog()

        log.info("Agent aktywny.")
        try:
            while not self._quit:
                mining = self.xmrig.get_stats()
                hw     = self.hw.collect()
                cmd    = self._heartbeat(mining, hw)
                self._handle(cmd)

                log.info(
                    f"HR: {mining.get('hashrate_hs',0):.1f} H/s"
                    f" | 1m: {mining.get('hashrate_1m',0):.1f}"
                    f" | CPU: {hw['cpu_percent']:.0f}%"
                    f" | GPU: {len(hw.get('gpus',[]))}"
                )
                time.sleep(self.INTERVAL)
        except KeyboardInterrupt:
            log.info("Zatrzymywanie...")
        finally:
            self.xmrig.stop_watchdog()
            self.xmrig.stop()


if __name__ == "__main__":
    MiningAgent(
        server_url      = os.environ.get("RM_SERVER_URL",    "http://localhost:8000"),
        pool            = os.environ.get("RM_POOL",          "pool.supportxmr.com:3333"),
        wallet          = os.environ.get("RM_WALLET",        "TWOJ_PORTFEL"),
        xmrig_path      = os.environ.get("RM_XMRIG_PATH",   "xmrig"),
        smart_plug_ip   = os.environ.get("RM_PLUG_IP",      ""),
        smart_plug_type = os.environ.get("RM_PLUG_TYPE",    ""),
    ).run()
