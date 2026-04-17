import math
import unittest

try:
    import numpy as np
except Exception:  # pragma: no cover - test environment fallback
    np = None

from lib.ai.vital_signs import VitalSignsEstimator
from lib.ai.vision import VisionEngine


@unittest.skipUnless(np is not None, "numpy gerekli")
class VisionVitalSignalTests(unittest.TestCase):
    def setUp(self):
        self.engine = VisionEngine(fps=5)

    def test_vital_signal_uses_mean_delta_inside_tracked_subject(self):
        frame_delta = np.zeros((100, 100), dtype=np.uint8)
        frame_delta[40:60, 40:60] = 18

        signal = self.engine._calculate_vital_signal(frame_delta, (30, 30, 70, 70))

        expected = ((18 * 20 * 20) / (40 * 40)) / 2.55
        self.assertAlmostEqual(signal, expected, places=3)
        self.assertGreater(signal, 1.0)
        self.assertLess(signal, 2.0)


class VitalSignsEstimatorTests(unittest.TestCase):
    def test_estimator_resolves_subtle_periodic_respiration_signal(self):
        estimator = VitalSignsEstimator(window_seconds=60.0, min_bpm=5.0, max_bpm=80.0)
        target_bpm = 24.0
        period_seconds = 60.0 / target_bpm
        fps = 5.0

        for index in range(int(60 * fps)):
            t = index / fps
            respiration_wave = 0.22 + (0.16 * math.sin((2.0 * math.pi * t) / period_seconds))
            slow_drift = 0.03 * math.sin((2.0 * math.pi * t) / 18.0)
            estimator.add_sample(respiration_wave + slow_drift, t=t)

        result = estimator.get_estimate()

        self.assertEqual(result["status"], "OK")
        self.assertIsNotNone(result["respiration_bpm"])
        self.assertGreaterEqual(result["confidence"], 0.5)
        self.assertAlmostEqual(result["respiration_bpm"], target_bpm, delta=2.0)

    def test_estimator_suppresses_sparse_spike_artifacts(self):
        estimator = VitalSignsEstimator(window_seconds=60.0, min_bpm=5.0, max_bpm=80.0)
        target_bpm = 24.0
        period_seconds = 60.0 / target_bpm
        fps = 5.0
        spike_indices = {50, 90, 140, 190, 240}

        for index in range(int(60 * fps)):
            t = index / fps
            respiration_wave = 0.22 + (0.16 * math.sin((2.0 * math.pi * t) / period_seconds))
            if index in spike_indices:
                respiration_wave += 1.2
            estimator.add_sample(respiration_wave, t=t)

        result = estimator.get_estimate()

        self.assertEqual(result["status"], "OK")
        self.assertIsNotNone(result["respiration_bpm"])
        self.assertAlmostEqual(result["respiration_bpm"], target_bpm, delta=3.0)
        self.assertGreaterEqual(result["confidence"], 0.5)

    def test_estimator_marks_heavily_corrupted_signal_low_confidence(self):
        estimator = VitalSignsEstimator(window_seconds=60.0, min_bpm=5.0, max_bpm=80.0)
        target_bpm = 24.0
        period_seconds = 60.0 / target_bpm
        fps = 5.0

        for index in range(int(60 * fps)):
            t = index / fps
            respiration_wave = 0.22 + (0.16 * math.sin((2.0 * math.pi * t) / period_seconds))
            if 50 <= index < 60:
                respiration_wave += 1.2
            estimator.add_sample(respiration_wave, t=t)

        result = estimator.get_estimate()

        self.assertEqual(result["status"], "LOW_CONF")
        self.assertIsNone(result["respiration_bpm"])

    def test_rejects_high_bpm_when_supported_by_too_few_peaks(self):
        estimator = VitalSignsEstimator(window_seconds=60.0, min_bpm=5.0, max_bpm=80.0)

        self.assertTrue(
            estimator._should_reject_short_peak_tachypnea(
                bpm=44.8,
                peak_count=3,
                interval_count=2,
            )
        )
        self.assertFalse(
            estimator._should_reject_short_peak_tachypnea(
                bpm=27.0,
                peak_count=3,
                interval_count=2,
            )
        )

    def test_rejects_sudden_large_jump_without_strong_support(self):
        estimator = VitalSignsEstimator(window_seconds=60.0, min_bpm=5.0, max_bpm=80.0)
        estimator._last_reliable_bpm = 16.0
        estimator._last_reliable_ts = 10.0

        self.assertTrue(
            estimator._should_reject_sudden_jump(
                bpm=44.8,
                confidence=0.84,
                peak_count=3,
                interval_support=0.7,
                now=40.0,
            )
        )
        self.assertFalse(
            estimator._should_reject_sudden_jump(
                bpm=44.8,
                confidence=0.9,
                peak_count=9,
                interval_support=0.9,
                now=40.0,
            )
        )


if __name__ == "__main__":
    unittest.main()
