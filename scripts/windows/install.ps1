$ErrorActionPreference = 'Stop'
Set-Location (Resolve-Path (Join-Path $PSScriptRoot '../..'))
$pyCmd = if (Get-Command 'py' -ErrorAction SilentlyContinue) { 'py' } elseif (Get-Command 'python' -ErrorAction SilentlyContinue) { 'python' } else { throw "Missing prerequisite: Python (py or python)" }
foreach ($cmd in @('git','node','npm')) { if (!(Get-Command $cmd -ErrorAction SilentlyContinue)) { throw "Missing prerequisite: $cmd" } }
if ($pyCmd -eq 'py') { py -3 -m venv .venv } else { python -m venv .venv }
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
try {
 $npmCmd = if (Get-Command 'npm.cmd' -ErrorAction SilentlyContinue) { 'npm.cmd' } else { 'npm' }
 & $npmCmd test
 if ($LASTEXITCODE -ne 0) { throw "Upstream tests failed" }
} finally { Pop-Location }
Write-Host 'Installed pinned upstream for INSPECTION, not enabled for live generation.'
