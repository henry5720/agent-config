"""windows-access 的 script：同一台用的 windows-mcp-stdio、別台用的 windows-mcp-http.ps1。

windows-mcp-stdio 在假 WSL 跑：powershell.exe、wslpath 換成 PATH 上的假指令。
windows-mcp-http.ps1 要 PowerShell 才跑（TEST_POWERSHELL 指定哪支，預設 pwsh，沒有就 skip）：Get-NetTCPConnection、Get-CimInstance、Stop-Process、Start-Process、
Set-Clipboard、防火牆 cmdlet 換成同名的 PowerShell 函式（函式比 cmdlet 先被找到），windows-mcp.exe 換成假的：
Linux 放在 mise shim 的位置，Windows 上做不出假 .exe，改放 PATH 上的 windows-mcp.cmd（script 找不到 shim 時找 PATH）。
假 windows-mcp 把每次呼叫記進 calls、auth 時換 key 並把 key 印到 stdout／stderr，用來驗 script 有把它丟掉。
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "windows-access" / "scripts"
STDIO_SCRIPT = SCRIPTS / "windows-mcp-stdio"
HTTP_SCRIPT = SCRIPTS / "windows-mcp-http.ps1"
PWSH = os.environ.get("TEST_POWERSHELL") or shutil.which("pwsh")
WINDOWS = os.name == "nt"
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
        text = (ROOT / "mcp.yaml").read_text(encoding="utf-8")
        path = re.search(r'\$HOME/\.claude/skills/([^"]+windows-mcp-stdio)', text).group(1)
        self.assertTrue((ROOT / "skills" / path).is_file(), path)


@unittest.skipIf(WINDOWS, "windows-mcp-stdio 在 WSL 跑")
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
# Windows PowerShell 5.1 導向時用 OEM code page 輸出，中文訊息會壞
[Console]::OutputEncoding = New-Object Text.UTF8Encoding $false
function Get-NetTCPConnection { [CmdletBinding()] param($LocalPort, $State)
  if (Test-Path "$env:FAKE_STATE/listening") { [pscustomobject]@{ OwningProcess = 4242 } } }
# 聽 8000 的那支行程：預設是 windows-mcp，FAKE_PROC_* 換成別的程式
function Get-CimInstance { [CmdletBinding()] param($ClassName, $Filter)
  $cmd = if ($env:FAKE_PROC_CMDLINE) { $env:FAKE_PROC_CMDLINE } else { 'C:\Users\me\AppData\Local\mise\shims\windows-mcp.exe serve --host 0.0.0.0' }
  $name = if ($env:FAKE_PROC_NAME) { $env:FAKE_PROC_NAME } else { 'windows-mcp.exe' }
  [pscustomobject]@{ ProcessId = 4242; Name = $name; CommandLine = $cmd } }
function Stop-Process { [CmdletBinding()] param($Id, [switch]$Force)
  Add-Content "$env:FAKE_STATE/calls" "stop $Id"; Remove-Item "$env:FAKE_STATE/listening" -ErrorAction SilentlyContinue }
function Start-Process { [CmdletBinding()] param($FilePath, $ArgumentList, $WindowStyle)
  & $FilePath @ArgumentList }
function Set-Clipboard { [CmdletBinding()] param([Parameter(ValueFromPipeline)]$Value)
  process { Set-Content "$env:FAKE_STATE/clip" $Value -NoNewline } }
# FAKE_FIREWALL_ALLOW 有值時有一條啟用中的 inbound 允許規則；FAKE_FW_* 換它的程式、通訊協定、port（預設放行 windows-mcp）
function Get-NetFirewallRule { [CmdletBinding()] param($Direction, $Action, $Enabled)
  if ($env:FAKE_FIREWALL_ALLOW) { [pscustomobject]@{ DisplayName = 'test allow' } } }
function Get-NetFirewallApplicationFilter { [CmdletBinding()] param([Parameter(ValueFromPipeline)]$AssociatedNetFirewallRule)
  process { $p = if ($env:FAKE_FW_PROGRAM) { $env:FAKE_FW_PROGRAM } else { 'C:\Users\me\AppData\Local\mise\installs\windows-mcp\windows-mcp.exe' }
    [pscustomobject]@{ Program = $p } } }
function Get-NetFirewallPortFilter { [CmdletBinding()] param([Parameter(ValueFromPipeline)]$AssociatedNetFirewallRule)
  process { $proto = if ($env:FAKE_FW_PROTOCOL) { $env:FAKE_FW_PROTOCOL } else { 'TCP' }
    $port = if ($env:FAKE_FW_PORT) { $env:FAKE_FW_PORT } else { 'Any' }
    [pscustomobject]@{ Protocol = $proto; LocalPort = @($port -split ',') } } }
"""

# 假 windows-mcp：auth 換 key 並把 key 印出來（真的 auth --force 也會印）；serve 開始「聽」後就結束
FAKE_WINDOWS_MCP = r"""
import os, random, sys
from pathlib import Path
state = Path(os.environ["FAKE_STATE"])
with open(state / "calls", "a") as f:
    f.write(" ".join(sys.argv[1:]) + "\n")
if sys.argv[1] == "auth":
    if os.environ.get("FAKE_AUTH_BROKEN"):
        sys.exit(1)
    k = f"rotated-{random.randrange(10**9)}"
    Path(os.environ["FAKE_CONFIG"]).write_text(f'transport = "streamable-http"\nauth_key = "{k}"\n')
    print(f"Generated auth key: {k}")
    print(f"Authorization: Bearer {k}", file=sys.stderr)
elif sys.argv[1] == "serve":
    (state / "listening").touch()
"""


def auth_call(host):
    return f"auth --transport streamable-http --host {host} --port 8000 --force"


@unittest.skipUnless(PWSH, "沒有 PowerShell")
class WindowsMcpHttpTest(unittest.TestCase):
    """windows-mcp-http.ps1 start|stop|rotate|auth-header：key 不印出來、rotate 先停再換 key、stop 不換、
    --host 傳到 auth 和 serve、有 --ip-allowlist 時不查防火牆。"""

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
        fake = self.tmp / "fake_windows_mcp.py"
        fake.write_text(FAKE_WINDOWS_MCP)
        self.env = {**os.environ, "HOME": str(home), "LOCALAPPDATA": str(local), "FAKE_STATE": str(self.state),
                    "FAKE_CONFIG": str(self.config)}
        if WINDOWS:
            bin_dir = self.tmp / "bin"
            bin_dir.mkdir()
            (bin_dir / "windows-mcp.cmd").write_text(f'@"{sys.executable}" "{fake}" %*\r\n@exit /b %ERRORLEVEL%\r\n')
            drive, rest = os.path.splitdrive(str(home))
            # pwsh 7 的 $HOME 取 USERPROFILE，5.1 取 HOMEDRIVE + HOMEPATH
            self.env.update(USERPROFILE=str(home), HOMEDRIVE=drive, HOMEPATH=rest,
                            PATH=f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
        else:
            exe = local / MISE_SHIM.relative_to("AppData/Local")
            exe.parent.mkdir(parents=True)
            exe.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{fake}" "$@"\n')
            exe.chmod(0o755)
        self.fakes = self.tmp / "fakes.ps1"
        self.fakes.write_text(FAKES_PS1, encoding="utf-8-sig")  # 5.1 讀沒有 BOM 的檔照 ANSI 解

    def run_ps(self, *args, **env):
        # 參數不加引號，跟人在 PowerShell 打的一樣（--host 這種 token 要照原樣進 $args）
        cmd = f". '{self.fakes}'; & '{HTTP_SCRIPT}' {' '.join(args)}; exit $LASTEXITCODE"
        return subprocess.run([PWSH, "-NoProfile", "-NonInteractive", "-Command", cmd], env={**self.env, **env},
                              capture_output=True, encoding="utf-8", timeout=60)

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
        for word in ("start", "stop", "rotate", "auth-header", "--host", "--ip-allowlist"):
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
        self.assertIn("4242", result.stderr)

    def test_start_on_all_interfaces_refuses_when_firewall_allows_inbound(self):
        result = self.run_ps("start", "--host", "0.0.0.0", FAKE_FIREWALL_ALLOW="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("防火牆", result.stderr)
        self.assertEqual(self.calls(), [])

    def test_start_on_all_interfaces_refuses_when_firewall_allows_port_for_any_program(self):
        # 規則沒寫 windows-mcp，但放行 8000 的 inbound：誰聽 8000 區網都連得到
        result = self.run_ps("start", FAKE_FIREWALL_ALLOW="1", FAKE_FW_PROGRAM="C:\\Other\\app.exe", FAKE_FW_PORT="8000")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("test allow", result.stderr)
        self.assertEqual(self.calls(), [])

    def test_start_on_all_interfaces_refuses_when_firewall_allows_any_port_any_program(self):
        result = self.run_ps("start", FAKE_FIREWALL_ALLOW="1", FAKE_FW_PROGRAM="Any", FAKE_FW_PORT="Any")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("test allow", result.stderr)
        self.assertEqual(self.calls(), [])

    def test_start_on_all_interfaces_ignores_rules_bound_to_other_programs(self):
        # Teams 這類「指定程式、不限 port」的規則每台都有，擋了就永遠起不來
        result = self.run_ps("start", FAKE_FIREWALL_ALLOW="1", FAKE_FW_PROGRAM="C:\\Other\\app.exe", FAKE_FW_PORT="Any")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.calls(), [auth_call("0.0.0.0"), "serve --host 0.0.0.0"])

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

    def test_stop_stops_server_and_keeps_key(self):
        (self.state / "listening").touch()
        result = self.run_ps("stop")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.calls(), ["stop 4242"])
        self.assertEqual(self.key(), KEY)
        self.assertIn("還在聽 8000 的程式：0", result.stdout)
        self.assert_no_key(result)

    def test_stop_leaves_other_programs_on_port_alone_and_names_them(self):
        (self.state / "listening").touch()
        result = self.run_ps("stop", FAKE_PROC_NAME="python.exe", FAKE_PROC_CMDLINE="python.exe -m http.server 8000")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("stop 4242", self.calls())
        self.assertIn("4242", result.stderr)
        self.assertIn("python.exe", result.stderr)
        self.assertNotIn("已收掉", result.stdout)
        self.assertEqual(self.key(), KEY)

    def test_rotate_stops_server_before_rotating_key_back_to_loopback(self):
        (self.state / "listening").touch()
        result = self.run_ps("rotate")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.calls(), ["stop 4242", auth_call("127.0.0.1")])
        self.assertNotEqual(self.key(), KEY)
        self.assertIn("key 已換新", result.stdout)
        self.assert_no_key(result)

    def test_rotate_still_rotates_when_another_program_holds_the_port(self):
        (self.state / "listening").touch()
        result = self.run_ps("rotate", FAKE_PROC_NAME="python.exe", FAKE_PROC_CMDLINE="python.exe -m http.server 8000")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("stop 4242", self.calls())
        # 交出去的 key 照樣作廢
        self.assertNotEqual(self.key(), KEY)

    def test_rotate_fails_when_key_not_rotated(self):
        result = self.run_ps("rotate", FAKE_AUTH_BROKEN="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("已收掉", result.stdout)

    def test_start_with_allowlist_skips_firewall_check_and_passes_it_to_serve(self):
        result = self.run_ps("start", "--ip-allowlist", "100.100.7.68,100.64.0.2", FAKE_FIREWALL_ALLOW="1",
                             FAKE_FW_PROGRAM="Any", FAKE_FW_PORT="Any")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.calls(), [auth_call("0.0.0.0"),
                                        "serve --host 0.0.0.0 --ip-allowlist 100.100.7.68,100.64.0.2"])
        self.assert_no_key(result)

    def test_start_rejects_allowlist_that_is_not_ips(self):
        result = self.run_ps("start", "--ip-allowlist", "'1.2.3.4;calc'")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.calls(), [])

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
