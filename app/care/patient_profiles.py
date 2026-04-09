"""Patient care profile helpers.

This module contains the pure logic used to convert patient age strings into
weeks and to derive environment targets for automatic care mode.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional


CAT_TOKENS = ("kedi", "cat", "katze")
DOG_TOKENS = ("kopek", "köpek", "dog", "hund")
BIRD_TOKENS = ("kus", "kuş", "bird", "vogel")


def parse_age_weeks(raw: Any) -> Optional[float]:
    """Convert a human-readable age string into weeks.

    Supported units:
    - years
    - months
    - weeks
    - days

    If the input is only a numeric value, it is treated as years for backward
    compatibility with the current server behavior.
    """
    if raw is None:
        return None

    text = str(raw).lower().strip()
    if not text:
        return None

    total_weeks = 0.0
    matched = False
    patterns = (
        (r"(\d+(?:[.,]\d+)?)\s*(y[iı]l|yaş|yas|year|years|yr|jahre?|jahr)", 52.0),
        (r"(\d+(?:[.,]\d+)?)\s*(ay|ayl[iı]k|aylik|month|months|mo|monate?|monat)", 4.345),
        (r"(\d+(?:[.,]\d+)?)\s*(hafta|week|weeks|wk|wochen?|woche)", 1.0),
        (r"(\d+(?:[.,]\d+)?)\s*(g[uü]n|gun|day|days|tage?|tag)", 1.0 / 7.0),
    )

    for pattern, multiplier in patterns:
        for match in re.finditer(pattern, text):
            total_weeks += float(match.group(1).replace(",", ".")) * multiplier
            matched = True

    if matched:
        return total_weeks

    try:
        return float(text.replace(",", ".")) * 52.0
    except ValueError:
        return None


def _is_species_match(species: str, tokens: tuple[str, ...]) -> bool:
    return any(token in species for token in tokens)


def build_patient_auto_profile(patient_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Build an automatic care profile from patient context.

    The output shape mirrors the current backend behavior so the caller can
    swap this module in without changing UI payloads.
    """
    patient_context = patient_context or {}
    species = str(patient_context.get("species") or "").strip().lower()
    age_weeks = parse_age_weeks(patient_context.get("age"))

    if not species:
        return {
            "supported": False,
            "reason_code": "missing_patient",
        }

    if age_weeks is None:
        return {
            "supported": False,
            "reason_code": "missing_age",
        }

    if _is_species_match(species, CAT_TOKENS):
        if age_weeks < 1.0:
            profile_code = "cat_0_1_week"
            temp_min, temp_max = 30.0, 32.0
            humidity_min, humidity_max = 55.0, 65.0
        elif age_weeks < 3.0:
            profile_code = "cat_1_3_weeks"
            temp_min, temp_max = 27.0, 29.0
            humidity_min, humidity_max = 55.0, 65.0
        elif age_weeks < 52.0:
            profile_code = "cat_4_plus_weeks"
            temp_min, temp_max = 21.0, 24.0
            humidity_min, humidity_max = 50.0, 60.0
        else:
            profile_code = "cat_adult"
            temp_min, temp_max = 20.0, 22.0
            humidity_min, humidity_max = 45.0, 55.0
    elif _is_species_match(species, DOG_TOKENS):
        if age_weeks < 2.0:
            profile_code = "dog_0_2_weeks"
            temp_min, temp_max = 29.0, 32.0
            humidity_min, humidity_max = 55.0, 65.0
        elif age_weeks < 4.0:
            profile_code = "dog_2_4_weeks"
            temp_min, temp_max = 26.0, 29.0
            humidity_min, humidity_max = 55.0, 65.0
        elif age_weeks < 12.0:
            profile_code = "dog_4_12_weeks"
            temp_min, temp_max = 22.0, 26.0
            humidity_min, humidity_max = 50.0, 60.0
        elif age_weeks < 52.0:
            profile_code = "dog_juvenile"
            temp_min, temp_max = 18.0, 22.0
            humidity_min, humidity_max = 45.0, 55.0
        else:
            profile_code = "dog_adult"
            temp_min, temp_max = 18.0, 22.0
            humidity_min, humidity_max = 40.0, 50.0
    elif _is_species_match(species, BIRD_TOKENS):
        if age_weeks < 2.0:
            profile_code = "bird_0_2_weeks"
            temp_min, temp_max = 32.0, 35.0
            humidity_min, humidity_max = 60.0, 70.0
        elif age_weeks < 4.0:
            profile_code = "bird_2_4_weeks"
            temp_min, temp_max = 29.0, 32.0
            humidity_min, humidity_max = 55.0, 65.0
        elif age_weeks < 8.0:
            profile_code = "bird_4_8_weeks"
            temp_min, temp_max = 26.0, 29.0
            humidity_min, humidity_max = 50.0, 60.0
        elif age_weeks < 52.0:
            profile_code = "bird_juvenile"
            temp_min, temp_max = 22.0, 26.0
            humidity_min, humidity_max = 45.0, 55.0
        else:
            profile_code = "bird_adult"
            temp_min, temp_max = 20.0, 24.0
            humidity_min, humidity_max = 40.0, 50.0
    else:
        return {
            "supported": False,
            "reason_code": "unsupported_species",
        }

    humidity_target = round((humidity_min + humidity_max) / 2.0, 1)

    return {
        "supported": True,
        "reason_code": None,
        "profile_code": profile_code,
        "targets": {
            "sld3": round((temp_min + temp_max) / 2.0, 1),
            "sld2": humidity_target,
            "sld12": round(temp_max, 1),
        },
        "bands": {
            "temperature": {
                "min": round(temp_min, 1),
                "max": round(temp_max, 1),
            },
            "humidity": {
                "min": round(humidity_min, 1),
                "max": round(humidity_max, 1),
            },
        },
    }


def get_care_status(
    care_settings: Optional[Dict[str, Any]],
    patient_context: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Return a UI-friendly care status payload."""
    care_settings = care_settings or {}
    patient_context = patient_context or {}
    profile = build_patient_auto_profile(patient_context)

    effective_values = {}
    if isinstance(care_settings.get("targets"), dict):
        effective_values.update(care_settings["targets"])

    if care_settings.get("mode") == "auto" and profile.get("supported"):
        effective_values.update(profile["targets"])

    return {
        "mode": care_settings.get("mode", "manual"),
        "auto_available": bool(profile.get("supported")),
        "manual_locked": care_settings.get("mode") == "auto" and bool(profile.get("supported")),
        "profile_code": profile.get("profile_code"),
        "reason_code": profile.get("reason_code"),
        "patient_name": patient_context.get("name", ""),
        "patient_species": patient_context.get("species", ""),
        "patient_age": patient_context.get("age", ""),
        "targets": {
            "sld2": effective_values.get("sld2"),
            "sld3": effective_values.get("sld3"),
            "sld12": effective_values.get("sld12"),
        },
        "bands": profile.get("bands", {}),
    }

