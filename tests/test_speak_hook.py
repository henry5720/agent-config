"""hooks/speak.yaml：Stop hook 把 stdin 交給 voice-out-speak，沒裝就安靜結束。

直接拿 yaml 裡 Claude Code、Codex 兩邊的 command 用 sh -c 跑（兩個 agent 都是交給 shell 跑），
HOME 換成暫存目錄：不放 voice-out-speak 就是「沒勾 snapserver 的機器」，
放一支假的（把 argv 與 stdin 寫到檔案）就能看 hook 交了什麼過去。
"""
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ENTRY = ROOT / "hooks" / "speak.yaml"
AGENTS = ("claude", "codex")

STOP_JSON = (
    '{"session_id":"s1","hook_event_name":"Stop","stop_hook_active":false,'
    '"last_assistant_message":"好了，測試都過了。\\n\\n```sh\\nls\\n```"}\n'
)

FAKE_SPEAK = """#!/bin/sh
printf '%s\\n' "$@" > "$HOME/argv"
cat > "$HOME/stdin"
"""


def load_entry():
    return yaml.safe_load(ENTRY.read_text(encoding="utf-8"))


def stop_handlers(entry, agent):
    return [h for group in entry["bindings"][agent]["events"]["Stop"] for h in group["hooks"]]


def run_hook(command, home):
    env = {"HOME": str(home), "PATH": "/usr/bin:/bin"}
    start = time.monotonic()
    proc = subprocess.run(
        ["sh", "-c", command], input=STOP_JSON, capture_output=True, text=True, env=env, timeout=10
    )
    return proc, time.monotonic() - start


# ==========================================================================
# 定義：只掛 Stop、async
# ==========================================================================


class EntryTest(unittest.TestCase):
    def test_only_stop_on_both_agents(self):
        entry = load_entry()
        self.assertEqual(set(entry["bindings"]), set(AGENTS))
        for agent in AGENTS:
            with self.subTest(agent=agent):
                self.assertEqual(list(entry["bindings"][agent]["events"]), ["Stop"])

    def test_handlers_are_async_commands(self):
        entry = load_entry()
        for agent in AGENTS:
            for handler in stop_handlers(entry, agent):
                with self.subTest(agent=agent):
                    self.assertEqual(handler["type"], "command")
                    self.assertIs(handler["async"], True)


# ==========================================================================
# command：沒裝就結束、有裝就原樣轉交
# ==========================================================================


class CommandTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.commands = {a: stop_handlers(load_entry(), a)[0]["command"] for a in AGENTS}

    def tearDown(self):
        self.tmp.cleanup()

    def install_fake(self):
        bin_dir = self.home / ".local" / "bin"
        bin_dir.mkdir(parents=True)
        fake = bin_dir / "voice-out-speak"
        fake.write_text(FAKE_SPEAK)
        fake.chmod(0o755)

    def test_missing_command_exits_zero_quietly_and_fast(self):
        for agent, command in self.commands.items():
            with self.subTest(agent=agent):
                proc, elapsed = run_hook(command, self.home)
                self.assertEqual(proc.returncode, 0)
                self.assertEqual(proc.stdout, "")
                self.assertEqual(proc.stderr, "")
                self.assertLess(elapsed, 0.5)

    def test_non_executable_file_is_treated_as_missing(self):
        bin_dir = self.home / ".local" / "bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "voice-out-speak").write_text(FAKE_SPEAK)
        for agent, command in self.commands.items():
            with self.subTest(agent=agent):
                proc, _ = run_hook(command, self.home)
                self.assertEqual((proc.returncode, proc.stderr), (0, ""))

    def test_passes_stdin_verbatim_with_background(self):
        self.install_fake()
        for agent, command in self.commands.items():
            with self.subTest(agent=agent):
                proc, _ = run_hook(command, self.home)
                self.assertEqual(proc.returncode, 0)
                self.assertEqual((self.home / "stdin").read_text(), STOP_JSON)
                self.assertEqual((self.home / "argv").read_text(), "--background\n")
                os.remove(self.home / "stdin")


if __name__ == "__main__":
    unittest.main()
