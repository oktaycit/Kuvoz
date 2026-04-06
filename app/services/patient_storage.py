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
        'ownerName', 'diagnosis', 'admissionDate', 'currentTreatment'
    )
    return any(str(record.get(key) or '').strip() for key in keys)


def build_patient_id(record):
    admission_date = str(record.get('admissionDate') or '').strip()
    name = re.sub(r'\s+', '_', str(record.get('name') or '').strip())
    fallback = str(record.get('savedAt') or '').replace(':', '-').replace('.', '-')
    base = f"{admission_date}_{name}".strip('_')
    return base or fallback or f"patient_{int(time.time())}"


def normalize_patient_record(record):
    normalized = dict(record) if isinstance(record, dict) else {}
    has_id = bool(str(normalized.get('id') or '').strip())
    if not patient_record_has_content(normalized) and not has_id:
        return {}
    normalized.setdefault('id', build_patient_id(normalized))
    return normalized


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
