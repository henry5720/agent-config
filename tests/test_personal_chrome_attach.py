"""browser-access 的 personal-chrome-attach --tunnel：印出使用者要做的事、接上、各種結束方式都收掉 cloudflared。

playwright-cli、cloudflared 換成 PATH 上的假指令（見 FAKE_*），不連網、不開 Chrome、不開公開網址。
假 playwright-cli 的 attach 照真的流程走：起一個 daemon 子行程（代表 relay），把 connect 網址交給
PLAYWRIGHT_MCP_EXECUTABLE_PATH，等測試建 state/connect（使用者按了允許）才 exit 0；
`detach` 建 state/detached，daemon 看到就結束。
假 cloudflared 跟真的一樣把網址印在 stderr，pid 寫進 state/cloudflared.pid。
"""
import os
import select
import signal
import subprocess
import tempfile
import time
import unittest
import urllib.parse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "browser-access" / "scripts" / "personal-chrome-attach"

QUICK_HOST = "quiet-fox-123.trycloudflare.com"
RELAY_PORT = "45678"
RELAY_UUID = "0f8e2a4c-1b3d-4e5f-9a7b-6c8d0e1f2a3b"
TOKEN = "tok-s3cret"
READY = "等使用者接上"  # 交付的內容印完了

# ==========================================================================
# 假指令
# ==========================================================================

FAKE_PLAYWRIGHT_CLI = r"""#!/usr/bin/env bash
state="$FAKE_STATE"
echo "playwright-cli $*" >> "$state/calls"
case "$*" in
  *" attach --extension=chrome")
    bash -c 'echo $$ > "$1/daemon.pid"; while [ ! -e "$1/detached" ]; do sleep 0.1; done' _ "$state" &
    relay="ws://127.0.0.1:__RELAY_PORT__/cdp/__UUID__"
    url="chrome-extension://mmlmfjhmonkocbjadbfplnigmagldckm/connect.html?mcpRelayUrl=$(python3 -c 'import sys, urllib.parse as u; print(u.quote(sys.argv[1], safe=""))' "$relay")&client=%7B%22name%22%3A%22playwright-cli%22%7D"
    [ -n "${PLAYWRIGHT_MCP_EXTENSION_TOKEN:-}" ] && url="$url&token=$PLAYWRIGHT_MCP_EXTENSION_TOKEN"
    "$PLAYWRIGHT_MCP_EXECUTABLE_PATH" --remote-debugging-pipe "$url"
    while :; do
      [ -e "$state/connect" ] && exit 0
      [ -e "$state/connect-fail" ] && { echo "Error: extension connection failed" >&2; exit 1; }
      sleep 0.1
    done ;;
  *" detach") touch "$state/detached" ;;
esac
""".replace("__RELAY_PORT__", RELAY_PORT).replace("__UUID__", RELAY_UUID)

FAKE_CLOUDFLARED = r"""#!/usr/bin/env bash
state="$FAKE_STATE"
echo "cloudflared $*" >> "$state/calls"
echo $$ > "$state/cloudflared.pid"
if [ -n "${FAKE_CF_FAIL:-}" ]; then echo "ERR failed to request quick Tunnel: 429 Too Many Requests" >&2; exit 1; fi
if [ -n "${FAKE_CF_API_ERR:-}" ]; then
  echo "INF Requesting new quick Tunnel on trycloudflare.com..." >&2
  echo 'ERR failed to request quick Tunnel: Post "https://api.trycloudflare.com/tunnel": dial tcp: i/o timeout' >&2
  sleep 0.5; exit 1
fi
trap 'exit 0' TERM INT
echo "INF Requesting new quick Tunnel on trycloudflare.com..." >&2
echo "INF |  https://__QUICK_HOST__  |" >&2
while :; do sleep 0.1; done
""".replace("__QUICK_HOST__", QUICK_HOST)


class TunnelTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = Path(self.tmp.name) / "state"
        self.bin = Path(self.tmp.name) / "bin"
        self.state.mkdir()
        self.bin.mkdir()
        for name, body in (("playwright-cli", FAKE_PLAYWRIGHT_CLI), ("cloudflared", FAKE_CLOUDFLARED)):
            path = self.bin / name
            path.write_text(body)
            path.chmod(0o755)
        self.env = {
            **os.environ,
            "PATH": f"{self.bin}:{os.environ['PATH']}",
            "FAKE_STATE": str(self.state),
            "PLAYWRIGHT_MCP_EXTENSION_TOKEN": TOKEN,
        }

    # ----------------------------------------------------------------------
    # 小工具
    # ----------------------------------------------------------------------

    def start(self, *args):
        proc = subprocess.Popen(
            [str(SCRIPT), "--tunnel", *args], env=self.env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True,
        )
        self.addCleanup(self.kill_group, proc)
        return proc

    def kill_group(self, proc):
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()
        proc.stdout.close()
        for name in ("cloudflared.pid", "daemon.pid"):
            pid = self.pid(name)
            if pid:
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

    def read_until(self, proc, needle, timeout=15):
        data = b""
        deadline = time.monotonic() + timeout
        while needle.encode() not in data:
            if time.monotonic() > deadline:
                self.fail(f"等不到 {needle!r}，目前輸出：\n{data.decode()}")
            ready, _, _ = select.select([proc.stdout], [], [], 0.2)
            if ready:
                chunk = os.read(proc.stdout.fileno(), 4096)
                if not chunk:
                    self.fail(f"程式結束了還沒印 {needle!r}：\n{data.decode()}")
                data += chunk
        return data.decode()

    def finish(self, proc, timeout=20):
        rest, _ = proc.communicate(timeout=timeout)
        return proc.returncode, rest.decode()

    def pid(self, name):
        path = self.state / name
        return int(path.read_text()) if path.exists() else None

    def alive(self, name):
        """state/<name> 記的行程還在不在（殭屍不算）。"""
        pid = self.pid(name)
        if pid is None:
            return False
        try:
            status = Path(f"/proc/{pid}/status").read_text()
        except FileNotFoundError:
            return False
        return "\nState:\tZ" not in status

    def calls(self):
        path = self.state / "calls"
        return path.read_text() if path.exists() else ""

    def assert_all_closed(self):
        self.assertFalse(self.alive("cloudflared.pid"), "cloudflared 還在跑")
        self.assertFalse(self.alive("daemon.pid"), "attach 的 daemon 還在跑")

    # ----------------------------------------------------------------------
    # 印出來的東西
    # ----------------------------------------------------------------------

    def test_prints_access_line_with_hostname_and_local_port(self):
        proc = self.start()
        out = self.read_until(proc, READY)
        self.assertIn(f"cloudflared access tcp --hostname {QUICK_HOST} --url 127.0.0.1:9555", out)

    def test_tunnel_points_at_the_relay_over_tcp(self):
        proc = self.start()
        self.read_until(proc, READY)
        self.assertIn(f"cloudflared tunnel --url tcp://127.0.0.1:{RELAY_PORT}", self.calls())

    def test_connect_url_relay_is_rewritten_to_local_port(self):
        proc = self.start()
        out = self.read_until(proc, READY)
        url = next(w for w in out.split() if w.startswith("chrome-extension://"))
        relay = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))["mcpRelayUrl"]
        self.assertEqual(relay, f"ws://127.0.0.1:9555/cdp/{RELAY_UUID}")

    def test_token_stays_out_of_tunnel_mode(self):
        proc = self.start("--timeout=1")
        rc, rest = self.finish(proc)
        self.assertNotIn(TOKEN, rest)
        self.assertNotIn("token=", rest)
        self.assertIn("chrome-extension://", rest)

    # ----------------------------------------------------------------------
    # 結束方式：cloudflared 都收掉
    # ----------------------------------------------------------------------

    def test_detach_closes_tunnel_and_exits_0(self):
        proc = self.start()
        self.read_until(proc, READY)
        (self.state / "connect").touch()
        self.read_until(proc, "已接上,session:personal-chrome")
        self.assertTrue(self.alive("cloudflared.pid"), "接上之後 tunnel 要開著")
        subprocess.run(["playwright-cli", "-s=personal-chrome", "detach"], env=self.env, check=True)
        rc, rest = self.finish(proc)
        self.assertEqual(rc, 0, rest)
        self.assertIn("session personal-chrome 結束了", rest)
        self.assertIn("cloudflared 剩 0 個", rest)
        self.assert_all_closed()

    def test_timeout_closes_tunnel_and_exits_1(self):
        proc = self.start("--timeout=1")
        rc, rest = self.finish(proc)
        self.assertEqual(rc, 1, rest)
        self.assertIn("等了 1 秒沒人連進來", rest)
        self.assertIn("cloudflared 剩 0 個", rest)
        self.assert_all_closed()

    def test_sigterm_while_waiting_closes_tunnel_and_exits_130(self):
        proc = self.start()
        self.read_until(proc, READY)
        os.kill(proc.pid, signal.SIGTERM)
        rc, rest = self.finish(proc)
        self.assertEqual(rc, 130, rest)
        self.assert_all_closed()

    def test_sigterm_after_connected_detaches_and_closes_tunnel(self):
        proc = self.start()
        self.read_until(proc, READY)
        (self.state / "connect").touch()
        self.read_until(proc, "已接上")
        os.kill(proc.pid, signal.SIGTERM)
        rc, rest = self.finish(proc)
        self.assertEqual(rc, 130, rest)
        self.assertIn("playwright-cli -s=personal-chrome detach", self.calls())
        self.assert_all_closed()

    def test_attach_failure_closes_tunnel_and_exits_1(self):
        proc = self.start()
        self.read_until(proc, READY)
        (self.state / "connect-fail").touch()
        rc, rest = self.finish(proc)
        self.assertEqual(rc, 1, rest)
        self.assert_all_closed()

    def test_cloudflared_failing_to_start_exits_1_with_its_error(self):
        self.env["FAKE_CF_FAIL"] = "1"
        proc = self.start()
        rc, rest = self.finish(proc)
        self.assertEqual(rc, 1, rest)
        self.assertIn("429 Too Many Requests", rest)
        self.assertNotIn("chrome-extension://", rest)
        self.assert_all_closed()

    def test_cloudflare_api_url_in_error_log_is_not_taken_as_hostname(self):
        self.env["FAKE_CF_API_ERR"] = "1"
        proc = self.start()
        rc, rest = self.finish(proc)
        self.assertEqual(rc, 1, rest)
        self.assertIn("i/o timeout", rest)
        self.assertNotIn("cloudflared access tcp", rest)
        self.assertNotIn("chrome-extension://", rest)
        self.assert_all_closed()


if __name__ == "__main__":
    unittest.main()
