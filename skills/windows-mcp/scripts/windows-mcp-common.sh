# windows-mcp-serve、windows-mcp-stop、windows-mcp-auth-header 共用：叫 PowerShell、找 Windows 家目錄、讀 key。
# 不是可以直接跑的腳本，由那三支 source。要在桌機 WSL：靠 powershell.exe 操作 Windows 那邊。

PORT=8000

command -v powershell.exe >/dev/null || { echo "找不到 powershell.exe：要在桌機 WSL 跑" >&2; exit 1; }

# 跑一行 PowerShell，去掉 \r。擋掉 stdin，不然 powershell.exe 會把它吃掉。
# PowerShell 查無結果也會回 exit 1，成敗一律看呼叫端最後的檢查
pwsh() { powershell.exe -NoProfile -Command "$1" </dev/null | tr -d '\r' || true; }

# Windows 的 %USERPROFILE%，換成 WSL 路徑
win_home() { wslpath "$(pwsh '$env:USERPROFILE')"; }

# 印出 Windows 那邊 ~/.windows-mcp/config.toml 的 auth_key；沒有就回非 0
auth_key() { grep -oP 'auth_key\s*=\s*"\K[^"]+' "$(win_home)/.windows-mcp/config.toml"; }
