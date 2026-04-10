import unittest

from lib.ai.vision import (
    HIGH_MOTION_ENTER_SECONDS,
    LOAD_PROFILE_SETTINGS,
    NO_ANIMAL_IDLE_SECONDS,
    STARTUP_VITAL_COLLECTION_SECONDS,
    VisionEngine,
)


class VisionLoadProfileTests(unittest.TestCase):
    def setUp(self):
        self.engine = VisionEngine(fps=5)

    def update_profile(self, now, activity=0.0, status="DURGUN", vitals=None):
        self.engine.activity_level = activity
        self.engine.status = status
        self.engine._update_load_profile(
            vitals or {
                "status": "LOW_CONF",
                "respiration_bpm": None,
                "confidence": 0.0,
            },
            now=now,
        )

    def test_holds_normal_profile_during_startup_vital_collection_window(self):
        self.update_profile(now=0.0)
        self.update_profile(now=NO_ANIMAL_IDLE_SECONDS + 0.1)

        self.assertEqual(self.engine.load_profile, "normal")
        self.assertEqual(self.engine.load_reason, "startup_vital_collection")

    def test_reduces_to_idle_after_startup_window_expires(self):
        self.update_profile(now=0.0)
        self.update_profile(
            now=STARTUP_VITAL_COLLECTION_SECONDS + NO_ANIMAL_IDLE_SECONDS + 0.1
        )

        self.assertEqual(self.engine.load_profile, "idle")
        self.assertAlmostEqual(self.engine.target_fps, LOAD_PROFILE_SETTINGS["idle"]["fps"])
        self.assertEqual(self.engine.jpeg_quality, LOAD_PROFILE_SETTINGS["idle"]["jpeg_quality"])

    def test_restores_normal_when_subject_returns(self):
        self.update_profile(now=0.0)
        self.update_profile(
            now=STARTUP_VITAL_COLLECTION_SECONDS + NO_ANIMAL_IDLE_SECONDS + 0.1
        )
        self.assertEqual(self.engine.load_profile, "idle")

        self.update_profile(
            now=STARTUP_VITAL_COLLECTION_SECONDS + NO_ANIMAL_IDLE_SECONDS + 1.0,
            activity=2.0,
            status="HAREKETLI",
            vitals={"status": "LOW_CONF", "respiration_bpm": None, "confidence": 0.1},
        )

        self.assertEqual(self.engine.load_profile, "normal")
        self.assertAlmostEqual(self.engine.target_fps, LOAD_PROFILE_SETTINGS["normal"]["fps"])

    def test_reliable_vitals_prevent_idle_profile(self):
        reliable_vitals = {"status": "OK", "respiration_bpm": 24.0, "confidence": 0.82}

        self.update_profile(now=0.0, vitals=reliable_vitals)
        self.update_profile(now=NO_ANIMAL_IDLE_SECONDS + 5.0, vitals=reliable_vitals)

        self.assertEqual(self.engine.load_profile, "normal")
        self.assertIsNone(self.engine.no_subject_since_ts)

    def test_limits_processing_when_motion_is_too_high(self):
        chaotic_vitals = {"status": "TOO_MUCH_MOTION", "respiration_bpm": None, "confidence": 0.0}

        self.update_profile(now=0.0, activity=12.0, status="HAREKETLI", vitals=chaotic_vitals)
        self.update_profile(
            now=HIGH_MOTION_ENTER_SECONDS + 0.1,
            activity=12.0,
            status="HAREKETLI",
            vitals=chaotic_vitals,
        )

        self.assertEqual(self.engine.load_profile, "motion_limited")
        self.assertAlmostEqual(
            self.engine.target_fps,
            LOAD_PROFILE_SETTINGS["motion_limited"]["fps"],
        )

    def test_thermal_cap_still_limits_effective_fps(self):
        self.engine.thermal_fps_cap = 2.0
        self.update_profile(now=0.0, activity=2.0, status="HAREKETLI")

        self.assertEqual(self.engine.load_profile, "normal")
        self.assertAlmostEqual(self.engine.target_fps, 2.0)

    def test_center_focus_box_excludes_fisheye_edges(self):
        focus_box = self.engine._calculate_analysis_focus_box((480, 640, 3))
        self.engine.analysis_focus_box = focus_box
        self.engine.analysis_focus_source = "center_focus_window"
        self.engine.analysis_focus_coverage = 0.562

        self.assertEqual(focus_box, (89, 53, 550, 427))
        self.assertEqual(
            self.engine.get_status()["analysis_focus_box"],
            {"x": 89, "y": 53, "width": 461, "height": 374},
        )


if __name__ == "__main__":
    unittest.main()
