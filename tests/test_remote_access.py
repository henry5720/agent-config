"""remote-access 的 funnel 與 quick-tunnel 子命令：開、公網驗證、收。

tailscale、cloudflared、curl、sudo 都換成 PATH 上的假指令（見 FAKE_*），不會真的開公開網址或連外。
假 tailscale 用檔案代表「Funnel 開著」：前景的 `funnel --https=N <target>` 在跑時 fg-funnel-N 在，
被收掉（SIGTERM）後消失；`--bg` 留下的設定是 bg-funnel-N，`funnel --https=N off` 才會消失。
假 cloudflared 同理（cloudflared-running）。
假 curl 打公開網址：有東西開著時帶了正確 header 回 200、否則 401；沒開時 Funnel 回 000、quick tunnel 回 530。
假 powershell.exe 模擬從 WSL 叫 Windows 的程式：它開的 tailscale／cloudflared 在 powershell.exe 被停掉後還在跑。
"""
import os
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RA_SCRIPTS = ROOT / "skills" / "remote-access" / "scripts"
ENTRY = RA_SCRIPTS / "remote-access"
FUNNEL = [sys.executable, str(ENTRY), "funnel"]
QUICK = [sys.executable, str(ENTRY), "quick-tunnel"]
# 舊名 alias（dotfiles 換完由 agent-config#124 收）：直接執行，不經 python

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
    # FAKE_STATUS_HIDES_FG=1：前景 Funnel 不列成 serve config（2026-11-05 henry-laptop 的 Windows tailscale 就是這樣）
    listed=0 hidden=0
    for f in "$state"/bg-funnel-* "$state"/fg-funnel-*; do
      [ -e "$f" ] || continue
      case "$f" in */fg-funnel-*) [ -n "$FAKE_STATUS_HIDES_FG" ] && { hidden=1; continue; } ;; esac
      listed=1
      p=${f##*-funnel-}
      echo "# Funnel on:"
      echo "https://__HOST__:$p (Funnel on)"
      echo "|-- / proxy $(cat "$f")"
    done
    if [ "$listed" = 0 ]; then [ "$hidden" = 1 ] && echo "# Funnel on:"; echo "No serve config"; fi
    ;;
  funnel\ --https=*)
    port=${2#--https=}
    if [ "$3" = off ]; then rm -f "$state/bg-funnel-$port"; exit 0; fi
    echo "$3" > "$state/fg-funnel-$port"
    trap 'rm -f "$state/fg-funnel-$port"; exit 0' TERM INT
    while :; do sleep 0.1; done
    ;;
esac
"""

FAKE_CURL = r"""#!/usr/bin/env bash
state="$FAKE_STATE"
printf 'curl' >> "$state/calls"; printf ' %q' "$@" >> "$state/calls"; echo >> "$state/calls"
case "$*" in *dns-query*)
  # FAKE_DNS_MISSES=N：前 N 次查詢還沒有紀錄（Funnel 剛開時公開 DNS 還查不到）
  n=$(cat "$state/dns-count" 2>/dev/null || echo 0); echo $((n + 1)) > "$state/dns-count"
  if [ "$n" -lt "${FAKE_DNS_MISSES:-0}" ]; then echo '{"Status":3}'; exit 0; fi
  echo '{"Answer":[{"type":5,"data":"x."},{"type":1,"data":"__IP__"}]}'; exit 0 ;; esac
header="" all="$*"
while [ $# -gt 0 ]; do
  if [ "$1" = -H ] && [ "${2:0:1}" = @ ]; then header=$(cat "${2:1}"); fi
  shift
done
if [ -n "$FAKE_CURL_DOWN" ]; then printf 000; exit 7; fi
# 公開網址有沒有東西在接：remote-up 代表別台開著
case "$all" in
  *__QUICK_HOST__*) [ -e "$state/cloudflared-running" ] || [ -e "$state/remote-up" ] || { printf 530; exit 0; } ;;
  *) compgen -G "$state/*-funnel-*" >/dev/null || [ -e "$state/remote-up" ] || { printf 000; exit 7; } ;;
esac
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
FAKE_CURL = FAKE_CURL.replace("__IP__", PUBLIC_IP).replace("__KEY__", KEY).replace("__QUICK_HOST__", QUICK_HOST)

# 從 WSL 叫 Windows 程式（TAILSCALE='powershell.exe -NoProfile -Command tailscale'、
# CLOUDFLARED='powershell.exe -NoProfile -Command cloudflared'）：開出來的 tailscale.exe／cloudflared.exe
# 自己一個 session，powershell.exe 被停掉它還在（2026-11-05 henry-laptop 實測）。
# 腳本用 Get-CimInstance … | Stop-Process 停、用 @(…).Count 數，這裡只認這兩種。
FAKE_WIN_POWERSHELL = r"""#!/usr/bin/env bash
state="$FAKE_STATE"
shift 2  # -NoProfile -Command
echo "powershell $*" >> "$state/calls"
name=$(printf '%s' "$*" | grep -oP "Name='\K[a-z]+" | head -1)
case "$*" in
  *Stop-Process*)
    pid=$(cat "$state/win-$name.pid" 2>/dev/null) || exit 0
    kill "$pid" 2>/dev/null
    while kill -0 "$pid" 2>/dev/null; do sleep 0.05; done
    rm -f "$state/win-$name.pid" ;;
  *.Count*)
    pid=$(cat "$state/win-$name.pid" 2>/dev/null)
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then echo 1; else echo 0; fi ;;
  "tailscale funnel --https="*" off"|"tailscale funnel status"*|"tailscale status"*|"tailscale debug"*)
    exec "$@" ;;
  tailscale\ *|cloudflared\ *)
    # 換個檔名跑：Windows 的行程在 WSL 用 pgrep 看不到，腳本只能從 PowerShell 停
    cp "$(command -v "$1")" "$state/$1.winbin"
    prog=$1; shift
    setsid "$state/$prog.winbin" "$@" </dev/null &
    set -- "$prog"
    echo $! > "$state/win-$1.pid"
    while :; do sleep 0.1; done ;;
esac
"""

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
        return any((self.state / f"{kind}-funnel-{port}").exists() for kind in ("fg", "bg"))

    def use_windows(self, var, prog):
        """把 var 設成經假 powershell.exe 叫 Windows 的 prog；測完收掉它留下的程式。"""
        ps = self.bin / "powershell.exe"
        ps.write_text(FAKE_WIN_POWERSHELL)
        ps.chmod(0o755)
        self.env[var] = f"{ps} -NoProfile -Command {prog}"
        self.addCleanup(self.kill_windows, prog)

    def kill_windows(self, prog):
        pid_file = self.state / f"win-{prog}.pid"
        if pid_file.exists():
            try:
                os.kill(int(pid_file.read_text()), signal.SIGKILL)
            except ProcessLookupError:
                pass

    def open_args(self, *extra, header_cmd=None):
        return [
            *FUNNEL, "open", "--port", "8000", "--https", "8443",
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
        self.assertIn("Funnel :8443 已收乾淨", rest)

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

    def test_open_waits_until_public_dns_has_the_name(self):
        self.env["FAKE_DNS_MISSES"] = "3"
        proc = self.start(self.open_args())
        out = self.read_until(proc, "公開網址")
        self.assertIn("不帶驗證=401（要 401）", out)
        self.assertIn(f"--resolve {HOST}:8443:{PUBLIC_IP}", self.calls())
        proc.send_signal(signal.SIGTERM)
        proc.communicate(timeout=15)
        self.assertFalse(self.funnel_open())

    def test_open_fails_and_closes_when_public_dns_never_has_the_name(self):
        self.env["FAKE_DNS_MISSES"] = "999"
        proc = self.start(self.open_args())
        out, _ = proc.communicate(timeout=30)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("公開 DNS 一直查不到", out)
        self.assertNotIn("公開網址", out)
        self.assertFalse(self.funnel_open())

    def test_open_refuses_when_that_funnel_port_is_taken(self):
        (self.state / "bg-funnel-8443").write_text("http://127.0.0.1:3000")
        proc = self.start(self.open_args())
        out, _ = proc.communicate(timeout=15)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("8443", out)
        self.assertNotIn("funnel --https=8443 http", self.calls())
        # 別人的 Funnel 不能被收掉
        self.assertEqual((self.state / "bg-funnel-8443").read_text(), "http://127.0.0.1:3000")

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
        # 從 WSL 叫 Windows 的 tailscale 就靠這個
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
        (self.state / "bg-funnel-8443").write_text("http://127.0.0.1:8000")
        result = subprocess.run(
            [*FUNNEL, "close", "--https", "8443"],
            env=self.env, capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(self.funnel_open())
        self.assertIn("Funnel :8443 已收乾淨", result.stdout)

    def test_close_is_safe_to_rerun(self):
        result = subprocess.run(
            [*FUNNEL, "close", "--https", "8443"],
            env=self.env, capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Funnel :8443 已收乾淨", result.stdout)

    def test_close_fails_when_public_url_still_answers_though_status_shows_nothing(self):
        # 前景 Funnel 不列在 status（# Funnel on: 後接 No serve config），但行程還在、公網還回 401
        self.env["FAKE_STATUS_HIDES_FG"] = "1"
        (self.state / "fg-funnel-8443").write_text("http://127.0.0.1:8000")
        result = subprocess.run(
            [*FUNNEL, "close", "--https", "8443"],
            env=self.env, capture_output=True, text=True, timeout=30,
        )
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("已收乾淨", result.stdout)
        self.assertIn("401", result.stdout)

    def test_sigterm_stops_windows_tailscale_left_behind_by_powershell(self):
        # 從 WSL 叫 Windows 的 tailscale：停掉 powershell.exe 不會停掉 tailscale.exe，腳本要自己停
        self.use_windows("TAILSCALE", "tailscale")
        self.env["FAKE_STATUS_HIDES_FG"] = "1"
        proc = self.start(self.open_args())
        out = self.read_until(proc, "公開網址")
        proc.send_signal(signal.SIGTERM)
        rest, _ = proc.communicate(timeout=30)
        self.assertEqual(proc.returncode, 0, out + rest)
        self.assertIn("Stop-Process", self.calls())
        self.assertFalse(self.funnel_open())
        self.assertIn("行程剩 0 個", rest)
        self.assertIn("Funnel :8443 已收乾淨", rest)

    def test_open_refuses_when_public_url_already_answers(self):
        # status 看不到的前景 Funnel 佔著這個 port：從公網打得到就不開
        self.env["FAKE_STATUS_HIDES_FG"] = "1"
        (self.state / "fg-funnel-8443").write_text("http://127.0.0.1:3000")
        proc = self.start(self.open_args())
        out, _ = proc.communicate(timeout=15)
        self.assertNotEqual(proc.returncode, 0)
        self.assertNotIn("funnel --https=8443 http", self.calls())

    # ======================================================================
    # verify、check-closed：Funnel 開在別台（使用者貼指令開的），只從這邊驗
    # ======================================================================

    def funnel_verify_args(self, url=f"https://{HOST}:8443", header_cmd=None):
        return [
            *FUNNEL, "verify", "--url", url, "--path", "/mcp",
            "--expect-without", "401", "--expect-with", "200",
            "--auth-header-cmd", header_cmd or self.header_cmd, "--", "-X", "POST",
        ]

    def test_verify_checks_a_funnel_opened_elsewhere(self):
        (self.state / "remote-up").touch()
        result = subprocess.run(self.funnel_verify_args(), env=self.env, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("不帶驗證=401（要 401），帶驗證=200（要 200）", result.stdout)
        self.assertIn(f"公開網址：https://{HOST}:8443/mcp", result.stdout)
        self.assertIn(f"--resolve {HOST}:8443:{PUBLIC_IP}", self.calls())
        self.assertNotIn("tailscale funnel", self.calls())

    def test_verify_rejects_urls_that_are_not_funnel(self):
        result = subprocess.run(self.funnel_verify_args(url=f"https://{QUICK_HOST}"),
                                env=self.env, capture_output=True, text=True, timeout=15)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("curl", self.calls())

    def test_check_closed_passes_only_when_public_url_is_unreachable(self):
        args = [*FUNNEL, "check-closed", "--url", f"https://{HOST}:8443"]
        (self.state / "remote-up").touch()
        still = subprocess.run(args, env=self.env, capture_output=True, text=True, timeout=30)
        self.assertNotEqual(still.returncode, 0, still.stdout)
        (self.state / "remote-up").unlink()
        gone = subprocess.run(args, env=self.env, capture_output=True, text=True, timeout=30)
        self.assertEqual(gone.returncode, 0, gone.stdout)
        self.assertIn("000", gone.stdout)


class QuickTunnelTest(FakeBinTest):
    def quick_args(self, *extra, header_cmd=None):
        return [
            *QUICK, "open", "--port", "8000", "--host-header", "localhost",
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
            *QUICK, "verify", "--url", url, "--path", "/mcp",
            "--expect-without", "401", "--expect-with", "200",
            "--auth-header-cmd", header_cmd or self.header_cmd, "--", "-X", "POST",
        ]

    def test_verify_passes_and_prints_endpoint(self):
        (self.state / "remote-up").touch()
        result = subprocess.run(self.verify_args(), env=self.env, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("不帶驗證=401（要 401），帶驗證=200（要 200）", result.stdout)
        self.assertIn(f"公開網址：https://{QUICK_HOST}/mcp", result.stdout)
        self.assertNotIn("cloudflared", self.calls())

    def test_verify_fails_on_wrong_key(self):
        (self.state / "remote-up").touch()
        result = subprocess.run(self.verify_args(header_cmd="echo 'Authorization: Bearer wrong'"),
                                env=self.env, capture_output=True, text=True, timeout=15)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("公開網址", result.stdout)

    def test_verify_rejects_urls_that_are_not_quick_tunnels(self):
        result = subprocess.run(self.verify_args(url="https://example.com"),
                                env=self.env, capture_output=True, text=True, timeout=15)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("curl", self.calls())

    def test_sigterm_stops_windows_cloudflared_and_checks_public_url(self):
        # 從 WSL 叫 Windows 的 cloudflared：停掉 powershell.exe 不會停掉 cloudflared.exe，腳本要自己停
        self.use_windows("CLOUDFLARED", "cloudflared")
        proc = self.start(self.quick_args())
        out = self.read_until(proc, "公開網址")
        proc.send_signal(signal.SIGTERM)
        rest, _ = proc.communicate(timeout=30)
        self.assertEqual(proc.returncode, 0, out + rest)
        self.assertIn("Stop-Process", self.calls())
        self.assertFalse(self.tunnel_running())
        self.assertIn("cloudflared → :8000 剩 0 個（要 0）", rest)
        self.assertIn("530", rest)

    def test_check_closed_fails_while_quick_tunnel_still_answers(self):
        (self.state / "remote-up").touch()
        result = subprocess.run([*QUICK, "check-closed", "--url", f"https://{QUICK_HOST}"],
                                env=self.env, capture_output=True, text=True, timeout=30)
        self.assertNotEqual(result.returncode, 0, result.stdout)

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
        result = subprocess.run([*QUICK, "close", "--port", str(port)],
                                env=self.env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(f"cloudflared → :{port} 剩 0 個（要 0）", result.stdout)
        mine.wait(timeout=5)
        self.assertIsNone(other.poll())

    def test_close_is_safe_to_rerun(self):
        result = subprocess.run([*QUICK, "close", "--port", "18765"],
                                env=self.env, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("剩 0 個", result.stdout)


class EntryTest(FakeBinTest):
    """remote-access 入口本身：--help，以及舊名 alias 跟新入口行為一樣。"""

    def help_of(self, args):
        result = subprocess.run([*args, "--help"], env=self.env, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def test_help_lists_subcommands(self):
        out = self.help_of([sys.executable, str(ENTRY)])
        self.assertIn("funnel", out)
        self.assertIn("quick-tunnel", out)

    def test_subcommand_help_shows_its_own_actions(self):
        for args in (FUNNEL, QUICK):
            with self.subTest(args=args[-1]):
                out = self.help_of(args)
                for action in ("open", "verify", "check-closed", "close"):
                    self.assertIn(action, out)

    def test_unknown_subcommand_fails(self):
        result = subprocess.run([sys.executable, str(ENTRY), "ngrok"], env=self.env, capture_output=True, text=True,
                                timeout=15)
        self.assertNotEqual(result.returncode, 0)


# ==========================================================================
# up／down：serve 模式接一台 windows-mcp
# ==========================================================================

UP = [sys.executable, str(ENTRY), "up"]
DOWN = [sys.executable, str(ENTRY), "down"]
WIN_HOST = "box.tail123.ts.net"
EC2_IP = "100.100.7.68"
SERVE_KEY = "fixed-key-0123456789"

# 假 ssh：`ssh -G <host>` 印 hostname；送去 Windows 的 PowerShell 一律是 -EncodedCommand，
# 解開後照第一行的 `# remote-access:<動作>` 模擬那台。那台的狀態用檔案代表：
#   desktop（有人登入桌面）、task（常駐 task 在）、listen（windows-mcp 聽著；內容 other:… 是別的程式）、
#   serve（tailscale serve 開著；內容 other 是別人的）、config（server 讀的設定檔，內容是 stdin 收到的 key）
# argv 記在 calls，解開的 script 記在 scripts，stdin 不記，方便檢查 key 沒進參數。
FAKE_SSH = r"""#!/usr/bin/env python3
import base64, os, sys
from pathlib import Path
st = Path(os.environ["FAKE_STATE"])
argv = sys.argv[1:]
with open(st / "calls", "a") as f:
    f.write("ssh " + " ".join(argv) + "\n")
if argv[0] == "-G":
    print("hostname " + os.environ.get("FAKE_HOSTNAME", "__WIN_HOST__"))
    sys.exit(0)
if "-EncodedCommand" not in argv:
    sys.exit("fake ssh: 只認 -EncodedCommand")
script = base64.b64decode(argv[argv.index("-EncodedCommand") + 1]).decode("utf-16-le")
with open(st / "scripts", "a") as f:
    f.write(script + "\n=====\n")
action = script.split("# remote-access:", 1)[1].split()[0]
has = lambda n: (st / n).exists()
read = lambda n: (st / n).read_text() if has(n) else ""
def probe():
    print("desktop=" + ("1" if has("desktop") else "0"))
    print("task=" + ("1" if has("task") else "0"))
    listen = read("listen")
    print("listen=" + ("none" if not has("listen") else listen if listen.startswith("other") else "ours"))
    print("serve=" + ("none" if not has("serve") else "other" if read("serve") == "other" else "ours"))
# 模擬 PowerShell 5.1 經 ssh 的雜訊：CLIXML 進度訊息、Big5 中文
sys.stdout.buffer.write("#< CLIXML\n準備中\n".encode("big5"))
sys.stdout.flush()
if action == "probe":
    probe()
elif action == "start":
    key = sys.stdin.readline().strip()
    if not has("task"):
        if "$create = $true" not in script:
            print("error=notask"); sys.exit(1)
        (st / "task").write_text("")
    (st / "config").write_text(key)
    if os.environ.get("FAKE_NO_LISTEN"):
        print("error=nolisten"); sys.exit(1)
    (st / "listen").write_text("ours")
    (st / "serve").write_text("ours")
    print("started=1")
elif action == "stop":
    was = 0
    if has("listen") and not read("listen").startswith("other"):
        (st / "listen").unlink(); was = 1
    if has("serve") and read("serve") != "other":
        (st / "serve").unlink(); was = 1
    if has("config"):
        (st / "config").unlink()
    if "$keep = $false" in script and has("task"):
        (st / "task").unlink()
    print(f"was_running={was}")
""".replace("__WIN_HOST__", WIN_HOST)

FAKE_SERVE_TAILSCALE = r"""#!/usr/bin/env bash
echo "tailscale $*" >> "$FAKE_STATE/calls"
if [ "$1 $2 $3" = "ip -4 company-ec2" ]; then echo "__EC2_IP__"; exit 0; fi
exit 1
""".replace("__EC2_IP__", EC2_IP)

# 假 curl 打 serve 網址：windows-mcp 聽著、serve 開著時，帶的 key 跟那台 config 一樣回 200，否則 401；沒開回 000
FAKE_SERVE_CURL = r"""#!/usr/bin/env bash
state="$FAKE_STATE"
printf 'curl' >> "$state/calls"; printf ' %q' "$@" >> "$state/calls"; echo >> "$state/calls"
header=""
while [ $# -gt 0 ]; do
  if [ "$1" = -H ] && [ "${2:0:1}" = @ ]; then header=$(cat "${2:1}"); fi
  shift
done
if [ -n "$FAKE_VERIFY_500" ]; then printf 500; exit 0; fi
if [ ! -e "$state/serve" ] || [ "$(cat "$state/listen" 2>/dev/null)" != ours ]; then printf 000; exit 7; fi
if [ "$header" = "Authorization: Bearer $(cat "$state/config")" ]; then printf 200; else printf 401; fi
"""


class ServeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.state, self.bin, home = root / "state", root / "bin", root / "home"
        for d in (self.state, self.bin, home / ".ssh"):
            d.mkdir(parents=True)
        (home / ".ssh" / "config").write_text(
            "Host *\n  ServerAliveInterval 30\n\nHost box\n  HostName box.tail123.ts.net\n\nhost other-box\n")
        for name, body in (("ssh", FAKE_SSH), ("tailscale", FAKE_SERVE_TAILSCALE), ("curl", FAKE_SERVE_CURL)):
            path = self.bin / name
            path.write_text(body)
            path.chmod(0o755)
        (self.state / "desktop").write_text("")
        self.env = {
            **os.environ,
            "HOME": str(home),
            "PATH": f"{self.bin}:{os.environ['PATH']}",
            "FAKE_STATE": str(self.state),
            "EXPOSE_PORT_PROBE_INTERVAL": "0",
            "WINDOWS_MCP_AUTH_KEY": SERVE_KEY,
        }

    def run_cli(self, args):
        result = subprocess.run(args, env=self.env, capture_output=True, text=True, timeout=30)
        return result.returncode, result.stdout + result.stderr

    def read(self, name):
        path = self.state / name
        return path.read_text() if path.exists() else ""

    def has(self, name):
        return (self.state / name).exists()

    def test_up_starts_server_opens_serve_and_verifies(self):
        code, out = self.run_cli([*UP, "windows-mcp", "box", "--create-task"])
        self.assertEqual(code, 0, out)
        self.assertIn("不帶驗證=401（要 401）", out)
        self.assertIn("帶驗證=200（要 200）", out)
        self.assertIn(f"https://{WIN_HOST}/mcp", out)
        self.assertIn("/mcp 重連", out)
        # key 經 stdin 到那台的設定檔；allowlist 是 company-ec2 的 tailnet IP
        self.assertEqual(self.read("config"), SERVE_KEY)
        self.assertIn(EC2_IP, self.read("scripts"))
        self.assertTrue(self.has("task") and self.has("listen") and self.has("serve"))


    def test_key_stays_out_of_argv_scripts_and_output(self):
        code, out = self.run_cli([*UP, "windows-mcp", "box", "--create-task"])
        self.assertEqual(code, 0, out)
        code2, out2 = self.run_cli([*DOWN, "windows-mcp", "box"])
        self.assertEqual(code2, 0, out2)
        # calls 有 ssh／curl／tailscale 的參數，scripts 有送去那台的 PowerShell（含 task 定義）
        for where in (out, out2, self.read("calls"), self.read("scripts")):
            self.assertNotIn(SERVE_KEY, where)

    def test_windows_commands_are_encoded(self):
        self.run_cli([*UP, "windows-mcp", "box", "--create-task"])
        ssh_calls = [c for c in self.read("calls").splitlines() if c.startswith("ssh ") and " -G " not in c]
        self.assertTrue(ssh_calls)
        for c in ssh_calls:
            self.assertIn("-EncodedCommand", c)

    def test_up_refuses_without_desktop_session(self):
        (self.state / "desktop").unlink()
        code, out = self.run_cli([*UP, "windows-mcp", "box", "--create-task"])
        self.assertEqual(code, 1, out)
        self.assertIn("請先登入 box 的桌面", out)
        self.assertFalse(self.has("task") or self.has("listen") or self.has("config"))

    def test_up_asks_before_creating_resident_task(self):
        code, out = self.run_cli([*UP, "windows-mcp", "box"])
        self.assertEqual(code, 1, out)
        self.assertIn("--create-task", out)
        self.assertFalse(self.has("task") or self.has("listen") or self.has("config"))
        # task 已經在的機器不用再加
        (self.state / "task").write_text("")
        code, out = self.run_cli([*UP, "windows-mcp", "box"])
        self.assertEqual(code, 0, out)

    def test_up_tears_down_when_verification_fails(self):
        self.env["FAKE_VERIFY_500"] = "1"
        code, out = self.run_cli([*UP, "windows-mcp", "box", "--create-task"])
        self.assertEqual(code, 1, out)
        self.assertIn("已收掉", out)
        self.assertFalse(self.has("listen") or self.has("serve") or self.has("config"))
        self.assertTrue(self.has("task"))  # keep: true

    def test_up_tears_down_when_server_never_listens(self):
        self.env["FAKE_NO_LISTEN"] = "1"
        code, out = self.run_cli([*UP, "windows-mcp", "box", "--create-task"])
        self.assertEqual(code, 1, out)
        self.assertIn("沒在 8000 起來", out)
        self.assertFalse(self.has("config"))

    def test_up_twice_reports_running(self):
        self.run_cli([*UP, "windows-mcp", "box", "--create-task"])
        code, out = self.run_cli([*UP, "windows-mcp", "box"])
        self.assertEqual(code, 0, out)
        self.assertIn("已經起好", out)
        self.assertEqual(self.read("scripts").count("# remote-access:start"), 1)

    def test_up_restarts_when_running_server_has_another_key(self):
        self.run_cli([*UP, "windows-mcp", "box", "--create-task"])
        self.env["WINDOWS_MCP_AUTH_KEY"] = "rotated-key-9876543210"
        code, out = self.run_cli([*UP, "windows-mcp", "box"])
        self.assertEqual(code, 0, out)
        self.assertEqual(self.read("config"), "rotated-key-9876543210")

    def test_up_reads_key_from_key_env(self):
        self.env.pop("WINDOWS_MCP_AUTH_KEY")
        self.env["CLIENT_KEY"] = "client-key-0123456789"
        code, out = self.run_cli([*UP, "windows-mcp", "box", "--create-task"])
        self.assertEqual(code, 1, out)
        self.assertIn("WINDOWS_MCP_AUTH_KEY", out)
        code, out = self.run_cli([*UP, "windows-mcp", "box", "--create-task", "--key-env", "CLIENT_KEY"])
        self.assertEqual(code, 0, out)
        self.assertEqual(self.read("config"), "client-key-0123456789")

    def test_up_refuses_when_port_is_taken_by_another_program(self):
        (self.state / "task").write_text("")
        (self.state / "listen").write_text("other:4242/nginx.exe")
        code, out = self.run_cli([*UP, "windows-mcp", "box"])
        self.assertEqual(code, 1, out)
        self.assertIn("4242/nginx.exe", out)
        self.assertEqual(self.read("listen"), "other:4242/nginx.exe")
        self.assertNotIn("# remote-access:start", self.read("scripts"))

    def test_up_refuses_when_serve_is_used_by_someone_else(self):
        (self.state / "task").write_text("")
        (self.state / "serve").write_text("other")
        code, out = self.run_cli([*UP, "windows-mcp", "box"])
        self.assertEqual(code, 1, out)
        self.assertIn("tailscale serve", out)
        self.assertEqual(self.read("serve"), "other")

    def test_unknown_service_or_host_lists_choices(self):
        code, out = self.run_cli([*UP, "chrome", "box"])
        self.assertEqual(code, 1, out)
        self.assertIn("windows-mcp", out)
        code, out = self.run_cli([*DOWN, "windows-mcp", "nobox"])
        self.assertEqual(code, 1, out)
        self.assertIn("box、other-box", out)
        self.assertNotIn("ssh -o", self.read("calls"))

    def test_dry_run_does_not_touch_the_host(self):
        code, out = self.run_cli([*UP, "windows-mcp", "box", "--dry-run"])
        self.assertEqual(code, 0, out)
        self.assertIn(EC2_IP, out)
        code, out = self.run_cli([*DOWN, "windows-mcp", "box", "--dry-run"])
        self.assertEqual(code, 0, out)
        self.assertEqual(self.read("scripts"), "")

    def test_down_cleans_up_and_keeps_task(self):
        self.run_cli([*UP, "windows-mcp", "box", "--create-task"])
        code, out = self.run_cli([*DOWN, "windows-mcp", "box"])
        self.assertEqual(code, 0, out)
        self.assertIn("已收乾淨", out)
        self.assertFalse(self.has("listen") or self.has("serve") or self.has("config"))
        self.assertTrue(self.has("task"))

    def test_client_host_with_keep_false_leaves_no_task(self):
        # 客戶機器：在 services.yaml 用 hosts 覆寫那台的 start，task 用完就刪
        skill = Path(self.tmp.name) / "remote-access"
        shutil.copytree(RA_SCRIPTS.parent, skill)
        with open(skill / "services.yaml", "a") as f:
            f.write("    hosts:\n      client-box:\n"
                    "        start: [{task: {name: remote-access-windows-mcp, keep: false}}]\n")
        with open(Path(self.env["HOME"]) / ".ssh" / "config", "a") as f:
            f.write("\nHost client-box\n  HostName client-box.tail123.ts.net\n")
        entry = [sys.executable, str(skill / "scripts" / "remote-access")]
        # 不用 --create-task：task 不會留在那台
        code, out = self.run_cli([*entry, "up", "windows-mcp", "client-box"])
        self.assertEqual(code, 0, out)
        self.assertTrue(self.has("task") and self.has("listen"))
        code, out = self.run_cli([*entry, "down", "windows-mcp", "client-box"])
        self.assertEqual(code, 0, out)
        self.assertFalse(self.has("task") or self.has("listen") or self.has("serve") or self.has("config"))
        # 其他 host 照服務定義 keep: true
        self.run_cli([*entry, "up", "windows-mcp", "box", "--create-task"])
        self.run_cli([*entry, "down", "windows-mcp", "box"])
        self.assertTrue(self.has("task"))

    def test_down_when_not_running(self):
        code, out = self.run_cli([*DOWN, "windows-mcp", "box"])
        self.assertEqual(code, 0, out)
        self.assertIn("本來就沒開", out)

    def test_down_leaves_other_programs_alone(self):
        (self.state / "listen").write_text("other:4242/nginx.exe")
        (self.state / "serve").write_text("other")
        code, out = self.run_cli([*DOWN, "windows-mcp", "box"])
        self.assertEqual(code, 0, out)
        self.assertEqual(self.read("listen"), "other:4242/nginx.exe")
        self.assertEqual(self.read("serve"), "other")

    def test_help(self):
        for args in (UP, DOWN):
            code, out = self.run_cli([*args, "--help"])
            self.assertEqual(code, 0, out)
            self.assertIn("--dry-run", out)
        code, out = self.run_cli([sys.executable, str(ENTRY), "--help"])
        self.assertIn("up", out)
        self.assertIn("down", out)


if __name__ == "__main__":
    unittest.main()
