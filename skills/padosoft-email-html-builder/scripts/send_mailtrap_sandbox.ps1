# Invia payload.json alla sandbox Mailtrap indicata da $env:MAILTRAP_INBOX_ID.
# Uso (PowerShell, nella cartella dove hai salvato anche payload.json):
#   $env:MAILTRAP_TOKEN = "il_tuo_token"; $env:MAILTRAP_INBOX_ID = "2494982"
#   .\send_mailtrap_sandbox.ps1
$ErrorActionPreference = "Stop"

# Guard: token obbligatorio
if ([string]::IsNullOrWhiteSpace($env:MAILTRAP_TOKEN) -or [string]::IsNullOrWhiteSpace($env:MAILTRAP_INBOX_ID)) {
    Write-Error "Imposta MAILTRAP_TOKEN e MAILTRAP_INBOX_ID"
    exit 1
}

$payloadPath = Join-Path $PSScriptRoot "payload.json"
if (-not (Test-Path $payloadPath)) {
    Write-Error "Payload non trovato: $payloadPath"
    exit 1
}

# Lettura come byte UTF-8 per non corrompere accenti ed entita' HTML
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
    Write-Host "Invio fallito:" $_.Exception.Message -ForegroundColor Red
    if ($_.ErrorDetails.Message) { Write-Host $_.ErrorDetails.Message }
    exit 1
}
