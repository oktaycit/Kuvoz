import unittest
import numpy as np
import cv2
from lib.ai.lens_correction import LensCorrection, lens_settings_update
from lib.ai.vision import VisionEngine


class LensCorrectionTests(unittest.TestCase):
    def setUp(self):
        self.lens=LensCorrection(cv2,np)

    def test_default_is_exactly_original_and_allocates_no_maps(self):
        frame=np.zeros((240,320,3),np.uint8)
        for mode in ('off',None,'invalid',[]):
            self.assertIs(self.lens.apply(frame,mode),frame)
        self.assertEqual(len(self.lens.maps),0)

    def test_straightens_a_known_barrel_curve(self):
        width,height=320,240
        camera=np.array([[width/2,0,width/2],[0,height/2,height/2],[0,0,1.]])
        points=np.array([[.6,y,1.] for y in np.linspace(-1.5,1.5,500)],np.float64)
        distorted,_=cv2.projectPoints(points,np.zeros(3),np.zeros(3),camera,np.array([-.18,.03,0.,0.,0.]))
        source=np.zeros((height,width,3),np.uint8)
        cv2.polylines(source,[np.round(distorted).astype(np.int32)],False,(255,255,255),2)
        output=self.lens.apply(source,'flat')
        columns=[]
        for row in range(40,200):
            candidates=np.flatnonzero(output[row,:,0]>180)
            if len(candidates):columns.append(float(candidates.mean()))
        self.assertGreater(len(columns),140)
        self.assertLess(max(columns)-min(columns),3)
        self.assertAlmostEqual(np.mean(columns),width/2+.6*width/2,delta=2)

    def test_maps_are_reused_and_memory_is_bounded(self):
        frame=np.zeros((120,160,3),np.uint8)
        self.lens.apply(frame,'wide');maps=self.lens.maps[('wide',160,120)]
        self.lens.apply(frame,'wide');self.assertIs(self.lens.maps[('wide',160,120)],maps)
        for size in range(6):self.lens.apply(np.zeros((120,160+size,3),np.uint8),'flat')
        self.assertLessEqual(len(self.lens.maps),4)

    def test_analysis_and_preview_use_matching_normalized_geometry(self):
        for size in ((320,240),(960,960)):
            self.lens.apply(np.zeros((size[1],size[0],3),np.uint8),'wide')
        normalized=[]
        for width,height in ((320,240),(960,960)):
            a,b=self.lens.maps[('wide',width,height)]
            x,y=cv2.convertMaps(a,b,cv2.CV_32FC1)
            normalized.append((x[height//4,width*3//4]/width,y[height//4,width*3//4]/height))
        np.testing.assert_allclose(normalized[0],normalized[1],atol=.001)

    def test_projection_change_resets_tracker_identity(self):
        engine=VisionEngine();engine.set_system_settings({})
        engine.last_frame=np.zeros((240,320),np.uint8)
        engine.set_system_settings({'camera_lens_correction':'wide'})
        self.assertIsNone(engine.last_frame)
        self.assertEqual(engine.camera_lens_correction,'wide')

    def test_changed_projection_disables_old_regions_but_preserves_other_settings(self):
        update=lens_settings_update({},dict(camera_lens_correction='wide',animal_roi_enabled=True,ai_enabled=True))
        for name in ('animal','respiration','feeding','drinking'):
            self.assertFalse(update[name+'_roi_enabled'])
        self.assertTrue(update['ai_enabled'])
        same=lens_settings_update({'camera_lens_correction':'wide'},dict(camera_lens_correction='wide',animal_roi_enabled=True))
        self.assertTrue(same['animal_roi_enabled'])
        with self.assertRaises(ValueError):lens_settings_update({},dict(camera_lens_correction=[]))

    def test_both_streams_are_corrected_before_the_same_orientation(self):
        engine=VisionEngine(resolution=(320,240));engine.camera_type='ip'
        engine.set_system_settings({'camera_source':'ip','ip_camera_url':'rtsp://camera/live',
                                    'camera_lens_correction':'wide','camera_transform':'flip_vertical'})
        frame=np.random.default_rng(2).integers(0,256,(240,320,3),dtype=np.uint8)
        analysis,preview=engine._prepare_capture_frames(frame)
        expected=cv2.flip(self.lens.apply(frame,'wide'),0)
        np.testing.assert_array_equal(analysis,expected)
        np.testing.assert_array_equal(preview,expected)
