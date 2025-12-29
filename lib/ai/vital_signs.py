import math
import statistics
import time
from collections import deque
from typing import Deque, Dict, List, Optional, Tuple


class VitalSignsEstimator:
    """Estimate basic vitals from a motion/activity time-series.

    Current output:
      - respiration_bpm: Breaths per minute estimated from periodic motion.

    Notes:
      - This is a heuristic estimator (not medical-grade).
      - Designed to be dependency-free and safe to run on Raspberry Pi.
    """

    def __init__(
        self,
        window_seconds: float = 60.0,
        min_bpm: float = 5.0,
        max_bpm: float = 80.0,
        smoothing_seconds: float = 2.0,
    ):
        self.window_seconds = float(window_seconds)
        self.min_bpm = float(min_bpm)
        self.max_bpm = float(max_bpm)
        self.smoothing_seconds = float(smoothing_seconds)

        self._samples: Deque[Tuple[float, float]] = deque()

    def reset(self) -> None:
        self._samples.clear()

    def add_sample(self, activity_level: float, t: Optional[float] = None) -> None:
        if t is None:
            t = time.time()

        try:
            value = float(activity_level)
        except (TypeError, ValueError):
            return

        self._samples.append((float(t), value))
        self._trim(float(t))

    def _trim(self, now: float) -> None:
        cutoff = now - self.window_seconds
        while self._samples and self._samples[0][0] < cutoff:
            self._samples.popleft()

    def get_estimate(self) -> Dict[str, object]:
        # Need enough time span and samples.
        if len(self._samples) < 20:
            return {
                "status": "NOT_ENOUGH_DATA",
                "respiration_bpm": None,
                "confidence": 0.0,
                "method": "activity_peaks",
            }

        times = [t for t, _ in self._samples]
        values = [v for _, v in self._samples]
        duration = times[-1] - times[0]
        if duration < 15.0:
            return {
                "status": "NOT_ENOUGH_DATA",
                "respiration_bpm": None,
                "confidence": 0.0,
                "method": "activity_peaks",
            }

        # If motion is very high and chaotic, breathing estimate will be unreliable.
        try:
            stdev = statistics.pstdev(values)
        except statistics.StatisticsError:
            stdev = 0.0

        avg = sum(values) / len(values)
        if avg > 10.0 and stdev > 10.0:
            return {
                "status": "TOO_MUCH_MOTION",
                "respiration_bpm": None,
                "confidence": 0.0,
                "method": "activity_peaks",
            }

        # Smooth: simple moving average over last ~smoothing_seconds.
        smoothed = self._smooth(times, values)

        # Normalize for peak detection.
        mean = sum(smoothed) / len(smoothed)
        try:
            sd = statistics.pstdev(smoothed)
        except statistics.StatisticsError:
            sd = 0.0

        if sd <= 1e-6:
            return {
                "status": "LOW_CONF",
                "respiration_bpm": None,
                "confidence": 0.0,
                "method": "activity_peaks",
            }

        z = [(x - mean) / sd for x in smoothed]

        # Peak finding with constraints.
        min_interval = 60.0 / self.max_bpm
        max_interval = 60.0 / self.min_bpm
        peaks = self._find_peaks(times, z, threshold=0.6, min_separation=min_interval)

        if len(peaks) < 3:
            return {
                "status": "LOW_CONF",
                "respiration_bpm": None,
                "confidence": 0.15,
                "method": "activity_peaks",
            }

        intervals = [peaks[i] - peaks[i - 1] for i in range(1, len(peaks))]
        # Filter improbable intervals.
        intervals = [dt for dt in intervals if min_interval <= dt <= max_interval]
        if len(intervals) < 2:
            return {
                "status": "LOW_CONF",
                "respiration_bpm": None,
                "confidence": 0.2,
                "method": "activity_peaks",
            }

        median_dt = statistics.median(intervals)
        bpm = 60.0 / median_dt if median_dt > 1e-6 else None
        if bpm is None or math.isnan(bpm) or bpm < self.min_bpm or bpm > self.max_bpm:
            return {
                "status": "LOW_CONF",
                "respiration_bpm": None,
                "confidence": 0.2,
                "method": "activity_peaks",
            }

        # Confidence: more peaks + more consistent intervals => higher confidence.
        try:
            interval_sd = statistics.pstdev(intervals)
        except statistics.StatisticsError:
            interval_sd = 0.0
        consistency = max(0.0, 1.0 - (interval_sd / (median_dt + 1e-6)))
        peak_factor = min(1.0, len(peaks) / 10.0)
        confidence = round(0.15 + 0.85 * (0.6 * consistency + 0.4 * peak_factor), 2)

        return {
            "status": "OK" if confidence >= 0.5 else "LOW_CONF",
            "respiration_bpm": round(float(bpm), 1),
            "confidence": float(confidence),
            "method": "activity_peaks",
            "window_seconds": round(duration, 1),
            "peaks": len(peaks),
        }

    def _smooth(self, times: List[float], values: List[float]) -> List[float]:
        if not times:
            return []

        smoothed: List[float] = []
        for i, t in enumerate(times):
            cutoff = t - self.smoothing_seconds
            j = i
            while j > 0 and times[j - 1] >= cutoff:
                j -= 1
            window = values[j : i + 1]
            smoothed.append(sum(window) / len(window))
        return smoothed

    def _find_peaks(
        self,
        times: List[float],
        signal: List[float],
        threshold: float,
        min_separation: float,
    ) -> List[float]:
        peaks: List[float] = []
        last_peak_t: Optional[float] = None
        for i in range(1, len(signal) - 1):
            if signal[i] < threshold:
                continue
            if signal[i] <= signal[i - 1] or signal[i] <= signal[i + 1]:
                continue

            t = times[i]
            if last_peak_t is not None and (t - last_peak_t) < min_separation:
                # Too close; keep the stronger of the two peaks.
                # NOTE: times.index(...) is O(n) but peak collisions are rare at low FPS.
                if signal[i] > signal[times.index(last_peak_t)]:
                    peaks[-1] = t
                    last_peak_t = t
                continue

            peaks.append(t)
            last_peak_t = t
        return peaks
