param([switch]$EnableLive, [switch]$ResumePending)
$ErrorActionPreference='Stop'
Set-Location (Resolve-Path (Join-Path $PSScriptRoot '../..'))
if (!(Test-Path .venv/Scripts/python.exe)) { throw 'Execute install.ps1 antes.' }
if ($EnableLive) {
  # Offline safety gate: never execute old approved queued jobs silently.
  $checkArgs = @('scripts/preflight_accounts.py')
  if ($ResumePending) { $checkArgs += '--allow-queued' }
  & .\.venv\Scripts\python.exe @checkArgs
  if ($LASTEXITCODE -ne 0) { throw 'Preflight bloqueou LIVE. Revise jobs, lock, integridade DB e sessao antes de iniciar.' }
  if (!(Test-Path vendor/flowmusic-cli/bin/flowmusic.mjs)) { throw 'CLI upstream nao instalado.' }
  Write-Host 'Perfis de conta sao selecionados por pedido; cada perfil precisa de sua propria sessao.'
  $env:FLOWMUSIC_PROVIDER = 'cli'
  $env:FLOWMUSIC_ALLOW_LIVE = 'true'
  Write-Warning 'FILA REAL ATIVA: somente jobs com approve_live=true podem consumir creditos.'
  Write-Warning 'Uso de endpoints nao oficiais exige validacao dos termos. Nao use workers adicionais.'
} else {
  $env:FLOWMUSIC_PROVIDER = 'mock'
  $env:FLOWMUSIC_ALLOW_LIVE = 'false'
  Write-Host 'API simulada, sem consumo de creditos.'
}
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --workers 1
exit $LASTEXITCODE
