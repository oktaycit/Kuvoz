# Local animal recognition

`efficientdet_lite0.tflite` is Google's EfficientDet-Lite0 int8 model (320x320).
Source: https://storage.googleapis.com/mediapipe-models/object_detector/efficientdet_lite0/int8/latest/efficientdet_lite0.tflite
SHA-256: 0720bf247bd76e6594ea28fa9c6f7c5242be774818997dbbeffc4da460c723bb
Model documentation: https://developers.google.com/edge/mediapipe/solutions/vision/object_detector
Anchor ordering and decoding follow Google's Apache-2.0 implementation:
https://github.com/google/automl/blob/master/efficientdet/tf2/anchors.py

Enable with `KUVOZ_AI_SEMANTIC_TRACKING=1` and an enabled animal region.
Install the optional runtime into the project, without changing system Python:

```
python3 -m pip install --target .runtime/tflite --no-deps tflite-runtime==2.14.0
```

Tested on Raspberry Pi 3, ARMv7, Python 3.11, NumPy 1.24.2. Runtime 2.14 needs
NumPy 1.x. The runtime is ignored by Git and must be installed per device.
Inference took approximately one second on this device with one CPU thread.
The region enables observation; each displayed box comes from repeated cat/dog
recognition. Missing or ambiguous recognition hides the box. Detection runs
locally on one low-priority background worker with one bounded input frame,
at most once every two seconds. A missed recognition rotates the next input.
Boxes are carried from their capture frame to the current frame using
forward/backward optical flow and a verified affine center displacement.
Unverified movement hides the box instead of showing delayed coordinates.
Recognition older than eight seconds cannot support a lock. The model score
is reported separately from temporally confirmed tracking confidence.
No downloads occur at runtime and no frames leave the device.

Recognition mode deliberately uses the analysis capture for the displayed
preview too. The independent HD keyframe stream can be up to four seconds old
and cannot support a correctly aligned live box. Preview resolution therefore
follows the camera substream; high-resolution cached preview remains available
when semantic tracking is disabled.
