"""Hostname management helpers for device identity and Tailscale naming."""

from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import sys
from typing import Callable, Optional


HOSTNAME_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
RESERVED_HOSTNAMES = {"localhost", "localhost.localdomain"}

HOSTS_UPDATE_SCRIPT = r"""
from pathlib import Path
import sys

hostname = sys.argv[1]
path = Path("/etc/hosts")
lines = path.read_text(encoding="utf-8").splitlines()
updated = []
found = False

for line in lines:
    stripped = line.strip()
    fields = stripped.split()
    if fields and fields[0] == "127.0.1.1" and (not stripped.startswith("#")):
        if not found:
            updated.append(f"127.0.1.1\t{hostname}")
            found = True
        continue
    updated.append(line)

if not found:
    if updated and updated[-1].strip():
        updated.append("")
    updated.append(f"127.0.1.1\t{hostname}")

path.write_text("\n".join(updated) + "\n", encoding="utf-8")
"""


Runner = Callable[..., subprocess.CompletedProcess]
CommandExists = Callable[[str], Optional[str]]


def normalize_hostname(value) -> str:
    """Normalize user-facing hostname input without guessing unsafe characters."""
    return str(value or "").strip().lower()


def validate_hostname(value):
    """Validate a single-label Linux/Tailscale-friendly hostname."""
    hostname = normalize_hostname(value)
    if not hostname:
        return False, hostname, "Hostname boş olamaz."
    if hostname in RESERVED_HOSTNAMES:
        return False, hostname, "Bu hostname sistem tarafından ayrılmış."
    if "." in hostname:
        return False, hostname, "Nokta kullanmadan tek parça bir cihaz adı girin."
    if hostname.isdigit():
        return False, hostname, "Hostname sadece rakamlardan oluşamaz."
    if not HOSTNAME_PATTERN.match(hostname):
        return (
            False,
            hostname,
            "Hostname küçük harf, rakam ve tire içerebilir; tire ile başlayıp bitemez.",
        )
    return True, hostname, None


def _default_use_sudo() -> bool:
    geteuid = getattr(os, "geteuid", None)
    return bool(geteuid and geteuid() != 0)


def _with_sudo(command: list[str], *, use_sudo: Optional[bool] = None) -> list[str]:
    if use_sudo is None:
        use_sudo = _default_use_sudo()
    return ["sudo", *command] if use_sudo else command


def _run(
    command: list[str],
    *,
    runner: Runner = subprocess.run,
    timeout: int = 10,
):
    return runner(
        command,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=timeout,
    )


def _command_message(result: subprocess.CompletedProcess) -> str:
    return (result.stderr or result.stdout or "").strip()


def get_system_hostname(
    *,
    runner: Runner = subprocess.run,
    command_exists: CommandExists = shutil.which,
) -> str:
    """Read the current OS hostname with safe fallbacks for dev machines."""
    try:
        if command_exists("hostnamectl"):
            result = _run(["hostnamectl", "--static"], runner=runner, timeout=3)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().split(".", 1)[0]
    except Exception:
        pass

    try:
        return socket.gethostname().strip().split(".", 1)[0] or "kuvoz"
    except Exception:
        return "kuvoz"


def get_tailscale_machine_info(
    *,
    runner: Runner = subprocess.run,
    command_exists: CommandExists = shutil.which,
    timeout: int = 5,
) -> dict:
    """Read Tailscale machine name if the CLI is installed and responsive."""
    if not command_exists("tailscale"):
        return {"installed": False}

    try:
        result = _run(["tailscale", "status", "--json"], runner=runner, timeout=timeout)
    except Exception as exc:
        return {"installed": True, "success": False, "message": str(exc)}

    if result.returncode != 0:
        return {
            "installed": True,
            "success": False,
            "message": _command_message(result) or "Tailscale durumu okunamadı.",
        }

    try:
        status = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return {
            "installed": True,
            "success": False,
            "message": "Tailscale JSON çıktısı okunamadı.",
        }

    self_info = status.get("Self") or {}
    return {
        "installed": True,
        "success": True,
        "state": status.get("BackendState", "Unknown"),
        "hostname": self_info.get("HostName"),
        "dns_name": (self_info.get("DNSName") or "").rstrip("."),
        "ips": self_info.get("TailscaleIPs") or [],
    }


def get_hostname_status(
    *,
    include_tailscale: bool = False,
    runner: Runner = subprocess.run,
    command_exists: CommandExists = shutil.which,
) -> dict:
    status = {
        "hostname": get_system_hostname(runner=runner, command_exists=command_exists),
    }
    if include_tailscale:
        status["tailscale"] = get_tailscale_machine_info(
            runner=runner,
            command_exists=command_exists,
        )
    return status


def update_hosts_file(
    hostname: str,
    *,
    runner: Runner = subprocess.run,
    use_sudo: Optional[bool] = None,
) -> subprocess.CompletedProcess:
    command = [sys.executable, "-c", HOSTS_UPDATE_SCRIPT, hostname]
    return _run(_with_sudo(command, use_sudo=use_sudo), runner=runner, timeout=10)


def set_tailscale_hostname(
    hostname: str,
    *,
    runner: Runner = subprocess.run,
    command_exists: CommandExists = shutil.which,
    use_sudo: Optional[bool] = None,
) -> dict:
    if not command_exists("tailscale"):
        return {
            "attempted": False,
            "installed": False,
            "success": True,
            "message": "Tailscale kurulu değil; yalnızca sistem hostname değiştirildi.",
        }

    result = _run(
        _with_sudo(["tailscale", "set", f"--hostname={hostname}"], use_sudo=use_sudo),
        runner=runner,
        timeout=20,
    )
    if result.returncode != 0:
        return {
            "attempted": True,
            "installed": True,
            "success": False,
            "message": _command_message(result) or "Tailscale makine adı güncellenemedi.",
        }

    return {
        "attempted": True,
        "installed": True,
        "success": True,
        "hostname": hostname,
        "message": "Tailscale makine adı güncellendi.",
    }


def set_device_hostname(
    hostname,
    *,
    update_tailscale: bool = True,
    runner: Runner = subprocess.run,
    command_exists: CommandExists = shutil.which,
    use_sudo: Optional[bool] = None,
) -> dict:
    """Set OS hostname, /etc/hosts mapping and optionally Tailscale name."""
    valid, normalized, error = validate_hostname(hostname)
    if not valid:
        return {"success": False, "message": error, "hostname": normalized}

    previous_hostname = get_system_hostname(
        runner=runner,
        command_exists=command_exists,
    )
    changed = previous_hostname != normalized

    if changed:
        if not command_exists("hostnamectl"):
            return {
                "success": False,
                "message": "hostnamectl bulunamadı; hostname değiştirilemedi.",
                "hostname": previous_hostname,
                "requested_hostname": normalized,
            }

        host_result = _run(
            _with_sudo(["hostnamectl", "set-hostname", normalized], use_sudo=use_sudo),
            runner=runner,
            timeout=15,
        )
        if host_result.returncode != 0:
            return {
                "success": False,
                "message": _command_message(host_result) or "Hostname güncellenemedi.",
                "hostname": previous_hostname,
                "requested_hostname": normalized,
            }

        hosts_result = update_hosts_file(
            normalized,
            runner=runner,
            use_sudo=use_sudo,
        )
        if hosts_result.returncode != 0:
            return {
                "success": False,
                "partial_success": True,
                "message": (
                    "Hostname değişti ancak /etc/hosts güncellenemedi: "
                    f"{_command_message(hosts_result) or 'Bilinmeyen hata'}"
                ),
                "hostname": normalized,
                "previous_hostname": previous_hostname,
            }

    tailscale_result = {
        "attempted": False,
        "success": True,
        "message": "Tailscale eşitlemesi istenmedi.",
    }
    if update_tailscale:
        tailscale_result = set_tailscale_hostname(
            normalized,
            runner=runner,
            command_exists=command_exists,
            use_sudo=use_sudo,
        )

    success = bool(tailscale_result.get("success", True))
    if success:
        message = (
            f"Hostname {previous_hostname} → {normalized} olarak güncellendi."
            if changed
            else f"Hostname zaten {normalized}; Tailscale adı eşitlendi."
        )
    else:
        message = (
            f"Linux hostname {normalized} olarak ayarlandı; "
            f"Tailscale adı güncellenemedi: {tailscale_result.get('message')}"
        )

    return {
        "success": success,
        "partial_success": changed and not success,
        "message": message,
        "hostname": normalized,
        "previous_hostname": previous_hostname,
        "changed": changed,
        "tailscale": tailscale_result,
        "restart_recommended": False,
    }
