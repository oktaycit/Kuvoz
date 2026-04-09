"""Git version and update diagnostics helpers."""

from __future__ import annotations

import subprocess


def get_git_version_info(*, script_dir: str, logger):
    """Return current git commit hash and branch information."""
    try:
        hash_result = subprocess.run(
            ['git', 'rev-parse', '--short=7', 'HEAD'],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=script_dir
        )
        git_hash = hash_result.stdout.strip() if hash_result.returncode == 0 else 'Unknown'

        branch_result = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=script_dir
        )
        git_branch = branch_result.stdout.strip() if branch_result.returncode == 0 else 'Unknown'
        return {'hash': git_hash, 'branch': git_branch}
    except Exception as exc:
        logger.warning(f"Failed to get git version info: {exc}")
        return {'hash': 'Unknown', 'branch': 'Unknown'}


def _parse_git_status_porcelain(output):
    dirty_entries = []
    for raw_line in (output or "").splitlines():
        line = raw_line.rstrip()
        if not line:
            continue
        path = line[3:] if len(line) > 3 else line
        if " -> " in path:
            path = path.split(" -> ", 1)[-1]
        dirty_entries.append({
            'status': line[:2].strip() or '??',
            'path': path
        })
    return dirty_entries


def get_git_update_diagnostics(*, script_dir: str, logger):
    """Return local git state information for update UI and troubleshooting."""
    git_info = get_git_version_info(script_dir=script_dir, logger=logger)
    diagnostics = {
        'branch': git_info['branch'],
        'hash': git_info['hash'],
        'blocked': False,
        'reasons': [],
        'notes': [],
        'dirty_files': [],
        'upstream_ref': ''
    }

    try:
        status_result = subprocess.run(
            ['git', 'status', '--porcelain'],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=script_dir
        )
        if status_result.returncode == 0:
            dirty_entries = _parse_git_status_porcelain(status_result.stdout)
            diagnostics['dirty_files'] = [entry['path'] for entry in dirty_entries]
            if dirty_entries:
                diagnostics['blocked'] = True
                diagnostics['reasons'].append('Git çalışma ağacında yerel değişiklikler var.')
        else:
            diagnostics['blocked'] = True
            diagnostics['reasons'].append('Git durum bilgisi okunamadı.')

        branch_name = diagnostics['branch']
        if branch_name in ('HEAD', 'Unknown', ''):
            diagnostics['blocked'] = True
            diagnostics['reasons'].append('Aktif branch belirlenemedi (detached HEAD veya git hatası).')

        upstream_result = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}'],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=script_dir
        )
        if upstream_result.returncode == 0:
            diagnostics['upstream_ref'] = upstream_result.stdout.strip()
        elif branch_name not in ('HEAD', 'Unknown', ''):
            diagnostics['notes'].append(
                f'Bu branch için upstream ayarı bulunamadı. Update origin/{branch_name} üzerinden denenecek.'
            )
    except Exception as exc:
        diagnostics['blocked'] = True
        diagnostics['reasons'].append(f'Git teşhisi alınamadı: {str(exc)}')

    if not diagnostics['blocked'] and not diagnostics['reasons']:
        diagnostics['notes'].append('Güncellemeyi engelleyen yerel bir durum görünmüyor.')

    return diagnostics


def classify_git_update_error(output, current_branch):
    text = (output or '').strip()
    lower = text.lower()

    if (
        'could not resolve host' in lower or
        'failed to connect' in lower or
        'network is unreachable' in lower or
        'connection timed out' in lower or
        'operation timed out' in lower
    ):
        return 'network', '❌ İnternet bağlantısı veya DNS erişimi yok.', text

    if "couldn't find remote ref" in lower or 'remote ref does not exist' in lower:
        return 'missing_remote_branch', f'❌ origin/{current_branch} branch’i bulunamadı.', text

    if 'authentication failed' in lower or 'permission denied' in lower:
        return 'permission', '❌ GitHub erişim yetkisi başarısız oldu.', text

    if 'not possible to fast-forward' in lower:
        return 'diverged', '❌ Yerel branch origin ile ayrışmış. Önce manuel olarak birleştirme veya geri alma gerekiyor.', text

    return 'unknown', f'Güncelleme hatası: {text or "Bilinmeyen hata"}', text
