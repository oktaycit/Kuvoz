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
        self._last_reliable_bpm: Optional[float] = None
        self._last_reliable_ts: Optional[float] = None

    def reset(self) -> None:
        self._samples.clear()
        self._last_reliable_bpm = None
        self._last_reliable_ts = None

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

        # First suppress isolated spikes, then smooth and remove slow baseline drift.
        cleaned, replaced_samples = self._despike(times, values)
        smoothed = self._smooth(times, cleaned, window_seconds=self.smoothing_seconds)
        baseline = self._smooth(
            times,
            smoothed,
            window_seconds=max(self.smoothing_seconds * 4.0, 8.0),
        )
        detrended = [sample - trend for sample, trend in zip(smoothed, baseline)]

        # Normalize for peak detection.
        mean = sum(detrended) / len(detrended)
        try:
            sd = statistics.pstdev(detrended)
        except statistics.StatisticsError:
            sd = 0.0

        if sd <= 1e-6:
            return {
                "status": "LOW_CONF",
                "respiration_bpm": None,
                "confidence": 0.0,
                "method": "activity_peaks",
            }

        z = [(x - mean) / sd for x in detrended]

        # Peak finding with constraints.
        min_interval = 60.0 / self.max_bpm
        max_interval = 60.0 / self.min_bpm
        peaks = self._find_peaks(
            times,
            z,
            threshold=0.55,
            min_separation=min_interval,
            prominence=0.35,
        )

        if len(peaks) < 3:
            return {
                "status": "LOW_CONF",
                "respiration_bpm": None,
                "confidence": 0.15,
                "method": "activity_peaks",
            }

        intervals = [peaks[i] - peaks[i - 1] for i in range(1, len(peaks))]
        intervals = [dt for dt in intervals if min_interval <= dt <= max_interval]
        filtered_intervals, interval_support = self._filter_intervals(intervals)
        if len(filtered_intervals) < 2 or interval_support < 0.5:
            return {
                "status": "LOW_CONF",
                "respiration_bpm": None,
                "confidence": 0.2,
                "method": "activity_peaks",
            }

        median_dt = statistics.median(filtered_intervals)
        bpm = 60.0 / median_dt if median_dt > 1e-6 else None
        if bpm is None or math.isnan(bpm) or bpm < self.min_bpm or bpm > self.max_bpm:
            return {
                "status": "LOW_CONF",
                "respiration_bpm": None,
                "confidence": 0.2,
                "method": "activity_peaks",
            }

        if len(peaks) < 5 or len(filtered_intervals) < 4:
            return {
                "status": "LOW_CONF",
                "respiration_bpm": None,
                "confidence": 0.2,
                "method": "activity_peaks",
            }

        if self._should_reject_short_peak_tachypnea(
            bpm=bpm,
            peak_count=len(peaks),
            interval_count=len(filtered_intervals),
        ):
            return {
                "status": "LOW_CONF",
                "respiration_bpm": None,
                "confidence": 0.2,
                "method": "activity_peaks",
            }

        # Confidence: reward stable interval clusters and penalize spike repair volume.
        try:
            interval_sd = statistics.pstdev(filtered_intervals)
        except statistics.StatisticsError:
            interval_sd = 0.0
        consistency = max(0.0, 1.0 - (interval_sd / (median_dt + 1e-6)))
        peak_factor = min(1.0, len(peaks) / 10.0)
        artifact_penalty = max(0.35, 1.0 - (replaced_samples / max(len(values), 1)) * 2.0)
        confidence = round(
            (
                0.15
                + 0.85
                * (
                    0.45 * consistency
                    + 0.25 * peak_factor
                    + 0.15 * interval_support
                    + 0.15 * artifact_penalty
                )
            )
            * artifact_penalty,
            2,
        )

        if self._should_reject_sudden_jump(
            bpm=bpm,
            confidence=confidence,
            peak_count=len(peaks),
            interval_support=interval_support,
            now=times[-1],
        ):
            return {
                "status": "LOW_CONF",
                "respiration_bpm": None,
                "confidence": min(float(confidence), 0.2),
                "method": "activity_peaks",
            }

        if confidence >= 0.5:
            self._last_reliable_bpm = float(bpm)
            self._last_reliable_ts = float(times[-1])

        return {
            "status": "OK" if confidence >= 0.5 else "LOW_CONF",
            "respiration_bpm": round(float(bpm), 1),
            "confidence": float(confidence),
            "method": "activity_peaks",
            "window_seconds": round(duration, 1),
            "peaks": len(peaks),
            "artifact_replacements": int(replaced_samples),
            "interval_support": round(float(interval_support), 2),
        }

    def _smooth(
        self,
        times: List[float],
        values: List[float],
        *,
        window_seconds: Optional[float] = None,
    ) -> List[float]:
        if not times:
            return []

        smooth_window = self.smoothing_seconds if window_seconds is None else max(float(window_seconds), 0.0)
        smoothed: List[float] = []
        for i, t in enumerate(times):
            cutoff = t - smooth_window
            j = i
            while j > 0 and times[j - 1] >= cutoff:
                j -= 1
            window = values[j : i + 1]
            smoothed.append(sum(window) / len(window))
        return smoothed

    def _despike(self, times: List[float], values: List[float]) -> Tuple[List[float], int]:
        if len(values) < 7:
            return list(values), 0

        sample_intervals = [
            times[i] - times[i - 1]
            for i in range(1, len(times))
            if (times[i] - times[i - 1]) > 1e-6
        ]
        if not sample_intervals:
            return list(values), 0

        median_sample_dt = statistics.median(sample_intervals)
        half_window = max(2, int(round(0.75 / median_sample_dt)))
        cleaned = list(values)
        replacements = 0

        for i, value in enumerate(values):
            start = max(0, i - half_window)
            end = min(len(values), i + half_window + 1)
            window = values[start:end]
            if len(window) < 5:
                continue

            local_median = statistics.median(window)
            deviations = [abs(sample - local_median) for sample in window]
            local_mad = statistics.median(deviations)
            sigma = max(local_mad * 1.4826, 0.03)

            if abs(value - local_median) > (3.5 * sigma):
                cleaned[i] = local_median
                replacements += 1

        return cleaned, replacements

    def _filter_intervals(self, intervals: List[float]) -> Tuple[List[float], float]:
        if not intervals:
            return [], 0.0
        if len(intervals) < 3:
            return list(intervals), 1.0

        median_dt = statistics.median(intervals)
        deviations = [abs(dt - median_dt) for dt in intervals]
        mad = statistics.median(deviations)
        tolerance = max(mad * 2.5, median_dt * 0.2)
        filtered = [dt for dt in intervals if abs(dt - median_dt) <= tolerance]

        support = len(filtered) / len(intervals)
        return filtered, support

    def _should_reject_short_peak_tachypnea(
        self,
        *,
        bpm: float,
        peak_count: int,
        interval_count: int,
    ) -> bool:
        if bpm < 40.0:
            return False
        return peak_count < 5 or interval_count < 4

    def _should_reject_sudden_jump(
        self,
        *,
        bpm: float,
        confidence: float,
        peak_count: int,
        interval_support: float,
        now: float,
    ) -> bool:
        if self._last_reliable_bpm is None or self._last_reliable_ts is None:
            return False

        previous_bpm = self._last_reliable_bpm
        if previous_bpm < 1e-6:
            return False

        elapsed = now - self._last_reliable_ts
        if elapsed < 1.0 or elapsed > max(self.window_seconds * 2.0, 180.0):
            return False

        relative_jump = abs(bpm - previous_bpm) / previous_bpm
        if relative_jump < 0.6:
            return False

        # Allow strong, well-supported signals to pass even after a big change.
        if confidence >= 0.88 and peak_count >= 8 and interval_support >= 0.85:
            return False

        return True

    def _find_peaks(
        self,
        times: List[float],
        signal: List[float],
        threshold: float,
        min_separation: float,
        prominence: float = 0.0,
    ) -> List[float]:
        peaks: List[float] = []
        last_peak_t: Optional[float] = None
        for i in range(1, len(signal) - 1):
            if signal[i] < threshold:
                continue
            if signal[i] <= signal[i - 1] or signal[i] <= signal[i + 1]:
                continue
            if prominence > 0.0 and not self._has_min_prominence(
                times,
                signal,
                index=i,
                min_prominence=prominence,
                min_separation=min_separation,
            ):
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

    def _has_min_prominence(
        self,
        times: List[float],
        signal: List[float],
        *,
        index: int,
        min_prominence: float,
        min_separation: float,
    ) -> bool:
        left_bound = times[index] - max(min_separation * 1.5, 1.0)
        right_bound = times[index] + max(min_separation * 1.5, 1.0)

        left_index = index
        while left_index > 0 and times[left_index - 1] >= left_bound:
            left_index -= 1

        right_index = index
        while right_index < len(signal) - 1 and times[right_index + 1] <= right_bound:
            right_index += 1

        left_min = min(signal[left_index:index + 1]) if left_index < index else signal[index]
        right_min = min(signal[index:right_index + 1]) if index < right_index else signal[index]
        local_floor = max(left_min, right_min)
        return (signal[index] - local_floor) >= min_prominence
