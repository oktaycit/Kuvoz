import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, MagicMock, patch
from lib.ai.hd_preview import KeyframePreview
from lib.ai.ip_camera import validate_preview_url

class HDPreviewTests(unittest.TestCase):
    def reader(self):
        r=KeyframePreview.__new__(KeyframePreview)
        r.cv=Mock();r.url='rtsp://camera/live/ch00_0';r.resolution=(1280,960)
        r._stop=threading.Event();r._lock=threading.Lock()
        r.resolver=Mock();r.resolver.resolve.return_value=r.url
        r._frame=None;r._timestamp=0;r.thread=None
        return r

    def test_only_same_camera_can_supply_preview(self):
        self.assertEqual(validate_preview_url({},'rtsp://camera/live/ch00_1'),'')
        self.assertEqual(validate_preview_url({'ip_camera_preview_url':'rtsp://camera/live/ch00_0'},'rtsp://camera/live/ch00_1'),'rtsp://camera/live/ch00_0')
        for url in ('http://camera/image','rtsp://camera:0/live'):
            with self.assertRaises(ValueError):validate_preview_url({'ip_camera_preview_url':url},'rtsp://camera/live')

    def test_stale_hd_frames_are_not_used(self):
        r=self.reader();r._frame=object();r._timestamp=10
        with patch('lib.ai.hd_preview.time.monotonic',return_value=13):self.assertIsNotNone(r.read())
        with patch('lib.ai.hd_preview.time.monotonic',return_value=14):self.assertIsNone(r.read())

    def test_decoder_uses_only_keyframes_and_one_thread(self):
        r=self.reader();av=MagicMock();container=MagicMock();av.open.return_value.__enter__.return_value=container
        stream=Mock();container.streams.video=[stream]
        ignored=Mock(key_frame=False,is_corrupt=False)
        key=Mock(key_frame=True,is_corrupt=False)
        image=SimpleNamespace(shape=(480,480,3))
        def convert(**kwargs):r._stop.set();return image
        key.to_ndarray.side_effect=convert
        container.decode.return_value=iter([ignored,key])
        with patch('lib.ai.hd_preview.av',av):r._run()
        self.assertEqual(stream.codec_context.skip_frame,'NONKEY')
        self.assertEqual(stream.codec_context.thread_count,1)
        ignored.to_ndarray.assert_not_called();key.to_ndarray.assert_called_once()
        self.assertIsNone(r._frame)

    def test_unavailable_decoder_preserves_fallback(self):
        with patch('lib.ai.hd_preview.av',None):r=KeyframePreview(Mock(),'rtsp://camera/live',(1280,960))
        self.assertIsNone(r.thread);self.assertIsNone(r.read());r.release()

    def test_replacing_or_disabling_camera_drops_old_preview(self):
        settings={'ip_camera_preview_url':'rtsp://old-camera/live/ch00_0'}
        self.assertEqual(validate_preview_url(settings,'rtsp://new-camera/live/ch00_1'),'')
        self.assertEqual(validate_preview_url(settings,''),'')
