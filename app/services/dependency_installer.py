"""Dependency installation helpers for UI-triggered maintenance."""

from __future__ import annotations

import os
import platform
import shlex
import sys
from dataclasses import dataclass
from typing import Iterable, List, Optional


CORE_PIP_PACKAGES = [
    "flask",
    "flask-socketio",
    "eventlet",
    "qrcode[pil]",
    "pillow",
    "reportlab",
]

CORE_APT_PACKAGES = [
    "python3-flask",
    "python3-flask-socketio",
    "python3-eventlet",
    "python3-qrcode",
    "python3-pil",
    "python3-reportlab",
    "python3-smbus",
    "python3-smbus2",
    "python3-rpi.gpio",
]


@dataclass(frozen=True)
class DependencyInstallStep:
    """A fixed command step used by the maintenance UI."""

    name: str
    message: str
    command: List[str]
    timeout: int = 600


@dataclass(frozen=True)
class DependencyInstallPlan:
    """Primary pip install plus an optional Linux system-package fallback."""

    primary: DependencyInstallStep
    fallback: Optional[DependencyInstallStep]
    requirements_path: str
    uses_requirements: bool


def build_dependency_install_plan(
    script_dir: str,
    *,
    python_executable: Optional[str] = None,
    platform_system: Optional[str] = None,
) -> DependencyInstallPlan:
    """Build the fixed dependency installation plan for the current project."""

    py = python_executable or sys.executable
    requirements_path = os.path.join(script_dir, "requirements.txt")
    uses_requirements = os.path.exists(requirements_path)

    if uses_requirements:
        primary_command = [
            py,
            "-m",
            "pip",
            "install",
            "-r",
            requirements_path,
            "--break-system-packages",
        ]
        primary_message = "Python bağımlılıkları requirements.txt üzerinden kuruluyor..."
    else:
        primary_command = [
            py,
            "-m",
            "pip",
            "install",
            *CORE_PIP_PACKAGES,
            "--break-system-packages",
        ]
        primary_message = "Temel Python bağımlılıkları kuruluyor..."

    system_name = platform_system or platform.system()
    fallback = None
    if system_name == "Linux":
        fallback = DependencyInstallStep(
            name="apt_core_packages",
            message="Pip kurulumu başarısız oldu; sistem paketleri deneniyor...",
            command=[
                "sudo",
                "-n",
                "env",
                "DEBIAN_FRONTEND=noninteractive",
                "apt-get",
                "install",
                "-y",
                *CORE_APT_PACKAGES,
            ],
            timeout=600,
        )

    return DependencyInstallPlan(
        primary=DependencyInstallStep(
            name="pip_requirements" if uses_requirements else "pip_core_packages",
            message=primary_message,
            command=primary_command,
            timeout=600,
        ),
        fallback=fallback,
        requirements_path=requirements_path,
        uses_requirements=uses_requirements,
    )


def command_to_text(command: Iterable[str]) -> str:
    """Render a command safely for logs and diagnostics."""

    return " ".join(shlex.quote(str(part)) for part in command)


def summarize_process_output(stdout, stderr, *, max_chars: int = 5000) -> str:
    """Return a compact tail of subprocess output for UI diagnostics."""

    parts = []
    for value in (stdout, stderr):
        if value is None:
            continue
        if isinstance(value, bytes):
            value = value.decode("utf-8", errors="replace")
        value = str(value).strip()
        if value:
            parts.append(value)

    text = "\n".join(parts).strip()
    if len(text) <= max_chars:
        return text
    return "...\n" + text[-max_chars:]
