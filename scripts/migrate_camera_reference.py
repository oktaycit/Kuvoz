#!/usr/bin/env python3
"""Explicit URL→MAC reference migration after verifying the selected device on LAN."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import sys
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    from lib.ai.camera_discovery import CameraResolver, normalize_mac
    from lib.ai.ip_camera import validate_camera_settings
    from lib.ai.vision import VisionEngine, cv2, np
    from lib.ai.manager import _vision_runtime_config
    from lib.ai.appearance_recovery import AppearanceRecovery
    from lib.ai.reference_cache import ReferenceCache
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previous-url', required=True)
    parser.add_argument('--mac', required=True)
    parser.add_argument('--settings', default='failure.dat')
    parser.add_argument('--directory', default=os.getenv('KUVOZ_AI_CAMERA_REFERENCE_DIR','data/camera_reference'))
    args=parser.parse_args()
    settings=json.loads(Path(args.settings).read_text())['system_settings']
    mac=normalize_mac(args.mac)
    if not mac or normalize_mac(settings.get('ip_camera_mac'))!=mac:
        parser.error('Kayıtlı kamera MAC adresi eşleşmiyor')
    source,url=validate_camera_settings(settings)
    if source!='ip': parser.error('Seçili kaynak IP kamera değil')
    if not CameraResolver(url,mac,threading.Event()).resolve():
        parser.error('Kamera MAC adresi yerel ağda doğrulanamadı')
    validate_camera_settings({'camera_source':'ip','ip_camera_url':args.previous_url})
    engine=VisionEngine(resolution=_vision_runtime_config()[0]);engine.set_system_settings(settings)
    regions={}
    if engine.animal_roi:regions['animal']=engine.animal_roi
    if engine.respiration_roi_enabled:regions['respiration']=engine.respiration_roi
    identity=['ip',mac,engine.camera_transform,engine.resolution,regions,
              settings.get('region_tracking_revision',0)]
    directory=Path(args.directory)
    cache=ReferenceCache(directory,identity,(engine.resolution[1],engine.resolution[0]))
    recovery=AppearanceRecovery(cv2,np)
    if cache.load(recovery):
        print('Referans zaten MAC kimliğine bağlı.');return
    legacy=list(identity);legacy[1]=args.previous_url
    previous=ReferenceCache(directory,legacy,cache.shape)
    if previous.load(recovery) is None:
        parser.error('Eski kamera/kalibrasyon imzası veya referans verisi eşleşmiyor')
    backup=cache.path.with_name('selected-camera-before-mac-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'.npz')
    shutil.copy2(cache.path,backup)
    if not cache.migrate_from(recovery,legacy):
        raise RuntimeError('Referans geçişi kaydedilemedi')
    if cache.load(AppearanceRecovery(cv2,np)) is None:
        shutil.copy2(backup,cache.path)
        raise RuntimeError('Yeni referans doğrulanamadı; yedek geri yüklendi')
    print('MAC doğrulandı; eski referans, gövde eşlemesi ve kalibrasyon korundu.')
    print('Yedek:',backup)


if __name__=='__main__':main()
