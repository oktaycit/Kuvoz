import gc
import os
import unittest

from lib.data.sensor_logger import SensorLogger


class SensorLoggerClearTests(unittest.TestCase):
    def test_clear_all_data_resets_runtime_state(self):
        db_path = os.path.join(os.getcwd(), "test_sensor_logger_clear.db")
        if os.path.exists(db_path):
            os.remove(db_path)

        try:
            logger = SensorLogger(db_path=db_path, min_interval=0)

            sample = {
                "temperature": {"value": "25.5", "status": "OK"},
                "humidity": {"value": "60", "status": "OK"},
                "oxygen": {"value": "20.9", "status": "OK"},
                "co2": {"value": "450", "status": "OK"},
            }

            self.assertTrue(logger.log_if_changed(sample))
            self.assertGreater(logger.get_record_count(), 0)
            self.assertTrue(logger.histeresis_centers)

            self.assertTrue(
                logger.clear_all_data(
                    reason="patient_change",
                    context={"trigger": "unit_test"},
                )
            )

            self.assertEqual(logger.get_record_count(), 0)
            self.assertEqual(logger.last_values, {})
            self.assertIsNone(logger.last_log_time)
            self.assertEqual(logger.histeresis_centers, {})
            self.assertEqual(logger.is_stable, {})

            self.assertTrue(logger.log_if_changed(sample))
            self.assertEqual(logger.get_record_count(), 1)
        finally:
            logger = None
            gc.collect()
            if os.path.exists(db_path):
                os.remove(db_path)


if __name__ == "__main__":
    unittest.main()
