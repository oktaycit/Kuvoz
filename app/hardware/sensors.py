"""Sensor helper functions for Kuvoz hardware flows."""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple


def probe_oxygen_sensor(
    oxygen_library_available: bool,
    oxygen_factory: Optional[Callable[[int], object]],
    candidate_addresses: Tuple[int, ...],
    sample_count: int = 5,
) -> Tuple[Optional[object], Optional[int], Optional[float], Dict[str, str]]:
    """Probe common oxygen sensor addresses and return the first healthy sensor."""
    if not oxygen_library_available or oxygen_factory is None:
        return None, None, None, {}

    probe_errors: Dict[str, str] = {}
    for address in candidate_addresses:
        try:
            sensor = oxygen_factory(address)
            reading = sensor.get_oxygen_data(sample_count)
            if reading is not None and 0 <= reading <= 100:
                return sensor, address, reading, probe_errors
            probe_errors[f"0x{address:02X}"] = f"invalid reading: {reading}"
        except Exception as exc:  # pragma: no cover - hardware dependent
            probe_errors[f"0x{address:02X}"] = f"{type(exc).__name__}: {exc}"

    return None, None, None, probe_errors


def filter_dht_bit_shift(
    temp: Optional[float],
    hum: Optional[float],
    last_valid_temp: Optional[float],
    last_valid_humidity: Optional[float],
    *,
    debug: Optional[Callable[[str], None]] = None,
    info: Optional[Callable[[str], None]] = None,
    warning: Optional[Callable[[str], None]] = None,
) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
    """Correct common DHT11 bit-shift anomalies and update last valid values."""
    if temp is None or hum is None:
        return temp, hum, last_valid_temp, last_valid_humidity

    if debug:
        debug(
            f"🔍 DHT Filter Input: temp={temp:.1f}°C, hum={hum:.0f}%, "
            f"last_temp={last_valid_temp}, last_hum={last_valid_humidity}"
        )

    corrected_temp = temp
    corrected_hum = hum
    temp_corrected = False
    hum_corrected = False
    half_temp = temp / 2

    if last_valid_temp is not None:
        if last_valid_temp > 0:
            ratio = temp / last_valid_temp
            if debug:
                debug(f"  Temp ratio: {ratio:.2f}x (current/last: {temp:.1f}/{last_valid_temp:.1f})")

            if 1.8 <= ratio <= 2.2 and 15 <= half_temp <= 30:
                corrected_temp = half_temp
                temp_corrected = True
                if warning:
                    warning(
                        f"⚠️  DHT TEMP BIT-SHIFT: {temp:.1f}°C → {corrected_temp:.1f}°C "
                        f"(ratio: {ratio:.2f}x vs last: {last_valid_temp:.1f}°C)"
                    )
            elif temp > 35 and 15 <= half_temp <= 30 and abs(half_temp - last_valid_temp) < 5:
                corrected_temp = half_temp
                temp_corrected = True
                if warning:
                    warning(
                        f"⚠️  DHT TEMP HIGH: {temp:.1f}°C → {corrected_temp:.1f}°C "
                        f"(>35°C, half near last: {last_valid_temp:.1f}°C)"
                    )
            elif abs(temp - last_valid_temp) > 5.0:
                corrected_temp = last_valid_temp
                temp_corrected = True
                if warning:
                    warning(
                        f"⚠️  DHT TEMP SPIKE REJECTED: {temp:.1f}°C → {corrected_temp:.1f}°C "
                        f"(diff: {abs(temp - last_valid_temp):.1f}°C > 5°C threshold)"
                    )
    else:
        if debug:
            debug(f"  First temp read, checking if {temp:.1f}°C needs correction (half={half_temp:.1f}°C)")
        if temp > 35 and 15 <= half_temp <= 30:
            corrected_temp = half_temp
            temp_corrected = True
            if warning:
                warning(f"⚠️  DHT TEMP INIT: {temp:.1f}°C → {corrected_temp:.1f}°C (>35°C, no history)")

    half_hum = hum / 2
    if last_valid_humidity is not None:
        if last_valid_humidity > 0:
            ratio = hum / last_valid_humidity
            if debug:
                debug(f"  Hum ratio: {ratio:.2f}x (current/last: {hum:.0f}/{last_valid_humidity:.0f})")

            if 1.8 <= ratio <= 2.2 and 20 <= half_hum <= 70:
                corrected_hum = half_hum
                hum_corrected = True
                if warning:
                    warning(
                        f"⚠️  DHT HUM BIT-SHIFT: {hum:.0f}% → {corrected_hum:.0f}% "
                        f"(ratio: {ratio:.2f}x vs last: {last_valid_humidity:.0f}%)"
                    )
            elif hum > 60 and 20 <= half_hum <= 70 and abs(half_hum - last_valid_humidity) < 10:
                corrected_hum = half_hum
                hum_corrected = True
                if warning:
                    warning(
                        f"⚠️  DHT HUM HIGH: {hum:.0f}% → {corrected_hum:.0f}% "
                        f"(>60%, half near last: {last_valid_humidity:.0f}%)"
                    )
    else:
        if debug:
            debug(f"  First hum read, checking if {hum:.0f}% needs correction (half={half_hum:.0f}%)")
        if hum > 60 and 20 <= half_hum <= 70:
            corrected_hum = half_hum
            hum_corrected = True
            if warning:
                warning(f"⚠️  DHT HUM INIT: {hum:.0f}% → {corrected_hum:.0f}% (>60%, no history)")

    updated_temp = last_valid_temp
    updated_hum = last_valid_humidity
    if 10 <= corrected_temp <= 40 and 15 <= corrected_hum <= 95:
        updated_temp = corrected_temp
        updated_hum = corrected_hum
        if debug:
            debug(f"  Updated last valid: temp={corrected_temp:.1f}°C, hum={corrected_hum:.0f}%")
    elif debug:
        debug(f"  Skipped update (out of range): temp={corrected_temp:.1f}°C, hum={corrected_hum:.0f}%")

    if (temp_corrected or hum_corrected) and info:
        info(f"🔧 DHT Filter Output: {corrected_temp:.1f}°C, {corrected_hum:.0f}%")

    return corrected_temp, corrected_hum, updated_temp, updated_hum


def apply_moving_average(
    temp: Optional[float],
    hum: Optional[float],
    temp_readings: List[float],
    humidity_readings: List[float],
    window_size: int,
    *,
    debug: Optional[Callable[[str], None]] = None,
) -> Tuple[Optional[float], Optional[float], List[float], List[float]]:
    """Apply a small moving average window to noisy DHT readings."""
    if temp is None or hum is None:
        return temp, hum, temp_readings, humidity_readings

    next_temp_readings = list(temp_readings)
    next_humidity_readings = list(humidity_readings)

    next_temp_readings.append(temp)
    next_humidity_readings.append(hum)

    if len(next_temp_readings) > window_size:
        next_temp_readings.pop(0)
    if len(next_humidity_readings) > window_size:
        next_humidity_readings.pop(0)

    avg_temp = sum(next_temp_readings) / len(next_temp_readings)
    avg_hum = sum(next_humidity_readings) / len(next_humidity_readings)

    if len(next_temp_readings) < 2:
        return temp, hum, next_temp_readings, next_humidity_readings

    if debug and abs(temp - avg_temp) > 2.0:
        debug(f"📊 Moving avg smoothing: temp {temp:.1f}°C → {avg_temp:.1f}°C (window: {next_temp_readings})")
    if debug and abs(hum - avg_hum) > 5.0:
        debug(f"💧 Moving avg smoothing: humidity {hum:.0f}% → {avg_hum:.0f}% (window: {next_humidity_readings})")

    return avg_temp, avg_hum, next_temp_readings, next_humidity_readings
