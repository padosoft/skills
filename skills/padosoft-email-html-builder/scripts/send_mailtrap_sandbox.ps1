# Sends payload.json to the Mailtrap sandbox identified by $env:MAILTRAP_INBOX_ID.
# Usage (PowerShell, from the folder where payload.json is saved too):
#   $env:MAILTRAP_TOKEN = "your_token"; $env:MAILTRAP_INBOX_ID = "2494982"
#   .\send_mailtrap_sandbox.ps1
$ErrorActionPreference = "Stop"

# Guard: token required
if ([string]::IsNullOrWhiteSpace($env:MAILTRAP_TOKEN) -or [string]::IsNullOrWhiteSpace($env:MAILTRAP_INBOX_ID)) {
    Write-Error "Set MAILTRAP_TOKEN and MAILTRAP_INBOX_ID"
    exit 1
}

$payloadPath = Join-Path $PSScriptRoot "payload.json"
if (-not (Test-Path $payloadPath)) {
    Write-Error "Payload not found: $payloadPath"
    exit 1
}

# Read as UTF-8 bytes so accented characters and HTML entities are not corrupted
$body = [System.IO.File]::ReadAllBytes($payloadPath)

try {
    $resp = Invoke-RestMethod -Method Post `
        -Uri "https://sandbox.api.mailtrap.io/api/send/$($env:MAILTRAP_INBOX_ID)" `
        -Headers @{ Authorization = "Bearer $($env:MAILTRAP_TOKEN)" } `
        -ContentType "application/json; charset=utf-8" `
        -Body $body
    $resp | ConvertTo-Json -Depth 5
}
catch {
    Write-Host "Send failed:" $_.Exception.Message -ForegroundColor Red
    if ($_.ErrorDetails.Message) { Write-Host $_.ErrorDetails.Message }
    exit 1
}
