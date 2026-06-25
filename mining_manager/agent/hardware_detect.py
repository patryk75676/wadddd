"""
hardware_detect.py — Auto-detekcja sprzętu i optymalizacja XMRig
=================================================================
Wykrywa:
  - CPU: model, fizyczne rdzenie, obsługę AVX2/AES-NI
  - RAM: ilość, czy starczy na RandomX fast mode
  - GPU NVIDIA: model, VRAM, sterownik CUDA
  - GPU AMD: model, VRAM (przez OpenCL / ROCm)

Generuje config.json dla XMRig dopasowany do tego konkretnego sprzętu.
"""

import os, sys, json, subprocess, platform, re, math
from pathlib import Path
import psutil
import logging

log = logging.getLogger("hw_detect")


def detect_system_model() -> str:
    """Detect manufacturer + model name (e.g. 'Lenovo Legion Go')."""
    sys_type = platform.system()
    try:
        if sys_type == "Windows":
            r = subprocess.run(
                ["wmic", "computersystem", "get", "Manufacturer,Model", "/value"],
                capture_output=True, text=True, timeout=6,
            )
            manufacturer = model = ""
            for line in r.stdout.splitlines():
                if "Manufacturer=" in line:
                    manufacturer = line.split("=", 1)[1].strip()
                elif "Model=" in line:
                    model = line.split("=", 1)[1].strip()
            result = f"{manufacturer} {model}".strip()
            # Filter out generic/useless values
            generic = {"system product name", "to be filled by o.e.m.", ""}
            if result.lower() in generic:
                return ""
            return result
        elif sys_type == "Linux":
            vendor = Path("/sys/class/dmi/id/sys_vendor").read_text().strip()
            name   = Path("/sys/class/dmi/id/product_name").read_text().strip()
            result = f"{vendor} {name}".strip()
            generic = {"to be filled by o.e.m.", "system product name"}
            if result.lower() in generic:
                return ""
            return result
    except Exception:
        pass
    return ""


# ─────────────────────────────────────────────────────────────────────────────
#  CPU
# ─────────────────────────────────────────────────────────────────────────────
def detect_cpu() -> dict:
    cores_physical = psutil.cpu_count(logical=False) or 1
    cores_logical  = psutil.cpu_count(logical=True)  or 1
    freq           = psutil.cpu_freq()
    ram_gb         = psutil.virtual_memory().total / 1e9

    cpu = {
        "model":          _cpu_model(),
        "cores_physical": cores_physical,
        "cores_logical":  cores_logical,
        "freq_mhz":       round(freq.max if freq else 0),
        "ram_gb":         round(ram_gb, 1),
        "aes_ni":         _has_aes_ni(),
        "avx2":           _has_avx2(),
        "avx512":         _has_avx512(),
    }

    # Optymalny licznik wątków:
    # - Zostaw 1 rdzeń na system (jeśli >4 rdzeni)
    # - Na mniejszych maszynach: wszystkie rdzenie
    threads = max(1, cores_physical - 1) if cores_physical > 4 else cores_physical
    cpu["optimal_threads"] = threads

    # RandomX fast mode wymaga 2688 MB RAM na wątek
    rx_fast_required_gb = threads * 2.625  # 2688 MB ≈ 2.625 GB
    cpu["rx_mode"] = "fast" if ram_gb >= rx_fast_required_gb + 2 else "auto"

    # 1GB hugepages — wymagają 3 GB na wątek, ale dają +15% hashrate
    cpu["rx_1gb_pages"] = ram_gb >= threads * 3 + 2

    return cpu


def _cpu_model() -> str:
    sys_type = platform.system()
    try:
        if sys_type == "Windows":
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                 r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            return winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
        elif sys_type == "Linux":
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if "model name" in line:
                        return line.split(":")[1].strip()
        elif sys_type == "Darwin":
            r = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"],
                               capture_output=True, text=True)
            return r.stdout.strip()
    except Exception:
        pass
    return platform.processor() or "Nieznany CPU"


def _cpu_flags() -> str:
    try:
        if platform.system() == "Linux":
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if line.startswith("flags"):
                        return line.lower()
        elif platform.system() == "Windows":
            # Sprawdź przez Python ctypes (uproszczona metoda)
            import ctypes
            return ""  # Windows sprawdzamy inaczej
    except Exception:
        pass
    return ""


def _has_aes_ni() -> bool:
    flags = _cpu_flags()
    if flags:
        return "aes" in flags
    # Fallback: większość procesorów Intel/AMD z ostatnich 10 lat ma AES-NI
    return True


def _has_avx2() -> bool:
    flags = _cpu_flags()
    if flags:
        return "avx2" in flags
    try:
        if platform.system() == "Windows":
            # Sprawdź przez moduł cpuinfo jeśli dostępny
            import cpuinfo
            info = cpuinfo.get_cpu_info()
            return "avx2" in info.get("flags", [])
    except Exception:
        pass
    return False  # bezpieczna domyślna wartość


def _has_avx512() -> bool:
    flags = _cpu_flags()
    return "avx512" in flags if flags else False


# ─────────────────────────────────────────────────────────────────────────────
#  GPU
# ─────────────────────────────────────────────────────────────────────────────
def detect_gpus() -> list[dict]:
    gpus = []
    gpus.extend(_detect_nvidia())
    gpus.extend(_detect_amd())
    return gpus


def _detect_nvidia() -> list[dict]:
    """Wykryj karty NVIDIA przez nvidia-smi (niezawodne, nie wymaga SDK)."""
    gpus = []
    try:
        r = subprocess.run(
            ["nvidia-smi",
             "--query-gpu=index,name,memory.total,memory.free,driver_version,compute_cap",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode != 0:
            return []
        for line in r.stdout.strip().splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 4:
                vram_mb = int(parts[2]) if parts[2].isdigit() else 0
                gpus.append({
                    "index":   int(parts[0]),
                    "vendor":  "nvidia",
                    "name":    parts[1],
                    "vram_mb": vram_mb,
                    "driver":  parts[4] if len(parts) > 4 else "",
                    "compute": parts[5] if len(parts) > 5 else "",
                    "cuda_available": True,
                })
    except FileNotFoundError:
        pass  # nvidia-smi niedostępny — brak NVIDIA lub sterowników
    except Exception as e:
        log.debug(f"NVIDIA detect: {e}")
    return gpus


def _detect_amd() -> list[dict]:
    """Wykryj karty AMD przez clinfo lub rocm-smi."""
    gpus = []

    # Metoda 1: rocm-smi (Linux)
    try:
        r = subprocess.run(
            ["rocm-smi", "--showproductname", "--showmeminfo", "vram", "--json"],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode == 0:
            data = json.loads(r.stdout)
            for card_id, info in data.items():
                if card_id.startswith("card"):
                    vram_mb = 0
                    try:
                        vram_mb = int(info.get("VRAM Total Memory (B)", 0)) // (1024*1024)
                    except Exception:
                        pass
                    gpus.append({
                        "index":   len(gpus),
                        "vendor":  "amd",
                        "name":    info.get("Card Series", "AMD GPU"),
                        "vram_mb": vram_mb,
                        "opencl_available": True,
                    })
            if gpus:
                return gpus
    except (FileNotFoundError, json.JSONDecodeError, Exception):
        pass

    # Metoda 2: clinfo (działa też na Windows)
    try:
        r = subprocess.run(["clinfo", "--list"], capture_output=True, text=True, timeout=10)
        if r.returncode == 0 and "AMD" in r.stdout:
            for line in r.stdout.splitlines():
                if "AMD" in line and "GPU" in line:
                    gpus.append({
                        "index":   len(gpus),
                        "vendor":  "amd",
                        "name":    line.strip(),
                        "vram_mb": 0,  # clinfo --list nie daje VRAM
                        "opencl_available": True,
                    })
    except (FileNotFoundError, Exception):
        pass

    # Metoda 3: GPUtil (wykrywa też AMD na Windows przez WMI)
    if not gpus:
        try:
            import GPUtil
            for g in GPUtil.getGPUs():
                if "amd" in g.name.lower() or "radeon" in g.name.lower():
                    gpus.append({
                        "index":   g.id,
                        "vendor":  "amd",
                        "name":    g.name,
                        "vram_mb": g.memoryTotal,
                        "opencl_available": True,
                    })
        except Exception:
            pass

    return gpus


# ─────────────────────────────────────────────────────────────────────────────
#  Generowanie konfiguracji XMRig
# ─────────────────────────────────────────────────────────────────────────────
def generate_xmrig_config(
    pool:    str,
    wallet:  str,
    cpu:     dict,
    gpus:    list[dict],
    api_port: int = 4048,
) -> dict:
    """
    Generuje optymalny config.json dla XMRig na podstawie wykrytego sprzętu.
    Zwraca dict gotowy do zserializowania jako JSON.
    """

    nvidia_gpus = [g for g in gpus if g["vendor"] == "nvidia"]
    amd_gpus    = [g for g in gpus if g["vendor"] == "amd"]
    threads     = cpu["optimal_threads"]

    # ── CPU sekcja ──────────────────────────────────────────────────────────
    # Wątki: jedno-wątkowy profil per rdzeń fizyczny
    cpu_threads = []
    for i in range(threads):
        thread = {
            "low_power_mode": False,
            "prefetch":       None,   # auto
            "affinity":       -1,     # OS dobiera
        }
        cpu_threads.append(thread)

    cpu_config = {
        "enabled":        True,
        "huge-pages":     True,
        "huge-pages-jit": True,
        "hw-aes":         True if cpu["aes_ni"] else None,
        "priority":       5,
        "memory-pool":    False,
        "yield":          True,
        "max-threads-hint": 100,
        "asm":            "auto",
        "argon2-impl":    None,
    }

    # ── RandomX sekcja ──────────────────────────────────────────────────────
    rx_config = {
        "init":                    -1,
        "init-avx2":               -1,
        "mode":                    cpu["rx_mode"],
        "1gb-pages":               cpu["rx_1gb_pages"],
        "rdmsr":                   True,
        "wrmsr":                   True,
        "cache_qos":               False,
        "numa":                    True,
        "scratchpad_prefetch_mode": 1,
    }

    # ── CUDA (NVIDIA) ────────────────────────────────────────────────────────
    cuda_devices = []
    for g in nvidia_gpus:
        vram = g["vram_mb"]
        # Intensity: ~70% VRAM dla Monero, więcej dla innych coinów
        # Grid size: zależy od VRAM
        grid = _calc_cuda_grid(vram)
        cuda_devices.append({
            "index":          g["index"],
            "bfactor":        10,
            "bsleep":         25,
            "affinity":       -1,
            "dataset_host":   vram >= 6000,  # duże karty: dataset na GPU
        })

    cuda_config = {
        "enabled": bool(nvidia_gpus),
        "loader":  None,
        "nvml":    True,
        "devices": cuda_devices if nvidia_gpus else [],
    }

    # ── OpenCL (AMD) ─────────────────────────────────────────────────────────
    opencl_devices = []
    for g in amd_gpus:
        opencl_devices.append({
            "index":          g["index"],
            "intensity":      _calc_opencl_intensity(g.get("vram_mb", 4096)),
            "worksize":       8,
            "unroll":         8,
            "affinity":       -1,
            "dataset_host":   g.get("vram_mb", 0) >= 6000,
        })

    opencl_config = {
        "enabled":  bool(amd_gpus),
        "cache":    True,
        "loader":   None,
        "platform": "AMD" if amd_gpus else "NVIDIA",
        "adl":      True,
        "devices":  opencl_devices if amd_gpus else [],
    }

    # ── Pełny config ─────────────────────────────────────────────────────────
    config = {
        "autosave":      True,
        "background":    False,  # nie uruchamiaj w tle — agent zarządza procesem
        "colors":        False,
        "title":         False,
        "randomx":       rx_config,
        "cpu":           cpu_config,
        "opencl":        opencl_config,
        "cuda":          cuda_config,
        "donate-level":  1,
        "donate-over-proxy": 1,
        "log-file":      "xmrig.log",
        "print-time":    60,
        "health-print-time": 60,
        "retries":       5,
        "retry-pause":   5,
        "pools": [
            {
                "algo":       None,
                "coin":       None,
                "url":        pool,
                "user":       wallet,
                "pass":       "x",
                "keepalive":  True,
                "enabled":    True,
                "tls":        False,
                "socks5":     None,
                "self-select": None,
            }
        ],
        "http": {
            "enabled":   True,
            "host":      "127.0.0.1",
            "port":      api_port,
            "access-token": None,
            "restricted":   True,
        },
    }

    return config


def _calc_cuda_grid(vram_mb: int) -> int:
    """Oblicz optymalny grid-size dla CUDA na podstawie VRAM."""
    if vram_mb >= 10000: return 2560
    if vram_mb >= 8000:  return 2048
    if vram_mb >= 6000:  return 1536
    if vram_mb >= 4000:  return 1024
    return 512


def _calc_opencl_intensity(vram_mb: int) -> int:
    """Oblicz optymalną intensywność OpenCL."""
    if vram_mb >= 16000: return 2048
    if vram_mb >= 8000:  return 1024
    if vram_mb >= 4000:  return 512
    return 256


# ─────────────────────────────────────────────────────────────────────────────
#  Hugepages — konfiguracja systemowa
# ─────────────────────────────────────────────────────────────────────────────
def configure_hugepages(threads: int) -> bool:
    """Ustaw liczbę hugepages w systemie dla optymalnego RandomX."""
    sys_type = platform.system()

    if sys_type == "Linux":
        # 2MB hugepages: potrzeba 1280 na wątek (dla RandomX fast)
        needed = threads * 1280 + 128   # +128 margines
        try:
            current_path = "/proc/sys/vm/nr_hugepages"
            with open(current_path) as f:
                current = int(f.read().strip())
            if current < needed:
                with open(current_path, "w") as f:
                    f.write(str(needed))
                log.info(f"HugePages: {current} → {needed}")
            # Utrwal w sysctl
            sysctl_path = "/etc/sysctl.d/99-xmrig-hugepages.conf"
            with open(sysctl_path, "w") as f:
                f.write(f"vm.nr_hugepages = {needed}\n")
            return True
        except PermissionError:
            log.warning("HugePages: brak uprawnień root — uruchom agenta jako root")
        except Exception as e:
            log.warning(f"HugePages: {e}")

    elif sys_type == "Windows":
        # Windows: XMRig może sam ustawić hugepages jeśli ma uprawnienia "Lock pages in memory"
        # To robi się przez Local Security Policy — XMRig próbuje automatycznie
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 "Get-ItemProperty 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Memory Management' -Name LargePageMinimum"],
                capture_output=True, text=True, timeout=5
            )
            log.info("HugePages Windows: XMRig próbuje automatycznie")
            return True
        except Exception:
            pass

    return False


# ─────────────────────────────────────────────────────────────────────────────
#  Główna funkcja
# ─────────────────────────────────────────────────────────────────────────────
def auto_detect_and_configure(pool: str, wallet: str, api_port: int = 4048) -> dict:
    """
    Wykryj sprzęt i wygeneruj optymalną konfigurację XMRig.
    Zwraca słownik z kluczami: config, cpu, gpus, summary
    """
    log.info("=== Auto-detekcja sprzętu ===")

    cpu  = detect_cpu()
    gpus = detect_gpus()

    log.info(f"CPU:  {cpu['model']} | {cpu['cores_physical']}P/{cpu['cores_logical']}L rdzeni "
             f"| RAM: {cpu['ram_gb']} GB | AES-NI: {cpu['aes_ni']} | AVX2: {cpu['avx2']}")
    log.info(f"Wątki kopania: {cpu['optimal_threads']} | RandomX tryb: {cpu['rx_mode'].upper()}")
    log.info(f"GPU: {len(gpus)} kart "
             f"({len([g for g in gpus if g['vendor']=='nvidia'])} NVIDIA, "
             f"{len([g for g in gpus if g['vendor']=='amd'])} AMD)")
    for g in gpus:
        log.info(f"  [{g['vendor'].upper()}] {g['name']} — {g.get('vram_mb', '?')} MB VRAM")

    # Konfiguruj hugepages
    configure_hugepages(cpu["optimal_threads"])

    # Generuj config XMRig
    config = generate_xmrig_config(pool, wallet, cpu, gpus, api_port)

    # Podsumowanie w czytelnej formie
    summary = {
        "cpu_model":     cpu["model"],
        "cpu_threads":   cpu["optimal_threads"],
        "rx_mode":       cpu["rx_mode"],
        "ram_gb":        cpu["ram_gb"],
        "aes_ni":        cpu["aes_ni"],
        "avx2":          cpu["avx2"],
        "gpu_count":     len(gpus),
        "nvidia_count":  len([g for g in gpus if g["vendor"] == "nvidia"]),
        "amd_count":     len([g for g in gpus if g["vendor"] == "amd"]),
        "gpus":          gpus,
        "cuda_enabled":  config["cuda"]["enabled"],
        "opencl_enabled": config["opencl"]["enabled"],
    }

    return {"config": config, "cpu": cpu, "gpus": gpus, "summary": summary}


# ── Test standalone ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    result = auto_detect_and_configure(
        pool   = "pool.supportxmr.com:3333",
        wallet = "TEST_WALLET",
    )
    print("\n=== Wygenerowana konfiguracja XMRig ===")
    print(json.dumps(result["config"], indent=2, ensure_ascii=False))
    print("\n=== Podsumowanie ===")
    print(json.dumps(result["summary"], indent=2, ensure_ascii=False))
