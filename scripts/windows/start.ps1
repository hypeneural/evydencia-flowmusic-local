$ErrorActionPreference='Stop'
Set-Location (Resolve-Path (Join-Path $PSScriptRoot '../..'))
if (!(Test-Path .venv/Scripts/python.exe)) { throw 'Run install.ps1 first' }
if ($env:FLOWMUSIC_PROVIDER -and $env:FLOWMUSIC_PROVIDER -ne 'mock') { throw 'Live provider is disabled in this staging revision' }
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --workers 1
