param(
    [ValidateSet('ca','pva')]
    [string]$Protocol = 'ca'
)

if (-not (Test-Path -Path 'results')) { New-Item -ItemType Directory -Path 'results' | Out-Null }

Write-Host "Running latency monitor (protocol=$Protocol)..."
$lat = Start-Process -FilePath python -ArgumentList '01_latency_monitor.py','--protocol', $Protocol -PassThru

Write-Host "Running throughput monitor (protocol=$Protocol)..."
$thr = Start-Process -FilePath python -ArgumentList '02_throughput.py','--protocol', $Protocol -PassThru

Write-Host "Running packet loss monitor (protocol=$Protocol)..."
$loss = Start-Process -FilePath python -ArgumentList '03_packetloss.py','--protocol', $Protocol -PassThru

Write-Host "Running CPU monitor ..."
$cpu = Start-Process -FilePath python -ArgumentList '04_cpu.py' -PassThru

Write-Host "Press Ctrl+C to stop all tests."
try {
    while ($true) { Start-Sleep -Seconds 1 }
}
finally {
    foreach ($p in @($lat,$thr,$loss,$cpu)) {
        if ($p -and -not $p.HasExited) {
            try { $p.Kill() } catch {}
        }
    }
    Write-Host "All processes terminated."
}
