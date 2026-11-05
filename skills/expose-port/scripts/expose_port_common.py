"""expose-port-funnel 與 expose-port-quick-tunnel 共用的部分：輸出、跑指令、參數、從公網驗證開著或收掉、
停 Windows 那邊的程式。

不是可以直接跑的腳本。兩支腳本用 `Path(__file__).resolve().parent` 把這個目錄加進 sys.path 再 import，
skillshare sync 成 symlink 時也找得到。

環境變數：
  EXPOSE_PORT_PROBE_INTERVAL   等公開網址生效時每次重試間隔秒數，預設 3（測試設 0）
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlsplit

PROBE_TRIES = 10
DNS_TRIES = 20
# 從公網打收掉的網址會看到的碼：Funnel 連不上是 000，quick tunnel 是 Cloudflare 回 530（2026-11-05 henry-laptop 實測）
CLOSED_CODES = ("000", "530")
WINDOWS_SHELLS = ("powershell.exe", "pwsh.exe", "powershell", "pwsh")


def say(msg):
    print(msg, flush=True)


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def split_curl_args(argv):
    """`--` 之前給 argparse，之後是兩次驗證都帶的 curl 參數。"""
    if "--" not in argv:
        return argv, []
    i = argv.index("--")
    return argv[:i], argv[i + 1:]


def add_verify_args(p):
    p.add_argument("--path", default="/", help="驗證時打的路徑")
    p.add_argument("--expect-without", required=True, help="不帶驗證時要回的 HTTP 狀態碼")
    p.add_argument("--expect-with", required=True, help="帶驗證時要回的 HTTP 狀態碼")
    p.add_argument("--auth-header-cmd", required=True, help="印出一行驗證 header 的 shell 指令")


def public_ip(host):
    """用公開 DNS 查 host 的 IP。

    本機查可能拿錯或拿不到：ts.net 名稱在 tailnet 內會拿到 tailnet IP（連線逾時），
    剛開的 trycloudflare.com 網址可能已經被本機 DNS 快取成查無此名。
    """
    out = run([
        "curl", "-s", "-m", "10", f"https://cloudflare-dns.com/dns-query?name={host}&type=A",
        "-H", "accept: application/dns-json",
    ]).stdout
    try:
        answers = [a["data"] for a in json.loads(out).get("Answer", []) if a.get("type") == 1]
    except (ValueError, AttributeError):
        answers = []
    return answers[-1] if answers else ""


def wait_public_ip(host):
    """等公開 DNS 查得到 host 的 IP，每隔 EXPOSE_PORT_PROBE_INTERVAL 秒重查，最多 DNS_TRIES 次；查不到回空字串。

    Funnel 剛開時公開 DNS 可能還沒有那台 ts.net 名稱的紀錄（2026-11-05 在 henry-laptop 實測：
    開完立刻查是查無此名，之後才查得到）。
    """
    interval = float(os.environ.get("EXPOSE_PORT_PROBE_INTERVAL", "3"))
    for i in range(DNS_TRIES):
        ip = public_ip(host)
        if ip:
            return ip
        if i < DNS_TRIES - 1:
            time.sleep(interval)
    return ""


def probe(url, ip, curl_args, header_file=None):
    """打一次 url，回 HTTP 狀態碼字串（連不上回 000）。有 ip 就用 --resolve 指到那個 IP。"""
    parts = urlsplit(url)
    cmd = ["curl", "-s", "-m", "30", "-o", "/dev/null", "-w", "%{http_code}"]
    if ip:
        cmd += ["--resolve", f"{parts.hostname}:{parts.port or 443}:{ip}"]
    cmd += [*curl_args, url]
    if header_file:
        cmd += ["-H", f"@{header_file}"]
    return run(cmd).stdout.strip() or "000"


def verify(args, base_url, ip=""):
    """從公網打 base_url + args.path：不帶驗證要回 args.expect_without，帶了要回 args.expect_with。

    驗證 header 由 args.auth_header_cmd 印出，寫進只有自己讀得到的暫存檔再用 `curl -H @檔案` 帶，
    不會出現在 curl 的參數裡。沒給 ip 時每次重試前再查一次公開 DNS。
    """
    host = urlsplit(base_url).hostname
    url = base_url.rstrip("/") + args.path
    interval = float(os.environ.get("EXPOSE_PORT_PROBE_INTERVAL", "3"))
    header = run(["bash", "-c", args.auth_header_cmd])
    if header.returncode != 0 or not header.stdout.strip():
        say("--auth-header-cmd 沒印出 header")
        return False
    fd, header_file = tempfile.mkstemp(prefix="expose-port-")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(header.stdout.strip().splitlines()[0] + "\n")
        # 公開網址剛開要幾秒才通，等到不帶驗證的回應符合預期
        for i in range(PROBE_TRIES):
            ip = ip or public_ip(host)
            without = probe(url, ip, args.curl_args)
            if without == args.expect_without:
                break
            if i < PROBE_TRIES - 1:
                time.sleep(interval)
        with_auth = probe(url, ip, args.curl_args, header_file)
    finally:
        os.unlink(header_file)
    say(f"公網驗證：不帶驗證={without}（要 {args.expect_without}），帶驗證={with_auth}（要 {args.expect_with}）")
    return without == args.expect_without and with_auth == args.expect_with


def public_state(url):
    """從公網打一次 url（不帶驗證）：回 (收掉了沒, 看到什麼)。公開 DNS 查不到也算收掉。"""
    host = urlsplit(url).hostname
    ip = public_ip(host)
    if not ip:
        return True, "公開 DNS 查不到"
    code = probe(url, ip, [])
    return code in CLOSED_CODES, code


def public_closed(url):
    """收的完成條件之一：從公網打 url 要連不上。剛停掉時可能還通一下，每隔幾秒重打，最多 PROBE_TRIES 次。

    不能只看 `tailscale funnel status`：前景開的 Funnel 不會列成 serve config，status 印
    `No serve config` 時公網照樣回 401（2026-11-05 henry-laptop 實測）。
    """
    interval = float(os.environ.get("EXPOSE_PORT_PROBE_INTERVAL", "3"))
    for i in range(PROBE_TRIES):
        closed, seen = public_state(url)
        if closed:
            break
        if i < PROBE_TRIES - 1:
            time.sleep(interval)
    say(f"公網 {url}：{seen}（要連不上：{'、'.join(CLOSED_CODES)} 或公開 DNS 查不到）")
    return closed


def windows_shell(cmd):
    """cmd 是叫 Windows 程式的指令（WSL 經 powershell.exe、或直接跑 .exe）時，回能跑 PowerShell 的那支；不是回 None。

    WSL 停掉自己這邊的行程，不會停掉它叫起來的 Windows 程式（2026-11-05 henry-laptop 實測 tailscale.exe、
    cloudflared.exe 都還在），收的時候要另外從 PowerShell 停。
    """
    name = os.path.basename(cmd[0]).lower()
    if name in WINDOWS_SHELLS:
        return cmd[0]
    if name.endswith(".exe"):
        return "powershell.exe"
    return None


def windows_procs(shell, exe, patterns, stop=False):
    """Windows 上名稱是 exe、命令列符合全部 patterns（.NET regex）的行程數；stop=True 先停掉再數。數不出來回 -1。"""
    conds = " -and ".join(f"$_.CommandLine -match '{pat}'" for pat in patterns)
    query = f"Get-CimInstance Win32_Process -Filter \"Name='{exe}'\" | Where-Object {{ {conds} }}"
    if stop:
        run([shell, "-NoProfile", "-Command", f"{query} | ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force }}"])
    out = run([shell, "-NoProfile", "-Command", f"@({query}).Count"]).stdout.strip()
    try:
        return int(out.splitlines()[-1])
    except (ValueError, IndexError):
        return -1


def cmd_check_closed(args):
    """check-closed：開在別台的網址收掉後，從這邊確認公網連不上。"""
    sys.exit(0 if public_closed(args.url.rstrip("/") + "/") else 1)
