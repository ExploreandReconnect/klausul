# Lists the models your Nebius Token Factory key can actually reach.
#
#   .\tools\list_models.ps1
#
# The key is read at the prompt, never stored, never echoed to PowerShell history,
# and never written to disk. Run it, then paste the output back.

$k = Read-Host "Paste your Nebius Token Factory key"

if ([string]::IsNullOrWhiteSpace($k)) {
    Write-Host "No key entered. Nothing to do." -ForegroundColor Yellow
    exit 1
}

$raw = curl.exe -s -H "Authorization: Bearer $k" https://api.tokenfactory.nebius.com/v1/models
Remove-Variable k

if ([string]::IsNullOrWhiteSpace($raw)) {
    Write-Host "Empty response. No network, or the host is unreachable." -ForegroundColor Red
    exit 1
}

try {
    $j = $raw | ConvertFrom-Json
} catch {
    Write-Host "Response was not JSON. First 300 characters:" -ForegroundColor Red
    Write-Host $raw.Substring(0, [Math]::Min(300, $raw.Length))
    exit 1
}

if ($j.error) {
    Write-Host "The API returned an error:" -ForegroundColor Red
    Write-Host ($j.error | ConvertTo-Json -Depth 4)
    exit 1
}

$all = $j.data.id
Write-Host ""
Write-Host ("Models reachable with this key: {0}" -f $all.Count) -ForegroundColor Green
Write-Host ""

$nv = $all | Where-Object { $_ -match 'nvidia|nemotron|nemo' }
if ($nv) {
    Write-Host "--- NVIDIA / Nemotron ---" -ForegroundColor Cyan
    $nv | ForEach-Object { Write-Host ("  " + $_) }
} else {
    Write-Host "--- No NVIDIA / Nemotron match. Full list follows. ---" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "--- every model, for the record ---" -ForegroundColor Cyan
$all | Sort-Object | ForEach-Object { Write-Host ("  " + $_) }
