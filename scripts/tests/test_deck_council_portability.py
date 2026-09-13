import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("deck_council", ROOT / "scripts/run-deck-council.py")
council = importlib.util.module_from_spec(spec)
spec.loader.exec_module(council)


class CouncilPortabilityTests(unittest.TestCase):
    def test_temp_root_uses_platform_directory(self):
        self.assertEqual(council.packet_root(), Path(tempfile.gettempdir()).resolve())

    def test_cli_resolves_path_and_explicit_override_without_launch(self):
        with patch.dict(os.environ, {"KIRO_DEMO_GROK_CLI": "/custom/bin/grok"}), patch.object(council.shutil, "which", return_value="/custom/bin/grok") as which:
            self.assertEqual(council.reviewer_executable("grok"), "/custom/bin/grok")
            which.assert_called_once_with("/custom/bin/grok")
        with patch.object(council.shutil, "which", return_value=None):
            with self.assertRaisesRegex(ValueError, "install and authenticate it separately"):
                council.reviewer_executable("claude")

    def test_commands_retain_models_restrictions_and_home_deny(self):
        with patch.object(council, "reviewer_executable", side_effect=lambda name: "/bin/" + name):
            grok = council.command_for("grok", Path("/tmp/packet"), "test prompt")
            claude = council.command_for("claude", Path("/tmp/packet"), "test prompt")
        for command, model in [(grok, "grok-4.6"), (claude, "claude-opus-5")]:
            self.assertIn(model, command)
            self.assertIn("xhigh", command)
            self.assertIn("dontAsk", command)
        self.assertIn(f"Read({Path.home().resolve()}/**)", grok)
        self.assertIn("--sandbox", grok)
        self.assertIn("--strict-mcp-config", claude)
        self.assertIn("--restricted", claude)
        prompt = council.prompt_for("candidate", "0" * 64)
        self.assertIn("slide-9.png", prompt)
        self.assertNotIn("slide-10.png", prompt)


if __name__ == "__main__":
    unittest.main()
