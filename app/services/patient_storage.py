"""Patient record storage helpers."""

from __future__ import annotations

import datetime
import json
import os
import re
import time


def patient_record_has_content(record):
    if not isinstance(record, dict):
        return False

    keys = (
        'name', 'species', 'breed', 'age', 'weight',
        'microchipNo', 'ownerName', 'diagnosis', 'admissionDate', 'currentTreatment'
    )
    return any(str(record.get(key) or '').strip() for key in keys)


def build_patient_id(record):
    admission_date = str(record.get('admissionDate') or '').strip()
    name = re.sub(r'\s+', '_', str(record.get('name') or '').strip())
    fallback = str(record.get('savedAt') or '').replace(':', '-').replace('.', '-')
    base = f"{admission_date}_{name}".strip('_')
    return base or fallback or f"patient_{int(time.time())}"


def build_readmission_patient_id(record, existing_patients=None):
    """Build a new episode id for a previously discharged patient."""
    base_id = build_patient_id(record)
    admission_time = re.sub(r'\D+', '', str(record.get('admissionTime') or ''))
    fallback = datetime.datetime.now().strftime('%H%M%S')
    suffix = admission_time or fallback
    candidate = f"{base_id}_{suffix}".strip('_')
    existing_ids = {
        str(patient.get('id') or '').strip()
        for patient in (existing_patients or [])
        if isinstance(patient, dict)
    }

    counter = 2
    unique_candidate = candidate
    while unique_candidate in existing_ids:
        unique_candidate = f"{candidate}_{counter}"
        counter += 1

    return unique_candidate


def normalize_patient_record(record):
    normalized = dict(record) if isinstance(record, dict) else {}
    has_id = bool(str(normalized.get('id') or '').strip())
    if not patient_record_has_content(normalized) and not has_id:
        return {}
    normalized.setdefault('id', build_patient_id(normalized))
    return normalized


def patient_identity_keys(record):
    """Return stable keys that can identify the same patient record."""
    if not isinstance(record, dict):
        return set()

    keys = set()
    patient_id = str(record.get('id') or '').strip()
    microchip_no = re.sub(r'\D+', '', str(record.get('microchipNo') or ''))
    name = re.sub(r'\s+', ' ', str(record.get('name') or '').strip()).lower()
    admission_date = str(record.get('admissionDate') or '').strip()
    admission_time = str(record.get('admissionTime') or '').strip()

    if patient_id:
        keys.add(f"id:{patient_id}")
    if microchip_no:
        keys.add(f"microchip:{microchip_no}")
    if name or admission_date or admission_time:
        keys.add(f"admission:{name}|{admission_date}|{admission_time}")

    return keys


def is_same_patient_record(left, right):
    left_keys = patient_identity_keys(left)
    right_keys = patient_identity_keys(right)
    return bool(left_keys and right_keys and left_keys.intersection(right_keys))


def annotate_patient_activity(patients, current_patient):
    """Mark the current incubator session patient separately from follow-up records."""
    current = normalize_patient_record(current_patient)
    current_is_active = bool(current and not current.get('discharged', False))
    annotated = []
    open_patient_count = 0

    for patient in patients or []:
        record = dict(patient)
        discharged = bool(record.get('discharged', False))
        if not discharged:
            open_patient_count += 1

        is_current = bool(current_is_active and not discharged and is_same_patient_record(record, current))
        record['is_current'] = is_current
        if discharged:
            record['active_status'] = 'discharged'
        elif is_current:
            record['active_status'] = 'current'
        else:
            record['active_status'] = 'follow_up'
        annotated.append(record)

    active_patient = current if current_is_active else {}
    return annotated, {
        'current_patient': active_patient,
        'active_patient_id': active_patient.get('id', ''),
        'open_patient_count': open_patient_count,
        'has_multiple_open_patients': open_patient_count > 1,
    }


def ensure_patient_storage(patients_dir):
    os.makedirs(patients_dir, exist_ok=True)


def load_patient_records(patients_file):
    if not os.path.exists(patients_file):
        return []

    with open(patients_file, 'r', encoding='utf-8') as handle:
        patients = json.load(handle)

    return patients if isinstance(patients, list) else []


def save_patient_records(patients_file, patients_dir, patients):
    ensure_patient_storage(patients_dir)
    with open(patients_file, 'w', encoding='utf-8') as handle:
        json.dump(patients, handle, ensure_ascii=False, indent=2)


def merge_current_patient_record(patients, current_patient):
    merged = list(patients or [])
    if not patient_record_has_content(current_patient):
        return merged

    record = dict(current_patient)
    record.setdefault('id', build_patient_id(record))
    record.setdefault('savedAt', datetime.datetime.now().isoformat())

    existing_index = next((i for i, patient in enumerate(merged) if patient.get('id') == record['id']), None)
    if existing_index is not None:
        merged[existing_index] = {**merged[existing_index], **record}
    elif not record.get('discharged', False):
        merged.insert(0, record)

    return merged
