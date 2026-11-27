"""agent 那台的固定 key：init、rotate。

  remote-access key init [--key-env <變數>] [--force]
  remote-access key rotate [--key-env <變數>] [--dry-run]

key 存在 agent 那台的 ~/.config/windows-mcp/auth.env（資料夾 700、檔案 600），一行一個
`export <變數>='<key>'`，~/.zshenv 會 source 它。所有機器共用這把，`up` 時經 ssh 的 stdin 同步過去。

init：產生一把新 key 存起來。那個變數已經有 key 就不覆蓋，要加 --force；檔案裡其他變數不動。
rotate：懷疑外洩時換一把：先存新 key，再把已接上、而且用舊 key 的機器重起成新 key。
用別把 key 的機器（例如 --key-env 給客戶機器的）不動。

key 一律由這支產生，不接受從參數輸入，也不印出來。已經開著的 session 只在啟動時讀環境變數，
換完要重開 session 才會讀到新 key。
"""
import argparse
import os
import re
import secrets
import sys
from pathlib import Path
from types import SimpleNamespace

from remote_access_common import say, verify
from remote_access_service import (
    ENV_NAME_RE, cmd_up, die, load_services, probe, resolve, serve_check, ssh_hostname, ssh_hosts,
)

# shortcut: auth.env 和預設變數是 windows-mcp 的；別的服務也要 key 時改成照 services.yaml 的 key.env 分檔
DEFAULT_KEY_ENV = "WINDOWS_MCP_AUTH_KEY"
RESTART_HINT = "已經開著的 session 還拿著舊 key：重開 session 才會讀到（claude --bg 要重啟 daemon）"


def auth_env_path():
    return Path.home() / ".config" / "windows-mcp" / "auth.env"


def read_lines(path):
    return path.read_text().splitlines() if path.exists() else []


def var_re(name):
    return re.compile(rf"^\s*(export\s+)?{name}=")


def saved_key(lines, name):
    for line in lines:
        m = re.fullmatch(rf"\s*(?:export\s+)?{name}='([^']*)'\s*", line)
        if m:
            return m.group(1)
    return ""


def save_key(path, lines, name, key):
    """把 name 那行換成新 key（沒有就加在最後），其他行照留。先寫暫存檔再 rename，不會寫到一半。"""
    line = f"export {name}='{key}'"
    out = [line if var_re(name).match(l) else l for l in lines]
    if line not in out:
        out.append(line)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write("\n".join(out) + "\n")
    os.replace(tmp, path)


def new_key():
    # 43 字元，只有英數和 -_，符合 up 的 KEY_RE，也不用在 shell 單引號裡跳脫
    return secrets.token_urlsafe(32)


def connected_machines(key_env, key):
    """已接上、而且用的是這把 key 的 [(服務, host)]。

    shortcut: 用 probe 逐台查 ssh config 的 host（連不上的 ConnectTimeout 後跳過）；#143 的 ps 進來後改用它。
    那台在跑我們的服務、而且這把 key 驗證得過才算，用別把 key 的機器不算。
    """
    found = []
    for name, raw in load_services().items():
        if raw.get("mode") != "serve":
            continue
        for host in ssh_hosts():
            svc = resolve(SimpleNamespace(service=name, host=host))
            state = probe(host, svc)
            if "ours" not in (state.get("listen"), state.get("serve")):
                continue
            os.environ[key_env] = key
            if verify(serve_check(svc, key_env), f"https://{ssh_hostname(host)}", public_dns=False):
                found.append((name, host))
            else:
                say(f"{host} 的 {name} 用的不是 {key_env} 這把 key，不動")
    return found


def cmd_init(args):
    path = auth_env_path()
    lines = read_lines(path)
    if any(var_re(args.key_env).match(l) for l in lines) and not args.force:
        die(f"{path} 已經有 {args.key_env}，不覆蓋：懷疑外洩用 remote-access key rotate；真的要蓋掉加 --force")
    save_key(path, lines, args.key_env, new_key())
    say(f"{args.key_env} 已存到 {path}（600，沒有印出來）")
    say(f"新開的 session 才讀得到；{RESTART_HINT}")


def cmd_rotate(args):
    path = auth_env_path()
    lines = read_lines(path)
    old = saved_key(lines, args.key_env)
    if not old:
        die(f"{path} 沒有 {args.key_env}：先跑 remote-access key init")
    machines = connected_machines(args.key_env, old)
    names = "、".join(f"{h}（{s}）" for s, h in machines) or "沒有"
    if args.dry_run:
        say(f"[dry-run] 換 {path} 的 {args.key_env}，同步到已接上的機器：{names}")
        return
    # 先存新 key 再同步：同步到一半失敗時，已經換成新 key 的機器還對得上 auth.env
    key = new_key()
    save_key(path, lines, args.key_env, key)
    say(f"{args.key_env} 已換新存到 {path}（沒有印出來），同步到：{names}")
    os.environ[args.key_env] = key
    failed = []
    for name, host in machines:
        try:
            cmd_up(SimpleNamespace(service=name, host=host, key_env=args.key_env, create_task=False, dry_run=False))
        except SystemExit as e:
            if e.code:
                failed.append((name, host))
    say(RESTART_HINT)
    if failed:
        die("這幾台沒同步到，舊 key 可能還能用：" + "；".join(
            f"remote-access up {s} {h} --key-env {args.key_env}" for s, h in failed) + "（在讀得到新 key 的 session 跑）")


def main(argv, prog):
    parser = argparse.ArgumentParser(prog=prog, description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="action", required=True)
    init = sub.add_parser("init", help="產生 key 存到 auth.env")
    init.add_argument("--force", action="store_true", help="那個變數已經有 key 時也蓋掉（不會同步到別台）")
    rotate = sub.add_parser("rotate", help="換新 key，同步到已接上的機器")
    rotate.add_argument("--dry-run", action="store_true", help="只印會同步到哪幾台，不換")
    for p in (init, rotate):
        p.add_argument("--key-env", default=DEFAULT_KEY_ENV, help=f"auth.env 裡的變數名稱，預設 {DEFAULT_KEY_ENV}")
    args = parser.parse_args(argv)
    if not ENV_NAME_RE.fullmatch(args.key_env):
        die(f"--key-env 要是環境變數名稱：{args.key_env}")
    sys.stdout.reconfigure(line_buffering=True)
    (cmd_init if args.action == "init" else cmd_rotate)(args)
