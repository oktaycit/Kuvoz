import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from lib.ai.ip_camera import IPCamera, validate_camera_settings
from lib.ai.vision import VisionEngine


class CameraSettingsTests(unittest.TestCase):
    def test_old_settings_default_to_local(self):
        self.assertEqual(validate_camera_settings({}), ('raspberry_pi', ''))

    def test_rtsp_address_and_credentials_are_preserved(self):
        url = 'rtsp://user:password@192.168.1.175:554/live/ch00_1'
        self.assertEqual(validate_camera_settings({'camera_source': 'ip', 'ip_camera_url': url}), ('ip', url))

    def test_invalid_source_or_address_rejected(self):
        for data in ({'camera_source': 'other'}, {'camera_source': 'ip'},
                     {'ip_camera_url': 'file:///etc/passwd'},
                     {'ip_camera_url': 'rtsp://host:bad/path'},
                     {'ip_camera_url': 'rtsp://host/with space'}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                validate_camera_settings(data)

    def test_source_change_runs_on_analysis_thread(self):
        engine = VisionEngine()
        engine.running = True
        engine.stop = Mock(side_effect=lambda: setattr(engine, 'running', False))
        engine.start = Mock(return_value=False)
        engine.set_system_settings({'camera_source': 'ip', 'ip_camera_url': 'rtsp://camera/live'})
        engine.stop.assert_not_called()
        engine.process_frame()
        engine.stop.assert_called_once()
        engine.start.assert_called_once()
        self.assertIsNone(engine.latest_vitals['respiration_bpm'])

    def test_can_select_local_after_failed_camera_start(self):
        engine = VisionEngine()
        engine.camera_source = 'ip'
        engine.ip_camera_url = 'rtsp://camera/live'
        engine.set_system_settings({'camera_source': 'raspberry_pi'})
        self.assertTrue(engine._camera_restart_pending)

    def test_ip_selection_does_not_open_local_camera(self):
        engine = VisionEngine()
        engine.set_system_settings({'camera_source': 'ip', 'ip_camera_url': 'rtsp://camera/live'})
        with patch('lib.ai.vision.OPENCV_AVAILABLE', True), \
             patch('lib.ai.vision.cv2', create=True), \
             patch('lib.ai.vision.IPCamera') as capture:
            self.assertTrue(engine.start())
            capture.assert_called_once()
            self.assertEqual(engine.camera_type, 'ip')


class IPCameraRateTests(unittest.TestCase):
    def test_ip_uses_five_fps_with_low_rate_lifecycle_modes(self):
        engine = VisionEngine(fps=1)
        engine.set_system_settings({'camera_source': 'ip', 'ip_camera_url': 'rtsp://camera/live'})
        self.assertEqual(engine.target_fps, 5.0)
        engine._set_load_profile('idle', 'no_animal')
        self.assertEqual(engine.target_fps, 1.0)
        engine._set_load_profile('motion_limited', 'movement')
        self.assertEqual(engine.target_fps, 2.0)

    def test_local_rate_is_restored_and_invalid_rates_are_bounded(self):
        engine = VisionEngine(fps=1)
        for value, expected in [('bad', 5), (float('nan'), 5), (100, 8), (0, 3)]:
            engine.set_system_settings({'camera_source': 'ip', 'ip_camera_url': 'rtsp://camera/live', 'ip_camera_analysis_fps': value})
            self.assertEqual(engine.base_fps, expected)
        engine.set_system_settings({'camera_source': 'raspberry_pi'})
        self.assertEqual(engine.base_fps, engine.local_camera_fps)

    def test_rate_updates_do_not_reopen_camera(self):
        engine = VisionEngine()
        settings = {'camera_source': 'ip', 'ip_camera_url': 'rtsp://camera/live'}
        engine.set_system_settings(settings)
        engine._camera_restart_pending = False
        engine.set_system_settings(dict(settings, ip_camera_analysis_fps=3))
        self.assertFalse(engine._camera_restart_pending)
        self.assertEqual(engine.target_fps, 3)

    def test_thermal_cap_remains_in_force_after_settings_update(self):
        engine = VisionEngine()
        engine._throttled = True
        engine.set_system_settings({'camera_source': 'ip', 'ip_camera_url': 'rtsp://camera/live'})
        self.assertLessEqual(engine.target_fps, 1)

    def test_effective_rate_excludes_old_or_stopped_streams(self):
        engine = VisionEngine()
        with patch('lib.ai.vision.time.monotonic', return_value=10.0):
            engine._processed_frame_times.extend([8.0 + i * .2 for i in range(11)])
            self.assertAlmostEqual(engine._effective_analysis_fps(), 5.0)
        with patch('lib.ai.vision.time.monotonic', return_value=20.0):
            self.assertEqual(engine._effective_analysis_fps(), 0.0)

    def test_lost_selection_uses_slow_search_even_if_background_moves(self):
        engine=VisionEngine()
        engine.set_system_settings({'camera_source':'ip','ip_camera_url':'rtsp://camera/live'})
        engine.region_tracker=Mock(state='lost')
        engine.activity_level=50
        engine._update_load_profile(now=10)
        self.assertEqual(engine.target_fps,1)
        self.assertEqual(engine.load_reason,'tracking_lost')

    def test_temperature_read_is_shared_and_cached(self):
        engine=VisionEngine()
        with patch.object(engine,'_read_cpu_temp',return_value=50) as read, \
             patch('lib.ai.vision.time.monotonic',return_value=10):
            engine._check_thermal_throttle()
            engine.get_status()
            engine._check_thermal_throttle()
            read.assert_called_once()
        with patch.object(engine,'_read_cpu_temp',return_value=51) as read, \
             patch('lib.ai.vision.time.monotonic',return_value=15.1):
            self.assertEqual(engine._cached_cpu_temp(),51)
            read.assert_called_once()


class LatestFrameTests(unittest.TestCase):
    def reader(self):
        reader = IPCamera.__new__(IPCamera)
        reader._lock = threading.Lock()
        reader._frame = object()
        reader._timestamp = time.monotonic()
        reader._sequence = 3
        reader._consumed = 0
        return reader

    def test_only_newest_frame_is_consumed_once(self):
        reader = self.reader()
        self.assertTrue(reader.read()[0])
        self.assertEqual(reader.read(), (False, None))

    def test_stale_frames_are_rejected(self):
        reader = self.reader()
        reader._timestamp -= 4
        self.assertFalse(reader.is_fresh())
        self.assertEqual(reader.read(), (False, None))

    def test_disconnect_clears_old_image_and_measurement(self):
        engine = VisionEngine()
        engine.running = True
        engine.camera_type = 'ip'
        engine.camera = Mock()
        engine.camera.read.return_value = (False, None)
        engine.camera.is_fresh.return_value = False
        engine.latest_jpeg = b'old-image'
        engine.latest_vitals = {'respiration_bpm': 30}
        engine.process_frame()
        self.assertIsNone(engine.get_frame())
        self.assertIsNone(engine.latest_vitals['respiration_bpm'])
        self.assertEqual(engine.status, 'DISCONNECTED')

    def test_worker_releases_capture_when_stopped(self):
        reader = self.reader()
        reader._stop = threading.Event()
        reader.url = 'rtsp://camera/live'
        reader.resolver = Mock(); reader.resolver.resolve.return_value = reader.url
        reader.cv2 = Mock()
        reader.resolution = (320, 240)
        reader.set_analysis_fps(5)
        capture = reader.cv2.VideoCapture.return_value
        def grab():
            reader._stop.set()
            return False
        capture.grab.side_effect = grab
        reader._run()
        reader.cv2.ocl.setUseOpenCL.assert_called_once_with(False)
        capture.release.assert_called_once()
        self.assertIsNone(reader._frame)

    def test_worker_skips_unneeded_conversion_but_grabs_every_frame(self):
        reader=self.reader();reader._stop=threading.Event()
        reader.url='rtsp://camera/live';reader.resolver=Mock();reader.resolver.resolve.return_value=reader.url;reader.cv2=Mock()
        reader.resolution=(320,240);reader.set_analysis_fps(1)
        cap=reader.cv2.VideoCapture.return_value
        cap.retrieve.return_value=(True,SimpleNamespace(shape=(480,480,3)))
        calls=[]
        def grab():
            calls.append(1)
            if len(calls)>10:
                reader._stop.set();return False
            return True
        cap.grab.side_effect=grab
        ticks=iter(i*.01 for i in range(100))
        with patch('lib.ai.ip_camera.time.monotonic',side_effect=lambda:next(ticks)):
            reader._run()
        self.assertEqual(cap.grab.call_count,11)
        self.assertLessEqual(cap.retrieve.call_count,2)
        self.assertEqual(reader.cv2.resize.call_count,cap.retrieve.call_count)
        cap.release.assert_called_once()

    def test_connection_warmup_does_not_publish_decoder_startup_frames(self):
        reader=self.reader();reader._stop=threading.Event();reader.cv2=Mock()
        reader.url='rtsp://camera/live';reader.resolver=Mock();reader.resolver.resolve.return_value=reader.url;reader._warmup_seconds=10
        cap=reader.cv2.VideoCapture.return_value
        def grab():
            if cap.grab.call_count>4:reader._stop.set();return False
            return True
        cap.grab.side_effect=grab
        with patch('lib.ai.ip_camera.time.monotonic',return_value=1):reader._run()
        cap.retrieve.assert_not_called()
        self.assertIsNone(reader._frame)


if __name__ == '__main__':
    unittest.main()
