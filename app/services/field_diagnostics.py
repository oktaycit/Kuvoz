"""Field setup diagnostics for Kuvoz devices.

The checks in this module are intentionally read-only. They are used by both
the web setup page and the command line field-check script so technicians see
the same result in either workflow.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import re
import shutil
import socket
import subprocess
from typing import Any


POWER_THROTTLED_FLAGS = {
    0: "undervoltage_now",
    1: "arm_frequency_capped_now",
    2: "throttled_now",
    3: "soft_temperature_limit_now",
    16: "undervoltage_occurred",
    17: "arm_frequency_capped_occurred",
    18: "throttled_occurred",
    19: "soft_temperature_limit_occurred",
}

FLAG_LABELS_TR = {
    "undervoltage_now": "Anlik dusuk voltaj var",
    "arm_frequency_capped_now": "CPU frekansi anlik kisiliyor",
    "throttled_now": "Sistem anlik throttle oluyor",
    "soft_temperature_limit_now": "Sicaklik limiti anlik aktif",
    "undervoltage_occurred": "Gecmiste dusuk voltaj goruldu",
    "arm_frequency_capped_occurred": "Gecmiste CPU frekansi kisildi",
    "throttled_occurred": "Gecmiste throttle goruldu",
    "soft_temperature_limit_occurred": "Gecmiste sicaklik limiti goruldu",
}

STATUS_ORDER = {"ok": 0, "warn": 1, "fail": 2, "unknown": 1}


def read_text_file(path: str, max_chars: int = 4000) -> str | None:
    """Read a small system text file if available."""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            return handle.read(max_chars).strip()
    except OSError:
        return None


def parse_meminfo_snapshot(raw: str | None) -> dict[str, int]:
    """Parse /proc/meminfo text into kB values."""
    values: dict[str, int] = {}
    if not raw:
        return values

    for line in raw.splitlines():
        if ":" not in line:
            continue
        key, rest = line.split(":", 1)
        match = re.search(r"([0-9]+)", rest)
        if match:
            values[key] = int(match.group(1))
    return values


def format_uptime(seconds: float | None) -> str | None:
    if seconds is None:
        return None
    total_minutes = int(seconds // 60)
    days, minutes_after_days = divmod(total_minutes, 60 * 24)
    hours, minutes = divmod(minutes_after_days, 60)
    if days:
        return f"{days} gün {hours} saat"
    if hours:
        return f"{hours} saat {minutes} dk"
    return f"{minutes} dk"


def raise_status(current: str, candidate: str) -> str:
    if STATUS_ORDER.get(candidate, 1) > STATUS_ORDER.get(current, 0):
        return candidate
    return current


def run_command(args: list[str], timeout: int = 5) -> dict[str, Any]:
    """Run a command and return a JSON-safe result."""
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "available": True,
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "timeout": False,
        }
    except FileNotFoundError:
        return {
            "available": False,
            "ok": False,
            "returncode": None,
            "stdout": "",
            "stderr": f"{args[0]} bulunamadi",
            "timeout": False,
        }
    except subprocess.TimeoutExpired:
        return {
            "available": True,
            "ok": False,
            "returncode": None,
            "stdout": "",
            "stderr": "Komut zaman asimina ugradi",
            "timeout": True,
        }
    except Exception as exc:
        return {
            "available": True,
            "ok": False,
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
            "timeout": False,
        }


def split_nmcli_line(line: str) -> list[str]:
    """Split nmcli terse output while respecting escaped colons."""
    parts: list[str] = []
    current: list[str] = []
    escaped = False
    for char in line:
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == ":":
            parts.append("".join(current))
            current = []
        else:
            current.append(char)
    parts.append("".join(current))
    return parts


def decode_power_throttled(raw: str | None) -> dict[str, Any]:
    """Decode vcgencmd get_throttled output."""
    if not raw or "=" not in raw:
        return {
            "raw": raw,
            "mask": None,
            "active_flags": [],
            "current_flags": [],
            "historical_flags": [],
            "flag_labels": [],
            "error": "Beklenmeyen get_throttled ciktisi",
        }

    try:
        mask = int(raw.split("=", 1)[1].strip().lower(), 16)
    except ValueError:
        return {
            "raw": raw,
            "mask": None,
            "active_flags": [],
            "current_flags": [],
            "historical_flags": [],
            "flag_labels": [],
            "error": "get_throttled mask okunamadi",
        }

    active_flags = [
        flag_name for bit, flag_name in POWER_THROTTLED_FLAGS.items()
        if mask & (1 << bit)
    ]
    current_flags = [flag for flag in active_flags if flag.endswith("_now")]
    historical_flags = [flag for flag in active_flags if flag.endswith("_occurred")]
    return {
        "raw": raw,
        "mask": mask,
        "active_flags": active_flags,
        "current_flags": current_flags,
        "historical_flags": historical_flags,
        "flag_labels": [FLAG_LABELS_TR.get(flag, flag) for flag in active_flags],
        "error": None,
    }


def collect_power_status() -> dict[str, Any]:
    """Collect Raspberry Pi power and throttling diagnostics."""
    if not shutil.which("vcgencmd"):
        return {
            "key": "power",
            "status": "unknown",
            "title": "Güç ve undervoltage",
            "message": "vcgencmd bulunamadi; bu kontrol sadece Raspberry Pi uzerinde calisir.",
            "details": {},
            "actions": [
                "Bu cikti Mac veya PC uzerinde alindiysa normaldir.",
                "Sahada Raspberry Pi uzerinde make field-check calistirin.",
            ],
        }

    throttled_cmd = run_command(["vcgencmd", "get_throttled"], timeout=4)
    if not throttled_cmd["ok"]:
        return {
            "key": "power",
            "status": "fail",
            "title": "Güç ve undervoltage",
            "message": throttled_cmd["stderr"] or "vcgencmd get_throttled basarisiz.",
            "details": {"command": throttled_cmd},
            "actions": ["Raspberry Pi firmware/boot kurulumunu ve vcgencmd erisimini kontrol edin."],
        }

    decoded = decode_power_throttled(throttled_cmd["stdout"])
    temp_c = None
    volts = None

    temp_cmd = run_command(["vcgencmd", "measure_temp"], timeout=4)
    if temp_cmd["ok"]:
        temp_match = re.search(r"temp=([0-9.]+)", temp_cmd["stdout"])
        if temp_match:
            temp_c = float(temp_match.group(1))

    volts_cmd = run_command(["vcgencmd", "measure_volts"], timeout=4)
    if volts_cmd["ok"]:
        volts_match = re.search(r"volt=([0-9.]+)V", volts_cmd["stdout"])
        if volts_match:
            volts = float(volts_match.group(1))

    current_flags = decoded["current_flags"]
    historical_flags = decoded["historical_flags"]
    actions: list[str] = []
    if current_flags:
        status = "fail"
        message = "Anlik guc/thermal kisitlama var."
        actions.extend([
            "5V 3A kaliteli adaptore gecin; mumkunse resmi Raspberry Pi adaptoru kullanin.",
            "Ince/uzun USB kabloyu degistirin; 24AWG veya daha kalin, kisa kablo kullanin.",
            "Role, fan, sensor ve kamera yuklerini ayni anda test ederken voltaj dususunu izleyin.",
        ])
    elif historical_flags:
        status = "warn"
        message = "Cihaz bu acilistan beri dusuk voltaj veya throttle yasamis."
        actions.extend([
            "Adaptoru ve kabloyu degistirip yeniden baslatin; get_throttled 0x0 olana kadar kontrol edin.",
            "Saha kurulumu tamamlanmadan once en az 10 dakika yuk altinda tekrar make field-check calistirin.",
        ])
    else:
        status = "ok"
        message = "Dusuk voltaj veya throttle kaydi yok."

    if temp_c is not None and temp_c >= 75:
        status = "fail"
        actions.append("Raspberry Pi sicakligi yuksek; havalandirma/sogutucu kontrol edin.")
    elif temp_c is not None and temp_c >= 65 and status == "ok":
        status = "warn"
        actions.append("Raspberry Pi sicakligi yukseliyor; kasa ici hava akisini kontrol edin.")

    return {
        "key": "power",
        "status": status,
        "title": "Güç ve undervoltage",
        "message": message,
        "details": {
            "raw": decoded["raw"],
            "mask": decoded["mask"],
            "active_flags": decoded["active_flags"],
            "current_flags": current_flags,
            "historical_flags": historical_flags,
            "flag_labels": decoded["flag_labels"],
            "temperature_c": temp_c,
            "core_volts": volts,
        },
        "actions": actions,
    }


def collect_performance_status() -> dict[str, Any]:
    """Collect CPU, memory and swap pressure signals that explain slow UI."""
    actions: list[str] = []
    details: dict[str, Any] = {
        "model": read_text_file("/proc/device-tree/model"),
        "cpu_count": os.cpu_count() or 1,
        "load_average": None,
        "load_1m_per_core": None,
        "memory_used_percent": None,
        "memory_available_mb": None,
        "swap_used_percent": None,
        "swap_used_mb": None,
        "uptime": None,
    }

    try:
        load_1m, load_5m, load_15m = os.getloadavg()
        cpu_count = max(int(details["cpu_count"] or 1), 1)
        details["load_average"] = {
            "1m": round(load_1m, 2),
            "5m": round(load_5m, 2),
            "15m": round(load_15m, 2),
        }
        details["load_1m_per_core"] = round(load_1m / cpu_count, 2)
    except OSError:
        pass

    meminfo = parse_meminfo_snapshot(read_text_file("/proc/meminfo", max_chars=12000))
    mem_total_kb = meminfo.get("MemTotal")
    mem_available_kb = meminfo.get("MemAvailable")
    if mem_total_kb and mem_available_kb is not None:
        mem_used_kb = max(mem_total_kb - mem_available_kb, 0)
        details["memory_used_percent"] = round((mem_used_kb / mem_total_kb) * 100, 1)
        details["memory_available_mb"] = round(mem_available_kb / 1024)

    swap_total_kb = meminfo.get("SwapTotal", 0)
    swap_free_kb = meminfo.get("SwapFree", 0)
    if swap_total_kb:
        swap_used_kb = max(swap_total_kb - swap_free_kb, 0)
        details["swap_used_percent"] = round((swap_used_kb / swap_total_kb) * 100, 1)
        details["swap_used_mb"] = round(swap_used_kb / 1024)
    elif meminfo:
        details["swap_used_percent"] = 0.0
        details["swap_used_mb"] = 0

    uptime_raw = read_text_file("/proc/uptime", max_chars=80)
    if uptime_raw:
        try:
            uptime_seconds = float(uptime_raw.split()[0])
            details["uptime"] = format_uptime(uptime_seconds)
        except (ValueError, IndexError):
            pass

    status = "ok"
    load_per_core = details.get("load_1m_per_core")
    memory_used_percent = details.get("memory_used_percent")
    swap_used_percent = details.get("swap_used_percent")

    if isinstance(load_per_core, (int, float)):
        if load_per_core >= 1.5:
            status = raise_status(status, "fail")
            actions.append("CPU yükü yüksek; Chromium sekmeleri, AI kamera ve servis loglarını kontrol edin.")
        elif load_per_core >= 0.9:
            status = raise_status(status, "warn")
            actions.append("CPU yükleniyor; Pi 3 cihazlarda kiosk ve AI aynı anda yavaşlık yapabilir.")

    if isinstance(memory_used_percent, (int, float)):
        if memory_used_percent >= 95:
            status = raise_status(status, "fail")
            actions.append("Bellek kritik seviyede; kuvoz-kiosk servisini yeniden başlatıp log/cache büyümesini kontrol edin.")
        elif memory_used_percent >= 85:
            status = raise_status(status, "warn")
            actions.append("Bellek kullanımı yüksek; Chromium cache ve arka plan servislerini izleyin.")

    if isinstance(swap_used_percent, (int, float)):
        if swap_used_percent >= 50:
            status = raise_status(status, "fail")
            actions.append("Swap kullanımı yüksek; microSD I/O yavaşlığı arayüz tepkisini belirgin düşürür.")
        elif swap_used_percent >= 15:
            status = raise_status(status, "warn")
            actions.append("Swap kullanımı başlamış; Pi 3 için bu genellikle RAM baskısı işaretidir.")

    if (
        details.get("load_average") is None
        and details.get("memory_used_percent") is None
        and details.get("swap_used_percent") is None
    ):
        status = "unknown"
        message = "Performans metrikleri bu ortamda okunamadı."
        actions.append("Bu çıktı Mac/PC üzerinde alındıysa normaldir; Raspberry Pi üzerinde tekrar kontrol edin.")
    elif status == "ok":
        message = "CPU yükü, bellek ve swap sağlıklı görünüyor."
    else:
        message = "Performans baskısı arayüz tepkisini yavaşlatabilir."

    return {
        "key": "performance",
        "status": status,
        "title": "Performans baskısı",
        "message": message,
        "details": details,
        "actions": actions,
    }


def collect_wifi_status() -> dict[str, Any]:
    """Collect Wi-Fi, IP and basic internet diagnostics."""
    details: dict[str, Any] = {
        "connected": False,
        "ssid": None,
        "signal": None,
        "device": None,
        "ip": None,
        "default_route": None,
        "dns_ok": False,
        "internet_ok": False,
    }
    actions: list[str] = []

    nmcli_cmd = run_command(
        ["nmcli", "-t", "-f", "ACTIVE,SSID,SIGNAL,SECURITY,DEVICE", "dev", "wifi"],
        timeout=12,
    )
    if nmcli_cmd["available"] and nmcli_cmd["ok"]:
        for line in nmcli_cmd["stdout"].splitlines():
            parts = split_nmcli_line(line)
            if len(parts) >= 5 and parts[0] == "yes":
                details.update({
                    "connected": True,
                    "ssid": parts[1] or None,
                    "signal": int(parts[2]) if parts[2].isdigit() else None,
                    "security": parts[3] or None,
                    "device": parts[4] or "wlan0",
                })
                break
    elif not nmcli_cmd["available"]:
        actions.append("NetworkManager/nmcli bulunamadi; sudo apt install network-manager ile kurun.")
    else:
        actions.append(nmcli_cmd["stderr"] or "nmcli Wi-Fi durumu okunamadi.")

    device = details["device"] or "wlan0"
    ip_cmd = run_command(["ip", "-4", "-o", "addr", "show", "dev", device], timeout=5)
    if ip_cmd["ok"]:
        match = re.search(r"inet\s+([0-9.]+)/", ip_cmd["stdout"])
        if match:
            details["ip"] = match.group(1)

    route_cmd = run_command(["ip", "route", "get", "1.1.1.1"], timeout=5)
    if route_cmd["ok"]:
        details["default_route"] = route_cmd["stdout"].splitlines()[0] if route_cmd["stdout"] else None

    dns_cmd = run_command(["getent", "hosts", "login.tailscale.com"], timeout=5)
    details["dns_ok"] = dns_cmd["ok"]

    internet_cmd = run_command(["curl", "-fsSIL", "--max-time", "6", "https://login.tailscale.com"], timeout=8)
    if not internet_cmd["available"]:
        internet_cmd = run_command(["ping", "-c", "1", "-W", "3", "1.1.1.1"], timeout=5)
    details["internet_ok"] = internet_cmd["ok"]

    if not details["connected"]:
        status = "fail"
        message = "Wi-Fi bagli degil."
        actions.extend([
            "Ana ekrandan Wi-Fi Ayarlari sayfasina girip agi tara ve sifreyle baglan.",
            "Mumkunse 2.4 GHz ag kullan; Pi Zero 2 W 5 GHz aglari gormez.",
            "Kurulumda telefon hotspot ile hizli dogrulama yapilabilir.",
        ])
    elif not details["ip"]:
        status = "fail"
        message = "Wi-Fi bagli gorunuyor ama IP alinmamis."
        actions.extend([
            "Modem DHCP ayarini kontrol edin.",
            "Wi-Fi baglantisini kesip tekrar baglanin veya cihazi yeniden baslatin.",
        ])
    elif details["signal"] is not None and details["signal"] < 35:
        status = "warn"
        message = f"Wi-Fi sinyali zayif: %{details['signal']}."
        actions.append("Cihazi modeme yaklastirin veya daha guclu 2.4 GHz ag/mesh kullanin.")
    elif not details["internet_ok"]:
        status = "warn"
        message = "Yerel ag bagli ama internet/Tailscale girisi dogrulanamadi."
        actions.extend([
            "Klinik aginda internet cikisi ve DNS engeli olup olmadigini kontrol edin.",
            "Tailscale girisi icin captive portal varsa once tarayicidan giris yapin.",
        ])
    else:
        status = "ok"
        message = f"Wi-Fi bagli: {details['ssid']} ({details['ip']})."

    return {
        "key": "wifi",
        "status": status,
        "title": "Wi-Fi ve internet",
        "message": message,
        "details": details,
        "actions": actions,
    }


def collect_tailscale_status() -> dict[str, Any]:
    """Collect Tailscale installation and connection diagnostics."""
    actions: list[str] = []
    if not shutil.which("tailscale"):
        return {
            "key": "tailscale",
            "status": "fail",
            "title": "Tailscale",
            "message": "Tailscale kurulu degil.",
            "details": {"installed": False},
            "actions": [
                "Web arayuzunde Uzaktan Erisim sayfasindan Tailscale'i Kur butonunu kullanin.",
                "Komut satirindan: make tailscale-install && make tailscale-up",
            ],
        }

    service_cmd = run_command(["systemctl", "is-active", "tailscaled"], timeout=5)
    service_active = service_cmd["ok"] and service_cmd["stdout"] == "active"
    if not service_active:
        return {
            "key": "tailscale",
            "status": "fail",
            "title": "Tailscale",
            "message": "tailscaled servisi calismiyor.",
            "details": {
                "installed": True,
                "service_active": False,
                "service_output": service_cmd["stdout"] or service_cmd["stderr"],
            },
            "actions": [
                "sudo systemctl enable --now tailscaled komutunu calistirin.",
                "Ardindan web arayuzunden Uzaktan Erisim > Baglanti Kur adimini uygulayin.",
            ],
        }

    status_cmd = run_command(["tailscale", "status", "--json"], timeout=20)
    if not status_cmd["ok"]:
        return {
            "key": "tailscale",
            "status": "warn",
            "title": "Tailscale",
            "message": "Tailscale durumu okunamadi.",
            "details": {
                "installed": True,
                "service_active": True,
                "error": status_cmd["stderr"] or status_cmd["stdout"],
            },
            "actions": ["sudo tailscale up komutunu veya web QR akisini tekrar deneyin."],
        }

    try:
        status_data = json.loads(status_cmd["stdout"])
    except json.JSONDecodeError:
        return {
            "key": "tailscale",
            "status": "warn",
            "title": "Tailscale",
            "message": "Tailscale JSON ciktisi okunamadi.",
            "details": {"raw": status_cmd["stdout"][:500]},
            "actions": ["tailscale status komut ciktisini kontrol edin."],
        }

    backend_state = status_data.get("BackendState", "Unknown")
    self_info = status_data.get("Self") or {}
    ips = self_info.get("TailscaleIPs") or []
    hostname = self_info.get("HostName")

    if backend_state == "Running" and ips:
        status = "ok"
        message = f"Tailscale bagli: {ips[0]}."
    elif backend_state in {"NeedsLogin", "Stopped", "NoState"}:
        status = "fail"
        message = "Tailscale giris/onay bekliyor."
        actions.extend([
            "Uzaktan Erisim sayfasinda Baglanti Kur butonuna basin.",
            "Cikan QR/link ile Tailscale hesabinda cihazi onaylayin.",
        ])
    else:
        status = "warn"
        message = f"Tailscale durumu: {backend_state}."
        actions.append("tailscale status ve journalctl -u tailscaled ciktisini kontrol edin.")

    return {
        "key": "tailscale",
        "status": status,
        "title": "Tailscale",
        "message": message,
        "details": {
            "installed": True,
            "service_active": True,
            "state": backend_state,
            "ips": ips,
            "hostname": hostname,
        },
        "actions": actions,
    }


def collect_service_status() -> dict[str, Any]:
    """Collect Kuvoz service and disk health diagnostics."""
    services = {}
    for service in ("kuvoz-web", "kuvoz-kiosk"):
        cmd = run_command(["systemctl", "is-active", service], timeout=5)
        services[service] = {
            "active": cmd["ok"] and cmd["stdout"] == "active",
            "state": cmd["stdout"] or cmd["stderr"],
        }

    disk = shutil.disk_usage("/")
    disk_used_percent = round((disk.used / disk.total) * 100, 1)
    details = {
        "services": services,
        "disk_used_percent": disk_used_percent,
        "disk_free_gb": round(disk.free / (1024 ** 3), 2),
    }
    actions: list[str] = []

    if disk_used_percent >= 95:
        status = "fail"
        message = f"Disk dolu: %{disk_used_percent}."
        actions.append("make disk-clean komutunu calistirin; gerekirse loglari temizleyin.")
    elif disk_used_percent >= 85:
        status = "warn"
        message = f"Disk kullanimi yuksek: %{disk_used_percent}."
        actions.append("Kurulum bitmeden make disk-clean ile alan acin.")
    elif not services["kuvoz-web"]["active"]:
        status = "fail"
        message = "kuvoz-web servisi calismiyor."
        actions.append("sudo systemctl restart kuvoz-web && sudo journalctl -u kuvoz-web -n 80 komutlarini kontrol edin.")
    elif not services["kuvoz-kiosk"]["active"]:
        status = "warn"
        message = "Web servisi calisiyor, kiosk servisi aktif degil."
        actions.append("Dokunmatik ekranda otomatik acilis isteniyorsa sudo systemctl restart kuvoz-kiosk calistirin.")
    else:
        status = "ok"
        message = "Kuvoz servisleri ve disk durumu iyi."

    return {
        "key": "services",
        "status": status,
        "title": "Servisler ve disk",
        "message": message,
        "details": details,
        "actions": actions,
    }


def collect_field_diagnostics() -> dict[str, Any]:
    """Collect all field setup diagnostics."""
    checks = [
        collect_power_status(),
        collect_performance_status(),
        collect_wifi_status(),
        collect_tailscale_status(),
        collect_service_status(),
    ]

    worst_status = "ok"
    for check in checks:
        if STATUS_ORDER.get(check["status"], 1) > STATUS_ORDER.get(worst_status, 0):
            worst_status = check["status"]

    summary_messages = {
        "ok": "Saha kurulumu temel kontrollerden gecti.",
        "warn": "Kurulum calisir durumda olabilir, fakat sahada takip gerektiren uyari var.",
        "fail": "Kurulum tamamlanmadan once kritik sorun giderilmeli.",
        "unknown": "Bazi kontroller bu ortamda calistirilamadi.",
    }

    return {
        "timestamp": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "hostname": socket.gethostname(),
        "overall_status": worst_status,
        "summary": summary_messages.get(worst_status, summary_messages["unknown"]),
        "checks": checks,
    }
