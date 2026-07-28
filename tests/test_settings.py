import importlib
import os
import sys
import unittest
from unittest.mock import patch


class SettingsDefaultsTests(unittest.TestCase):
    def test_missing_optional_env_vars_default_safely(self):
        with patch.dict(os.environ, {}, clear=False):
            for key in [
                "ALLOWED_HOSTS",
                "CORS_ALLOWED_ORIGINS",
                "LANGUAGE_CODE",
                "TIME_ZONE",
            ]:
                os.environ.pop(key, None)

            os.environ.setdefault("SECRET_KEY", "test-secret-key")
            os.environ.setdefault("DEBUG", "False")

            sys.modules.pop("config.settings", None)
            import config.settings as settings_module

            reloaded_settings = importlib.reload(settings_module)

            self.assertEqual(reloaded_settings.ALLOWED_HOSTS, [])
            self.assertEqual(reloaded_settings.CORS_ALLOWED_ORIGINS, [])
            self.assertEqual(reloaded_settings.LANGUAGE_CODE, "en-us")
            self.assertEqual(reloaded_settings.TIME_ZONE, "UTC")


if __name__ == "__main__":
    unittest.main()
