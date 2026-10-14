$ErrorActionPreference = 'Stop'
Set-Location (Resolve-Path (Join-Path $PSScriptRoot '../..'))
foreach ($cmd in @('py','git','node','npm')) { if (!(Get-Command $cmd -ErrorAction SilentlyContinue)) { throw "Missing prerequisite: $cmd" } }
py -3 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw "venv creation failed" }
& .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
if ($LASTEXITCODE -ne 0) { throw "pip failed" }
if (!(Test-Path vendor/flowmusic-cli/.git)) {
 New-Item -ItemType Directory -Path vendor -Force | Out-Null
 git clone https://github.com/deluxebear/flowmusic-cli.git vendor/flowmusic-cli
 if ($LASTEXITCODE -ne 0) { throw "Upstream clone failed" }
}
git -C vendor/flowmusic-cli fetch origin
if ($LASTEXITCODE -ne 0) { throw "Upstream fetch failed" }
git -C vendor/flowmusic-cli checkout --detach 08491dc3319ae9f530c5c05c431196bbbbb10607
if ($LASTEXITCODE -ne 0) { throw "Upstream SHA not found" }
Push-Location vendor/flowmusic-cli
try { npm test; if ($LASTEXITCODE -ne 0) { throw "Upstream tests failed" } } finally { Pop-Location }
Write-Host 'Installed pinned upstream for INSPECTION, not enabled for live generation.'
