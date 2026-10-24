import unittest
from unittest.mock import Mock, patch
try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = np = None
from lib.ai.region_tracker import RegionTracker
from lib.ai.vision import VisionEngine

BOXES={'animal':{'x':.25,'y':.25,'width':.5,'height':.5},
       'respiration':{'x':.4,'y':.4,'width':.15,'height':.15}}


@unittest.skipUnless(cv2 is not None, 'OpenCV gerekli')
class RegionTrackingTests(unittest.TestCase):
    def setUp(self):
        self.frame=np.zeros((240,320),np.uint8)
        rng=np.random.default_rng(42)
        self.frame[60:180,80:240]=rng.integers(25,230,(120,160),dtype=np.uint8)
        self.tracker=RegionTracker(cv2,np)
        self.tracker.initialize(self.frame,BOXES,0)

    def test_locks_only_after_stable_frames(self):
        self.assertEqual(self.tracker.state,'acquiring')
        for t in [.2,.4,.6]:self.tracker.update(self.frame,t)
        self.assertEqual(self.tracker.state,'locked')

    def test_cached_reference_revalidates_appearance_before_template(self):
        self.tracker.lose('restoring_reference')
        self.tracker.recovery_kind='cached'
        with patch.object(self.tracker,'_appearance_search',return_value=True) as find, \
             patch.object(cv2,'matchTemplate',side_effect=AssertionError('Stale template used')):
            self.tracker.update(self.frame,1)
        find.assert_called_once()

    def test_head_motion_does_not_break_a_stable_verified_torso(self):
        # Move only the head-side quarter; the selected torso is unchanged.
        changed=self.frame.copy()
        changed[60:180,80:120]=np.random.default_rng(9).integers(25,230,(120,40),dtype=np.uint8)
        for i in range(1,10):self.tracker.update(changed,i*.2)
        self.assertEqual(self.tracker.state,'locked')
        self.assertTrue(self.tracker.respiration_ready)
        self.assertGreaterEqual(self.tracker.confidence,.8)

    def test_verified_torso_occlusion_invalidates_respiration(self):
        changed=self.frame.copy();changed[96:132,128:176]=0
        self.tracker.update(changed,.2)
        self.assertEqual(self.tracker.state,'lost')
        self.assertFalse(self.tracker.respiration_ready)

    def test_flow_pyramids_only_cover_local_search_window(self):
        with patch.object(cv2, 'calcOpticalFlowPyrLK', wraps=cv2.calcOpticalFlowPyrLK) as flow:
            self.tracker.update(self.frame,.2)
        self.assertEqual(flow.call_count,2)
        for call in flow.call_args_list:
            self.assertLess(call.args[0].size,self.frame.size)
            self.assertEqual(call.args[0].shape,call.args[1].shape)

    def test_features_are_reused_between_refreshes(self):
        with patch.object(self.tracker,'_features',wraps=self.tracker._features) as features:
            for t in [.2,.4,.6,.8]:self.tracker.update(self.frame,t)
            features.assert_not_called()
            self.tracker.update(self.frame,1.61)
            features.assert_called_once()

    def test_stationary_body_flow_slows_down_but_occlusion_is_immediate(self):
        for t in [.2,.4,.6]:self.tracker.update(self.frame,t)
        with patch.object(cv2,'calcOpticalFlowPyrLK',wraps=cv2.calcOpticalFlowPyrLK) as flow:
            for t in [.8,1.0,1.2,1.4]:self.tracker.update(self.frame,t)
            flow.assert_not_called()
            self.tracker.update(np.zeros_like(self.frame),1.5)
            self.assertEqual(self.tracker.state,'lost')

    def test_movement_decision_is_independent_of_sample_interval(self):
        shifted=cv2.warpAffine(self.frame,np.float32([[1,0,3],[0,1,2]]),(320,240))
        self.tracker.update(shifted,.5)
        self.assertEqual(self.tracker.state,'moving')
        self.assertGreater(self.tracker.motion_activity,5)

    def test_subpixel_scale_noise_does_not_resize_respiration_window(self):
        matrix=np.array([[1.005,0,-.8],[0,1.005,-.6]])
        with patch.object(cv2,'estimateAffinePartial2D',return_value=(matrix,np.ones((40,1),np.uint8))):
            self.tracker.update(self.frame,.2)
        boxes=self.tracker.normalized_boxes(self.frame.shape)
        self.assertAlmostEqual(boxes['animal']['width'],BOXES['animal']['width'])
        self.assertAlmostEqual(boxes['respiration']['width'],BOXES['respiration']['width'])

    def test_translates_both_boxes_with_same_displacement(self):
        transform=np.float32([[1,0,3],[0,1,2]])
        shifted=cv2.warpAffine(self.frame,transform,(320,240))
        self.tracker.update(shifted,.2)
        self.assertEqual(self.tracker.state,'moving')
        boxes=self.tracker.normalized_boxes(self.frame.shape)
        for name in BOXES:
            self.assertAlmostEqual(boxes[name]['x']-BOXES[name]['x'],3/320,delta=.003)
            self.assertAlmostEqual(boxes[name]['y']-BOXES[name]['y'],2/240,delta=.003)
        for t in [.4,.6,.8]:self.tracker.update(shifted,t)
        self.assertEqual(self.tracker.state,'locked')

    def test_returning_image_cannot_immediately_reacquire(self):
        self.tracker.update(np.zeros_like(self.frame),.2)
        self.assertEqual(self.tracker.state,'lost')
        self.tracker.update(self.frame,.4)
        self.assertEqual(self.tracker.state,'lost')
        self.tracker.initialize(self.frame,BOXES,.6)
        self.assertEqual(self.tracker.state,'acquiring')

    def test_gap_rejects_stale_frame(self):
        self.tracker.update(self.frame,3)
        self.assertEqual(self.tracker.state,'lost')
        self.assertEqual(self.tracker.reason,'frame_gap')

    def test_blank_selection_cannot_lock(self):
        self.tracker.initialize(np.zeros_like(self.frame),BOXES,0)
        self.assertEqual(self.tracker.state,'lost')

    def test_flat_decoder_start_retries_selection_when_image_arrives(self):
        self.tracker.initialize(np.zeros_like(self.frame),BOXES,0)
        self.tracker.update(self.frame,1)
        self.assertEqual(self.tracker.state,'acquiring')
        for t in [1.2,1.4,1.6]:self.tracker.update(self.frame,t)
        self.assertEqual(self.tracker.state,'locked')

    def test_rotation_pauses_tracking(self):
        matrix=cv2.getRotationMatrix2D((160,120),10,1)
        rotated=cv2.warpAffine(self.frame,matrix,(320,240))
        self.tracker.update(rotated,.2)
        self.assertEqual(self.tracker.state,'lost')

    def test_reappearance_requires_repeated_match_then_stabilization(self):
        self.tracker.update(np.zeros_like(self.frame),.2)
        shifted=cv2.warpAffine(self.frame,np.float32([[1,0,12],[0,1,8]]),(320,240))
        for t in [.4,1.4,2.4]:self.tracker.update(shifted,t)
        self.assertEqual(self.tracker.state,'acquiring')
        boxes=self.tracker.normalized_boxes(self.frame.shape)
        self.assertAlmostEqual(boxes['animal']['x'],BOXES['animal']['x']+12/320,delta=.01)
        self.assertAlmostEqual(boxes['respiration']['x'],BOXES['respiration']['x']+12/320,delta=.01)
        for t in [2.6,2.8,3.0,3.2,3.4]:self.tracker.update(shifted,t)
        self.assertNotEqual(self.tracker.state,'locked')
        self.tracker.update(shifted,4.5)
        self.assertEqual(self.tracker.state,'locked')

    def test_unrelated_object_cannot_reacquire(self):
        self.tracker.lose('occluded')
        other=np.random.default_rng(98).integers(0,255,self.frame.shape,dtype=np.uint8)
        for t in [1,2,3,4]:self.tracker.update(other,t)
        self.assertEqual(self.tracker.state,'lost')

    def test_two_identical_candidates_are_rejected(self):
        self.tracker.lose('occluded')
        ambiguous=np.zeros_like(self.frame)
        ambiguous[60:180,:160]=self.frame[60:180,80:240]
        ambiguous[60:180,160:]=self.frame[60:180,80:240]
        for t in [1,2,3,4]:self.tracker.update(ambiguous,t)
        self.assertEqual(self.tracker.state,'lost')

    def test_one_candidate_flash_cannot_resume(self):
        self.tracker.lose('occluded')
        self.tracker.update(self.frame,1)
        self.tracker.update(np.zeros_like(self.frame),2)
        self.tracker.update(self.frame,3)
        self.assertEqual(self.tracker.state,'lost')
        self.assertEqual(self.tracker.candidate_hits,1)

    def test_sparse_matches_do_not_count_as_continuous_confirmation(self):
        self.tracker.lose('occluded')
        for t in [1,5,10]:self.tracker.update(self.frame,t)
        self.assertEqual(self.tracker.state,'lost')
        self.assertEqual(self.tracker.candidate_hits,1)


class RespirationSafetyTests(unittest.TestCase):
    def test_selected_respiration_cannot_bypass_lost_body_tracking(self):
        engine=VisionEngine()
        engine.animal_roi=BOXES['animal']
        engine.respiration_roi_enabled=True
        for state in ('lost','moving','acquiring'):
            engine.region_tracker=Mock(state=state)
            self.assertFalse(engine._region_vitals_allowed())
        engine.region_tracker=Mock(state='locked',confidence=.9)
        self.assertTrue(engine._region_vitals_allowed())
        engine.region_tracker.confidence=.7
        self.assertFalse(engine._region_vitals_allowed())

    def test_automatic_hold_is_not_a_valid_respiration_lock(self):
        engine=VisionEngine()
        engine.subject_tracking_state='holding'
        self.assertFalse(engine._region_vitals_allowed())

    @unittest.skipUnless(cv2 is not None, 'OpenCV gerekli')
    def test_loss_clears_previous_numeric_result(self):
        engine=VisionEngine()
        engine.set_system_settings({'animal_roi_enabled':True,'animal_roi':BOXES['animal'],
                                    'respiration_roi_enabled':True,'respiration_roi':BOXES['respiration']})
        frame=np.zeros((240,320,3),np.uint8)
        engine.latest_vitals={'status':'OK','respiration_bpm':25,'confidence':.9}
        engine._update_region_tracking(frame)
        self.assertIsNone(engine.latest_vitals['respiration_bpm'])
        self.assertEqual(engine.region_tracker.state,'lost')
        engine.latest_vitals={'status':'OK','respiration_bpm':25,'confidence':.9}
        engine._update_region_tracking(frame)
        self.assertIsNone(engine.latest_vitals['respiration_bpm'])


@unittest.skipUnless(cv2 is not None, 'OpenCV gerekli')
class RegionPipelineTests(unittest.TestCase):
    def test_selected_body_skips_contours_and_exports_full_frame_coordinates(self):
        from lib.data.ai_behavior_mapper import AIBehaviorMapper
        engine=VisionEngine(resolution=(320,240))
        engine.set_system_settings({'animal_roi_enabled':True,'animal_roi':BOXES['animal'],
                                    'respiration_roi_enabled':True,'respiration_roi':BOXES['respiration']})
        engine.running=True;engine.camera_type='ip';engine.camera=Mock()
        image=np.zeros((240,320),np.uint8)
        image[60:180,80:240]=np.random.default_rng(42).integers(25,230,(120,160),dtype=np.uint8)
        engine.camera.read.return_value=(True,cv2.cvtColor(image,cv2.COLOR_GRAY2BGR))
        engine._check_thermal_throttle=Mock()
        engine._find_motion_candidate_boxes=Mock(side_effect=AssertionError('Duplicate tracker'))
        with patch.object(cv2.ocl,'setUseOpenCL') as opencl:
            for _ in range(6):engine.process_frame()
            opencl.assert_called_once_with(False)
        status=engine.get_status()
        self.assertTrue(status['subject_tracking_locked'])
        for key,value in BOXES['animal'].items():
            self.assertAlmostEqual(status['subject_box'][key+'_norm'],value,delta=.01)
        self.assertLess(status['pixel_budget']['motion'],320*240*.3)
        behavior=AIBehaviorMapper().derive_behavior({'vision':status,'vitals':engine.get_vitals()})
        self.assertIsNotNone(behavior)
        self.assertEqual(behavior.behavior_type,'resting')

    def test_process_frame_never_keeps_numeric_result_after_occlusion(self):
        engine=VisionEngine(resolution=(320,240),fps=1)
        engine.set_system_settings({'camera_source':'ip','ip_camera_url':'rtsp://camera/live',
                                    'animal_roi_enabled':True,'animal_roi':BOXES['animal'],
                                    'respiration_roi_enabled':True,'respiration_roi':BOXES['respiration']})
        engine._camera_restart_pending=False
        engine.running=True
        engine.camera_type='opencv'
        engine.camera=Mock()
        engine._check_thermal_throttle=Mock()
        image=np.zeros((240,320),np.uint8)
        image[60:180,80:240]=np.random.default_rng(42).integers(25,230,(120,160),dtype=np.uint8)
        frame=cv2.cvtColor(image,cv2.COLOR_GRAY2BGR)
        engine.camera.read.return_value=(True,frame)
        for _ in range(5):engine.process_frame()
        self.assertEqual(engine.region_tracker.state,'locked')
        engine.latest_vitals={'status':'OK','respiration_bpm':25,'confidence':.9}
        engine.camera.read.return_value=(True,np.zeros_like(frame))
        engine.process_frame()
        self.assertEqual(engine.region_tracker.state,'lost')
        self.assertIsNone(engine.get_vitals()['respiration_bpm'])
        self.assertEqual(engine.status,'TRACKING_LOST')
        self.assertGreater(engine.activity_level,0)
        engine.camera.read.return_value=(True,frame)
        engine.process_frame()
        self.assertEqual(engine.region_tracker.state,'lost')
        self.assertIsNone(engine.get_vitals()['respiration_bpm'])
