"""Small, standalone helpers for Kuvoz settings persistence.

This module is intentionally independent from the Flask server so it can be
reused by future refactors or tests without importing the full runtime.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

DEFAULT_SETTINGS_FILENAME = "failure.dat"


@dataclass
class SettingsLoadResult:
    """Result wrapper for safe settings loading."""

    data: Dict[str, Any] = field(default_factory=dict)
    path: Path = Path()
    source: str = "missing"
    errors: List[str] = field(default_factory=list)
    is_json: bool = False
    is_empty: bool = False
    is_case_mismatch: bool = False

    @property
    def ok(self) -> bool:
        return self.is_json and not self.errors


@dataclass
class SettingsWriteResult:
    """Result wrapper for safe settings saving."""

    path: Path
    success: bool
    errors: List[str] = field(default_factory=list)


PathLikeOrStr = Union[str, os.PathLike[str]]


def _coerce_base_dir(base_dir: Optional[PathLikeOrStr]) -> Path:
    if base_dir is None:
        return Path.cwd()
    return Path(base_dir)


def resolve_settings_path(
    base_dir: Optional[PathLikeOrStr] = None,
    filename: str = DEFAULT_SETTINGS_FILENAME,
) -> Path:
    """Return the canonical settings path used by the app."""

    return _coerce_base_dir(base_dir) / filename


def find_case_insensitive_filename_matches(
    base_dir: Optional[PathLikeOrStr] = None,
    expected_filename: str = DEFAULT_SETTINGS_FILENAME,
) -> List[Path]:
    """Find files whose name matches the expected settings file case-insensitively."""

    directory = _coerce_base_dir(base_dir)
    if not directory.exists() or not directory.is_dir():
        return []

    expected_lower = expected_filename.lower()
    matches: List[Path] = []
    for entry in directory.iterdir():
        if entry.is_file() and entry.name.lower() == expected_lower:
            matches.append(entry)
    return matches


def detect_case_mismatch(
    base_dir: Optional[PathLikeOrStr] = None,
    expected_filename: str = DEFAULT_SETTINGS_FILENAME,
) -> Dict[str, Any]:
    """Detect case-sensitive filename drift such as `Failure.dat` vs `failure.dat`."""

    canonical = resolve_settings_path(base_dir, expected_filename)
    matches = find_case_insensitive_filename_matches(base_dir, expected_filename)
    exact_exists = canonical.exists()
    return {
        "expected": canonical,
        "exact_exists": exact_exists,
        "matches": matches,
        "has_mismatch": bool(matches) and not exact_exists,
        "unexpected_variants": [path for path in matches if path.name != expected_filename],
    }


def resolve_existing_settings_path(
    base_dir: Optional[PathLikeOrStr] = None,
    filename: str = DEFAULT_SETTINGS_FILENAME,
) -> Path:
    """Return the best existing settings path, falling back to case-insensitive matches."""

    canonical = resolve_settings_path(base_dir, filename)
    if canonical.exists():
        return canonical

    matches = find_case_insensitive_filename_matches(base_dir, filename)
    if len(matches) == 1:
        return matches[0]

    return canonical


def load_settings_json(
    path: Optional[PathLikeOrStr] = None,
    *,
    base_dir: Optional[PathLikeOrStr] = None,
    filename: str = DEFAULT_SETTINGS_FILENAME,
) -> SettingsLoadResult:
    """Safely load JSON settings from disk.

    Empty files, missing files, malformed JSON, or non-dict payloads are treated
    as non-fatal and reported through the result object.
    """

    resolved = Path(path) if path is not None else resolve_existing_settings_path(base_dir, filename)
    result = SettingsLoadResult(path=resolved)

    if not resolved.exists():
        result.errors.append("missing_file")
        return result

    try:
        raw = resolved.read_text(encoding="utf-8").strip()
    except OSError as exc:
        result.errors.append(f"os_error: {exc}")
        return result

    if not raw:
        result.is_empty = True
        result.errors.append("empty_file")
        return result

    if not raw.startswith("{"):
        result.errors.append("non_json_content")
        return result

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        result.errors.append(f"json_decode_error: {exc}")
        return result

    if not isinstance(parsed, dict):
        result.errors.append("json_root_not_object")
        return result

    result.data = parsed
    result.is_json = True
    mismatch = detect_case_mismatch(resolved.parent, resolved.name)
    result.is_case_mismatch = bool(mismatch["has_mismatch"])
    if result.is_case_mismatch:
        result.errors.append("case_mismatch_detected")
    return result


def save_settings_json(
    data: Dict[str, Any],
    path: Optional[PathLikeOrStr] = None,
    *,
    base_dir: Optional[PathLikeOrStr] = None,
    filename: str = DEFAULT_SETTINGS_FILENAME,
    indent: int = 4,
) -> SettingsWriteResult:
    """Safely write JSON settings to disk."""

    resolved = Path(path) if path is not None else resolve_settings_path(base_dir, filename)
    errors: List[str] = []

    try:
        resolved.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return SettingsWriteResult(path=resolved, success=False, errors=[f"mkdir_error: {exc}"])

    try:
        payload = json.dumps(data, indent=indent, ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        return SettingsWriteResult(path=resolved, success=False, errors=[f"json_encode_error: {exc}"])

    tmp_path = resolved.with_name(f".{resolved.name}.tmp")
    try:
        tmp_path.write_text(payload, encoding="utf-8")
        tmp_path.replace(resolved)
    except OSError as exc:
        errors.append(f"os_error: {exc}")
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass
        return SettingsWriteResult(path=resolved, success=False, errors=errors)

    return SettingsWriteResult(path=resolved, success=True, errors=[])


def find_settings_name_ttl(
    base_dir: Optional[PathLikeOrStr] = None,
    expected_filename: str = DEFAULT_SETTINGS_FILENAME,
) -> Dict[str, Any]:
    """Compatibility helper for callers that want a compact status summary.

    The name is intentionally generic enough to support future use in the UI or
    diagnostics without coupling to the server internals.
    """

    mismatch = detect_case_mismatch(base_dir, expected_filename)
    return {
        "expected": str(mismatch["expected"]),
        "exact_exists": mismatch["exact_exists"],
        "has_mismatch": mismatch["has_mismatch"],
        "unexpected_variants": [str(path) for path in mismatch["unexpected_variants"]],
    }
