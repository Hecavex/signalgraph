import re
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch

import ci_environment
from ci_environment import configuration
from ci_health import public_status

ROOT = Path(__file__).resolve().parents[1]


class AssuranceContracts(unittest.TestCase):
    def test_ci_bootstrap_refuses_local_or_self_hosted_execution(self):
        for environment in ({}, {"GITHUB_ACTIONS": "true", "RUNNER_ENVIRONMENT": "self-hosted"}):
            with patch.dict("os.environ", environment, clear=True), self.assertRaises(SystemExit):
                ci_environment.main()

    def test_configuration_is_random_and_has_no_provider_credentials(self):
        first, password = configuration()
        second, _ = configuration()
        self.assertGreaterEqual(len(password), 32)
        self.assertNotEqual(first["SECRET_KEY"], second["SECRET_KEY"])
        self.assertIn(first["POSTGRES_PASSWORD"], first["DATABASE_URL"])
        self.assertEqual(first["URLSCAN_API_KEY"], "")
        self.assertEqual(first["AUTO_CREATE_TABLES"], "false")

    def test_diagnostics_drop_environment_tokens_and_commands(self):
        status = public_status({"Service": "api", "State": "running", "Health": "healthy", "ExitCode": 0,
                                "Env": {"SECRET_KEY": "sensitive"}, "Command": "password sensitive"})
        self.assertEqual(set(status[0]), {"Service", "State", "Health", "ExitCode"})
        self.assertNotIn("sensitive", str(status))
        self.assertEqual(len(public_status([{}] * 10)), 6)

    def test_runtime_and_dev_locks_preserve_identical_runtime_pins(self):
        def pins(name):
            text = (ROOT / "backend" / name).read_text(encoding="utf-8")
            records = [line for line in text.splitlines() if line and line[0].isalnum()]
            result = {}
            for record in records:
                match = re.fullmatch(r"([a-z0-9-]+)==([^ ;]+)(?: ; .+)? \\", record)
                self.assertIsNotNone(match, record)
                result[match[1]] = match[2]
            for block in re.split(r"(?m)(?=^[a-z0-9-]+==)", text)[1:]:
                self.assertRegex(block, r"--hash=sha256:[a-f0-9]{64}")
            self.assertNotRegex(text, r"(?m)^--(?:index|extra-index|find-links)")
            return result

        runtime = pins("requirements.lock")
        development = pins("requirements-dev.lock")
        build = pins("requirements-build.lock")
        self.assertTrue(runtime)
        for name, version in runtime.items():
            self.assertEqual(development[name], version)
        project = tomllib.loads((ROOT / "backend/pyproject.toml").read_text(encoding="utf-8"))
        for requirement in project["project"]["dependencies"]:
            name = re.split(r"[\[><=]", requirement)[0].lower().replace("_", "-")
            self.assertIn(name, runtime)
        self.assertIn("setuptools", build)
        self.assertIn("wheel", build)
        for name in set(runtime) & set(build):
            self.assertEqual(runtime[name], build[name])


if __name__ == "__main__":
    unittest.main()
