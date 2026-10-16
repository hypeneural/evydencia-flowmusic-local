# API + fila FIFO durável — Windows MVP (v0.2)

**Integração real opcional e explicitamente autorizada**, sobre o `mvp_probe.py` que já gerou um WAV na validação local relatada em 14/10/2026. A API fica sempre local (`127.0.0.1:8765`). O serviço não usa Celery/Redis/Docker, nem modifica o Workflow principal. A API mock é o padrão.

## Codegraph
```mermaid
flowchart TD
  W["Future Python Workflow / localhost"] --> A["POST /v1/music/jobs (approve_live)"]
  A --> V["Pydantic + local token"]
  V --> DB["SQLite jobs / request_id UNIQUE"]
  DB --> Q["Queue FIFO: queued"]
  Q --> C["Single worker: BEGIN IMMEDIATE claim"]
  C --> P["submitting; run mvp_probe.py --approve-live ONCE"]
  P --> CLI["Pinned CLI, serialized OAuth + Flow Music generation"]
  CLI --> L["MVP ledger + WAV output; hash verification"]
  L --> OK["completed (artifacts)"]
  P --> BAD["needs_review; suspend queue, no retry"]
  BAD --> H["Manual inspection and reconciliation"]
```

## Status
- `queued`: gravado antes de qualquer solicitação remota; permanecerá no banco após reinício e poderá ser executado no modo live autorizado.
- `submitting`: reservado atomicamente por um worker; se houver crash será convertido em `needs_review`, mesmo que o envio talvez não tenha ocorrido. Conservador para evitar duplicação.
- `completed`: o probe concluiu, gravou ledger e todos os arquivos foram revalidados com SHA256.
- `needs_review`: saída ambígua, erro, timeout ou interrupção; nenhuma repetição automática. Bloqueia novos pedidos **no perfil afetado**; outros perfis podem seguir com novos pedidos independentes quando não há trava global.
- `abandoned`: operador confirmou revisão da biblioteca e decidiu abandonar; não há reenvio.
- `auth_required`: provider diferente de mock mas serviço live não habilitado.

## API
- `GET /health`: servidor responde.
- `GET /v1/music/status`: provider, fila, worker, bloqueios.
- `GET /v1/music/queue`: totais e bloqueios.
- `GET /v1/music/jobs?limit=30`: últimos jobs; o retorno contém prompts e deve ficar estritamente protegido em localhost.
- `GET /v1/music/jobs/{id}`: estado e arquivos se concluído.
- `GET /v1/music/jobs/{id}/events`: eventos redigidos sem prompt ou tokens.
- `GET /v1/music/jobs/{id}/artifacts`: arquivos após conclusão.
- `POST /v1/music/jobs`: `request_id`, `prompt`, `model`, `duration_seconds`, `instrumental`, `output_format`, `approve_live`.
- `POST /v1/music/jobs/{id}/reconcile`: somente para `needs_review` e confirmação explícita; `resolution=abandoned|completed`. Marcar completed exige ledger concluído e hash válido; não reexecuta a tarefa.
- `POST /v1/music/queue/resume`: não produz música diretamente; remove bloqueio de processamento somente após nenhum job unresolved e nenhuma `generation.lock`.

As requisições exceto health precisam do header `X-Local-Token` de `data/local-token.txt`. **Nunca inclua esse token em logs enviados ao agente.**

## Ativação local
```powershell
# Opção 1 — desenvolvimento seguro (sem chamadas Google):
.\scripts\windows\start.ps1

# Opção 2 — fila real: operador confirma termos e autoriza uso de créditos:
.\scripts\windows\start.ps1 -EnableLive
```

Em outro terminal, sem mostrar o valor do token:
```powershell
$token = (Get-Content data/local-token.txt -Raw).Trim()
$headers = @{ 'X-Local-Token' = $token }
$body = @{
  request_id = ('mvp-' + [guid]::NewGuid().ToString('N'))  # gerar novo ID
  prompt = 'Trilha instrumental de Natal com piano e sinos'
  instrumental = $true
  model = 'Lyria 3.5'
  duration_seconds = 120
  output_format = 'wav'
  approve_live = $true
} | ConvertTo-Json

# SOMENTE se quiser consumir créditos:
Invoke-RestMethod 'http://127.0.0.1:8765/v1/music/jobs' -Method Post -Headers $headers -ContentType 'application/json' -Body $body

# Consultas seguras em seguida:
Invoke-RestMethod 'http://127.0.0.1:8765/v1/music/queue' -Headers $headers
```

**A submissão real pode consumir créditos.** Não dispare o exemplo automaticamente. A criação em SQLite é idempotente com o mesmo `request_id` e payload; payload diferente retorna 409. A proteção não implica que a API não documentada do Google aceite uma chave idempotente. O worker chama o probe uma única vez. Se houver erro após tentativa, isola a conta original em `needs_review`; as outras contas só podem processar pedidos novos e independentes. Travas globais como `generation.lock` ainda bloqueiam todos os workers. O operador deve verificar o áudio/biblioteca antes de usar `reconcile` ou remover qualquer lock órfão. Nunca apague locks durante processo ativo.

A fila limita a 25 pendentes, usa um worker sem concorrência e faz polling local a cada ~0,75s. Não aciona chamadas automáticas para consultar créditos. As duas validações antes de ativar são: conta autenticada no Windows e termos de uso compatíveis com a forma de integração. Não usar proxies, rotação de contas ou bypass de proteções.

## Limites conhecidos
- O `mvp_probe.py` ainda só recebe a geração por prompt, modelo, instrumental, formato e duração; **lyrics personalizadas não são suportadas pela fila live** e retornam 422 em vez de serem ignoradas.
- O ledger originalmente não registrava `provider_job_id`/SSE incremental, então a recuperação após erro ambíguo é manual. Uma melhoria futura deve persistir esse ID antes de aguardar áudio, sem provocar novo POST.
- FFprobe e qualidade musical ainda precisam de validação antes do Workflow consumir WAV; a fila atual revalida caminho, tamanho e SHA-256.
- Prompts constam do SQLite local para recuperar jobs; proteger `data/` com NTFS ACL em máquinas compartilhadas.
- O servidor FastAPI executa um worker interno no `lifespan`, mantido por um único processo Windows. Não inicie vários Uvicorn workers. O serviço não integra o Workflow automaticamente; consumo depende de comando explícito.


## Perfis múltiplos e saldos — extensão da API
`GET /v1/music/accounts` lista aliases, presença local da sessão, último saldo consultado, `checked_at` e `stale` (cache com mais de 30 minutos). A lista é ordenada pelos **saldos recentes conhecidos** para auxiliar escolha manual; não consulta Google em background.

`POST /v1/music/jobs` aceita `account_profile` (alias; padrão `default`) além de `approve_live=true`. O perfil é persistido no payload do SQLite, exibido no retorno HTTP e inserido no ledger. Antes de finalizar, a fila confere o perfil do ledger e o SHA-256 do áudio.

`request_id` continua global entre perfis. O mesmo ID+payload retorna o mesmo job mesmo se a sessão do perfil estiver temporariamente indisponível. Novos IDs exigem sessão existente. A seleção do perfil não muda depois da aceitação e **não existe fallback automático por falta de créditos ou falha do provedor**.

O executor usa `FLOWMUSIC_HOME` individual; ver [ACCOUNTS.md](ACCOUNTS.md). Manter um worker global e não consultar saldos enquanto houver geração ativa. Os snapshots de saldo ficam em arquivos locais ignorados pelo Git, não numa nova tabela SQLite: isso evita migrar o banco já operacional.

## Ativação real após reinício
O script `start.ps1 -EnableLive` executa um preflight offline: em `needs_review`, `submitting`, arquivo de lock ou erro de integridade SQLite, recusa iniciar. Havendo tarefas live `queued`, a retomada exige revisão dos pedidos e a opção explícita `-ResumePending`. Nenhuma tarefa nova é enviada automaticamente apenas por consultar o inventário.

## Cadastro de perfis em SQLite
A migração transacional, antes de alterar o esquema, salva `jobs.db` pelo mecanismo SQLite backup em `data/backups`. Cria `account_profiles(alias, registered_at)` e `jobs.account_profile` com índice. Registros anteriores são associados a `default`, mantendo hash, ID e resultados originais. A coluna indexada é conferida contra o payload antes do envio ao provedor. Créditos permanecem em snapshots JSON locais de valor e horário para evitar fontes concorrentes.


## Atualização P0 de multicontas — 16/10/2026

A PR #3 (sobre PR #1) implementou `GET /v1/music/accounts`
com `enabled`, `auto_select`, `eligible`, `eligibility_reasons`
e `blocking_jobs_count`, além de
`POST /v1/music/accounts/{alias}/routing` (autenticado) para
habilitação explícita por conta.

`eligible=true` significa apenas pré-checagem local com sessão não
expirada, saldo recente, provider CLI LIVE e opt-in; NÃO é comprovação
de autorização remota do Google. `provider=mock` jamais indica
conta pronta para geração real.

O worker continua único: gerações de dois perfis diferentes não são
paralelas. Um job em `needs_review` não pode ser reenviado, nem pode
ser remapeado para outra conta. Outro pedido realmente independente
pode avançar em um segundo perfil válido.

No Windows, timeout do probe agora tenta encerrar apenas a árvore de
processos daquele Python/Node, preservando o banco e o job incerto.
Nenhum log de erro bruto do Google deve sair para o navegador.

Para reconciliação após timeout HTTP no gateway :8766, usar a rota
indexada `GET /v1/music/jobs/by-request/{request_id}`; buscar apenas
os últimos 100 jobs não é confiável.

Testes adicionais precisam ser reexecutados no Windows depois de
qualquer commit novo. Sem merge direto da PR #3 na main antes de
homologar a PR #1. Uma conta local com saldo conhecido não é prova
de fluxo musical de ponta a ponta em produção.
