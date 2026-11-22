# windows-mcp-stdio 用：叫 PowerShell、找 windows-mcp.exe。
# 不是可以直接跑的腳本，由 windows-mcp-stdio source。要在桌機 WSL：靠 powershell.exe 操作 Windows 那邊。

command -v powershell.exe >/dev/null || { echo "找不到 powershell.exe：要在桌機 WSL 跑" >&2; exit 1; }

# 跑一行 PowerShell，去掉 \r。擋掉 stdin，不然 powershell.exe 會把它吃掉。
# PowerShell 查無結果也會回 exit 1，成敗一律看呼叫端最後的檢查
pwsh() { powershell.exe -NoProfile -Command "$1" </dev/null | tr -d '\r' || true; }

# 印出 dotfiles 用 mise 裝的 windows-mcp.exe（shim）的 Windows 路徑；沒裝就說怎麼裝、回非 0。
# 寫完整路徑不靠 PATH：-NoProfile 的 PowerShell 沒有 mise 的 shims（henry5720/dotfiles#343 實測）
win_exe() {
  local exe; exe=$(pwsh '"$env:LOCALAPPDATA\mise\shims\windows-mcp.exe"')
  [ -f "$(wslpath "$exe")" ] || { echo "windows-mcp：找不到 $exe。在 Windows 主機的 PowerShell 打 tools 勾 windows-mcp 再 apply（dotfiles）" >&2; return 1; }
  echo "$exe"
}
