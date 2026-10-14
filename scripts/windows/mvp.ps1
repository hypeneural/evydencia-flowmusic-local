param(
  [ValidateSet('check','accounts','login','account','generate')][string]$Mode = 'check',
  [ValidatePattern('^[a-z][a-z0-9_-]{0,31}$')][string]$Profile = 'default',
  [string]$RequestId,
  [string]$Prompt,
  [string]$Model = 'Lyria 3.5',
  [ValidateRange(60,600)][int]$Seconds = 120,
  [ValidateSet('wav','mp3','m4a')][string]$Format = 'wav',
  [switch]$Instrumental,
  [switch]$ApproveLive
)
$ErrorActionPreference = 'Stop'
Set-Location (Resolve-Path (Join-Path $PSScriptRoot '../..'))
if (!(Test-Path '.venv/Scripts/python.exe')) { throw 'Execute scripts/windows/install.ps1 antes.' }
$python = (Resolve-Path '.venv/Scripts/python.exe').Path
$argv = @('scripts/mvp_probe.py','--mode', $Mode, '--profile', $Profile)
if ($Mode -eq 'generate') {
  if (-not $RequestId -or -not $Prompt) { throw 'RequestId e Prompt sao obrigatorios para gerar.' }
  $argv += @('--request-id', $RequestId, '--prompt', $Prompt, '--model', $Model,
             '--seconds', [string]$Seconds, '--format', $Format)
  if ($Instrumental) { $argv += '--instrumental' }
  if ($ApproveLive) { $argv += '--approve-live' }
}
& $python @argv
exit $LASTEXITCODE
