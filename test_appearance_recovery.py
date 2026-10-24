import unittest
from unittest.mock import Mock, patch

try:
    import cv2
    import numpy as np
except ImportError:
    cv2=np=None

from lib.ai.appearance_recovery import AppearanceRecovery
from lib.ai.region_tracker import RegionTracker
from lib.ai.vision import VisionEngine


@unittest.skipUnless(cv2 is not None,'OpenCV gerekli')
class AppearanceRecoveryTests(unittest.TestCase):
    def setUp(self):
        cv2.setNumThreads(1)
        self.image=np.full((240,320),220,np.uint8)
        texture=np.random.default_rng(23).integers(20,150,(100,140),dtype=np.uint8)
        self.image[70:170,90:230]=cv2.GaussianBlur(texture,(3,3),0)
        self.boxes={'animal':(90,70,140,100),'respiration':(135,100,45,35)}
        self.recovery=AppearanceRecovery(cv2,np)
        self.recovery.remember(self.image,self.boxes,0,True)

    def test_stationary_fallback_restores_body_without_transferring_chest(self):
        self.recovery._foreground = Mock(return_value=[])
        normal = self.recovery._correspondences
        calls = [0]
        def crowded(ref, desc, points):
            calls[0] += 1
            if calls[0] == 1:
                return np.empty((0,2),np.float32), np.empty((0,2),np.float32), np.empty((0,2),np.float32)
            return normal(ref, desc, points)
        self.recovery._correspondences = crowded
        found = self.recovery.find(self.image)
        self.assertIsNotNone(found)
        self.assertEqual(found['kind'], 'stationary_features')
        self.assertNotIn('respiration', found['boxes'])

    def test_stationary_fallback_rejects_empty_and_unrelated_scene(self):
        mask = np.full_like(self.image, 255)
        self.assertEqual(self.recovery._stationary_candidates(np.full_like(self.image,220), mask), [])
        unrelated = np.random.default_rng(71).integers(0,255,self.image.shape,dtype=np.uint8)
        self.assertEqual(self.recovery._stationary_candidates(unrelated, mask), [])

    def transformed(self,angle):
        matrix=cv2.getRotationMatrix2D((160,120),angle,1)
        return cv2.warpAffine(self.image,matrix,(320,240),borderValue=220),matrix

    def test_rotation_recovers_body_and_corresponding_respiration(self):
        rotated,matrix=self.transformed(90)
        found=self.recovery.find(rotated)
        self.assertIsNotNone(found)
        self.assertIn('respiration',found['boxes'])
        expected=self.recovery._transform_box(self.boxes['respiration'],matrix,rotated.shape)
        for actual,wanted in zip(found['boxes']['respiration'],expected):
            self.assertAlmostEqual(actual,wanted,delta=3)

    def test_occluded_chest_can_resume_body_without_respiration(self):
        rotated,matrix=self.transformed(180)
        x,y,w,h=self.recovery._transform_box(self.boxes['respiration'],matrix,rotated.shape)
        rotated[int(y)-3:int(y+h)+3,int(x)-3:int(x+w)+3]=220
        found=self.recovery.find(rotated)
        self.assertIsNotNone(found)
        self.assertNotIn('respiration',found['boxes'])

    def test_blank_or_unrelated_scene_does_not_match(self):
        self.assertIsNone(self.recovery.find(np.full_like(self.image,220)))
        unrelated=np.random.default_rng(89).integers(0,255,self.image.shape,dtype=np.uint8)
        self.assertIsNone(self.recovery.find(unrelated))

    def test_foreground_histogram_does_not_require_reference_bedding(self):
        ref=dict(self.recovery.references[0])
        # A selected torso rectangle includes bright bedding. Recovery masks
        # out that bedding, so its histogram must be conditioned identically.
        ref['posterior']=np.zeros(32,np.float32)
        ref['posterior'][:20]=1
        ref['lookup']=np.repeat((ref['posterior']>=.62).astype(np.uint8)*255,8)
        fur=cv2.calcHist([self.image[70:170,90:230]],[0],None,[32],[0,256]).ravel()+1
        fur[20:]=0;fur/=fur.sum()
        ref['hist']=fur*.4;ref['hist'][27]=.6
        motion=np.zeros_like(self.image);motion[70:170,90:230]=255
        supported=np.array([[110,90],[140,110],[180,130],[210,150]],np.float32)
        found=self.recovery._foreground(self.image,ref,supported,motion)
        self.assertTrue(found)
        self.assertNotIn('respiration',found[0]['boxes'])

    def test_different_texture_with_same_shape_and_tone_does_not_match(self):
        other=np.full_like(self.image,220)
        texture=np.random.default_rng(945).integers(20,150,(100,140),dtype=np.uint8)
        other[70:170,90:230]=cv2.GaussianBlur(texture,(3,3),0)
        self.assertIsNone(self.recovery.find(other))

    def test_two_rotated_copies_are_ambiguous(self):
        rotated,matrix=self.transformed(90)
        x,y,w,h=[round(v) for v in self.recovery._transform_box(self.boxes['animal'],matrix,rotated.shape)]
        patch=rotated[y:y+h,x:x+w];scene=np.full_like(self.image,220)
        scene[50:50+h,30:30+w]=patch;scene[50:50+h,190:190+w]=patch
        self.assertIsNone(self.recovery.find(scene))

    def test_moderate_lighting_change_preserves_correspondence(self):
        lit=np.clip(self.image.astype(np.int16)+20,0,255).astype(np.uint8)
        found=self.recovery.find(lit)
        self.assertIsNotNone(found)
        self.assertIn('respiration',found['boxes'])

    def test_recent_body_reference_does_not_hide_verified_anatomy(self):
        self.recovery.remember(self.image,{'animal':self.boxes['animal']},5,True)
        original=self.recovery._geometric
        def correspondence(gray,ref,src,dst):
            result=original(gray,ref,src,dst)
            if result and ref['chest'] is not None:result['confidence']=.9
            return result
        with patch.object(self.recovery,'_geometric',side_effect=correspondence):
            found=self.recovery.find(self.image)
        self.assertIsNotNone(found)
        self.assertIn('respiration',found['boxes'])

    def test_motion_and_fur_can_restore_lifecycle_without_descriptor_matches(self):
        rotated,_=self.transformed(90)
        empty=tuple(np.empty((0,2),np.float32) for _ in range(3))
        with patch.object(self.recovery,'_correspondences',return_value=empty):
            found=self.recovery.find(rotated,self.image)
        self.assertIsNotNone(found)
        self.assertEqual(found['kind'],'motion_foreground')
        self.assertNotIn('respiration',found['boxes'])

    def test_animal_leaving_cannot_turn_empty_bedding_into_a_subject(self):
        empty=np.full_like(self.image,220)
        self.assertIsNone(self.recovery.find(empty,self.image))

    def test_motion_inside_excluded_bowl_does_not_reacquire(self):
        self.recovery.exclusions=[(90/320,70/240,140/320,100/240)]
        self.assertIsNone(self.recovery.find(self.image,np.full_like(self.image,220)))

    def test_global_brightness_change_is_not_motion_evidence(self):
        lit=np.clip(self.image.astype(np.int16)+40,0,255).astype(np.uint8)
        empty=tuple(np.empty((0,2),np.float32) for _ in range(3))
        with patch.object(self.recovery,'_correspondences',return_value=empty):
            self.assertIsNone(self.recovery.find(lit,self.image))

    def test_body_only_memory_does_not_learn_white_bedding_as_fur(self):
        original=self.recovery.references[0]['posterior'].copy()
        self.recovery.remember(self.image,{'animal':(65,50,190,140)},5,True)
        np.testing.assert_allclose(self.recovery.references[-1]['posterior'],original)

    def test_anatomy_probe_skips_foreground_and_body_only_references(self):
        self.recovery.remember(self.image,{'animal':self.boxes['animal']},5,True)
        with patch.object(self.recovery,'_foreground',side_effect=AssertionError('Unneeded silhouette search')):
            found=self.recovery.find(self.image,anatomy_only=True)
        self.assertIsNotNone(found)
        self.assertIn('respiration',found['boxes'])

    def test_memory_is_bounded_and_initial_anatomy_is_retained(self):
        first=self.recovery.references[0]
        for i in range(1,9):self.recovery.remember(self.image,self.boxes,i,True)
        self.assertEqual(len(self.recovery.references),3)
        self.assertIs(self.recovery.references[0],first)
        self.assertLessEqual(sum(r['descriptors'].nbytes for r in self.recovery.references),3*240*32)
        self.assertLess(self.recovery.memory_bytes(),40000)

    def test_steady_tracking_does_not_extract_descriptors_each_frame(self):
        normalized={name:{'x':x/320,'y':y/240,'width':w/320,'height':h/240}
                    for name,(x,y,w,h) in self.boxes.items()}
        tracker=RegionTracker(cv2,np);tracker.initialize(self.image,normalized,0)
        spy=Mock(wraps=tracker.recovery.orb);tracker.recovery.orb=spy
        for i in range(1,25):tracker.update(self.image,i*.2)
        spy.detectAndCompute.assert_not_called()
        tracker.update(self.image,5.2)
        spy.detectAndCompute.assert_called_once()

    def test_failed_reference_refresh_is_also_rate_limited(self):
        spy=Mock(wraps=self.recovery.orb);self.recovery.orb=spy
        spy.detectAndCompute.return_value=([],None)
        for t in [5,5.2,5.4,5.6]:self.recovery.remember(self.image,self.boxes,t)
        spy.detectAndCompute.assert_called_once()

    def test_loss_search_is_bounded_to_one_hz(self):
        normalized={name:{'x':x/320,'y':y/240,'width':w/320,'height':h/240}
                    for name,(x,y,w,h) in self.boxes.items()}
        tracker=RegionTracker(cv2,np);tracker.initialize(self.image,normalized,0)
        tracker.lose('pose_changed')
        with patch.object(tracker.recovery,'find',return_value=None) as find:
            for now in [.2,.4,.6,.8,1.0,1.2,1.4]:tracker.update(np.full_like(self.image,220),now)
        self.assertEqual(find.call_count,2)

    def test_rotated_animal_relocks_without_operator_selection(self):
        normalized={name:{'x':x/320,'y':y/240,'width':w/320,'height':h/240}
                    for name,(x,y,w,h) in self.boxes.items()}
        tracker=RegionTracker(cv2,np);tracker.initialize(self.image,normalized,0)
        rotated,_=self.transformed(90);tracker.lose('pose_changed')
        for now in [1,2,3]:tracker.update(rotated,now)
        self.assertEqual(tracker.state,'acquiring')
        for now in [3.2,3.4,3.6,3.8,4,4.2,4.4,4.6,4.8,5.1]:tracker.update(rotated,now)
        self.assertEqual(tracker.state,'locked')
        self.assertTrue(tracker.respiration_ready)

    def test_body_recovery_and_later_respiration_recovery_are_independent(self):
        normalized={name:{'x':x/320,'y':y/240,'width':w/320,'height':h/240}
                    for name,(x,y,w,h) in self.boxes.items()}
        tracker=RegionTracker(cv2,np);tracker.initialize(self.image,normalized,0)
        rotated,matrix=self.transformed(180);occluded=rotated.copy()
        x,y,w,h=self.recovery._transform_box(self.boxes['respiration'],matrix,rotated.shape)
        occluded[int(y)-3:int(y+h)+3,int(x)-3:int(x+w)+3]=220
        tracker.lose('pose_changed')
        for t in [1,2,3,3.2,3.4,3.6,3.8,4,4.2,4.4,4.6,4.8,5.2]:tracker.update(occluded,t)
        self.assertEqual(tracker.state,'locked')
        self.assertFalse(tracker.respiration_ready)
        for i in range(1,61):tracker.update(rotated,5.2+i*.2)
        self.assertEqual(tracker.state,'locked')
        self.assertTrue(tracker.respiration_ready)

    def test_configured_old_chest_is_hidden_during_body_only_recovery(self):
        engine=VisionEngine()
        engine.set_system_settings({'animal_roi_enabled':True,
            'animal_roi':{'x':.2,'y':.2,'width':.5,'height':.5},
            'respiration_roi_enabled':True,'respiration_roi':{'x':.3,'y':.3,'width':.15,'height':.15}})
        engine.region_tracker=Mock(state='locked',confidence=.99,respiration_ready=False)
        engine._tracked_regions={'animal':{'x':.4,'y':.4,'width':.3,'height':.3}}
        self.assertIsNone(engine._respiration_roi_to_frame_box((240,320,3)))

    def test_single_chest_match_cannot_resume_respiration(self):
        tracker=RegionTracker(cv2,np)
        normalized={name:{'x':x/320,'y':y/240,'width':w/320,'height':h/240}
                    for name,(x,y,w,h) in self.boxes.items()}
        tracker.initialize(self.image,normalized,0)
        tracker.state='locked';tracker.confidence=.99;tracker.respiration_ready=False
        found={'boxes':self.boxes,'confidence':.99,'kind':'features'}
        with patch.object(tracker.recovery,'find',side_effect=[found,None,found,found]):
            for t in [10,12,14]:
                tracker._maintain_reference(self.image,t)
                self.assertFalse(tracker.respiration_ready)
            tracker._maintain_reference(self.image,16)
            self.assertTrue(tracker.respiration_ready)
        tracker._confirm_chest(None,20)
        self.assertFalse(tracker._confirm_chest(self.boxes['respiration'],21))
        self.assertFalse(tracker._confirm_chest(self.boxes['respiration'],30))


class AnatomyGateTests(unittest.TestCase):
    def test_body_lock_does_not_reuse_old_configured_chest(self):
        engine=VisionEngine();engine.animal_roi={'x':.2,'y':.2,'width':.5,'height':.5}
        engine.respiration_roi_enabled=True
        engine.region_tracker=Mock(state='locked',confidence=.99,respiration_ready=False)
        self.assertFalse(engine._region_vitals_allowed())
        engine.region_tracker.respiration_ready=True
        self.assertTrue(engine._region_vitals_allowed())

    def test_body_only_tracking_uses_two_fps_then_restores_vital_rate(self):
        engine=VisionEngine();engine.set_system_settings({'camera_source':'ip',
            'ip_camera_url':'rtsp://camera/live','respiration_roi_enabled':True,
            'respiration_roi':{'x':.3,'y':.3,'width':.15,'height':.15}})
        engine.region_tracker=Mock(state='locked',confidence=.99,respiration_ready=False)
        engine._update_load_profile(now=10)
        self.assertEqual(engine.target_fps,2)
        engine.region_tracker.respiration_ready=True
        engine._update_load_profile(now=11)
        self.assertEqual(engine.target_fps,5)


if __name__=='__main__':unittest.main()
