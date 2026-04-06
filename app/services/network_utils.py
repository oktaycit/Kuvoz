"""Network helper functions shared across Kuvoz services and routes."""

from __future__ import annotations

import re
import socket
import subprocess


def get_all_ips():
    """Get all local interface IPv4 addresses as a dictionary."""
    ips = {}
    try:
        result = subprocess.run(
            ['nmcli', '-t', '-f', 'DEVICE,IP4.ADDRESS', 'dev', 'show'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            device = None
            for line in result.stdout.split('\n'):
                if not line:
                    continue
                if ': ' not in line and ':' in line:
                    parts = line.split(':')
                    if parts[0] == 'GENERAL.DEVICE':
                        device = parts[1]
                    elif parts[0] == 'IP4.ADDRESS[1]':
                        ip = parts[1].split('/')[0]
                        if device:
                            ips[device] = ip

        if not ips:
            result = subprocess.run(
                ['ip', '-4', '-o', 'addr', 'show'],
                capture_output=True,
                text=True,
                timeout=5
            )
            for line in result.stdout.split('\n'):
                match = re.search(r'\d+:\s+(\w+).*inet\s+([\d\.]+)', line)
                if match and match.group(1) != 'lo':
                    ips[match.group(1)] = match.group(2)
    except Exception:
        pass
    return ips


def get_local_ip():
    """Get the primary local network IP address (prefers ethernet then wifi)."""
    try:
        ips = get_all_ips()
        if 'eth0' in ips:
            return ips['eth0']
        if 'wlan0' in ips:
            return ips['wlan0']
        if 'tailscale0' in ips:
            return ips['tailscale0']

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        local_ip = sock.getsockname()[0]
        sock.close()
        return local_ip
    except Exception:
        return "127.0.0.1"
