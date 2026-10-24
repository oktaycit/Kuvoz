import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from lib.ai.ip_camera import IPCamera


class AvReaderTests(unittest.TestCase):
    def test_tcp_keyframe_gate_corruption_and_bounded_conversion(self):
        reader=IPCamera.__new__(IPCamera)
        reader.cv2=Mock();reader.url='rtsp://camera/live';reader.resolver=Mock();reader.resolver.resolve.return_value=reader.url
        reader.resolution=(320,240);reader._stop=threading.Event()
        reader._lock=threading.Lock();reader._sequence=0;reader._frame=None
        reader.set_analysis_fps(1)
        frames=[Mock(key_frame=k,is_corrupt=c) for k,c in
                [(False,False),(True,True),(True,False),(False,False),(False,False)]]
        for f in frames:f.to_ndarray.return_value=SimpleNamespace(shape=(240,320,3))
        stream=SimpleNamespace(codec_context=SimpleNamespace(thread_count=0))
        container=Mock();container.streams.video=[stream]
        def decode(s):
            yield from frames
            reader._stop.set()
        container.decode.side_effect=decode
        context=Mock();context.__enter__=Mock(return_value=container)
        context.__exit__=Mock(return_value=False)
        fake=Mock();fake.open.return_value=context
        with patch('lib.ai.ip_camera.av',fake), patch('lib.ai.ip_camera.time.monotonic',return_value=1):
            reader._run_av()
        fake.open.assert_called_once_with(reader.url,options={'rtsp_transport':'tcp'},timeout=(3,5))
        self.assertEqual(stream.codec_context.thread_count,1)
        self.assertEqual(reader._sequence,1)
        frames[0].to_ndarray.assert_not_called()
        frames[1].to_ndarray.assert_not_called()
        frames[2].to_ndarray.assert_called_once()
        frames[3].to_ndarray.assert_not_called()
        self.assertIsNone(reader._frame)
        context.__exit__.assert_called_once()

    def test_decoder_error_clears_stale_frame_and_retries(self):
        reader=IPCamera.__new__(IPCamera)
        reader.cv2=Mock();reader.url='rtsp://camera/live';reader.resolver=Mock();reader.resolver.resolve.return_value=reader.url;reader._lock=threading.Lock()
        reader._frame=object();reader._timestamp=123
        reader._stop=Mock();reader._stop.is_set.side_effect=[False,True]
        fake=Mock();fake.open.side_effect=RuntimeError('connection failed')
        with patch('lib.ai.ip_camera.av',fake):reader._run_av()
        self.assertIsNone(reader._frame)
        self.assertEqual(reader._timestamp,0)
        reader._stop.wait.assert_called_once_with(2)
