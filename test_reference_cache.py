import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
try:
    import cv2
    import numpy as np
except ImportError:
    cv2=np=None

from lib.ai.appearance_recovery import AppearanceRecovery
from lib.ai.reference_cache import ReferenceCache
from lib.ai.vision import VisionEngine


@unittest.skipUnless(cv2 is not None,'OpenCV gerekli')
class ReferenceCacheTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.image=np.full((240,320),220,np.uint8)
        self.image[70:170,90:230]=np.random.default_rng(73).integers(20,150,(100,140),dtype=np.uint8)
        self.boxes={'animal':(90,70,140,100),'respiration':(135,100,45,35)}
        self.recovery=AppearanceRecovery(cv2,np);self.recovery.remember(self.image,self.boxes,0,True,verified=True)
        self.cache=ReferenceCache(self.directory.name,['camera',1],self.image.shape)

    def test_checkpoint_restores_references_and_last_trusted_frame(self):
        self.assertTrue(self.cache.save(self.recovery,self.image,self.boxes))
        fresh=AppearanceRecovery(cv2,np);restored=self.cache.load(fresh)
        self.assertIsNotNone(restored)
        np.testing.assert_array_equal(restored[0],self.image)
        self.assertEqual(restored[1],self.boxes)
        np.testing.assert_array_equal(fresh.references[0]['descriptors'],self.recovery.references[0]['descriptors'])
        np.testing.assert_array_equal(fresh.references[0]['appearance'],self.recovery.references[0]['appearance'])
        self.assertLess(self.cache.path.stat().st_size,256000)

    def test_legacy_checkpoint_without_night_texture_still_loads(self):
        self.cache.save(self.recovery,self.image,self.boxes)
        with np.load(self.cache.path,allow_pickle=False) as archive:
            arrays={key:archive[key].copy() for key in archive.files if not key.endswith('_appearance')}
        np.savez_compressed(self.cache.path,**arrays)
        fresh=AppearanceRecovery(cv2,np)
        self.assertIsNotNone(self.cache.load(fresh))
        self.assertIsNone(fresh.references[0]['appearance'])

    def test_invalid_night_texture_is_rejected(self):
        self.cache.save(self.recovery,self.image,self.boxes)
        with np.load(self.cache.path,allow_pickle=False) as archive:
            arrays={key:archive[key].copy() for key in archive.files}
        arrays['0_appearance']=np.zeros((100,100),np.uint8)
        np.savez_compressed(self.cache.path,**arrays)
        self.assertIsNone(self.cache.load(AppearanceRecovery(cv2,np)))

    def test_camera_or_calibration_change_rejects_old_checkpoint(self):
        self.cache.save(self.recovery,self.image,self.boxes)
        other=ReferenceCache(self.directory.name,['camera',2],self.image.shape)
        self.assertIsNone(other.load(AppearanceRecovery(cv2,np)))

    def test_verified_migration_keeps_frame_boxes_and_chest(self):
        self.cache.save(self.recovery,self.image,self.boxes)
        migrated=ReferenceCache(self.directory.name,['camera','selected-mac'],self.image.shape)
        fresh=AppearanceRecovery(cv2,np)
        self.assertTrue(migrated.migrate_from(fresh,['camera',1]))
        restored=migrated.load(AppearanceRecovery(cv2,np))
        np.testing.assert_array_equal(restored[0],self.image)
        self.assertEqual(restored[1],self.boxes)
        self.assertIsNotNone(fresh.references[0]['chest'])
        self.assertIsNone(self.cache.load(AppearanceRecovery(cv2,np)))

    def test_migration_rejects_wrong_camera_or_changed_calibration_without_writing(self):
        self.cache.save(self.recovery,self.image,self.boxes)
        original=self.cache.path.read_bytes()
        migrated=ReferenceCache(self.directory.name,['camera','selected-mac'],self.image.shape)
        self.assertFalse(migrated.migrate_from(AppearanceRecovery(cv2,np),['wrong-camera',1]))
        self.assertEqual(self.cache.path.read_bytes(),original)

    def test_scene_background_is_bounded_and_restored_with_camera_identity(self):
        self.recovery.scene_background=np.full_like(self.image,220)
        self.assertTrue(self.cache.save(self.recovery,self.image,self.boxes))
        fresh=AppearanceRecovery(cv2,np)
        self.assertIsNotNone(self.cache.load(fresh))
        np.testing.assert_array_equal(fresh.scene_background,self.recovery.scene_background)
        self.assertLess(self.cache.path.stat().st_size,256000)
        other=ReferenceCache(self.directory.name,['different-camera'],self.image.shape)
        fresh=AppearanceRecovery(cv2,np)
        self.assertIsNone(other.load(fresh));self.assertIsNone(fresh.scene_background)

    def test_corrupt_checkpoint_is_ignored(self):
        self.cache.path.write_bytes(b'not a calibration archive')
        self.assertIsNone(self.cache.load(self.recovery))

    def test_oversized_checkpoint_is_ignored(self):
        self.cache.path.write_bytes(b'x'*256001)
        self.assertIsNone(self.cache.load(self.recovery))

    def test_cache_write_failure_does_not_stop_tracking(self):
        blocked=Path(self.directory.name)/'not-a-directory';blocked.write_text('file')
        cache=ReferenceCache(blocked,['camera'],self.image.shape)
        self.assertFalse(cache.save(self.recovery,self.image,self.boxes))

    def test_body_restart_recovers_only_with_verified_features(self):
        settings={'camera_source':'ip','ip_camera_url':'rtsp://camera/live',
                  'animal_roi_enabled':True,'animal_roi':{'x':90/320,'y':70/240,'width':140/320,'height':100/240},
                  'respiration_roi_enabled':True,'respiration_roi':{'x':135/320,'y':100/240,'width':45/320,'height':35/240}}
        e=VisionEngine(resolution=(320,240));e.set_system_settings(settings)
        regions={'animal':e.animal_roi}
        identity=[e.camera_source,e.ip_camera_url,e.camera_transform,e.resolution,regions,0]
        checkpoint=ReferenceCache(self.directory.name,identity,self.image.shape)
        checkpoint.save(self.recovery,self.image,self.boxes)
        e.reference_cache_dir=self.directory.name;e._camera_restart_pending=False
        e.running=True;e.camera_type='ip';e.camera=Mock();e._check_thermal_throttle=Mock()
        rotated=cv2.warpAffine(self.image,cv2.getRotationMatrix2D((160,120),90,1),(320,240),borderValue=220)
        e.camera.read.return_value=(True,cv2.cvtColor(rotated,cv2.COLOR_GRAY2BGR))
        with patch('lib.ai.vision.time.monotonic') as mono,patch('lib.ai.vision.time.time') as wall:
            mono.return_value=100;wall.return_value=100;e.process_frame()
            self.assertTrue(e._reference_restored)
            self.assertFalse(e._region_vitals_allowed())
            for t in [1,2,3,3.2,3.4,3.6,3.8,4,4.2,4.4,4.6,4.8,5.2,5.4,6]:
                mono.return_value=100+t;wall.return_value=100+t;e.process_frame()
        self.assertEqual(e.region_tracker.state,'locked')
        self.assertFalse(e.region_tracker.respiration_ready)


if __name__=='__main__':unittest.main()
