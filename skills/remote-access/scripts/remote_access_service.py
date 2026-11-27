"""照 services.yaml 在別台起、收服務：up、down。

  remote-access up <服務> <host> [--create-task] [--key-env <變數>] [--dry-run]
  remote-access down <服務> <host> [--dry-run]

<服務> 是 skill 資料夾 services.yaml 的 services 底下的名稱；<host> 是 ssh config 的 Host。

up（serve 模式）：經 ssh 確認那台有人登入桌面（needs_desktop）→ key 經 ssh 的 stdin 寫到那台的設定檔 →
`schtasks /run` 常駐的 Interactive task 起 server → `tailscale serve --bg` → 從這邊打 ts.net 網址驗證
（不帶 key、帶 key 各回 verify 寫的碼）。驗證不過就收掉起了一半的東西、exit 1。已經起好而且驗證過就只回報。
第一次在那台建常駐 task 要加 --create-task（它會一直留在那台，先問使用者）。

down：停 task 和聽那個 port 的服務行程、關掉轉到那個 port 的 serve、刪掉那台的設定檔（裡面有 key）；
task 照 keep 留著或刪掉（keep: false 的 task 由 up 自己建，不用 --create-task）。本來就沒開也 exit 0。
services.yaml 的 hosts.<host> 可以蓋掉個別 host 的欄位，例如客戶機器的 start 改 keep: false。

key 從環境變數讀（services.yaml 的 key.env，--key-env 可以改讀別的變數），不接受從參數輸入；
不出現在任何指令參數、task 定義、輸出裡。送去 Windows 的 PowerShell 一律用 -EncodedCommand，
那邊只回 ASCII 的 key=value 行，不受 Big5、CLIXML 影響。

環境變數：
  EXPOSE_PORT_PROBE_INTERVAL   驗證時每次重試間隔秒數，預設 3（測試設 0）
"""
import argparse
import base64
import ipaddress
import os
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from remote_access_common import run, say, verify

SERVICES_FILE = Path(__file__).resolve().parent.parent / "services.yaml"
ENV_NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
# key 會寫進 TOML 字串，只收不用跳脫的字元
KEY_RE = re.compile(r"[A-Za-z0-9._~+/=-]{16,}")
TASK_NAME_RE = re.compile(r"[A-Za-z0-9._-]+")


def die(msg):
    say(msg)
    sys.exit(1)


def load_services():
    try:
        import yaml
    except ImportError:
        die("讀 services.yaml 要 PyYAML：python3 -m pip install --user PyYAML（或用系統套件 python3-yaml）")
    return yaml.safe_load(SERVICES_FILE.read_text())["services"]


def ssh_hosts():
    """ssh config 的 Host（不含萬用字元）。

    shortcut: 只讀 ~/.ssh/config 本身，不跟 Include；機器清單分檔時再補。
    """
    path = Path.home() / ".ssh" / "config"
    hosts = []
    for line in path.read_text().splitlines() if path.exists() else []:
        parts = line.split()
        if len(parts) >= 2 and parts[0].lower() == "host":
            hosts += [h for h in parts[1:] if not set(h) & set("*?!")]
    return hosts


def ssh_hostname(host):
    for line in run(["ssh", "-G", host]).stdout.splitlines():
        if line.startswith("hostname "):
            return line.split(None, 1)[1].strip()
    return ""


def tailnet_ip(name):
    out = run(["tailscale", "ip", "-4", name]).stdout.strip().splitlines()
    try:
        return str(ipaddress.IPv4Address(out[0].strip())) if out else ""
    except ValueError:
        return ""


# ==========================================================================
# 送去 Windows 的 PowerShell。@PORT@ 這類佔位在 ps_script 換掉；值都先驗過格式，不會拼出指令
# ==========================================================================

PS_PRELUDE = r"""
$ProgressPreference = 'SilentlyContinue'
$Port = @PORT@
$Task = '@TASK@'
$Match = '@MATCH@'
$Cfg = Join-Path $HOME '.windows-mcp\remote-access.toml'
function Listeners {
  @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) | ForEach-Object { $_.OwningProcess } |
    Select-Object -Unique | ForEach-Object { Get-CimInstance Win32_Process -Filter "ProcessId = $_" }
}
function Ours { @(Listeners | Where-Object { $_.CommandLine -match $Match }) }
# 轉到這個 port 的 serve 是我們的；shortcut: 有別的 serve 設定就當成衝突，不細分 port、路徑
function ServeState {
  $s = (tailscale serve status --json 2>$null | Out-String)
  if ($s -match "127\.0\.0\.1:$Port") { 'ours' } elseif ($s -match '"Proxy"') { 'other' } else { 'none' }
}
"""

PS_PROBE = r"""
$me = $env:USERNAME
$d = @(Get-CimInstance Win32_Process -Filter "Name='explorer.exe'" | Where-Object {
  $_.SessionId -ge 1 -and (Invoke-CimMethod -InputObject $_ -MethodName GetOwner).User -eq $me }).Count
"desktop=$d"
"task=$(if (Get-ScheduledTask -TaskName $Task -ErrorAction SilentlyContinue) { 1 } else { 0 })"
$l = @(Listeners)
if (-not $l.Count) { 'listen=none' }
elseif ($l | Where-Object { $_.CommandLine -notmatch $Match }) { 'listen=other:' + (($l | ForEach-Object { "$($_.ProcessId)/$($_.Name)" }) -join ',') }
else { 'listen=ours' }
"serve=$(ServeState)"
"""

# key 從 stdin 讀，寫進只有 server 讀的設定檔；task 的參數只有設定檔路徑
PS_START = r"""
$create = @CREATE@
$key = [Console]::In.ReadLine()
if (-not $key) { 'error=nokey'; exit 1 }
New-Item -ItemType Directory -Force -Path (Split-Path $Cfg) | Out-Null
$toml = "[server]`ntransport = `"streamable-http`"`nhost = `"0.0.0.0`"`nport = $Port`nauth_key = `"$key`"`n`n[security]`nip_allowlist = [@ALLOW@]`n"
[IO.File]::WriteAllText($Cfg, $toml)
if (-not (Get-ScheduledTask -TaskName $Task -ErrorAction SilentlyContinue)) {
  if (-not $create) { 'error=notask'; exit 1 }
  # 先找 dotfiles 用 mise 裝的 shim，沒有再找 PATH 上的（同 windows-mcp-http.ps1）
  $exe = Join-Path $env:LOCALAPPDATA 'mise\shims\windows-mcp.exe'
  if (-not (Test-Path -LiteralPath $exe)) { $exe = (Get-Command windows-mcp -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1).Source }
  if (-not $exe) { 'error=noexe'; exit 1 }
  $action = New-ScheduledTaskAction -Execute $exe -Argument "serve --config `"$Cfg`""
  $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive
  $settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
  Register-ScheduledTask -TaskName $Task -Action $action -Principal $principal -Settings $settings | Out-Null
  if (-not (Get-ScheduledTask -TaskName $Task -ErrorAction SilentlyContinue)) { 'error=taskcreate'; exit 1 }
}
schtasks /run /tn $Task *> $null
for ($i = 0; $i -lt 30 -and -not (Ours).Count; $i++) { Start-Sleep -Seconds 1 }
if (-not (Ours).Count) { 'error=nolisten'; exit 1 }
tailscale serve --bg "http://127.0.0.1:$Port" *> $null
if ((ServeState) -ne 'ours') { 'error=serve'; exit 1 }
'started=1'
"""

PS_STOP = r"""
$keep = @KEEP@
$was = 0
if (Get-ScheduledTask -TaskName $Task -ErrorAction SilentlyContinue) { Stop-ScheduledTask -TaskName $Task -ErrorAction SilentlyContinue }
$l = Ours
if ($l.Count) { $was = 1; $l | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue } }
for ($i = 0; $i -lt 10 -and (Ours).Count; $i++) { Start-Sleep -Seconds 1 }
if ((ServeState) -eq 'ours') { $was = 1; tailscale serve --https=443 off *> $null }
Remove-Item -LiteralPath $Cfg -Force -ErrorAction SilentlyContinue
if (-not $keep) { Unregister-ScheduledTask -TaskName $Task -Confirm:$false -ErrorAction SilentlyContinue }
"was_running=$was"
"""


def ps_script(action, body, svc, **extra):
    values = {"PORT": str(svc["port"]), "TASK": svc["task"]["name"], "MATCH": svc["match"], **extra}
    script = f"# remote-access:{action}\n" + PS_PRELUDE + body
    for k, v in values.items():
        script = script.replace(f"@{k}@", v)
    return script


def win(host, script, stdin=None):
    """經 ssh 在那台跑 PowerShell，回 (exit code, {key: value})。只認 ASCII 的 key=value 行，其他（CLIXML、中文）略過。"""
    encoded = base64.b64encode(script.encode("utf-16-le")).decode()
    p = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", host, "powershell", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
        input=(stdin + "\n") if stdin else "", capture_output=True, text=True, errors="replace",
    )
    out = {}
    for line in p.stdout.splitlines():
        m = re.fullmatch(r"([a-z_]+)=([\x20-\x7e]*)", line.strip())
        if m:
            out[m.group(1)] = m.group(2)
    return p.returncode, out


def probe(host, svc):
    return win(host, ps_script("probe", PS_PROBE, svc))[1]


def stop(host, svc):
    _, out = win(host, ps_script("stop", PS_STOP, svc, KEEP="$true" if svc["task"]["keep"] else "$false"))
    after = probe(host, svc)
    clean = after.get("listen") != "ours" and after.get("serve") != "ours"
    return out.get("was_running") == "1", clean


# ==========================================================================
# 子命令
# ==========================================================================

def resolve(args):
    """查服務定義和 host，不認得就列出可用的。回整理好的服務定義。"""
    services = load_services()
    if args.service not in services:
        die(f"不認得的服務：{args.service}。可用的：{'、'.join(services)}")
    hosts = ssh_hosts()
    if args.host not in hosts:
        die(f"不認得的 host：{args.host}（ssh config 的 Host）。可用的：{'、'.join(hosts) or '（~/.ssh/config 沒有 Host）'}")
    svc = dict(services[args.service])
    # 個別 host 的覆寫：hosts.<host> 底下的欄位整個蓋掉服務定義的同名欄位
    svc.update((svc.pop("hosts", None) or {}).get(args.host) or {})
    if svc.get("mode") != "serve":
        die(f"{args.service} 的 mode 是 {svc.get('mode')}：這版只支援 serve")
    # shortcut: 只支援第一個 start 是 Windows 的 task；ssh 起法、依序嘗試等需要時再加
    task = next((s["task"] for s in svc.get("start", []) if "task" in s), None)
    if not task or not TASK_NAME_RE.fullmatch(task.get("name", "")):
        die(f"{args.service} 的 start 要有 task（name 只能英數和 ._-）")
    svc["task"] = {"name": task["name"], "keep": bool(task.get("keep", True))}
    svc["port"] = int(svc["port"])
    svc["match"] = re.sub(r"[^A-Za-z0-9._-]", "", svc.get("stop", {}).get("match", args.service))
    return svc


def cmd_up(args):
    svc = resolve(args)
    key_env = args.key_env or svc["key"]["env"]
    if not ENV_NAME_RE.fullmatch(key_env):
        die(f"--key-env 要是環境變數名稱：{key_env}")
    key = os.environ.get(key_env, "")
    if not key:
        die(f"環境變數 {key_env} 沒有 key：先讓 shell 讀進 key（agent 那台的 ~/.config/windows-mcp/auth.env）")
    if not KEY_RE.fullmatch(key):
        die(f"{key_env} 的 key 格式不對：至少 16 字元，只能英數和 ._~+/=-")
    hostname = ssh_hostname(args.host)
    if not hostname.endswith(".ts.net"):
        die(f"{args.host} 在 ssh config 的 HostName 要是 ts.net 名稱，serve 網址從它來（現在是 {hostname or '空的'}）")
    allow = []
    for name in svc.get("allow", []):
        ip = tailnet_ip(name)
        if not ip:
            die(f"tailscale ip -4 {name} 查不到 IP：services.yaml 的 allow 要是 tailnet 裡的機器名稱")
        allow.append(ip)
    if not allow:
        die(f"{args.service} 的 allow 是空的：serve 模式要列允許連進來的 agent 機器")
    url = f"https://{hostname}"
    v = svc["verify"]
    curl_args = [a for h in v.get("headers", []) for a in ("-H", h)]
    if "body" in v:
        curl_args += ["-X", "POST", "--data-raw", v["body"]]
    check = SimpleNamespace(
        path=v.get("path", "/"), expect_without=str(v["expect_without"]), expect_with=str(v["expect_with"]),
        # header 指令只引用變數名稱，key 不進參數
        auth_header_cmd=f'printf "Authorization: Bearer %s\\n" "${key_env}"', curl_args=curl_args,
    )
    if args.dry_run:
        say(f"[dry-run] {args.host}：{svc['task']['name']} task 起 {args.service}（0.0.0.0:{svc['port']}，"
            f"allowlist {','.join(allow)}），tailscale serve → {url}{check.path}，key 從 {key_env}")
        return

    state = probe(args.host, svc)
    if not state:
        die(f"ssh {args.host} 跑 PowerShell 沒有回應：先確認 ssh {args.host} 連得上、那台是 Windows")
    if svc.get("needs_desktop") and state.get("desktop", "0") in ("", "0"):
        die(f"{args.host} 沒有人登入桌面：請先登入 {args.host} 的桌面（ssh 的那個帳號），再跑一次")
    if state.get("listen", "").startswith("other"):
        die(f"{args.host} 的 {svc['port']} 被別的程式佔著（{state['listen'][len('other:'):]}）：請使用者處理，不自動換 port")
    if state.get("serve") == "other":
        die(f"{args.host} 已經有別的 tailscale serve 設定：先在那台 tailscale serve status 看是誰在用")
    if state.get("listen") == "ours" or state.get("serve") == "ours":
        if verify(check, url, public_dns=False):
            say(f"{args.service} 在 {args.host} 已經起好：{url}{check.path}")
            return
        say("上一輪起的沒通過驗證，收掉重起")
        stop(args.host, svc)
    if state.get("task") != "1" and svc["task"]["keep"] and not args.create_task:
        die(f"{args.host} 還沒有常駐 task {svc['task']['name']}：它會一直留在那台，問過使用者後加 --create-task 再跑")

    say(f"在 {args.host} 起 {args.service}（task {svc['task']['name']}），開 tailscale serve…")
    allow_toml = ", ".join(f"'{ip}'" for ip in allow)
    code, out = win(args.host, ps_script("start", PS_START, svc, ALLOW=allow_toml,
                                         # keep: false 的 task 每次 up 建、down 刪，不用問
                                         CREATE="$true" if args.create_task or not svc["task"]["keep"] else "$false"),
                 stdin=key)
    if code != 0 or out.get("started") != "1":
        reason = {
            "notask": "task 不在（加 --create-task 建）",
            "noexe": "那台找不到 windows-mcp（照 windows-access 裝）",
            "taskcreate": "建 task 失敗",
            "nolisten": f"server 30 秒內沒在 {svc['port']} 起來（桌面 session 有沒有登入著）",
            "serve": "tailscale serve 沒開起來",
        }.get(out.get("error"), f"exit {code}")
        stop(args.host, svc)
        die(f"起不來：{reason}。起了一半的已收掉")
    if not verify(check, url, public_dns=False):
        stop(args.host, svc)
        die("驗證沒過，起了一半的已收掉。看 remote-access 的 reference.md")
    say(f"網址：{url}{check.path}（MCP 的 key 用 {key_env}）")
    say("MCP 設定指到這個網址後，在 session 裡打 /mcp 重連")


def cmd_down(args):
    svc = resolve(args)
    if args.dry_run:
        say(f"[dry-run] {args.host}：停 {svc['task']['name']} 和聽 {svc['port']} 的 {svc['match']}、關 serve、"
            f"刪那台的設定檔，task {'留著' if svc['task']['keep'] else '刪掉'}")
        return
    was, clean = stop(args.host, svc)
    if not clean:
        die(f"{args.host} 還沒收乾淨：在那台看 {svc['port']} 誰在聽、tailscale serve status，重跑 down 也安全")
    say(f"{args.service} 在 {args.host} 已收乾淨" if was else f"{args.service} 在 {args.host} 本來就沒開")


def main(argv, prog):
    cmd = prog.split()[-1]
    parser = argparse.ArgumentParser(prog=prog, description=__doc__.split("\n\n")[0])
    parser.add_argument("service", help="services.yaml 裡的服務名稱")
    parser.add_argument("host", help="ssh config 的 Host")
    parser.add_argument("--dry-run", action="store_true", help="只印要做什麼，不連那台")
    if cmd == "up":
        parser.add_argument("--create-task", action="store_true",
                            help="那台還沒有常駐 task 時建一個（會一直留著，先問使用者）")
        parser.add_argument("--key-env", help="改從這個環境變數讀 key（預設看 services.yaml 的 key.env）")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(line_buffering=True)
    (cmd_up if cmd == "up" else cmd_down)(args)
