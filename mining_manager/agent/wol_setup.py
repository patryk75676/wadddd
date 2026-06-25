"""
wol_setup.py — Auto-konfiguracja Wake-on-LAN
=============================================
Wykrywa OS, sprawdza status WoL i konfiguruje automatycznie.
Fallback: inteligentne gniazdko (Tasmota / TP-Link Kasa) jeśli WoL niedostępny.
"""

import platform
import subprocess
import socket
import os
import sys
import logging
import json
import re
import struct
import time
from typing import Optional

log = logging.getLogger("wol_setup")


# ─────────────────────────────────────────────────────────────────────────────
#  WYKRYWANIE WoL I KONFIGURACJA
# ─────────────────────────────────────────────────────────────────────────────

class WolResult:
    def __init__(self, method: str, success: bool, detail: str, fallback: bool = False):
        self.method   = method
        self.success  = success
        self.detail   = detail
        self.fallback = fallback  # True jeśli to gniazdko zamiast WoL

    def to_dict(self):
        return {
            "method":   self.method,
            "success":  self.success,
            "detail":   self.detail,
            "fallback": self.fallback,
        }


class WolConfigurator:
    """Wykrywa OS i konfiguruje WoL optymalną metodą."""

    def __init__(self, smart_plug_ip: str = "", smart_plug_type: str = ""):
        self.os_type        = platform.system()           # 'Windows' | 'Linux'
        self.smart_plug_ip  = smart_plug_ip
        self.smart_plug_type = smart_plug_type.lower()   # 'tasmota' | 'kasa'

    # ── Główny punkt wejścia ─────────────────────────────────────────────────
    def configure(self) -> WolResult:
        log.info(f"System: {self.os_type} — sprawdzam WoL...")

        if self.os_type == "Windows":
            return self._try_windows()
        elif self.os_type == "Linux":
            return self._try_linux()
        else:
            return WolResult("none", False, f"Nieobsługiwany system: {self.os_type}")

    def check_status(self) -> dict:
        """Sprawdź czy WoL jest aktualnie aktywny (bez zmian konfiguracji)."""
        if self.os_type == "Windows":
            return self._check_windows()
        elif self.os_type == "Linux":
            return self._check_linux()
        return {"active": False, "detail": "nieznany system"}

    # ── WINDOWS ──────────────────────────────────────────────────────────────
    def _check_windows(self) -> dict:
        try:
            ps = (
                "Get-NetAdapter | Where-Object { $_.Status -eq 'Up' -and "
                "$_.PhysicalMediaType -match '802.3' } | "
                "ForEach-Object { "
                "  $pm = Get-NetAdapterPowerManagement -Name $_.Name -ErrorAction SilentlyContinue; "
                "  [PSCustomObject]@{ Name=$_.Name; WoL=$pm.WakeOnMagicPacket } "
                "} | ConvertTo-Json"
            )
            r = subprocess.run(
                ["powershell", "-NonInteractive", "-Command", ps],
                capture_output=True, text=True, timeout=15
            )
            data = json.loads(r.stdout.strip() or "[]")
            if isinstance(data, dict):
                data = [data]
            active = any(d.get("WoL") == "Enabled" for d in data)
            adapters = [d.get("Name", "") for d in data]
            return {"active": active, "adapters": adapters, "detail": str(data)}
        except Exception as e:
            return {"active": False, "detail": str(e)}

    def _try_windows(self) -> WolResult:
        # Metoda 1: PowerShell cmdlet (Windows 10/11)
        result = self._win_powershell_cmdlet()
        if result.success:
            return result

        # Metoda 2: Rejestr systemowy
        result = self._win_registry()
        if result.success:
            return result

        # Metoda 3: devcon.exe (jeśli zainstalowany)
        result = self._win_devcon()
        if result.success:
            return result

        # Fallback: inteligentne gniazdko
        if self.smart_plug_ip:
            return self._test_smart_plug()

        return WolResult(
            "none", False,
            "WoL nie mógł być skonfigurowany automatycznie. "
            "Sprawdź BIOS: 'Wake on LAN' / 'Power On By PCI-E'."
        )

    def _win_powershell_cmdlet(self) -> WolResult:
        """PowerShell Enable-NetAdapterPowerManagement."""
        ps = (
            "$ok = 0; "
            "Get-NetAdapter | Where-Object { $_.Status -eq 'Up' -and $_.PhysicalMediaType -match '802.3' } | "
            "ForEach-Object { "
            "  try { "
            "    Enable-NetAdapterPowerManagement -Name $_.Name -WakeOnMagicPacket -ErrorAction Stop; "
            "    Set-NetAdapterPowerManagement -Name $_.Name -WakeOnMagicPacket Enabled -ErrorAction Stop; "
            "    $ok++ "
            "  } catch {} "
            "}; "
            "exit (if ($ok -gt 0) { 0 } else { 1 })"
        )
        try:
            r = subprocess.run(
                ["powershell", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", ps],
                capture_output=True, text=True, timeout=20
            )
            if r.returncode == 0:
                return WolResult("windows_powershell", True, "WoL włączony przez PowerShell cmdlet")
        except Exception as e:
            log.debug(f"PS cmdlet: {e}")
        return WolResult("windows_powershell", False, "PowerShell cmdlet niedostępny lub brak uprawnień")

    def _win_registry(self) -> WolResult:
        """Bezpośrednia edycja rejestru kart sieciowych."""
        try:
            import winreg
            base = r"SYSTEM\CurrentControlSet\Control\Class\{4D36E972-E325-11CE-BFC1-08002bE10318}"
            updated = 0
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base) as bk:
                i = 0
                while True:
                    try:
                        sub = winreg.EnumKey(bk, i)
                        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, f"{base}\\{sub}",
                                            0, winreg.KEY_ALL_ACCESS) as k:
                            try:
                                desc, _ = winreg.QueryValueEx(k, "DriverDesc")
                                if desc and "Virtual" not in desc and "WAN" not in desc:
                                    winreg.SetValueEx(k, "WakeOnMagicPacket",    0, winreg.REG_SZ, "1")
                                    winreg.SetValueEx(k, "PnPCapabilities",      0, winreg.REG_DWORD, 0)
                                    winreg.SetValueEx(k, "WakeOnPattern",        0, winreg.REG_SZ, "1")
                                    updated += 1
                            except FileNotFoundError:
                                pass
                        i += 1
                    except OSError:
                        break

            # Wyłącz Fast Boot
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                 r"SYSTEM\CurrentControlSet\Control\Session Manager\Power",
                                 0, winreg.KEY_SET_VALUE) as k:
                winreg.SetValueEx(k, "HiberbootEnabled", 0, winreg.REG_DWORD, 0)

            if updated > 0:
                return WolResult("windows_registry", True,
                                 f"Rejestr zaktualizowany ({updated} kart), Fast Boot wyłączony")
        except Exception as e:
            log.debug(f"Registry: {e}")
        return WolResult("windows_registry", False, "Brak dostępu do rejestru (uruchom jako Administrator)")

    def _win_devcon(self) -> WolResult:
        """Próba przez devcon.exe (Windows Driver Kit)."""
        try:
            r = subprocess.run(["devcon", "status", "=Net"], capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                return WolResult("windows_devcon", True, "devcon OK")
        except FileNotFoundError:
            pass
        return WolResult("windows_devcon", False, "devcon niedostępny")

    # ── LINUX ────────────────────────────────────────────────────────────────
    def _check_linux(self) -> dict:
        ifaces = self._linux_get_interfaces()
        results = {}
        for iface in ifaces:
            try:
                r = subprocess.run(["ethtool", iface], capture_output=True, text=True, timeout=5)
                match = re.search(r"Wake-on:\s*(\S+)", r.stdout)
                results[iface] = match.group(1) if match else "unknown"
            except Exception:
                results[iface] = "error"
        active = any("g" in v for v in results.values())
        return {"active": active, "interfaces": results}

    def _try_linux(self) -> WolResult:
        # Metoda 1: ethtool
        result = self._linux_ethtool()
        if result.success:
            # Utrwal przez systemd
            self._linux_systemd_persist()
            return result

        # Metoda 2: NetworkManager
        result = self._linux_networkmanager()
        if result.success:
            return result

        # Metoda 3: ip link (podstawowe)
        result = self._linux_ip_link()
        if result.success:
            return result

        # Fallback: inteligentne gniazdko
        if self.smart_plug_ip:
            return self._test_smart_plug()

        return WolResult(
            "none", False,
            "WoL nie mógł być skonfigurowany. "
            "Sprawdź BIOS: 'Wake on LAN' / 'Power On By PCI-E'."
        )

    def _linux_get_interfaces(self) -> list[str]:
        """Zwróć listę aktywnych interfejsów Ethernet (bez virtual/wifi/lo)."""
        try:
            r = subprocess.run(["ip", "-o", "link", "show", "up"],
                                capture_output=True, text=True, timeout=5)
            ifaces = []
            for line in r.stdout.splitlines():
                name = line.split(": ")[1].split("@")[0] if ": " in line else ""
                if name and not any(x in name for x in
                                    ["lo", "wl", "veth", "docker", "br-", "virbr", "tun", "tap"]):
                    if re.match(r"^(eth|en|eno|ens|enp)\w+", name):
                        ifaces.append(name)
            return ifaces
        except Exception:
            return []

    def _linux_ethtool(self) -> WolResult:
        if not self._cmd_exists("ethtool"):
            # Spróbuj zainstalować
            for pm in [["apt-get", "install", "-y", "ethtool"],
                       ["yum", "install", "-y", "ethtool"],
                       ["dnf", "install", "-y", "ethtool"]]:
                try:
                    subprocess.run(pm, capture_output=True, timeout=30)
                    if self._cmd_exists("ethtool"):
                        break
                except Exception:
                    pass

        if not self._cmd_exists("ethtool"):
            return WolResult("linux_ethtool", False, "ethtool niedostępny")

        ifaces = self._linux_get_interfaces()
        if not ifaces:
            return WolResult("linux_ethtool", False, "Brak interfejsów Ethernet")

        ok = 0
        for iface in ifaces:
            r = subprocess.run(["ethtool", "-s", iface, "wol", "g"],
                                capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                ok += 1
                log.info(f"WoL włączony na {iface}")

        if ok > 0:
            return WolResult("linux_ethtool", True,
                             f"ethtool: WoL Magic Packet włączony ({ok}/{len(ifaces)} interfejsów)")
        return WolResult("linux_ethtool", False, "ethtool nie mógł włączyć WoL")

    def _linux_networkmanager(self) -> WolResult:
        if not self._cmd_exists("nmcli"):
            return WolResult("linux_nm", False, "NetworkManager niedostępny")
        try:
            r = subprocess.run(
                ["nmcli", "-t", "-f", "NAME,DEVICE", "connection", "show", "--active"],
                capture_output=True, text=True, timeout=5
            )
            ok = 0
            for line in r.stdout.splitlines():
                parts = line.split(":")
                if len(parts) >= 2:
                    conn, dev = parts[0], parts[1]
                    if re.match(r"^(eth|en|eno|ens|enp)", dev):
                        subprocess.run(
                            ["nmcli", "connection", "modify", conn,
                             "802-3-ethernet.wake-on-lan", "magic"],
                            capture_output=True, timeout=5
                        )
                        ok += 1
            if ok > 0:
                return WolResult("linux_networkmanager", True,
                                 f"NetworkManager: WoL ustawiony ({ok} połączeń)")
        except Exception as e:
            log.debug(f"NM: {e}")
        return WolResult("linux_networkmanager", False, "NetworkManager nie skonfigurował WoL")

    def _linux_ip_link(self) -> WolResult:
        """Ostatnia deska ratunku — próba przez ip link."""
        ifaces = self._linux_get_interfaces()
        ok = 0
        for iface in ifaces:
            try:
                # Niektóre sterowniki obsługują to przez sysfs
                wol_path = f"/sys/class/net/{iface}/device/power/wakeup"
                if os.path.exists(wol_path):
                    with open(wol_path, "w") as f:
                        f.write("enabled")
                    ok += 1
            except Exception:
                pass
        if ok > 0:
            return WolResult("linux_sysfs", True, f"sysfs wakeup enabled ({ok} interfejsów)")
        return WolResult("linux_sysfs", False, "sysfs: brak obsługi")

    def _linux_systemd_persist(self):
        """Utwórz usługę systemd żeby WoL utrzymał się po restarcie."""
        ifaces = self._linux_get_interfaces()
        for iface in ifaces:
            service = f"""[Unit]
Description=Wake-on-LAN dla {iface}
After=network.target

[Service]
Type=oneshot
ExecStart=/sbin/ethtool -s {iface} wol g
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
"""
            path = f"/etc/systemd/system/wol-{iface}.service"
            try:
                with open(path, "w") as f:
                    f.write(service)
                subprocess.run(["systemctl", "enable", f"wol-{iface}.service"], capture_output=True)
                subprocess.run(["systemctl", "start",  f"wol-{iface}.service"], capture_output=True)
                log.info(f"Usługa WoL dla {iface} aktywna (przetrwa restart)")
            except Exception as e:
                log.warning(f"Nie udało się utworzyć usługi WoL dla {iface}: {e}")

    # ── FALLBACK: INTELIGENTNE GNIAZDKO ────────────────────────────────────
    def _test_smart_plug(self) -> WolResult:
        """Sprawdź łączność z gniazdkiem i zwróć wynik."""
        if self.smart_plug_type == "tasmota":
            return self._tasmota_ping()
        elif self.smart_plug_type == "kasa":
            return self._kasa_ping()
        return WolResult("smart_plug", False, f"Nieznany typ gniazdka: {self.smart_plug_type}",
                         fallback=True)

    def _tasmota_ping(self) -> WolResult:
        try:
            import urllib.request
            url = f"http://{self.smart_plug_ip}/cm?cmnd=Status"
            with urllib.request.urlopen(url, timeout=5) as r:
                data = json.loads(r.read())
                if "Status" in data:
                    return WolResult("tasmota", True,
                                     f"Gniazdko Tasmota dostępne @ {self.smart_plug_ip}",
                                     fallback=True)
        except Exception as e:
            pass
        return WolResult("tasmota", False,
                         f"Gniazdko Tasmota niedostępne @ {self.smart_plug_ip}", fallback=True)

    def _kasa_ping(self) -> WolResult:
        """Protokół TP-Link Kasa (lokalny, bez chmury)."""
        try:
            key = 0xAB
            cmd = json.dumps({"system": {"get_sysinfo": {}}}).encode()
            encrypted = bytes([b ^ key for b in cmd])
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect((self.smart_plug_ip, 9999))
            s.send(struct.pack(">I", len(encrypted)) + encrypted)
            data = s.recv(4096)
            s.close()
            if data:
                return WolResult("kasa", True,
                                 f"Gniazdko TP-Link Kasa dostępne @ {self.smart_plug_ip}",
                                 fallback=True)
        except Exception:
            pass
        return WolResult("kasa", False,
                         f"Gniazdko TP-Link Kasa niedostępne @ {self.smart_plug_ip}", fallback=True)

    # ── Helpers ──────────────────────────────────────────────────────────────
    @staticmethod
    def _cmd_exists(cmd: str) -> bool:
        import shutil
        return shutil.which(cmd) is not None


# ─────────────────────────────────────────────────────────────────────────────
#  ZDALNE STEROWANIE GNIAZDKIEM (używane przez server.py)
# ─────────────────────────────────────────────────────────────────────────────

def tasmota_power(ip: str, state: str = "ON") -> bool:
    """Włącz/wyłącz gniazdko Tasmota. state = 'ON' | 'OFF' | 'TOGGLE'"""
    try:
        import urllib.request
        url = f"http://{ip}/cm?cmnd=Power%20{state}"
        with urllib.request.urlopen(url, timeout=5) as r:
            data = json.loads(r.read())
            return data.get("POWER", "") == state
    except Exception:
        return False


def kasa_power(ip: str, state: bool = True) -> bool:
    """Włącz/wyłącz gniazdko TP-Link Kasa."""
    try:
        key = 0xAB
        cmd = json.dumps({
            "system": {"set_relay_state": {"state": 1 if state else 0}}
        }).encode()
        encrypted = bytes([b ^ key for b in cmd])
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect((ip, 9999))
        s.send(struct.pack(">I", len(encrypted)) + encrypted)
        data = s.recv(4096)
        s.close()
        return bool(data)
    except Exception:
        return False


# ── Test standalone ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    cfg = WolConfigurator(
        smart_plug_ip   = os.environ.get("SMART_PLUG_IP", ""),
        smart_plug_type = os.environ.get("SMART_PLUG_TYPE", ""),
    )
    print(f"\n=== Diagnostyka WoL — {cfg.os_type} ===")
    status = cfg.check_status()
    print(f"Aktualny status: {'✓ AKTYWNY' if status.get('active') else '✗ NIEAKTYWNY'}")
    print(f"Szczegóły: {status}")

    if not status.get("active"):
        print("\nPróbuję skonfigurować...")
        result = cfg.configure()
        print(f"\nWynik: {'✓' if result.success else '✗'} [{result.method}] {result.detail}")
        if result.fallback:
            print("→ Używam gniazdka jako alternatywy dla WoL")
    else:
        print("\nWoL jest już aktywny — brak potrzeby konfiguracji.")
