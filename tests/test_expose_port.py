"""expose-port 的 Funnel 腳本：開、公網驗證、收。

tailscale、curl、sudo 都換成 PATH 上的假指令（見 FAKE_*），不會真的開 Funnel 或連外。
假 tailscale 用一個檔案代表「Funnel 開著」：前景的 `funnel --https=N <target>` 在跑時檔案在，
被收掉（SIGTERM）或 `funnel --https=N off` 後檔案消失。假 curl 帶了正確 header 回 200，否則 401。
"""
import os
import select
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "expose-port" / "scripts" / "expose-port-funnel"
AUTH_HEADER_SCRIPT = ROOT / "skills" / "windows-mcp" / "scripts" / "windows-mcp-auth-header"

HOST = "box.tail123.ts.net"
PUBLIC_IP = "203.0.113.7"
KEY = "s3cret-key"

# ==========================================================================
# 假指令
# ==========================================================================

FAKE_TAILSCALE = r"""#!/usr/bin/env bash
state="$FAKE_STATE"
echo "tailscale $*" >> "$state/calls"
case "$1 $2" in
  "status --json") echo '{"Self":{"DNSName":"__HOST__."}}' ;;
  "debug prefs") echo "{\"OperatorUser\":\"${FAKE_OPERATOR:-$USER}\"}" ;;
  "funnel status")
    found=0
    for f in "$state"/funnel-*; do
      [ -e "$f" ] || continue
      found=1
      p=${f##*/funnel-}
      echo "# Funnel on:"
      echo "https://__HOST__:$p (Funnel on)"
      echo "|-- / proxy $(cat "$f")"
    done
    [ "$found" = 1 ] || echo "No serve config"
    ;;
  funnel\ --https=*)
    port=${2#--https=}
    if [ "$3" = off ]; then rm -f "$state/funnel-$port"; exit 0; fi
    echo "$3" > "$state/funnel-$port"
    trap 'rm -f "$state/funnel-$port"; exit 0' TERM INT
    while :; do sleep 0.1; done
    ;;
esac
"""

FAKE_CURL = r"""#!/usr/bin/env bash
state="$FAKE_STATE"
printf 'curl' >> "$state/calls"; printf ' %q' "$@" >> "$state/calls"; echo >> "$state/calls"
case "$*" in *dns-query*) echo '{"Answer":[{"type":5,"data":"x."},{"type":1,"data":"__IP__"}]}'; exit 0 ;; esac
header=""
while [ $# -gt 0 ]; do
  if [ "$1" = -H ] && [ "${2:0:1}" = @ ]; then header=$(cat "${2:1}"); fi
  shift
done
if [ -n "$FAKE_CURL_DOWN" ]; then printf 000; exit 7; fi
if [ "$header" = "Authorization: Bearer __KEY__" ]; then printf 200; else printf 401; fi
"""

FAKE_TAILSCALE = FAKE_TAILSCALE.replace("__HOST__", HOST)
FAKE_CURL = FAKE_CURL.replace("__IP__", PUBLIC_IP).replace("__KEY__", KEY)

FAKE_SUDO = r"""#!/usr/bin/env bash
echo "sudo $*" >> "$FAKE_STATE/calls"
exec "$@"
"""


class FunnelTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = Path(self.tmp.name) / "state"
        self.bin = Path(self.tmp.name) / "bin"
        self.state.mkdir()
        self.bin.mkdir()
        for name, body in (("tailscale", FAKE_TAILSCALE), ("curl", FAKE_CURL), ("sudo", FAKE_SUDO)):
            path = self.bin / name
            path.write_text(body)
            path.chmod(0o755)
        self.env = {
            **os.environ,
            "PATH": f"{self.bin}:{os.environ['PATH']}",
            "FAKE_STATE": str(self.state),
            "EXPOSE_PORT_PROBE_INTERVAL": "0",
        }
        self.env.pop("TAILSCALE", None)
        self.header_cmd = f"echo 'Authorization: Bearer {KEY}'"

    def calls(self):
        path = self.state / "calls"
        return path.read_text() if path.exists() else ""

    def funnel_open(self, port=8443):
        return (self.state / f"funnel-{port}").exists()

    def open_args(self, *extra, header_cmd=None):
        return [
            sys.executable, str(SCRIPT), "open", "--port", "8000", "--https", "8443",
            "--path", "/mcp", "--expect-without", "401", "--expect-with", "200",
            "--auth-header-cmd", header_cmd or self.header_cmd, *extra,
            "--", "-X", "POST", "-d", "{}",
        ]

    def start(self, args):
        proc = subprocess.Popen(
            args, env=self.env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            start_new_session=True,
        )
        # 測試失敗時連假 tailscale 一起收，不留孤兒
        self.addCleanup(self.kill_group, proc)
        return proc

    def kill_group(self, proc):
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()
        proc.stdout.close()

    def read_until(self, proc, needle, timeout=15):
        # 直接讀 fd：TextIOWrapper 的 readline 會把後面幾行吞進自己的緩衝，select 就看不到了
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

    # ======================================================================
    # open：開、驗證、停著；收到 SIGTERM 就撤掉
    # ======================================================================

    def test_open_verifies_from_public_ip_then_closes_on_sigterm(self):
        proc = self.start(self.open_args())
        out = self.read_until(proc, "公開網址")
        self.assertIn(f"https://{HOST}:8443/mcp", out)
        self.assertIn("不帶驗證=401（要 401）", out)
        self.assertIn("帶驗證=200（要 200）", out)
        self.assertTrue(self.funnel_open())
        # 前景 Funnel，不寫持久設定
        self.assertNotIn("--bg", self.calls())
        self.assertIn("tailscale funnel --https=8443 http://127.0.0.1:8000", self.calls())
        # 從公開 DNS 查到的 IP 打，不是本機解析的 tailnet IP
        self.assertIn(f"--resolve {HOST}:8443:{PUBLIC_IP}", self.calls())

        proc.send_signal(signal.SIGTERM)
        rest, _ = proc.communicate(timeout=15)
        self.assertEqual(proc.returncode, 0, out + rest)
        self.assertFalse(self.funnel_open())
        self.assertIn("Funnel :8443 剩 0 條", rest)

    def test_auth_header_stays_out_of_curl_argv(self):
        proc = self.start(self.open_args())
        self.read_until(proc, "公開網址")
        proc.send_signal(signal.SIGTERM)
        proc.communicate(timeout=15)
        self.assertNotIn(KEY, self.calls())

    def test_open_fails_and_closes_when_verification_fails(self):
        proc = self.start(self.open_args(header_cmd="echo 'Authorization: Bearer wrong'"))
        out, _ = proc.communicate(timeout=15)
        self.assertNotEqual(proc.returncode, 0)
        self.assertNotIn("公開網址", out)
        self.assertIn("帶驗證=401（要 200）", out)
        self.assertFalse(self.funnel_open())

    def test_open_fails_when_public_url_never_answers(self):
        self.env["FAKE_CURL_DOWN"] = "1"
        proc = self.start(self.open_args())
        out, _ = proc.communicate(timeout=30)
        self.assertNotEqual(proc.returncode, 0)
        self.assertNotIn("公開網址", out)
        self.assertFalse(self.funnel_open())

    def test_open_refuses_when_that_funnel_port_is_taken(self):
        (self.state / "funnel-8443").write_text("http://127.0.0.1:3000")
        proc = self.start(self.open_args())
        out, _ = proc.communicate(timeout=15)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("8443", out)
        self.assertNotIn("funnel --https=8443 http", self.calls())
        # 別人的 Funnel 不能被收掉
        self.assertEqual((self.state / "funnel-8443").read_text(), "http://127.0.0.1:3000")

    def test_open_rejects_ports_funnel_cannot_listen_on(self):
        args = self.open_args()
        args[args.index("8443")] = "9000"
        proc = self.start(args)
        out, _ = proc.communicate(timeout=15)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("443、8443、10000", out)
        self.assertNotIn("funnel --https", self.calls())

    def test_uses_sudo_when_user_is_not_tailscale_operator(self):
        self.env["FAKE_OPERATOR"] = "someone-else"
        proc = self.start(self.open_args())
        self.read_until(proc, "公開網址")
        proc.send_signal(signal.SIGTERM)
        proc.communicate(timeout=15)
        self.assertIn("sudo tailscale funnel --https=8443 http://127.0.0.1:8000", self.calls())

    def test_tailscale_command_can_be_overridden(self):
        # windows-mcp 從 WSL 叫 Windows 的 tailscale 就靠這個
        wrapper = self.bin / "win-tailscale"
        wrapper.write_text('#!/usr/bin/env bash\necho "wrapper" >> "$FAKE_STATE/calls"\nexec tailscale "$@"\n')
        wrapper.chmod(0o755)
        self.env["TAILSCALE"] = f"{wrapper}"
        self.env["FAKE_OPERATOR"] = "someone-else"
        proc = self.start(self.open_args())
        self.read_until(proc, "公開網址")
        proc.send_signal(signal.SIGTERM)
        proc.communicate(timeout=15)
        self.assertIn("wrapper", self.calls())
        self.assertNotIn("sudo", self.calls())

    # ======================================================================
    # close：收掉留下來的 Funnel
    # ======================================================================

    def test_close_turns_off_leftover_funnel(self):
        (self.state / "funnel-8443").write_text("http://127.0.0.1:8000")
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "close", "--https", "8443"],
            env=self.env, capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(self.funnel_open())
        self.assertIn("Funnel :8443 剩 0 條", result.stdout)

    def test_close_is_safe_to_rerun(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "close", "--https", "8443"],
            env=self.env, capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Funnel :8443 剩 0 條", result.stdout)


class WindowsMcpAuthHeaderTest(unittest.TestCase):
    """windows-mcp 交給 expose-port 的 --auth-header-cmd：從 Windows 的 config.toml 讀 key。"""

    def test_prints_bearer_header_from_windows_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            home = tmp / "winhome"
            (home / ".windows-mcp").mkdir(parents=True)
            (home / ".windows-mcp" / "config.toml").write_text(
                f'transport = "streamable-http"\nauth_key = "{KEY}"\n'
            )
            bin_dir = tmp / "bin"
            bin_dir.mkdir()
            (bin_dir / "powershell.exe").write_text("#!/usr/bin/env bash\nprintf 'C:\\\\Users\\\\me\\r\\n'\n")
            (bin_dir / "wslpath").write_text(f"#!/usr/bin/env bash\necho {home}\n")
            for p in bin_dir.iterdir():
                p.chmod(0o755)
            env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
            result = subprocess.run(["bash", str(AUTH_HEADER_SCRIPT)], env=env, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, f"Authorization: Bearer {KEY}\n")


if __name__ == "__main__":
    unittest.main()
