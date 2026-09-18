<#
.SYNOPSIS
  Installs the Padosoft skills of one or more profiles (Windows / PowerShell).

.EXAMPLE
  Install-PadosoftSkills core -Global          # cross-project skills, for every project
  Install-PadosoftSkills laravel, email        # the stack of the current project
  Install-PadosoftSkills -List                 # available profiles
  Install-PadosoftSkills core -DryRun          # print the commands without running them

.NOTES
  Requirement: Node.js 18+ (for npx).
  Quick use without cloning the repo:
    irm https://raw.githubusercontent.com/padosoft/skills/main/scripts/install-profile.ps1 | iex; Install-PadosoftSkills core -Global
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

    # Guard: npx is required
    if (-not (Get-Command npx -ErrorAction SilentlyContinue)) {
        Write-Error "npx not found: install Node.js 18+ (https://nodejs.org)"; return
    }

    # profiles.json: the local copy when running from a clone, otherwise fetched from GitHub.
    # $PSScriptRoot is empty when this file is piped into iex, so it is checked before use:
    # Split-Path would throw on an empty -Path and abort the whole run.
    $json = $null
    if ($PSScriptRoot) {
        $localProfiles = Join-Path (Split-Path $PSScriptRoot -Parent) "profiles.json"
        if (Test-Path $localProfiles) { $json = Get-Content $localProfiles -Raw | ConvertFrom-Json }
    }
    if (-not $json) {
        $json = Invoke-RestMethod "https://raw.githubusercontent.com/$Repo/$Branch/profiles.json"
    }

    if ($List -or -not $Profiles) {
        Write-Host "Available profiles:"
        foreach ($p in $json.profiles.PSObject.Properties) {
            Write-Host ("  - {0}: {1}" -f $p.Name, ($p.Value -join ", "))
        }
        if (-not $Profiles) { Write-Host "`nUsage: Install-PadosoftSkills <profile> [-Global] [-DryRun]" }
        return
    }

    $failed = $false
    foreach ($profileName in $Profiles) {
        $names = $json.profiles.$profileName
        if (-not $names) { Write-Warning "Unknown or empty profile: $profileName"; $failed = $true; continue }
        Write-Host ("== profile {0}{1}" -f $profileName, $(if ($Global) { " (global)" } else { "" }))
        foreach ($skill in $names) {
            $url = "https://github.com/$Repo/tree/$Branch/skills/$skill"
            $npxArgs = @("--yes", "skills", "add")
            if ($Global) { $npxArgs += "-g" }
            $npxArgs += $url
            if ($DryRun) { Write-Host ("npx " + ($npxArgs -join " ")) ; continue }
            Write-Host "-- $skill"
            & npx @npxArgs
            if ($LASTEXITCODE -ne 0) { Write-Warning "installation failed: $skill"; $failed = $true }
        }
    }
    if (-not $failed) { Write-Host "Done. 'npx skills list' shows what is installed and where." }
}

# Direct execution: .\install-profile.ps1 core -Global
if ($MyInvocation.InvocationName -ne '.' -and $args.Count -gt 0) {
    $positional = @($args | Where-Object { $_ -notlike '-*' })
    Install-PadosoftSkills -Profiles $positional `
        -Global:($args -contains '-Global' -or $args -contains '--global' -or $args -contains '-g') `
        -DryRun:($args -contains '-DryRun' -or $args -contains '--dry-run') `
        -List:($args -contains '-List' -or $args -contains '--list')
}
