"""windows-access 的 script：同一台用的 windows-mcp-stdio、別台用的 windows-mcp-http.ps1。

windows-mcp-stdio 在假 WSL 跑：powershell.exe、wslpath 換成 PATH 上的假指令。
windows-mcp-http.ps1 要 pwsh 才跑（沒有就 skip）：Get-NetTCPConnection、Stop-Process、Start-Process、Set-Clipboard、
防火牆 cmdlet 換成同名的 PowerShell 函式（函式比 cmdlet 先被找到），windows-mcp.exe 換成假的 mise shim。
假 windows-mcp 把每次呼叫記進 calls、auth 時換 key 並把 key 印到 stdout／stderr，用來驗 script 有把它丟掉。
"""
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "windows-access" / "scripts"
STDIO_SCRIPT = SCRIPTS / "windows-mcp-stdio"
HTTP_SCRIPT = SCRIPTS / "windows-mcp-http.ps1"
PWSH = shutil.which("pwsh")
KEY = "s3cret-key"
MISE_SHIM = Path("AppData") / "Local" / "mise" / "shims" / "windows-mcp.exe"

# windows-mcp-stdio 只會問 mise shim 的路徑
FAKE_POWERSHELL = r"""#!/usr/bin/env bash
case "$3" in
  '"$env:LOCALAPPDATA\mise\shims\windows-mcp.exe"') printf 'C:\\Users\\me\\AppData\\Local\\mise\\shims\\windows-mcp.exe\r\n' ;;
esac
"""
# C:\Users\me\... 換成假 Windows 家目錄底下的路徑
FAKE_WSLPATH = r"""#!/usr/bin/env bash
p=${1//\\//}
echo "$FAKE_WINHOME${p#C:/Users/me}"
"""


class McpYamlTest(unittest.TestCase):
    def test_stdio_server_points_at_existing_script(self):
        text = (ROOT / "mcp.yaml").read_text()
        path = re.search(r'\$HOME/\.claude/skills/([^"]+windows-mcp-stdio)', text).group(1)
        self.assertTrue((ROOT / "skills" / path).is_file(), path)


class WindowsMcpStdioTest(unittest.TestCase):
    """windows-mcp-stdio：mcp.yaml 的進入點。找到 mise 裝的 shim 就 exec，找不到叫人去 apply，不是 WSL 就結束。"""

    def run_stdio(self, wsl=True, installed=True):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            home = tmp / "winhome"
            calls = tmp / "exe-calls"
            if installed:
                (home / MISE_SHIM).parent.mkdir(parents=True)
                (home / MISE_SHIM).write_text(f'#!/usr/bin/env bash\necho "$*" > {calls}\n')
                (home / MISE_SHIM).chmod(0o755)
            bin_dir = tmp / "bin"
            bin_dir.mkdir()
            if wsl:
                (bin_dir / "powershell.exe").write_text(FAKE_POWERSHELL)
                (bin_dir / "wslpath").write_text(FAKE_WSLPATH)
            for p in bin_dir.iterdir():
                p.chmod(0o755)
            # 不接上真的 PATH：這台若真的有 powershell.exe 也不會被找到
            env = {**os.environ, "PATH": f"{bin_dir}:/usr/bin:/bin", "FAKE_WINHOME": str(home)}
            result = subprocess.run(["bash", str(STDIO_SCRIPT)], env=env, capture_output=True, text=True,
                                    stdin=subprocess.DEVNULL, timeout=15)
            args = calls.read_text() if calls.exists() else None
        return result, args

    def test_execs_mise_shim_with_stdio_transport(self):
        result, args = self.run_stdio()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(args, "serve --transport stdio\n")

    def test_missing_exe_says_to_apply_on_windows_host(self):
        result, args = self.run_stdio(installed=False)
        self.assertEqual(result.returncode, 1)
        self.assertIsNone(args)
        self.assertIn("勾 windows-mcp", result.stderr)
        self.assertIn("mise\\shims\\windows-mcp.exe", result.stderr)

    def test_not_wsl_exits_with_reason(self):
        result, args = self.run_stdio(wsl=False)
        self.assertEqual(result.returncode, 1)
        self.assertIsNone(args)
        self.assertIn("不是 Windows 桌機的 WSL", result.stderr)


class WindowsMcpHttpFileTest(unittest.TestCase):
    def test_saved_with_utf8_bom(self):
        # Windows PowerShell 5.1 讀沒有 BOM 的 .ps1 會照系統的 ANSI 編碼解，中文訊息會壞掉、甚至 parse 失敗
        self.assertTrue(HTTP_SCRIPT.read_bytes().startswith(b"\xef\xbb\xbf"))


# 換掉 script 會叫的 Windows cmdlet。server「在聽 8000」用 state/listening 檔案代表
FAKES_PS1 = r"""
function Get-NetTCPConnection { [CmdletBinding()] param($LocalPort, $State)
  if (Test-Path "$env:FAKE_STATE/listening") { [pscustomobject]@{ OwningProcess = 4242 } } }
function Stop-Process { [CmdletBinding()] param($Id, [switch]$Force)
  Add-Content "$env:FAKE_STATE/calls" "stop $Id"; Remove-Item "$env:FAKE_STATE/listening" -ErrorAction SilentlyContinue }
function Start-Process { [CmdletBinding()] param($FilePath, $ArgumentList, $WindowStyle)
  & $FilePath @ArgumentList }
function Set-Clipboard { [CmdletBinding()] param([Parameter(ValueFromPipeline)]$Value)
  process { Set-Content "$env:FAKE_STATE/clip" $Value -NoNewline } }
function Get-NetFirewallRule { [CmdletBinding()] param($Direction, $Action, $Enabled)
  if ($env:FAKE_FIREWALL_ALLOW) { [pscustomobject]@{ DisplayName = 'windows-mcp allow' } } }
function Get-NetFirewallApplicationFilter { [CmdletBinding()] param([Parameter(ValueFromPipeline)]$AssociatedNetFirewallRule)
  process { [pscustomobject]@{ Program = 'C:\Users\me\AppData\Local\mise\installs\windows-mcp\windows-mcp.exe' } } }
"""

# 假 windows-mcp：auth 換 key 並把 key 印出來（真的 auth --force 也會印）；serve 開始「聽」後就結束
FAKE_WINDOWS_MCP = r"""#!/usr/bin/env bash
echo "$*" >> "$FAKE_STATE/calls"
case "$1" in
  auth)
    [ -n "$FAKE_AUTH_BROKEN" ] && exit 1
    k="rotated-$RANDOM$RANDOM"
    printf 'transport = "streamable-http"\nauth_key = "%s"\n' "$k" > "$HOME/.windows-mcp/config.toml"
    echo "Generated auth key: $k"; echo "Authorization: Bearer $k" >&2 ;;
  serve) touch "$FAKE_STATE/listening" ;;
esac
"""


def auth_call(host):
    return f"auth --transport streamable-http --host {host} --port 8000 --force"


@unittest.skipUnless(PWSH, "沒有 pwsh")
class WindowsMcpHttpTest(unittest.TestCase):
    """windows-mcp-http.ps1 start|stop|auth-header：key 不印出來、先停再換 key、--host 傳到 auth 和 serve。"""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.state = self.tmp / "state"
        self.state.mkdir()
        home = self.tmp / "home"
        (home / ".windows-mcp").mkdir(parents=True)
        self.config = home / ".windows-mcp" / "config.toml"
        self.config.write_text(f'transport = "streamable-http"\nauth_key = "{KEY}"\n')
        local = self.tmp / "local"
        exe = local / "mise" / "shims" / "windows-mcp.exe"
        exe.parent.mkdir(parents=True)
        exe.write_text(FAKE_WINDOWS_MCP)
        exe.chmod(0o755)
        self.fakes = self.tmp / "fakes.ps1"
        self.fakes.write_text(FAKES_PS1)
        self.env = {**os.environ, "HOME": str(home), "LOCALAPPDATA": str(local), "FAKE_STATE": str(self.state)}

    def run_ps(self, *args, **env):
        # 參數不加引號，跟人在 PowerShell 打的一樣（--host 這種 token 要照原樣進 $args）
        cmd = f". '{self.fakes}'; & '{HTTP_SCRIPT}' {' '.join(args)}; exit $LASTEXITCODE"
        return subprocess.run([PWSH, "-NoProfile", "-NonInteractive", "-Command", cmd], env={**self.env, **env},
                              capture_output=True, text=True, timeout=60)

    def calls(self):
        path = self.state / "calls"
        return path.read_text().splitlines() if path.exists() else []

    def key(self):
        return re.search(r'auth_key = "([^"]+)"', self.config.read_text()).group(1)

    def clip(self):
        path = self.state / "clip"
        return path.read_text() if path.exists() else ""

    def assert_no_key(self, result):
        for key in (KEY, self.key()):
            self.assertNotIn(key, result.stdout + result.stderr)

    def test_help(self):
        result = self.run_ps("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        for word in ("start", "stop", "auth-header", "--host"):
            self.assertIn(word, result.stdout)
        self.assertEqual(self.calls(), [])

    def test_start_on_loopback_rotates_then_serves_and_copies_key(self):
        result = self.run_ps("start", "--host", "127.0.0.1")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.calls(), [auth_call("127.0.0.1"), "serve --host 127.0.0.1"])
        self.assertNotEqual(self.key(), KEY)
        self.assertEqual(self.clip(), self.key())
        self.assert_no_key(result)

    def test_start_defaults_to_all_interfaces(self):
        result = self.run_ps("start")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.calls(), [auth_call("0.0.0.0"), "serve --host 0.0.0.0"])
        self.assert_no_key(result)

    def test_start_refuses_while_server_is_running(self):
        (self.state / "listening").touch()
        result = self.run_ps("start", "--host", "127.0.0.1")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.calls(), [])
        self.assertEqual(self.key(), KEY)

    def test_start_on_all_interfaces_refuses_when_firewall_allows_inbound(self):
        result = self.run_ps("start", "--host", "0.0.0.0", FAKE_FIREWALL_ALLOW="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("防火牆", result.stderr)
        self.assertEqual(self.calls(), [])

    def test_start_refuses_when_key_not_rotated(self):
        result = self.run_ps("start", "--host", "127.0.0.1", FAKE_AUTH_BROKEN="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("key 沒換掉", result.stderr)
        self.assertNotIn("serve --host 127.0.0.1", self.calls())
        self.assertEqual(self.clip(), "")

    def test_start_rejects_other_hosts(self):
        result = self.run_ps("start", "--host", "192.168.1.5")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.calls(), [])

    def test_stop_stops_server_before_rotating_key_back_to_loopback(self):
        (self.state / "listening").touch()
        result = self.run_ps("stop")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.calls(), ["stop 4242", auth_call("127.0.0.1")])
        self.assertNotEqual(self.key(), KEY)
        self.assertIn("還在聽 8000 的程式：0", result.stdout)
        self.assert_no_key(result)

    def test_stop_fails_when_key_not_rotated(self):
        result = self.run_ps("stop", FAKE_AUTH_BROKEN="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("已收掉", result.stdout)

    def test_auth_header_prints_bearer_line(self):
        result = self.run_ps("auth-header")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, f"Authorization: Bearer {KEY}\n")

    def test_unknown_subcommand_fails(self):
        result = self.run_ps("serve")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.calls(), [])


if __name__ == "__main__":
    unittest.main()
