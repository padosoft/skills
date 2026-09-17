<#
.SYNOPSIS
  Installa le skill Padosoft di uno o piu' profili (Windows / PowerShell).

.EXAMPLE
  Install-PadosoftSkills core -Global          # trasversali, per tutti i progetti
  Install-PadosoftSkills laravel, email        # stack del progetto corrente
  Install-PadosoftSkills -List                 # profili disponibili
  Install-PadosoftSkills core -DryRun          # mostra i comandi senza eseguirli

.NOTES
  Prerequisito: Node.js 18+ (per npx).
  Uso rapido senza clonare il repo:
    iwr -useb https://raw.githubusercontent.com/padosoft/skills/main/scripts/install-profile.ps1 | iex; Install-PadosoftSkills core -Global
#>
function Install-PadosoftSkills {
    [CmdletBinding()]
    param(
        [Parameter(Position = 0)][string[]] $Profiles,
        [switch] $Global,
        [switch] $DryRun,
        [switch] $List,
        [string] $Repo = "padosoft/skills",
        [string] $Branch = "main"
    )
    $ErrorActionPreference = "Stop"

    # Guard: npx obbligatorio
    if (-not (Get-Command npx -ErrorAction SilentlyContinue)) {
        Write-Error "npx non trovato: installa Node.js 18+ (https://nodejs.org)"; return
    }

    # profiles.json: locale se siamo nel repo, altrimenti scaricato
    $local = Join-Path (Split-Path $PSScriptRoot -Parent) "profiles.json"
    $json = if ($PSScriptRoot -and (Test-Path $local)) {
        Get-Content $local -Raw | ConvertFrom-Json
    } else {
        Invoke-RestMethod "https://raw.githubusercontent.com/$Repo/$Branch/profiles.json"
    }

    if ($List -or -not $Profiles) {
        Write-Host "Profili disponibili:"
        foreach ($p in $json.profiles.PSObject.Properties) {
            Write-Host ("  - {0}: {1}" -f $p.Name, ($p.Value -join ", "))
        }
        if (-not $Profiles) { Write-Host "`nUso: Install-PadosoftSkills <profilo> [-Global] [-DryRun]" }
        return
    }

    $failed = $false
    foreach ($profile in $Profiles) {
        $names = $json.profiles.$profile
        if (-not $names) { Write-Warning "Profilo sconosciuto o vuoto: $profile"; $failed = $true; continue }
        Write-Host ("== profilo {0}{1}" -f $profile, $(if ($Global) { " (globale)" } else { "" }))
        foreach ($skill in $names) {
            $url = "https://github.com/$Repo/tree/$Branch/skills/$skill"
            $args = @("--yes", "skills", "add")
            if ($Global) { $args += "-g" }
            $args += $url
            if ($DryRun) { Write-Host ("npx " + ($args -join " ")) ; continue }
            Write-Host "-- $skill"
            & npx @args
            if ($LASTEXITCODE -ne 0) { Write-Warning "installazione fallita: $skill"; $failed = $true }
        }
    }
    if (-not $failed) { Write-Host "Fatto. 'npx skills list' mostra cosa e' installato e dove." }
}

# Esecuzione diretta: .\install-profile.ps1 core -Global
if ($MyInvocation.InvocationName -ne '.' -and $args.Count -gt 0) {
    $positional = @($args | Where-Object { $_ -notlike '-*' })
    Install-PadosoftSkills -Profiles $positional `
        -Global:($args -contains '-Global' -or $args -contains '--global' -or $args -contains '-g') `
        -DryRun:($args -contains '-DryRun' -or $args -contains '--dry-run') `
        -List:($args -contains '-List' -or $args -contains '--list')
}
