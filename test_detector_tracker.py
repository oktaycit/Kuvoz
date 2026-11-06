import os
import unittest
from unittest.mock import Mock, patch
try:
    import cv2
    import numpy as np
except ImportError:
    cv2=np=None
from lib.ai.animal_detector import AnimalDetector
from lib.ai.appearance_recovery import AppearanceRecovery
from lib.ai.detector_tracker import DetectorTracker


@unittest.skipUnless(cv2 is not None, 'OpenCV gerekli')
class SceneTrackerTests(unittest.TestCase):
    def setUp(self):
        cv2.setNumThreads(1);cv2.ocl.setUseOpenCL(False)
        self.background=np.full((240,320),220,np.uint8)
        self.gray=self.background.copy()
        self.gray[65:175,90:220]=cv2.GaussianBlur(np.random.default_rng(42).integers(25,140,(110,130),np.uint8),(3,3),0)
        self.boxes={'animal':(90,65,130,110),'respiration':(130,100,40,32)}
        self.regions={k:dict(x=v[0]/320,y=v[1]/240,width=v[2]/320,height=v[3]/240) for k,v in self.boxes.items()}
        self.recovery=AppearanceRecovery(cv2,np);self.recovery.remember(self.gray,self.boxes,0,True,verified=True)
        self.recovery.scene_background=self.background.copy()

    def test_night_exposure_recovers_pose_without_foreground_or_orb(self):
        # IR switching changes the bedding model; a learned body texture still
        # matches under gain/offset, without transferring a chest selection.
        night=(self.gray.astype(float)*.65+35).astype(np.uint8)
        self.recovery.scene_background=night.copy()
        self.recovery.orb=Mock()
        self.recovery.orb.detectAndCompute.return_value=([],None)
        self.recovery.observe_scene(night)
        found=self.recovery.find(night)
        self.assertIsNotNone(found)
        self.assertEqual(found['kind'],'appearance')
        self.assertGreater(self.recovery._iou(found['boxes']['animal'],self.boxes['animal']),.95)
        self.assertNotIn('respiration',found['boxes'])
        detector=AnimalDetector(cv2,np);detector.attach(self.recovery)
        self.assertEqual(len(detector.detect(cv2.cvtColor(night,cv2.COLOR_GRAY2BGR))),1)

    def test_night_pose_search_rejects_empty_bedding_and_mama_region(self):
        self.recovery.orb=Mock()
        self.recovery.orb.detectAndCompute.return_value=([],None)
        self.assertIsNone(self.recovery.find(self.background))
        self.recovery.exclusions=[(90/320,65/240,130/320,110/240)]
        self.recovery.scene_background=self.gray.copy()
        self.recovery.observe_scene(self.gray)
        self.assertIsNone(self.recovery.find(self.gray))

    def test_night_pose_search_rejects_two_identical_animals(self):
        image=self.background.copy()
        patch=cv2.resize(self.gray[65:175,90:220],(104,88))
        image[60:148,30:134]=patch;image[60:148,180:284]=patch
        self.recovery.orb=Mock()
        self.recovery.orb.detectAndCompute.return_value=([],None)
        self.recovery.scene_background=image.copy()
        self.recovery.observe_scene(image)
        self.assertIsNone(self.recovery.find(image))

    def test_startup_selection_alone_cannot_enable_night_fallback(self):
        recovery=AppearanceRecovery(cv2,np)
        recovery.remember(self.gray,self.boxes,0,force=True)
        self.assertIsNone(recovery.references[0]['appearance'])

    def test_night_pose_search_can_follow_verified_body_to_image_edge(self):
        image=self.background.copy()
        image[65:175,190:320]=self.gray[65:175,90:220]
        self.recovery.orb=Mock()
        self.recovery.orb.detectAndCompute.return_value=([],None)
        self.recovery.scene_background=image.copy()
        self.recovery.observe_scene(image)
        found=self.recovery.find(image)
        self.assertIsNotNone(found)
        self.assertGreater(self.recovery._iou(found['boxes']['animal'],(190,65,130,110)),.95)

    def test_low_fps_repeated_detections_still_reach_locked(self):
        detector=AnimalDetector(cv2,np);tracker=DetectorTracker(cv2,np,detector)
        tracker.recovery=self.recovery;detector.attach(self.recovery)
        frame=cv2.cvtColor(self.gray,cv2.COLOR_GRAY2BGR)
        for now in range(100,113,2):
            tracker.update_color(frame,self.gray,now)
        self.assertEqual(tracker.state,'locked')

    def test_verified_night_body_rebases_exposed_bedding_without_absorbing_cat(self):
        night=(self.gray.astype(float)*.5).astype(np.uint8)
        self.recovery.scene_mask=np.full_like(night,255)
        detector=AnimalDetector(cv2,np);detector.attach(self.recovery)
        detector._align_scene(night,self.boxes['animal'])
        self.assertEqual(int(self.recovery.scene_background[20,20]),110)
        self.assertGreater(cv2.countNonZero(self.recovery.scene_mask[65:175,90:220]),10000)
        self.assertEqual(cv2.countNonZero(self.recovery.scene_mask[:60]),0)
        self.recovery.observe_scene(np.full_like(night,110))
        self.assertEqual(cv2.countNonZero(self.recovery.scene_mask),0)

    def test_recent_night_pose_continues_against_the_wall(self):
        detector=AnimalDetector(cv2,np);detector.attach(self.recovery)
        self.assertTrue(detector.detect(cv2.cvtColor(self.gray,cv2.COLOR_GRAY2BGR)))
        moved=self.background.copy();moved[65:175,190:320]=self.gray[65:175,90:220]
        self.recovery.find=Mock(return_value=None)
        found=detector.detect(cv2.cvtColor(moved,cv2.COLOR_GRAY2BGR))
        self.assertEqual(len(found),1)
        self.assertGreater(self.recovery._iou(found[0]['box'],(190,65,130,110)),.9)

    def test_stationary_animal_does_not_get_absorbed_into_background(self):
        for _ in range(20):self.recovery.observe_scene(self.gray)
        self.assertGreater(cv2.countNonZero(self.recovery.scene_mask),10000)
        self.assertEqual(int(self.recovery.scene_background[100,150]),220)

    def test_uniform_exposure_change_does_not_create_foreground(self):
        self.recovery.scene_background=self.gray.copy()
        self.recovery.observe_scene((self.gray.astype(float)*.95).astype(np.uint8))
        self.assertLess(cv2.countNonZero(self.recovery.scene_mask),300)

    def test_semantic_free_scene_detector_restores_rotated_animal(self):
        d=AnimalDetector(cv2,np);d.attach(self.recovery)
        image=cv2.warpAffine(self.gray,cv2.getRotationMatrix2D((160,120),90,1),(320,240),borderValue=220)
        detections=d.detect(cv2.cvtColor(image,cv2.COLOR_GRAY2BGR))
        self.assertEqual(len(detections),1)
        self.assertGreater(detections[0]['confidence'],.8)
        self.assertIsNotNone(self.recovery.find(image))

    def test_periodic_identity_check_does_not_jitter_a_stable_surface(self):
        detector=AnimalDetector(cv2,np);detector.attach(self.recovery)
        frame=cv2.cvtColor(self.gray,cv2.COLOR_GRAY2BGR)
        first=detector.detect(frame);self.assertTrue(first)
        detector.hint=first[0]['box'];detector.last_full=-1000
        self.recovery.find=Mock(return_value={'boxes':{'animal':(95,70,125,105)},'confidence':.85})
        result=detector.detect(frame)
        self.assertEqual(result[0]['box'],detector.hint)
        self.assertGreater(result[0]['confidence'],.95)

    def test_short_pose_gap_uses_recent_foreground_continuity(self):
        d=AnimalDetector(cv2,np);d.attach(self.recovery)
        self.assertTrue(d.detect(cv2.cvtColor(self.gray,cv2.COLOR_GRAY2BGR)))
        moved=cv2.warpAffine(self.gray,cv2.getRotationMatrix2D((160,120),90,1),(320,240),borderValue=220)
        self.recovery.find=Mock(return_value=None)
        self.assertTrue(d.detect(cv2.cvtColor(moved,cv2.COLOR_GRAY2BGR)))

    def test_continuity_does_not_keep_an_empty_incubator_locked(self):
        d=AnimalDetector(cv2,np);d.attach(self.recovery)
        self.assertTrue(d.detect(cv2.cvtColor(self.gray,cv2.COLOR_GRAY2BGR)))
        d.hint=self.boxes['animal'];self.recovery.find=Mock(return_value=None)
        self.assertEqual(d.detect(cv2.cvtColor(self.background,cv2.COLOR_GRAY2BGR)),[])

    def test_continuity_expires_after_long_occlusion(self):
        d=AnimalDetector(cv2,np);d.attach(self.recovery)
        self.assertTrue(d.detect(cv2.cvtColor(self.gray,cv2.COLOR_GRAY2BGR)))
        d.last_seen=-1000;self.recovery.find=Mock(return_value=None)
        self.assertEqual(d.detect(cv2.cvtColor(self.gray,cv2.COLOR_GRAY2BGR)),[])

    def test_cached_pose_seeds_recovery_without_retrusting_old_coordinates(self):
        d=AnimalDetector(cv2,np);d.attach(self.recovery,self.gray,self.boxes['animal'])
        moved=cv2.warpAffine(self.gray,cv2.getRotationMatrix2D((160,120),90,1),(320,240),borderValue=220)
        self.recovery.find=Mock(return_value=None)
        result=d.detect(cv2.cvtColor(moved,cv2.COLOR_GRAY2BGR))
        self.assertTrue(result);self.assertNotEqual(result[0]['box'],self.boxes['animal'])

    def test_empty_incubator_does_not_lock(self):
        d=AnimalDetector(cv2,np);d.attach(self.recovery)
        self.assertEqual(d.detect(cv2.cvtColor(self.background,cv2.COLOR_GRAY2BGR)),[])

    def test_confirmed_body_and_chest_restore_independently(self):
        detector=Mock();detector.detect.return_value=[{'box':self.boxes['animal'],'confidence':.95}]
        t=DetectorTracker(cv2,np,detector);t.initialize(self.gray,self.regions,0)
        for n in range(31):t.update_color(cv2.cvtColor(self.gray,cv2.COLOR_GRAY2BGR),self.gray,n*.2)
        self.assertEqual(t.state,'locked');self.assertTrue(t.respiration_ready)

    def test_body_without_matching_chest_keeps_life_tracking_only(self):
        detector=Mock();detector.detect.return_value=[{'box':self.boxes['animal'],'confidence':.95}]
        t=DetectorTracker(cv2,np,detector);t.initialize(self.gray,self.regions,0)
        t.recovery.find_chest_features=Mock(return_value=None);t.recovery.find_local_chest=Mock(return_value=None)
        for n in range(31):t.update_color(cv2.cvtColor(self.gray,cv2.COLOR_GRAY2BGR),self.gray,n*.2)
        self.assertEqual(t.state,'locked');self.assertFalse(t.respiration_ready)

    def test_multiple_animals_invalidate_chest_and_body(self):
        detector=Mock();detector.detect.return_value=[{'box':self.boxes['animal'],'confidence':.95}]*2
        t=DetectorTracker(cv2,np,detector);t.initialize(self.gray,self.regions,0)
        t.update_color(cv2.cvtColor(self.gray,cv2.COLOR_GRAY2BGR),self.gray,1)
        self.assertEqual(t.state,'lost');self.assertFalse(t.respiration_ready)
        self.assertEqual(t.reason,'multiple_animals')

    def test_missing_detection_reason_survives_between_detector_checks(self):
        detector=Mock();detector.detect.return_value=[]
        t=DetectorTracker(cv2,np,detector);t.initialize(self.gray,self.regions,0)
        frame=cv2.cvtColor(self.gray,cv2.COLOR_GRAY2BGR)
        t.update_color(frame,self.gray,1)
        t.update_color(frame,self.gray,1.5)
        self.assertEqual(t.reason,'animal_not_detected')

    def test_torso_features_match_without_requiring_rigid_whole_body(self):
        self.assertIsNotNone(self.recovery.find_chest_features(self.gray,self.boxes['animal']))
        unrelated=np.random.default_rng(8).integers(0,255,(240,320),np.uint8)
        self.assertIsNone(self.recovery.find_chest_features(unrelated,self.boxes['animal']))

    def test_torso_correspondence_outside_detected_animal_is_rejected(self):
        self.assertIsNone(self.recovery.find_chest_features(self.gray,(10,10,50,50)))

    def test_surface_candidate_is_interior_and_textured(self):
        self.recovery.observe_scene(self.gray)
        surface=self.recovery.find_surface(self.gray,self.boxes['animal'])
        self.assertIsNotNone(surface)
        x,y,w,h=map(round,surface)
        self.assertGreaterEqual(w*h,120)
        self.assertTrue((self.recovery.scene_mask[y:y+h,x:x+w]>0).all())

    def test_scene_surfaces_do_not_create_anatomical_references(self):
        detector=Mock();detector.detect.return_value=[{'box':self.boxes['animal'],'confidence':.95}]
        t=DetectorTracker(cv2,np,detector);t.initialize(self.gray,self.regions,0)
        t.recovery.scene_background=self.background.copy();t.recovery.observe_scene(self.gray)
        t.recovery.find_chest_features=Mock(return_value=None);t.recovery.find_local_chest=Mock(return_value=None)
        original=t.recovery.references[0]['chest'].copy()
        for n in range(56):t.update_color(cv2.cvtColor(self.gray,cv2.COLOR_GRAY2BGR),self.gray,n*.2)
        self.assertTrue(t.respiration_ready);self.assertEqual(t.respiration_source,'surface')
        self.assertEqual(sum(ref['chest'] is not None for ref in t.recovery.references),1)
        self.assertTrue(all('respiration' not in ref['boxes'] for ref in t.recovery.references[1:]))
        np.testing.assert_array_equal(t.recovery.references[0]['chest'],original)

    def test_flat_surface_is_not_a_respiration_candidate(self):
        self.recovery.scene_mask=np.full_like(self.gray,255)
        self.assertIsNone(self.recovery.find_surface(self.background,self.boxes['animal']))

    def test_known_local_chest_can_match_without_rigid_whole_body(self):
        other=self.background.copy();other[90:122,150:190]=self.gray[100:132,130:170]
        box=self.recovery.find_local_chest(other,(80,60,160,120))
        self.assertIsNotNone(box)
        self.assertAlmostEqual(box[0],150,delta=2);self.assertAlmostEqual(box[1],90,delta=2)

    def test_repeated_chest_texture_is_ambiguous(self):
        other=self.background.copy();other[90:122,110:150]=self.gray[100:132,130:170]
        other[130:162,180:220]=self.gray[100:132,130:170]
        self.assertIsNone(self.recovery.find_local_chest(other,(80,60,170,130)))

    def test_local_chest_is_not_invented_for_unrelated_image(self):
        self.assertIsNone(self.recovery.find_local_chest(self.background,(80,60,160,120)))

    def test_static_scene_checks_are_sparse(self):
        detector=Mock();detector.detect.return_value=[{'box':self.boxes['animal'],'confidence':.95}]
        t=DetectorTracker(cv2,np,detector);t.initialize(self.gray,self.regions,0)
        for n in range(151):t.update_color(cv2.cvtColor(self.gray,cv2.COLOR_GRAY2BGR),self.gray,n*.2)
        self.assertLessEqual(detector.detect.call_count,9)

if __name__=='__main__':unittest.main()
