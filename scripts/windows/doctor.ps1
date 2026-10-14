$ErrorActionPreference = 'Stop'
Set-Location (Resolve-Path (Join-Path $PSScriptRoot '../..'))
Write-Host 'Evydencia FlowMusic doctor: mock-only, no Google credits'
foreach ($cmd in @('py','git','node','npm')) { if (!(Get-Command $cmd -ErrorAction SilentlyContinue)) { Write-Warning "$cmd missing" } }
if (!(Test-Path .venv/Scripts/python.exe)) { throw 'Run scripts/windows/install.ps1 first' }
& .\.venv\Scripts\python.exe -m compileall -q app tests
if ($LASTEXITCODE -ne 0) { throw 'compileall failed' }
& .\.venv\Scripts\python.exe -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'pytest failed' }
if (Test-Path vendor/flowmusic-cli/package.json) {
 Push-Location vendor/flowmusic-cli
 try { npm test; if ($LASTEXITCODE -ne 0) { throw 'npm test failed' } } finally { Pop-Location }
} else { Write-Warning 'Upstream not installed' }
Write-Host 'Local diagnostic finished; authenticated generation NOT tested.'
