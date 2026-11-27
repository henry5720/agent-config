# Read the Windows location service and print the gps JSON PMS punches need:
#   {latitude, longitude, accuracy, capturedAt}
# Keep this file ASCII-only: Windows PowerShell 5.1 reads BOM-less UTF-8 as the
# system code page, so any CJK character breaks parsing.
# Run with Windows PowerShell 5.1: System.Device exists only on .NET Framework.
# Needs Settings > Privacy & security > Location > "Let desktop apps access your location".
$ProgressPreference = 'SilentlyContinue'  # keep stdout to the one JSON line (no CLIXML progress over ssh)
Add-Type -AssemblyName System.Device
$w = New-Object System.Device.Location.GeoCoordinateWatcher('High')
$w.Start()
$deadline = (Get-Date).AddSeconds(15)
while ($w.Status -ne 'Ready' -and $w.Permission -ne 'Denied' -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 200 }
$p = $w.Position; $c = $p.Location; $w.Stop()
if ($w.Permission -eq 'Denied') { [Console]::Error.WriteLine('location permission denied: allow desktop apps to access location'); exit 2 }
if ($c.IsUnknown) { [Console]::Error.WriteLine("no location within 15s (status=$($w.Status))"); exit 1 }
[pscustomobject]@{
  latitude   = $c.Latitude
  longitude  = $c.Longitude
  accuracy   = $c.HorizontalAccuracy
  # PMS accepts at most 3 fractional digits; ToString('o') gives 7 and is rejected.
  capturedAt = $p.Timestamp.UtcDateTime.ToString("yyyy-MM-dd'T'HH:mm:ss.fff'Z'")
} | ConvertTo-Json -Compress
