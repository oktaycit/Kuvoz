import os
import tempfile
import unittest

from app.services.dependency_installer import (
    build_dependency_install_plan,
    summarize_process_output,
)


class DependencyInstallerTests(unittest.TestCase):
    def test_plan_uses_requirements_file_when_present(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            requirements_path = os.path.join(tmpdir, "requirements.txt")
            with open(requirements_path, "w", encoding="utf-8") as handle:
                handle.write("reportlab\n")

            plan = build_dependency_install_plan(
                tmpdir,
                python_executable="/usr/bin/python3",
                platform_system="Linux",
            )

        self.assertTrue(plan.uses_requirements)
        self.assertEqual(plan.requirements_path, requirements_path)
        self.assertEqual(plan.primary.name, "pip_requirements")
        self.assertEqual(plan.primary.command[:4], ["/usr/bin/python3", "-m", "pip", "install"])
        self.assertIn("-r", plan.primary.command)
        self.assertIn(requirements_path, plan.primary.command)
        self.assertIn("--break-system-packages", plan.primary.command)

    def test_linux_plan_has_noninteractive_apt_fallback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            plan = build_dependency_install_plan(
                tmpdir,
                python_executable="/usr/bin/python3",
                platform_system="Linux",
            )

        self.assertIsNotNone(plan.fallback)
        self.assertEqual(plan.fallback.command[:5], ["sudo", "-n", "env", "DEBIAN_FRONTEND=noninteractive", "apt-get"])
        self.assertIn("python3-reportlab", plan.fallback.command)

    def test_non_linux_plan_omits_apt_fallback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            plan = build_dependency_install_plan(
                tmpdir,
                python_executable="/usr/bin/python3",
                platform_system="Darwin",
            )

        self.assertIsNone(plan.fallback)

    def test_summarize_process_output_keeps_tail(self):
        output = summarize_process_output("a" * 20, "b" * 20, max_chars=12)

        self.assertTrue(output.startswith("...\n"))
        self.assertEqual(output[-12:], "b" * 12)


if __name__ == "__main__":
    unittest.main()
