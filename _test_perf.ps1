$sw = [System.Diagnostics.Stopwatch]::StartNew()
$r = Invoke-RestMethod -Uri 'http://localhost:8001/engine/llms/library/search?sort=downloads&force=true' -Method GET
$sw.Stop()
Write-Host "Time: $($sw.Elapsed.TotalSeconds)s, Models: $($r.count)"
