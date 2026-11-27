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
用法：windows-mcp-http.ps1 <start|stop|rotate|auth-header> [--host 127.0.0.1|0.0.0.0] [--ip-allowlist <IP,...>]

  start        確認 8000 沒有程式在聽 → 換 key → 起 server（最小化視窗）→ key 複製到剪貼簿，不印出來
  stop         停掉聽 8000 的 windows-mcp → 確認聽 8000 的是 0。key 不換，下次 start 前交出去的那把照樣能用
               聽 8000 的不是 windows-mcp 時不停它，列出 PID 和程式名、exit 1，交給使用者處理
  rotate       跟 stop 一樣先停，再換 key（交出去的那把作廢）、設定綁回 127.0.0.1。懷疑 key 外洩時用
  auth-header  印出 Authorization: Bearer <key>，給 remote-access 從公網驗證用

  --host          start 綁的位址，預設 0.0.0.0。ssh 轉發、quick tunnel 用 127.0.0.1；
                  Funnel、tailscale serve 不改寫 Host，用 0.0.0.0（會先檢查防火牆沒放行 inbound）
  --ip-allowlist  start 時只讓這些來源 IP 連（傳給 serve）。有給時綁 0.0.0.0 不查防火牆：區網直連也會被擋
  --help          印出這段
'@

function Fail($msg) { [Console]::Error.WriteLine($msg); exit 1 }

function Listening { @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue).Count }

# 聽 8000 的行程，帶命令列：stop 只停命令列看得出是 windows-mcp 的，別人的程式不殺
function Listeners {
  @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) | ForEach-Object { $_.OwningProcess } |
    Select-Object -Unique | ForEach-Object { Get-CimInstance Win32_Process -Filter "ProcessId = $_" }
}
function IsWindowsMcp($proc) { $proc.CommandLine -match 'windows-mcp' }
function DescribeListeners { (@(Listeners) | ForEach-Object { "PID $($_.ProcessId) $($_.Name)" }) -join '、' }

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
$allowlist = $null
for ($i = 0; $i -lt $argv.Count; $i++) {
  $a = $argv[$i]
  if ($a -eq '--help' -or $a -eq 'help') { $Usage; exit 0 }
  elseif ($a -eq '--host') { $i++; $bind = $argv[$i] }
  elseif ($a -eq '--ip-allowlist') { $i++; $allowlist = @($argv[$i]) -join ',' }  # 打 a,b 時 PowerShell 傳進來的是陣列
  elseif (-not $cmd -and $a -in 'start', 'stop', 'rotate', 'auth-header') { $cmd = $a }
  else { [Console]::Error.WriteLine($Usage); Fail "看不懂的參數：$a" }
}
if (-not $cmd) { [Console]::Error.WriteLine($Usage); exit 2 }
if ($bind -notin '127.0.0.1', '0.0.0.0') { Fail "--host 只能是 127.0.0.1 或 0.0.0.0，收到：${bind}" }
# 只收 IP、CIDR 和逗號，會原樣傳給 serve
if ($null -ne $allowlist -and "$allowlist" -notmatch '^[0-9A-Fa-f:./]+(,[0-9A-Fa-f:./]+)*$') { Fail "--ip-allowlist 要是逗號分隔的 IP，收到：${allowlist}" }

if ($cmd -eq 'start') {
  NeedExe
  # server 跑著時換 key 不生效、舊 key 照樣能用（2026-11-05 henry-laptop 實測），所以先確認沒有 server 再換
  if ((Listening) -ne 0) { Fail "${Port} 已經有程式在聽（$(DescribeListeners)）：是 windows-mcp 就先跑 stop，不是的話請自己處理" }
  if ($bind -eq '0.0.0.0' -and -not $allowlist) {
    # server 綁 0.0.0.0 時區網能直連 8000，只剩 key 擋；查不到規則也當成沒擋住。有 allowlist 時區網來源 IP 會被 server 擋，不查。
    # 擋三種：程式是 windows-mcp（或 uv 裝的）、TCP 放行 8000（不管程式）、不限程式也不限 port。
    # 指定別的程式、不限 port 的不擋（Teams 這類每台都有），那條只放行那支程式
    try {
      $allow = Get-NetFirewallRule -Direction Inbound -Action Allow -Enabled True -ErrorAction Stop |
        Where-Object {
          $prog = ($_ | Get-NetFirewallApplicationFilter).Program
          $pf = $_ | Get-NetFirewallPortFilter
          $ports = @($pf.LocalPort)
          ($prog -match 'windows-mcp|\\uv\\') -or
            (($pf.Protocol -in 'TCP', 'Any') -and (($ports -contains "$Port") -or ($ports -contains 'Any' -and $prog -eq 'Any')))
        } | ForEach-Object { $_.DisplayName }
    } catch { Fail "查不到防火牆規則，不綁 0.0.0.0：$($_.Exception.Message)" }
    if ($allow) { Fail "防火牆有放行 ${Port} 的 inbound 規則，區網可直連 ${Port}：$(@($allow) -join '、')" }
  }
  Rotate $bind
  $serveArgs = @('serve', '--host', $bind)
  if ($allowlist) { $serveArgs += @('--ip-allowlist', $allowlist) }
  Start-Process -WindowStyle Minimized -FilePath $Exe -ArgumentList $serveArgs
  for ($i = 0; $i -lt 30 -and (Listening) -eq 0; $i++) { Start-Sleep -Seconds 1 }
  if ((Listening) -eq 0) { Fail "server 30 秒內沒在 ${Port} 起來。從 ssh 跑的話沒有互動桌面，server 會直接結束：要在那台桌面開的 PowerShell 跑" }
  AuthKey | Set-Clipboard
  "server 在 ${bind}:${Port}，key 已複製到剪貼簿（沒有印出來）"
  exit 0
}

if ($cmd -in 'stop', 'rotate') {
  NeedExe
  # rotate 一定先停再換 key：server 跑著時 auth --force 只改 config.toml，跑著的 server 繼續收舊 key
  Listeners | Where-Object { IsWindowsMcp $_ } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
  if ($cmd -eq 'rotate') { Rotate '127.0.0.1' }
  $left = Listening
  "還在聽 ${Port} 的程式：${left}（要 0）"
  if ($left -ne 0) { Fail "還有程式在聽 ${Port}（$(DescribeListeners)）：是 windows-mcp 就重跑 ${cmd}（重跑也安全）；不是的話 ${cmd} 不會停它，請自己處理" }
  if ($cmd -eq 'rotate') { '已收掉，key 已換新' } else { '已收掉（key 沒換）' }
  exit 0
}

# auth-header
$key = AuthKey
if (-not $key) { Fail 'config.toml 裡沒有 auth_key：先跑 start' }
"Authorization: Bearer $key"
exit 0
