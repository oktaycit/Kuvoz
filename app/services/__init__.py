"""Shared app services."""

from .git_update import (
    classify_git_update_error,
    get_git_update_diagnostics,
    get_git_version_info,
)
from .field_diagnostics import collect_field_diagnostics, decode_power_throttled
from .network_utils import get_all_ips, get_local_ip
from .patient_storage import (
    build_patient_id,
    ensure_patient_storage,
    load_patient_records,
    merge_current_patient_record,
    normalize_patient_record,
    patient_record_has_content,
    save_patient_records,
)
from .task_manager import BackgroundTaskManager
from .wifi_wps import WifiWPSService

__all__ = [
    'BackgroundTaskManager',
    'WifiWPSService',
    'classify_git_update_error',
    'build_patient_id',
    'collect_field_diagnostics',
    'decode_power_throttled',
    'ensure_patient_storage',
    'get_all_ips',
    'get_git_update_diagnostics',
    'get_git_version_info',
    'get_local_ip',
    'load_patient_records',
    'merge_current_patient_record',
    'normalize_patient_record',
    'patient_record_has_content',
    'save_patient_records',
]
