import importlib.util
import unittest
from pathlib import Path

module_spec = importlib.util.spec_from_file_location(
    "publish_play", Path(__file__).with_name("publish_play.py")
)
publish_play = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(publish_play)
release_body = publish_play.release_body


class ReleaseBodyTests(unittest.TestCase):
    def test_full_production_rollout_is_completed(self):
        release = release_body("production", 321, "1.2.3", "Release 1.2.3", 100)["releases"][0]
        self.assertEqual(release["status"], "completed")
        self.assertNotIn("userFraction", release)

    def test_staged_production_rollout_sets_fraction(self):
        release = release_body("production", 321, "1.2.3", "Release 1.2.3", 25)["releases"][0]
        self.assertEqual(release["status"], "inProgress")
        self.assertEqual(release["userFraction"], 0.25)

    def test_testing_tracks_are_completed(self):
        release = release_body("alpha", 321, "1.2.3", "Release 1.2.3", 100)["releases"][0]
        self.assertEqual(release["status"], "completed")
        self.assertNotIn("userFraction", release)

    def test_partial_nonproduction_rollout_is_rejected(self):
        with self.assertRaises(ValueError):
            release_body("internal", 321, "1.2.3", "Release 1.2.3", 25)


if __name__ == "__main__":
    unittest.main()
