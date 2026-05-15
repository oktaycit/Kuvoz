import unittest

from app.services.patient_storage import normalize_patient_record, patient_record_has_content


class PatientStorageTests(unittest.TestCase):
    def test_microchip_no_counts_as_patient_content(self):
        record = {"microchipNo": "123456789012345"}

        self.assertTrue(patient_record_has_content(record))
        self.assertTrue(normalize_patient_record(record)["id"])


if __name__ == "__main__":
    unittest.main()
