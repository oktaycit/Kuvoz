#!/usr/bin/env python3
"""Print Kuvoz field setup diagnostics."""

from __future__ import annotations

import argparse
import json
import os
import sys


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.services.field_diagnostics import collect_field_diagnostics  # noqa: E402


STATUS_ICONS = {
    "ok": "OK",
    "warn": "UYARI",
    "fail": "HATA",
    "unknown": "BILINMIYOR",
}


def print_check(check: dict) -> None:
    status = check.get("status", "unknown")
    label = STATUS_ICONS.get(status, status.upper())
    print(f"[{label}] {check.get('title', 'Kontrol')}: {check.get('message', '')}")

    details = check.get("details") or {}
    if check.get("key") == "power":
        raw = details.get("raw")
        temp_c = details.get("temperature_c")
        volts = details.get("core_volts")
        flags = details.get("flag_labels") or []
        if raw:
            print(f"  - Throttled: {raw}")
        if temp_c is not None:
            print(f"  - Sicaklik: {temp_c} C")
        if volts is not None:
            print(f"  - Core voltaj: {volts} V")
        if flags:
            print(f"  - Bayraklar: {', '.join(flags)}")

    if check.get("key") == "wifi":
        if details.get("ssid"):
            print(f"  - SSID: {details.get('ssid')}")
        if details.get("ip"):
            print(f"  - IP: {details.get('ip')}")
        if details.get("signal") is not None:
            print(f"  - Sinyal: %{details.get('signal')}")
        print(f"  - DNS: {'OK' if details.get('dns_ok') else 'HATA'}")
        print(f"  - Internet: {'OK' if details.get('internet_ok') else 'HATA'}")

    if check.get("key") == "performance":
        load = details.get("load_average") or {}
        if details.get("model"):
            print(f"  - Model: {details.get('model')}")
        if load:
            print(f"  - Yuk: {load.get('1m')} / {load.get('5m')} / {load.get('15m')}")
        if details.get("load_1m_per_core") is not None:
            print(f"  - Yuk/cekirdek: {details.get('load_1m_per_core')}")
        if details.get("memory_used_percent") is not None:
            print(f"  - Bellek: %{details.get('memory_used_percent')} dolu, {details.get('memory_available_mb')} MB bos")
        if details.get("swap_used_percent") is not None:
            print(f"  - Swap: %{details.get('swap_used_percent')} dolu, {details.get('swap_used_mb')} MB kullaniliyor")
        if details.get("uptime"):
            print(f"  - Uptime: {details.get('uptime')}")

    if check.get("key") == "tailscale":
        if details.get("state"):
            print(f"  - Durum: {details.get('state')}")
        if details.get("ips"):
            print(f"  - IP: {', '.join(details.get('ips'))}")

    if check.get("key") == "services":
        services = details.get("services") or {}
        for name, info in services.items():
            print(f"  - {name}: {info.get('state')}")
        if details.get("disk_used_percent") is not None:
            print(f"  - Disk: %{details.get('disk_used_percent')} dolu, {details.get('disk_free_gb')} GB bos")

    actions = check.get("actions") or []
    if actions:
        print("  Aksiyon:")
        for action in actions:
            print(f"    - {action}")
    print("")


def main() -> int:
    parser = argparse.ArgumentParser(description="Kuvoz saha kurulum kontrolu")
    parser.add_argument("--json", action="store_true", help="Makine okunabilir JSON ciktisi ver")
    args = parser.parse_args()

    diagnostics = collect_field_diagnostics()
    if args.json:
        print(json.dumps(diagnostics, ensure_ascii=False, indent=2))
        return 0 if diagnostics["overall_status"] != "fail" else 2

    print("Kuvoz Saha Kurulum Kontrolu")
    print("===========================")
    print(f"Hostname: {diagnostics.get('hostname')}")
    print(f"Ozet: {diagnostics.get('summary')}")
    print("")

    for check in diagnostics.get("checks", []):
        print_check(check)

    if diagnostics["overall_status"] == "fail":
        print("Sonuc: Kritik sorun var. Kurulum tamamlandi sayilmasin.")
        return 2
    if diagnostics["overall_status"] == "warn":
        print("Sonuc: Calisir durumda olabilir; uyari aksiyonlarini sahada kapatin.")
        return 1

    print("Sonuc: Saha kurulumu icin temel kontroller temiz.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
