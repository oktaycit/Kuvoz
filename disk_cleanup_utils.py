#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Disk temizleme akışı için ortak yardımcılar."""

import subprocess
from typing import Any, Dict, List, Optional, Sequence


DEFAULT_DISK_CLEAN_COMMAND = ["make", "disk-clean"]


def _safe_record_count(logger_obj: Any) -> int:
    if not logger_obj or not hasattr(logger_obj, "get_record_count"):
        return 0

    try:
        return max(0, int(logger_obj.get_record_count() or 0))
    except Exception:
        return 0


def _join_human(parts: List[str]) -> str:
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    return f"{', '.join(parts[:-1])} ve {parts[-1]}"


def _first_line(text: Any) -> str:
    if text is None:
        return ""

    compact = " ".join(str(text).strip().splitlines())
    return compact[:200]


def _clear_logger_group(
    key: str,
    deleted_label: str,
    error_label: str,
    logger_obj: Any,
    reason: str,
    trigger: str,
) -> Dict[str, Any]:
    result = {
        "key": key,
        "deleted_label": deleted_label,
        "error_label": error_label,
        "available": bool(logger_obj),
        "attempted": False,
        "success": True,
        "deleted_records": 0,
        "before_count": 0,
        "after_count": 0,
        "error": "",
    }

    if not logger_obj:
        return result

    result["attempted"] = True
    result["before_count"] = _safe_record_count(logger_obj)

    try:
        clear_ok = bool(
            logger_obj.clear_all_data(
                reason=reason,
                context={"trigger": trigger},
            )
        )
        result["after_count"] = _safe_record_count(logger_obj)
        result["success"] = clear_ok
        if clear_ok:
            result["deleted_records"] = max(
                0,
                result["before_count"] - result["after_count"],
            )
        else:
            result["error"] = f"{error_label} silinemedi"
    except Exception as exc:
        result["success"] = False
        result["error"] = str(exc)

    return result


def build_disk_cleanup_message(result: Dict[str, Any]) -> str:
    system_cleanup = result.get("system_cleanup", {})
    application_cleanup = result.get("application_cleanup", {})
    groups = application_cleanup.get("groups", [])

    system_success = bool(system_cleanup.get("success"))
    app_success = bool(application_cleanup.get("success"))

    deleted_parts = [
        f"{group['deleted_records']} {group['deleted_label']}"
        for group in groups
        if group.get("attempted") and group.get("success") and group.get("deleted_records", 0) > 0
    ]
    attempted_groups = [group for group in groups if group.get("attempted")]
    failed_labels = [
        group.get("error_label", group.get("key", "loglar"))
        for group in groups
        if group.get("attempted") and not group.get("success")
    ]
    system_error = _first_line(system_cleanup.get("error") or system_cleanup.get("stderr"))

    if system_success and app_success:
        if deleted_parts:
            return f"Disk temizliği tamamlandı. {_join_human(deleted_parts)} silindi."
        if attempted_groups:
            return "Disk temizliği tamamlandı. Uygulama logları zaten boştu."
        return "Disk temizliği tamamlandı."

    if system_success and not app_success:
        return (
            "Sistem temizliği tamamlandı ancak "
            f"{_join_human(failed_labels)} temizlenemedi."
        )

    if not system_success and app_success:
        if attempted_groups:
            return (
                "Uygulama logları temizlendi ancak sistem temizliği başarısız oldu: "
                f"{system_error or 'bilinmeyen hata'}"
            )
        return f"Sistem temizliği başarısız oldu: {system_error or 'bilinmeyen hata'}"

    problems: List[str] = []
    if failed_labels:
        problems.append(f"{_join_human(failed_labels)} temizlenemedi")
    if system_success is False:
        problems.append(f"sistem temizliği başarısız oldu: {system_error or 'bilinmeyen hata'}")

    return f"Disk temizliği tamamlanamadı. {' '.join(problems).strip()}".strip()


def perform_disk_cleanup(
    sensor_logger: Any = None,
    ai_vitals_logger: Any = None,
    command: Optional[Sequence[str]] = None,
    runner: Any = None,
    timeout: int = 300,
    reason: str = "disk_cleanup",
    trigger: str = "settings_disk_cleanup",
) -> Dict[str, Any]:
    command = list(command or DEFAULT_DISK_CLEAN_COMMAND)
    runner = runner or subprocess.run

    groups = [
        _clear_logger_group(
            key="sensor_logs",
            deleted_label="sensör logu",
            error_label="sensör logları",
            logger_obj=sensor_logger,
            reason=reason,
            trigger=trigger,
        ),
        _clear_logger_group(
            key="ai_vitals",
            deleted_label="AI vital kaydı",
            error_label="AI vital kayıtları",
            logger_obj=ai_vitals_logger,
            reason=reason,
            trigger=trigger,
        ),
    ]

    app_cleanup = {
        "groups": groups,
        "success": all(group.get("success") for group in groups),
        "deleted_records_total": sum(group.get("deleted_records", 0) for group in groups),
    }

    system_cleanup = {
        "command": command,
        "success": False,
        "returncode": None,
        "stdout": "",
        "stderr": "",
        "error": "",
    }

    try:
        completed = runner(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        system_cleanup["returncode"] = getattr(completed, "returncode", None)
        system_cleanup["stdout"] = getattr(completed, "stdout", "") or ""
        system_cleanup["stderr"] = getattr(completed, "stderr", "") or ""
        system_cleanup["success"] = system_cleanup["returncode"] == 0
        if not system_cleanup["success"]:
            system_cleanup["error"] = _first_line(system_cleanup["stderr"] or system_cleanup["stdout"])
    except subprocess.TimeoutExpired as exc:
        system_cleanup["error"] = f"komut zaman aşımına uğradı ({timeout}s)"
        system_cleanup["stderr"] = _first_line(getattr(exc, "stderr", "") or getattr(exc, "stdout", ""))
    except Exception as exc:
        system_cleanup["error"] = str(exc)

    result = {
        "success": bool(app_cleanup["success"] and system_cleanup["success"]),
        "application_cleanup": app_cleanup,
        "system_cleanup": system_cleanup,
    }
    result["message"] = build_disk_cleanup_message(result)
    return result
