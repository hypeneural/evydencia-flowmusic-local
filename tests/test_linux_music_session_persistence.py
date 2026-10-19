"""Linux multicontas regression: no browser, provider, paid POST or real session."""
from __future__ import annotations

import ast
import importlib.util
import os
import subprocess
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT=Path(__file__).resolve().parents[1]
LOGIN=ROOT/"scripts/linux/login-music.sh"
MAINTAIN=ROOT/"scripts/maintain-music-sessions.py"


class MusicSessionPersistenceTests(unittest.TestCase):
    def test_login_embedded_python_compiles_and_guards_account_identity(self):
        lines=LOGIN.read_text(encoding="utf8").splitlines()
        start=next(i+1 for i,l in enumerate(lines) if "<<'PY'" in l)
        end=lines.index("PY",start)
        ast.parse("\n".join(lines[start:end]),filename=str(LOGIN))
        script="\n".join(lines)
        for marker in (
            'FLOWMUSIC_HOME="$d"',
            'previous="$d/.session-prelogin-${BASHPID}"',
            'cp -p -- "$session" "$previous"',
            'MUSIC_LOGIN_DIFFERENT_GOOGLE_IDENTITY',
            'MUSIC_LOGIN_NOT_PERSISTED',
            'os.chmod(path,0o600)',
            'cp -p -- "$previous" "$session"',
        ):
            self.assertIn(marker,script)
        self.assertNotIn("rm -rf /app/data/flowmusic-session",script)

    @unittest.skipIf(os.name=="nt","POSIX process groups run only on Ubuntu VPS")
    def test_timeout_kills_owned_process_group_including_node_descendants(self):
        spec=importlib.util.spec_from_file_location("session_maint_linux_test",MAINTAIN)
        mod=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        proc=MagicMock(pid=12345)
        proc.wait.side_effect=[subprocess.TimeoutExpired("probe",300),0,0]
        with patch.object(mod.subprocess,"Popen",return_value=proc) as launcher, \
             patch.object(mod.os,"killpg") as killgroup:
            self.assertFalse(mod._probe_once("default"))
        self.assertTrue(launcher.call_args.kwargs["start_new_session"])
        self.assertEqual(killgroup.call_count,2)
        self.assertEqual(killgroup.call_args_list[0].args,
                         (12345,mod.signal.SIGTERM))
        self.assertEqual(killgroup.call_args_list[1].args,
                         (12345,mod.signal.SIGKILL))

    def test_regular_account_check_finishes_without_killing_group(self):
        spec=importlib.util.spec_from_file_location("session_maint_regular_test",MAINTAIN)
        mod=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        proc=MagicMock(pid=12345)
        proc.wait.return_value=0
        with patch.object(mod.subprocess,"Popen",return_value=proc), \
             patch.object(mod.os,"killpg",create=True) as killgroup:
            self.assertTrue(mod._probe_once("studio02"))
        killgroup.assert_not_called()


if __name__=="__main__":
    unittest.main()
