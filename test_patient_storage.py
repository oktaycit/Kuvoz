import unittest

from app.services.patient_storage import (
    annotate_patient_activity,
    is_same_patient_record,
    build_readmission_patient_id,
    normalize_patient_record,
    patient_record_has_content,
)


class PatientStorageTests(unittest.TestCase):
    def test_microchip_no_counts_as_patient_content(self):
        record = {"microchipNo": "123456789012345"}

        self.assertTrue(patient_record_has_content(record))
        self.assertTrue(normalize_patient_record(record)["id"])

    def test_same_patient_uses_id_microchip_or_admission_identity(self):
        self.assertTrue(is_same_patient_record({"id": "p1"}, {"id": "p1"}))
        self.assertTrue(
            is_same_patient_record(
                {"microchipNo": "123 456 789 012 345"},
                {"microchipNo": "123456789012345"},
            )
        )
        self.assertTrue(
            is_same_patient_record(
                {"name": "Boncuk", "admissionDate": "2026-05-19", "admissionTime": "09:30"},
                {"name": " boncuk ", "admissionDate": "2026-05-19", "admissionTime": "09:30"},
            )
        )

    def test_annotate_patient_activity_marks_only_current_non_discharged_record(self):
        patients = [
            {"id": "old", "name": "Eski", "discharged": False},
            {"id": "current", "name": "Aktif", "discharged": False},
            {"id": "done", "name": "Taburcu", "discharged": True},
        ]

        annotated, meta = annotate_patient_activity(patients, {"id": "current", "name": "Aktif"})

        self.assertEqual([p["active_status"] for p in annotated], ["follow_up", "current", "discharged"])
        self.assertEqual([p["is_current"] for p in annotated], [False, True, False])
        self.assertEqual(meta["active_patient_id"], "current")
        self.assertEqual(meta["open_patient_count"], 2)
        self.assertTrue(meta["has_multiple_open_patients"])

    def test_discharged_current_patient_is_not_active(self):
        annotated, meta = annotate_patient_activity(
            [{"id": "done", "name": "Taburcu", "discharged": True}],
            {"id": "done", "name": "Taburcu", "discharged": True},
        )

        self.assertEqual(annotated[0]["active_status"], "discharged")
        self.assertFalse(annotated[0]["is_current"])
        self.assertEqual(meta["active_patient_id"], "")

    def test_readmission_id_creates_new_episode_on_same_day(self):
        record = {"name": "Boncuk", "admissionDate": "2026-05-19", "admissionTime": "14:35"}
        readmission_id = build_readmission_patient_id(
            record,
            [{"id": "2026-05-19_Boncuk"}, {"id": "2026-05-19_Boncuk_1435"}],
        )

        self.assertEqual(readmission_id, "2026-05-19_Boncuk_1435_2")


if __name__ == "__main__":
    unittest.main()
