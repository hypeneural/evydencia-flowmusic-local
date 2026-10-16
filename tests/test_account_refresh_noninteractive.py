"""No account inspection may fall back to interactive login after refresh fails."""
import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

PROBE=Path(__file__).resolve().parents[1]/"scripts"/"mvp_probe.py"


class AccountRefreshTest(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location("music_mvp_refresh_probe",PROBE)
        self.probe=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.probe)

    def test_failure_aborts_before_account_requests_or_browser_login(self):
        calls=[]
        def fake_command(args, **kwargs):
            calls.append(args)
            return SimpleNamespace(returncode=2)
        with patch.object(self.probe,"session_exists"), \
             patch.object(self.probe,"command",side_effect=fake_command), \
             patch.object(self.probe,"json_command",
                          side_effect=AssertionError("never call account after failed refresh")):
            with self.assertRaisesRegex(RuntimeError,"manual_login_required"):
                self.probe.account("default")
        self.assertEqual(len(calls),1)
        self.assertTrue(any("interactive: false" in v for v in calls[0]))
        self.assertNotIn("login",calls[0])

    def test_successful_silent_refresh_proceeds_to_read_only_queries(self):
        calls=[]
        def fake_command(args, **kwargs):
            calls.append(args)
            return SimpleNamespace(returncode=0)
        def fake_json(kind):
            self.assertIn(kind,("models","credits"))
            return [{"public_name":"Lyria 3.5"}] if kind=="models" else {"credits_remaining":55}
        with patch.object(self.probe,"session_exists"), \
             patch.object(self.probe,"command",side_effect=fake_command), \
             patch.object(self.probe,"json_command",side_effect=fake_json) as query, \
             patch.object(self.probe.profiles,"save_snapshot") as snapshot, \
             patch.object(self.probe,"event"):
            self.probe.account("default")
        self.assertEqual(len(calls),1)
        self.assertEqual(query.call_count,2)
        snapshot.assert_called_once_with("default",55)


if __name__=="__main__":
    unittest.main()
