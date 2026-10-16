"""Ensure an expired FlowMusic account never launches browser or pays for a new job."""
import argparse
import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

PROBE=Path(__file__).resolve().parents[1]/"scripts"/"mvp_probe.py"


class GenerateSessionPreflightTest(unittest.TestCase):
    def test_silent_session_failure_is_before_ledger_and_remote_post(self):
        spec=importlib.util.spec_from_file_location("mvp_live_auth_guard",PROBE)
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            ledger=Path(tmp)/"ledger"
            args=argparse.Namespace(
                approve_live=True,request_id="test-live-session-guard-001",
                prompt="Piano instrumental test",profile="default",
                model="Lyria 3.5",seconds=60,format="wav",
                instrumental=True)
            calls=[]
            def auth_result(argv, **kwargs):
                calls.append(argv)
                return SimpleNamespace(returncode=2)
            with patch.object(module,"LEDGER",ledger), \
                 patch.object(module,"session_exists"), \
                 patch.object(module,"command",side_effect=auth_result), \
                 patch.object(module,"harden_upstream_retry",
                              side_effect=AssertionError("must stop before vendor patch")), \
                 patch.object(module.profiles,"invalidate_snapshot",
                              side_effect=AssertionError("must stop before debit risk")):
                with self.assertRaisesRegex(RuntimeError,"manual_login_required"):
                    module.generate(args)
            self.assertFalse(ledger.exists())
            self.assertEqual(len(calls),1)
            self.assertIn("interactive: false"," ".join(calls[0]))


if __name__=="__main__":
    unittest.main()
