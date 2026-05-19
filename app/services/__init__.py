"""Shared app services."""

from .git_update import (
    classify_git_update_error,
    get_git_update_diagnostics,
    get_git_version_info,
)
from .ai_settings import normalize_ai_enabled_value, resolve_ai_enabled_preference
from .field_diagnostics import collect_field_diagnostics, decode_power_throttled
from .network_utils import get_all_ips, get_local_ip
from .hostname_manager import (
    get_hostname_status,
    set_device_hostname,
    validate_hostname,
)
from .patient_storage import (
    annotate_patient_activity,
    build_patient_id,
    ensure_patient_storage,
    is_same_patient_record,
    load_patient_records,
    merge_current_patient_record,
    normalize_patient_record,
    patient_record_has_content,
    patient_identity_keys,
    save_patient_records,
)
from .support_reports import (
    append_support_report,
    load_support_reports,
    update_support_report,
)
from .task_manager import BackgroundTaskManager
from .wifi_wps import WifiWPSService

__all__ = [
    'BackgroundTaskManager',
    'WifiWPSService',
    'classify_git_update_error',
    'normalize_ai_enabled_value',
    'resolve_ai_enabled_preference',
    'annotate_patient_activity',
    'build_patient_id',
    'collect_field_diagnostics',
    'decode_power_throttled',
    'ensure_patient_storage',
    'get_all_ips',
    'get_hostname_status',
    'get_git_update_diagnostics',
    'get_git_version_info',
    'get_local_ip',
    'is_same_patient_record',
    'load_patient_records',
    'load_support_reports',
    'merge_current_patient_record',
    'normalize_patient_record',
    'patient_record_has_content',
    'patient_identity_keys',
    'save_patient_records',
    'set_device_hostname',
    'append_support_report',
    'update_support_report',
    'validate_hostname',
]
