import unittest

from app.services.git_update import classify_git_update_error


class GitUpdateTests(unittest.TestCase):
    def test_classify_git_update_ssh_port_block(self):
        error_type, message, details = classify_git_update_error(
            "ssh: connect to host github.com port 22: Connection timed out",
            "master",
        )

        self.assertEqual(error_type, "network")
        self.assertIn("GitHub SSH", message)
        self.assertIn("port 22", details)

    def test_classify_git_update_https_network_error(self):
        error_type, message, _ = classify_git_update_error(
            "fatal: unable to access 'https://github.com/org/repo.git/': Failed to connect to github.com port 443",
            "master",
        )

        self.assertEqual(error_type, "network")
        self.assertIn("GitHub", message)
        self.assertNotIn("İnternet bağlantısı", message)


if __name__ == "__main__":
    unittest.main()
