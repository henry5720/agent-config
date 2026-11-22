# windows-mcp-http：在這台 Windows 起、收 Windows-MCP 的 HTTP server，給別台的 agent 連。
# 直接在 Windows PowerShell（5.1 或 7）跑，不經 WSL；要在使用者登入的桌面 session 跑。key 不印出來。
# 存成 UTF-8 BOM：Windows PowerShell 5.1 讀沒有 BOM 的檔案會照 ANSI 解，中文會壞。
# 不設 $ErrorActionPreference = 'Stop'：5.1 會把 native 指令的 stderr 變成例外，auth 印到 stderr 的 key 會跟著例外訊息印出來。

$Port = 8000
$Config = [IO.Path]::Combine($HOME, '.windows-mcp', 'config.toml')
# 先找 dotfiles 用 mise 裝的 shim（-NoProfile 的 PowerShell 沒有 mise 的 PATH），沒有再找 PATH 上的
$Exe = [IO.Path]::Combine("$env:LOCALAPPDATA", 'mise', 'shims', 'windows-mcp.exe')
if (-not (Test-Path -LiteralPath $Exe)) { $Exe = (Get-Command windows-mcp -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1).Source }

$Usage = @'
用法：windows-mcp-http.ps1 <start|stop|auth-header> [--host 127.0.0.1|0.0.0.0]

  start        確認 8000 沒有程式在聽 → 換 key → 起 server（最小化視窗）→ key 複製到剪貼簿，不印出來
  stop         停掉聽 8000 的程式 → 換 key（交出去的那把作廢）、設定綁回 127.0.0.1 → 確認聽 8000 的是 0
  auth-header  印出 Authorization: Bearer <key>，給 remote-access 從公網驗證用

  --host       start 綁的位址，預設 0.0.0.0。ssh 轉發、quick tunnel 用 127.0.0.1；
               Funnel、tailscale serve 不改寫 Host，用 0.0.0.0（會先檢查防火牆沒放行 inbound）
  --help       印出這段
'@

function Fail($msg) { [Console]::Error.WriteLine($msg); exit 1 }

function Listening { @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue).Count }

function AuthKey {
  if (-not (Test-Path -LiteralPath $Config)) { return $null }
  $m = Select-String -LiteralPath $Config -Pattern 'auth_key\s*=\s*"([^"]+)"' | Select-Object -First 1
  if ($m) { $m.Matches[0].Groups[1].Value }
}

function NeedExe {
  if (-not $Exe) { Fail '找不到 windows-mcp：裝了 dotfiles 的話在 PowerShell 打 tools 勾 windows-mcp 再 apply；沒裝的照 Windows-MCP 的 README 裝，裝完新開一個 PowerShell 再跑' }
}

# 換新 key。auth --force 會把新 key 印出來，所以輸出全丟掉；比對前後的 key，沒換掉就停，
# 不然會把上一輪交出去的舊 key 再交一次
function Rotate($bind) {
  $old = AuthKey
  & $Exe auth --transport streamable-http --host $bind --port $Port --force *> $null
  $code = $LASTEXITCODE
  $new = AuthKey
  if ($code -or -not $new -or $new -eq $old) { Fail "key 沒換掉（windows-mcp auth 失敗，exit ${code}）" }
}

$argv = @($args)
$cmd = $null
$bind = '0.0.0.0'
for ($i = 0; $i -lt $argv.Count; $i++) {
  $a = $argv[$i]
  if ($a -eq '--help' -or $a -eq 'help') { $Usage; exit 0 }
  elseif ($a -eq '--host') { $i++; $bind = $argv[$i] }
  elseif (-not $cmd -and $a -in 'start', 'stop', 'auth-header') { $cmd = $a }
  else { [Console]::Error.WriteLine($Usage); Fail "看不懂的參數：$a" }
}
if (-not $cmd) { [Console]::Error.WriteLine($Usage); exit 2 }
if ($bind -notin '127.0.0.1', '0.0.0.0') { Fail "--host 只能是 127.0.0.1 或 0.0.0.0，收到：${bind}" }

if ($cmd -eq 'start') {
  NeedExe
  # server 跑著時換 key 不生效、舊 key 照樣能用（2026-11-05 henry-laptop 實測），所以先確認沒有 server 再換
  if ((Listening) -ne 0) { Fail "${Port} 已經有程式在聽，先跑 stop" }
  if ($bind -eq '0.0.0.0') {
    # server 綁 0.0.0.0 時區網能直連 8000，只剩 key 擋；查不到規則也當成沒擋住
    try {
      $allow = Get-NetFirewallRule -Direction Inbound -Action Allow -Enabled True -ErrorAction Stop |
        Where-Object { ($_ | Get-NetFirewallApplicationFilter).Program -match 'windows-mcp|\\uv\\' } |
        ForEach-Object { $_.DisplayName }
    } catch { Fail "查不到防火牆規則，不綁 0.0.0.0：$($_.Exception.Message)" }
    if ($allow) { Fail "防火牆有放行 windows-mcp 的 inbound 規則，區網可直連 ${Port}：$(@($allow) -join '、')" }
  }
  Rotate $bind
  Start-Process -WindowStyle Minimized -FilePath $Exe -ArgumentList 'serve', '--host', $bind
  for ($i = 0; $i -lt 30 -and (Listening) -eq 0; $i++) { Start-Sleep -Seconds 1 }
  if ((Listening) -eq 0) { Fail "server 30 秒內沒在 ${Port} 起來。從 ssh 跑的話沒有互動桌面，server 會直接結束：要在那台桌面開的 PowerShell 跑" }
  AuthKey | Set-Clipboard
  "server 在 ${bind}:${Port}，key 已複製到剪貼簿（沒有印出來）"
  exit 0
}

if ($cmd -eq 'stop') {
  NeedExe
  # 一定先停再換 key：server 跑著時 auth --force 只改 config.toml，跑著的 server 繼續收舊 key
  Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
  Rotate '127.0.0.1'
  $left = Listening
  "還在聽 ${Port} 的程式：${left}（要 0）"
  if ($left -ne 0) { Fail "還有程式在聽 ${Port}：重跑 stop（重跑也安全）" }
  '已收掉，key 已換新'
  exit 0
}

# auth-header
$key = AuthKey
if (-not $key) { Fail 'config.toml 裡沒有 auth_key：先跑 start' }
"Authorization: Bearer $key"
exit 0
