"""Validation shared by camera region settings and the analysis engine."""
import math


def validate_camera_regions(settings):
    boxes = {}
    for name in ('animal', 'respiration'):
        if settings.get(name + '_roi_enabled') is not True:
            continue
        box = settings.get(name + '_roi')
        try:
            box = {key: float(box[key]) for key in ('x', 'y', 'width', 'height')}
        except (TypeError, KeyError, ValueError):
            raise ValueError('Seçili kamera alanı geçersiz') from None
        x, y, w, h = (box[k] for k in ('x', 'y', 'width', 'height'))
        if (not all(math.isfinite(v) for v in box.values()) or x < 0 or y < 0
                or w < .04 or h < .04 or x + w > 1.00001 or y + h > 1.00001):
            raise ValueError('Seçili alan görüntü içinde ve yeterince büyük olmalı')
        boxes[name] = box
    if 'animal' in boxes and 'respiration' in boxes:
        a, r = boxes['animal'], boxes['respiration']
        if (r['x'] < a['x'] - 1e-5 or r['y'] < a['y'] - 1e-5
                or r['x'] + r['width'] > a['x'] + a['width'] + 1e-5
                or r['y'] + r['height'] > a['y'] + a['height'] + 1e-5):
            raise ValueError('Solunum alanı hayvan alanının içinde olmalı')
    return boxes
