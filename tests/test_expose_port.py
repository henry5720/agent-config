"""expose-port 的 Funnel 與 quick tunnel 腳本：開、公網驗證、收。

tailscale、cloudflared、curl、sudo 都換成 PATH 上的假指令（見 FAKE_*），不會真的開公開網址或連外。
假 tailscale 用一個檔案代表「Funnel 開著」：前景的 `funnel --https=N <target>` 在跑時檔案在，
被收掉（SIGTERM）或 `funnel --https=N off` 後檔案消失。假 cloudflared 同理（cloudflared-running）。
假 curl 帶了正確 header 回 200，否則 401。
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
QUICK_SCRIPT = ROOT / "skills" / "expose-port" / "scripts" / "expose-port-quick-tunnel"
AUTH_HEADER_SCRIPT = ROOT / "skills" / "windows-mcp" / "scripts" / "windows-mcp-auth-header"
SERVE_SCRIPT = ROOT / "skills" / "windows-mcp" / "scripts" / "windows-mcp-serve"

HOST = "box.tail123.ts.net"
QUICK_HOST = "quiet-fox-123.trycloudflare.com"
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

# 跟真的 cloudflared 一樣把網址印在 stderr；在跑時 cloudflared-running 檔案在，SIGTERM 後消失
FAKE_CLOUDFLARED = r"""#!/usr/bin/env bash
state="$FAKE_STATE"
echo "cloudflared $*" >> "$state/calls"
if [ -n "$FAKE_CF_FAIL" ]; then echo "ERR failed to request quick Tunnel" >&2; exit 1; fi
touch "$state/cloudflared-running"
trap 'rm -f "$state/cloudflared-running"; exit 0' TERM INT
echo "INF Requesting new quick Tunnel on trycloudflare.com..." >&2
echo "INF |  https://__QUICK_HOST__  |" >&2
while :; do sleep 0.1; done
""".replace("__QUICK_HOST__", QUICK_HOST)

FAKE_TAILSCALE = FAKE_TAILSCALE.replace("__HOST__", HOST)
FAKE_CURL = FAKE_CURL.replace("__IP__", PUBLIC_IP).replace("__KEY__", KEY)

FAKE_SUDO = r"""#!/usr/bin/env bash
echo "sudo $*" >> "$FAKE_STATE/calls"
exec "$@"
"""


class FakeBinTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = Path(self.tmp.name) / "state"
        self.bin = Path(self.tmp.name) / "bin"
        self.state.mkdir()
        self.bin.mkdir()
        for name, body in (("tailscale", FAKE_TAILSCALE), ("curl", FAKE_CURL), ("sudo", FAKE_SUDO),
                           ("cloudflared", FAKE_CLOUDFLARED)):
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


class FunnelTest(FakeBinTest):
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


class QuickTunnelTest(FakeBinTest):
    def quick_args(self, *extra, header_cmd=None):
        return [
            sys.executable, str(QUICK_SCRIPT), "open", "--port", "8000", "--host-header", "localhost",
            "--path", "/mcp", "--expect-without", "401", "--expect-with", "200",
            "--auth-header-cmd", header_cmd or self.header_cmd, *extra,
            "--", "-X", "POST", "-d", "{}",
        ]

    def tunnel_running(self):
        return (self.state / "cloudflared-running").exists()

    # ======================================================================
    # open：本機有 cloudflared，開、驗證、停著；收到 SIGTERM 就收掉
    # ======================================================================

    def test_open_verifies_then_stops_cloudflared_on_sigterm(self):
        proc = self.start(self.quick_args())
        out = self.read_until(proc, "公開網址")
        self.assertIn(f"https://{QUICK_HOST}/mcp", out)
        self.assertIn("不帶驗證=401（要 401）", out)
        self.assertIn("帶驗證=200（要 200）", out)
        self.assertTrue(self.tunnel_running())
        # app 留在 loopback：cloudflared 把 Host 改寫成 app 要的
        self.assertIn("cloudflared tunnel --url http://127.0.0.1:8000 --http-host-header localhost", self.calls())
        self.assertIn(f"--resolve {QUICK_HOST}:443:{PUBLIC_IP}", self.calls())

        proc.send_signal(signal.SIGTERM)
        rest, _ = proc.communicate(timeout=15)
        self.assertEqual(proc.returncode, 0, out + rest)
        self.assertFalse(self.tunnel_running())
        self.assertIn("cloudflared → :8000 剩 0 個（要 0）", rest)

    def test_open_keeps_auth_header_out_of_curl_argv(self):
        proc = self.start(self.quick_args())
        self.read_until(proc, "公開網址")
        proc.send_signal(signal.SIGTERM)
        proc.communicate(timeout=15)
        self.assertNotIn(KEY, self.calls())

    def test_open_leaves_host_alone_without_host_header(self):
        args = self.quick_args()
        i = args.index("--host-header")
        del args[i:i + 2]
        proc = self.start(args)
        self.read_until(proc, "公開網址")
        proc.send_signal(signal.SIGTERM)
        proc.communicate(timeout=15)
        self.assertNotIn("--http-host-header", self.calls())

    def test_open_fails_and_stops_cloudflared_when_verification_fails(self):
        proc = self.start(self.quick_args(header_cmd="echo 'Authorization: Bearer wrong'"))
        out, _ = proc.communicate(timeout=15)
        self.assertNotEqual(proc.returncode, 0)
        self.assertNotIn("公開網址", out)
        self.assertIn("帶驗證=401（要 200）", out)
        self.assertFalse(self.tunnel_running())
        self.assertIn("剩 0 個", out)

    def test_open_fails_when_cloudflared_gives_no_url(self):
        self.env["FAKE_CF_FAIL"] = "1"
        proc = self.start(self.quick_args())
        out, _ = proc.communicate(timeout=15)
        self.assertNotEqual(proc.returncode, 0)
        self.assertNotIn("公開網址", out)
        # 把 cloudflared 的錯誤帶出來，不用另外翻 log
        self.assertIn("failed to request quick Tunnel", out)

    def test_open_says_how_to_install_when_cloudflared_missing(self):
        self.env["CLOUDFLARED"] = str(self.bin / "no-such-cloudflared")
        proc = self.start(self.quick_args())
        out, _ = proc.communicate(timeout=15)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("Cloudflare.cloudflared", out)

    # ======================================================================
    # verify：cloudflared 跑在別台（使用者貼指令開的），只從這邊驗
    # ======================================================================

    def verify_args(self, url=f"https://{QUICK_HOST}", header_cmd=None):
        return [
            sys.executable, str(QUICK_SCRIPT), "verify", "--url", url, "--path", "/mcp",
            "--expect-without", "401", "--expect-with", "200",
            "--auth-header-cmd", header_cmd or self.header_cmd, "--", "-X", "POST",
        ]

    def test_verify_passes_and_prints_endpoint(self):
        result = subprocess.run(self.verify_args(), env=self.env, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("不帶驗證=401（要 401），帶驗證=200（要 200）", result.stdout)
        self.assertIn(f"公開網址：https://{QUICK_HOST}/mcp", result.stdout)
        self.assertNotIn("cloudflared", self.calls())

    def test_verify_fails_on_wrong_key(self):
        result = subprocess.run(self.verify_args(header_cmd="echo 'Authorization: Bearer wrong'"),
                                env=self.env, capture_output=True, text=True, timeout=15)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("公開網址", result.stdout)

    def test_verify_rejects_urls_that_are_not_quick_tunnels(self):
        result = subprocess.run(self.verify_args(url="https://example.com"),
                                env=self.env, capture_output=True, text=True, timeout=15)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("curl", self.calls())

    # ======================================================================
    # close：收掉留下來的 quick tunnel
    # ======================================================================

    def test_close_stops_leftover_tunnel_for_that_port_only(self):
        port = 18765  # 避開這台上可能真的在跑的 tunnel
        cf = str(self.bin / "cloudflared")
        mine = subprocess.Popen([cf, "tunnel", "--url", f"http://127.0.0.1:{port}"], env=self.env,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        other = subprocess.Popen([cf, "tunnel", "--url", f"http://127.0.0.1:{port + 1}"], env=self.env,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for p in (mine, other):
            self.addCleanup(p.wait)
            self.addCleanup(p.kill)
        result = subprocess.run([sys.executable, str(QUICK_SCRIPT), "close", "--port", str(port)],
                                env=self.env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(f"cloudflared → :{port} 剩 0 個（要 0）", result.stdout)
        mine.wait(timeout=5)
        self.assertIsNone(other.poll())

    def test_close_is_safe_to_rerun(self):
        result = subprocess.run([sys.executable, str(QUICK_SCRIPT), "close", "--port", "18765"],
                                env=self.env, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("剩 0 個", result.stdout)


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


# 只認 windows-mcp-serve 會送的幾種 PowerShell 指令；server 起來後 listening 檔案在
FAKE_POWERSHELL = r"""#!/usr/bin/env bash
cmd="$3"
case "$cmd" in
  '$env:USERPROFILE') printf 'C:\\Users\\me\r\n' ;;
  *windows-mcp.exe\") printf 'C:\\Users\\me\\.local\\bin\\windows-mcp.exe\r\n' ;;
  *Measure-Object\).Count*) [ -e "$FAKE_STATE/listening" ] && echo 1 || echo 0 ;;
  *Start-Process*) touch "$FAKE_STATE/listening" ;;
esac
"""


class WindowsMcpServeTest(unittest.TestCase):
    """windows-mcp-serve：起 server 後把 key 放進 Windows 剪貼簿，不印出來。"""

    def test_copies_key_to_clipboard_without_printing_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            home = tmp / "winhome"
            (home / ".windows-mcp").mkdir(parents=True)
            (home / ".windows-mcp" / "config.toml").write_text(
                f'transport = "streamable-http"\nauth_key = "{KEY}"\n'
            )
            (home / ".local" / "bin").mkdir(parents=True)
            (home / ".local" / "bin" / "windows-mcp.exe").write_text("")
            state = tmp / "state"
            state.mkdir()
            bin_dir = tmp / "bin"
            bin_dir.mkdir()
            (bin_dir / "powershell.exe").write_text(FAKE_POWERSHELL)
            (bin_dir / "wslpath").write_text(
                f'#!/usr/bin/env bash\ncase "$1" in *windows-mcp.exe) echo {home}/.local/bin/windows-mcp.exe ;; *) echo {home} ;; esac\n'
            )
            (bin_dir / "clip.exe").write_text(f'#!/usr/bin/env bash\ncat > {state}/clip\n')
            for p in bin_dir.iterdir():
                p.chmod(0o755)
            env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "FAKE_STATE": str(state)}
            result = subprocess.run(["bash", str(SERVE_SCRIPT)], env=env, capture_output=True, text=True, timeout=30)
            clip = (state / "clip").read_text() if (state / "clip").exists() else ""
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(clip, KEY)
        self.assertNotIn(KEY, result.stdout + result.stderr)
        self.assertIn("key 已複製到 Windows 剪貼簿", result.stdout)


if __name__ == "__main__":
    unittest.main()
