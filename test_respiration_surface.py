import unittest
try:
    import cv2
    import numpy as np
except ImportError:
    cv2=np=None
from lib.ai.respiration_surface import RespirationSurface


@unittest.skipUnless(cv2 is not None, 'OpenCV gerekli')
class SurfaceTests(unittest.TestCase):
    def simulate(self, mode):
        guard=RespirationSurface(cv2,np);random=np.random.default_rng(72)
        base=np.repeat(np.tile(np.linspace(50,220,320,dtype=np.float32),(240,1))[:,:,None],3,axis=2)
        base[100:132,130:170]=random.uniform(80,120,(32,40,1))
        for n in range(270):
            t=n*.2;frame=base.copy();signal=3*np.sin(2*np.pi*.4*t)
            if mode=='breathing':frame[100:132,130:170]+=signal
            elif mode=='illumination':frame+=signal
            elif mode=='gain':frame=frame*(1+signal*.02)+signal
            elif mode=='one_patch':frame[100:116,130:150]+=signal
            elif mode=='noise':
                for y,x in [(100,130),(100,150),(116,130),(116,150)]:frame[y:y+16,x:x+20]+=random.normal(0,3)
            elif mode=='ramp':frame[100:132,130:170]+=t*.1
            guard.add(np.clip(frame,0,255).astype(np.uint8),(130,100,40,32),(90,60,130,110),t)
        return guard

    def test_coherent_periodic_surface_is_recognized(self):
        result=self.simulate('breathing').estimate()
        self.assertEqual(result['status'],'OK');self.assertAlmostEqual(result['respiration_bpm'],24,delta=1)
        self.assertGreater(result['confidence'],.8)

    def test_global_flicker_does_not_become_respiration(self):
        self.assertIsNone(self.simulate('illumination').estimate()['respiration_bpm'])

    def test_exposure_gain_and_offset_do_not_become_respiration(self):
        self.assertIsNone(self.simulate('gain').estimate()['respiration_bpm'])

    def test_independent_noise_does_not_become_respiration(self):
        self.assertIsNone(self.simulate('noise').estimate()['respiration_bpm'])

    def test_single_moving_patch_is_insufficient(self):
        self.assertIsNone(self.simulate('one_patch').estimate()['respiration_bpm'])

    def test_posture_brightness_drift_is_rejected(self):
        self.assertIsNone(self.simulate('ramp').estimate()['respiration_bpm'])

    def test_reset_drops_old_window(self):
        guard=self.simulate('breathing');guard.reset()
        self.assertEqual(len(guard.samples),0);self.assertIsNone(guard.estimate()['respiration_bpm'])

    def test_discontinuous_capture_does_not_produce_rate(self):
        guard=self.simulate('breathing');guard.samples[-1]=(100.,guard.samples[-1][1])
        self.assertIsNone(guard.estimate()['respiration_bpm'])

if __name__=='__main__':unittest.main()
