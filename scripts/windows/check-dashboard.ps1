$ErrorActionPreference = 'Stop'
Set-Location (Resolve-Path (Join-Path $PSScriptRoot '../..'))
$base = 'http://127.0.0.1:8765'
if (-not (Test-Path 'data/local-token.txt')) { throw 'Token local ausente; inicie start.ps1 em mock primeiro' }
$token = (Get-Content 'data/local-token.txt' -Raw).Trim()
if (-not $token) { throw 'Token local vazio' }
$headers = @{ 'X-Local-Token' = $token }
Write-Host 'Validacao REAL do HTTP local, sem invocar o Google nem gerar musica'
$page = Invoke-WebRequest -UseBasicParsing -Uri "$base/painel-contas" -TimeoutSec 10
if ($page.StatusCode -ne 200 -or $page.Content -notmatch 'id="accounts-body"') {
  throw 'Tela HTML indisponivel'
}
$accounts = Invoke-RestMethod -Uri "$base/v1/music/accounts" -Headers $headers -TimeoutSec 10
$queue = Invoke-RestMethod -Uri "$base/v1/music/queue" -Headers $headers -TimeoutSec 10
if ($null -eq $accounts.profiles) { throw 'Contrato profiles ausente' }
foreach ($profile in $accounts.profiles) {
  foreach ($secret in @('access_token','refresh_token','session','cookie')) {
    if ($profile.PSObject.Properties.Name -contains $secret) { throw "Campo sensivel na API: $secret" }
  }
  if ($profile.PSObject.Properties.Name -notcontains 'session_status') {
    throw "session_status ausente no perfil $($profile.profile)"
  }
  Write-Host ("Perfil={0} email_presente={1} sessao={2} creditos={3} expirado={4}" -f $profile.profile, [bool]$profile.email, $profile.session_status, $profile.credits_remaining, $profile.stale)
}
Write-Host "Fila live_enabled=$($queue.live_enabled) blocked=$($queue.blocked)"
Write-Host 'Painel e contrato HTTP local verificados. Nenhuma credencial foi exibida.'
