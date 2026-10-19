"""Music session maintenance: dry-run safety, refresh eligibility, no media calls."""
import importlib.util
import json
import sqlite3
from contextlib import closing
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

from app import profiles
from app.session_maintenance_lock import lock_maintenance, maintenance_active

SCRIPT=Path(__file__).resolve().parents[1]/"scripts"/"maintain-music-sessions.py"


class SessionMaintenanceTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.root.joinpath("data","flowmusic-session").mkdir(parents=True)
        session=self.root/"data"/"flowmusic-session"/"session.json"
        session.write_text(json.dumps({
            "email":"test@example.invalid","expires_at":
            (datetime.now(timezone.utc)-timedelta(minutes=3)).timestamp(),
            "refresh_token":"dummy-not-sent-to-provider"}),encoding="utf-8")
        database=self.root/"data"/"jobs.db"
        with closing(sqlite3.connect(database)) as conn:
            conn.execute("CREATE TABLE jobs(run_mode TEXT,state TEXT,account_profile TEXT)")
            conn.commit()
        self.patchers=[
            patch.object(profiles,"DATA",self.root/"data"),
            patch.object(profiles,"PROFILES",self.root/"data"/"flowmusic-profiles"),
            patch.object(profiles,"SNAPSHOTS",self.root/"data"/"account-snapshots"),
        ]
        for p in self.patchers:p.start()
        spec=importlib.util.spec_from_file_location("session_maintenance_runner",SCRIPT)
        self.module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.module.ROOT=self.root
        self.module.DB=database
        self.module.STATE=self.root/"data"/"session-maintenance"
        self.module.LOCK=self.module.STATE/"music-session-maintenance.lock"

    def tearDown(self):
        for p in reversed(self.patchers):p.stop()
        self.temp.cleanup()

    def test_expired_access_with_refresh_token_requires_account_check_not_relogin(self):
        result=self.module.decide("default")
        self.assertEqual(result["status"],"eligible_for_existing_cli_account_check")
        self.assertTrue(result["refresh_available"])
        self.assertFalse(result["generation_submitted"])
        self.assertNotIn("dummy-not-sent-to-provider",json.dumps(result))

    def test_recent_attempt_cooldown_prevents_refresh_loop(self):
        self.module._write_attempt("default","failed")
        self.assertEqual(self.module.decide("default")["status"],"cooldown")

    def test_queued_live_job_or_uncertain_job_blocks_refresh(self):
        for state in ("queued","needs_review"):
            with closing(sqlite3.connect(self.module.DB)) as conn:
                conn.execute("DELETE FROM jobs")
                conn.execute("INSERT INTO jobs VALUES('cli',?,'default')",(state,))
                conn.commit()
            self.assertEqual(self.module.decide("default")["status"],
                             "blocked_by_generation_or_review")

    def test_after_human_login_is_one_safe_account_check_even_during_old_cooldown(self):
        self.module._write_attempt("default","failed")
        self.assertEqual(self.module.decide("default")["status"],"cooldown")
        self.assertEqual(
            self.module.decide("default",after_human_login=True)["status"],
            "eligible_for_existing_cli_account_check")
        with patch.object(self.module,"_busy",return_value=True):
            self.assertEqual(
                self.module.decide("default",after_human_login=True)["status"],
                "blocked_by_generation_or_review")

    def test_after_human_login_failed_account_check_returns_failure_not_false_ready(self):
        with patch.object(self.module,"_probe_once",return_value=False), \
             patch.object(self.module,"_busy",return_value=False), \
             patch.object(self.module.sys,"argv",[
                 "maintain-music-sessions.py","--profile","default","--execute",
                 "--after-human-login"]):
            self.assertEqual(self.module.main(),2)

    def test_rotating_refresh_chain_is_exclusive(self):
        with lock_maintenance(self.module.LOCK):
            self.assertTrue(maintenance_active(self.module.LOCK))
        self.assertFalse(maintenance_active(self.module.LOCK))


if __name__=="__main__":
    unittest.main()
