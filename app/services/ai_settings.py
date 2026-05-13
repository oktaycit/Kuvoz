"""AI settings normalization helpers."""

from __future__ import annotations


TRUE_VALUES = {"1", "true", "yes", "on", "enabled"}
FALSE_VALUES = {"0", "false", "no", "off", "disabled", ""}


def normalize_ai_enabled_value(value) -> bool:
    """Return a predictable boolean for persisted or socket AI toggle values."""
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in TRUE_VALUES:
            return True
        if normalized in FALSE_VALUES:
            return False
    return bool(value)


def resolve_ai_enabled_preference(settings_data, default=False):
    """Resolve the persisted AI enabled flag from legacy and system settings.

    Root-level ``ai_enabled`` is canonical because it represents the runtime
    state written by ``save_settings``. ``system_settings.ai_enabled`` is kept as
    a mirrored UI field and used only for backward compatibility when the root
    key is absent.
    """
    data = settings_data if isinstance(settings_data, dict) else {}
    system_settings = data.get("system_settings")
    if not isinstance(system_settings, dict):
        system_settings = {}

    has_root = "ai_enabled" in data
    has_system = "ai_enabled" in system_settings
    root_value = normalize_ai_enabled_value(data.get("ai_enabled")) if has_root else None
    system_value = (
        normalize_ai_enabled_value(system_settings.get("ai_enabled"))
        if has_system
        else None
    )

    if has_root:
        return root_value, "ai_enabled", has_system and root_value != system_value
    if has_system:
        return system_value, "system_settings.ai_enabled", False
    return normalize_ai_enabled_value(default), "default", False
