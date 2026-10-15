# MVP real | execução Windows observável, sem testes em excesso

## Objetivo
Executar **uma tentativa real de cada vez** com o CLI upstream fixado, preservando `request_id`, sem refazer uma geração cujo resultado ficou incerto. O servidor FastAPI continua mock; o **probe real é um executável local independente**, não uma promessa de API integrada.

## Fonte e limitações
O Google AI Pro fornece benefícios no **Google Flow Music Plus** e direitos comerciais, mas isso **não concede automaticamente autorização para automação dos endpoints privados**. Confira os termos aplicáveis antes de usar o CLI comunitário. Fontes:
- https://support.google.com/flow/answer/17083870?hl=pt-br
- https://www.antigravity.google/docs/rules/
- https://www.antigravity.google/docs/skills
- https://www.antigravity.google/docs/agent-settings

## Passo a passo mínimo (PowerShell, dentro do repositório)
```powershell
git fetch origin
git status --short --branch
powershell -ExecutionPolicy Bypass -File scripts/windows/install.ps1
powershell -ExecutionPolicy Bypass -File scripts/windows/mvp.ps1 -Mode check
```

Apenas depois de decidir pessoalmente que as condições são compatíveis e de estar preparado para autenticar:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/windows/mvp.ps1 -Mode login
powershell -ExecutionPolicy Bypass -File scripts/windows/mvp.ps1 -Mode account
```

O `login` abre (ou imprime uma URL para abrir manualmente) o fluxo OAuth upstream. A sessão fica **somente no Windows**, no diretório `data/flowmusic-session`. Não envie a URL, o callback, cookies ou o conteúdo desse diretório ao agente.

Somente após conferir autorização de uso, modelo disponível e custo estimado por tentativa:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/windows/mvp.ps1 `
  -Mode generate `
  -RequestId natal-mvp-001 `
  -Prompt "Trilha natalina instrumental cinematografica, sinos e piano" `
  -ApproveLive
```

A invocação cria **antes do primeiro POST remoto** um registro exclusivo em `data/mvp/ledger/<request_id>.json`. Repetir o mesmo ID nunca gera novamente; timeout ou status ambíguo fica `needs_review`. Os resultados locais estarão em `data/mvp/output/<request_id>`. O comando não envia webhook e não modifica o CRM/Workflow.

## Logs e evidências
- `data/mvp/events.jsonl`: registros JSONL sem prompt, tokens, IDs de sessão ou URLs privadas. Campos: `ts,event,request_id,model,status,elapsed_ms,variant_count,artifact_count,error_class` (somente se presentes).
- `data/mvp/ledger/<request_id>.json`: intenção pré-envio, estado final, hashes de arquivos e caminhos locais; **não colocar prompts neste registro**.
- `data/mvp/output/<request_id>`: músicas reais se geradas; arquivos locais não versionados.
- Resultado `completed` somente quando o cliente entregou arquivos que existem, têm tamanho plausível e foram registrados com SHA-256. `ffprobe` é opcional no primeiro MVP e recomendado antes do consumo pelo Workflow.

## Encerramento de cada tentativa
Retornar apenas: ID, saldo consultado (se disponível), status, tempo, quantidade de variantes, tamanho/hash/codec se verificado e uma única próxima ação. Se `needs_review`, não executar novamente: primeiro consultar manualmente a biblioteca do Flow Music.

## O que não fazer
- Não rodar 15 testes Node + suite Python + CI + varredura de repo em toda iteração.
- Não acionar lotes com vários `--jobs`, proxies, rotação de contas ou browser oculto.
- Não anexar logs completos da autenticação à conversa.
- Não ativar chamada real automaticamente ao iniciar o FastAPI.

## API + fila em MVP
A validação real manual apresentada para `natal-mvp-001` confirmou WAV e débito relatado de 5 créditos. **Não reutilize esse ID**. A integração da nova fila deve ser validada com um ID novo, uma aprovação deliberada e logs do endpoint `/v1/music/jobs/{id}/events`. Ambiguidade = `needs_review`; nunca reenvie automaticamente.
