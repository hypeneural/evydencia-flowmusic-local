# Contrato de integração Google Flow + FlowMusic — validação Omni Flash (15/10/2026)

**Status:** documentação somente; não altera o motor musical ou sessões reais. **Workspace de vídeo:** projeto local `evydencia-flow-local` do operador, ainda sem repositório GitHub dedicado acessível. [Issue canônica #2](https://github.com/hypeneural/evydencia-flowmusic-local/issues/2).

## Observações forenses reportadas pelo Antigravity
- FlowMusic: API local `127.0.0.1:8765` e Lyria funcionando com WAVs reais.
- Google Flow: gateway local `127.0.0.1:8766`, leitura de 916 créditos via frontend RPC `nzlxg`, cache de modelos/projetos e imagem JPEG real, arquivo de 820260 bytes/1376x768, hash e job correlacionados.
- **Nenhum vídeo MP4 real foi apresentado.** G4/G5 de imagem não comprova vídeo.
- A imagem foi submetida com clique num Chrome controlado, capturando resposta RPC `ogiZ0b`: não chamar essa prova de submissão exclusivamente HTTP pelo backend.
- A versão de starter em ZIP não é igual aos arquivos Windows pós-Antigravity. Contém `LIVE=False`/adapter somente de leitura; NÃO sobrescrever o código local que funcionou.

## Interface entre serviços
`POST 127.0.0.1:8766/v1/media/audio` encaminha à API FlowMusic `8765/v1/music/jobs`, preservando `request_id`; áudio mantém banco/fila/sessão separados. `POST /v1/flow/videos` cria job no SQLite de vídeo com `request_id UNIQUE` e perfil/limite/crédito/consentimento fixados antes do envio. Nunca misturar cookies, tokens ou saldos dos serviços. Endpoints de GET recuperam jobs e artefatos e não fazem geração.

## Hotfix entregue para aplicação seletiva Windows
Artefatos na conversa: `evydencia-flow-local-omni-video-hardening.zip`, `evydencia-flow-local-omni-video-hardening.patch`. 14 arquivos modificados/adicionados em relação ao ZIP anterior, verificados por compileall, ASGI TestClient, node --check e git apply --check. Conteúdo:
- Novo `app/operations.py`, endpoint autenticado `GET /v1/flow/operations/preflight`: valida SQLite, conta, jobs ambíguos, fila e evidência separada por mídia. Nenhum request Google.
- Busca `GET /v1/flow/jobs/by-request/{request_id}`: localiza MESMO job após perda de HTTP 202; zero repost.
- MP4 comprovado somente com arquivo físico+SHA+assinatura e FFprobe coincidente com metadados.
- `scripts/backup-sqlite.py`: cópia consistente por API nativa SQLite, sem copiar banco ativo com shutil.
- `scripts/windows/prove-omni-video.ps1`, `generate-controlled.ps1` e `audit-media-services.ps1`: uma submissão, RequestId fixo, consentimento explícito e limite de 30 créditos; sob erro, reconciliar com GET e nunca autoPOST.
- Runbooks `docs/OMNI_FLASH_REAL_VIDEO_VALIDATION.md`, `docs/FORENSIC_OCT15_AUDIT.md`, `docs/PROMPT_ANTIGRAVITY_OMNI_VIDEO.md`; skill `.agents/skills/flow-video-real/SKILL.md`.

## Autorização de teste dada pelo operador
Uma prova real de vídeo **Omni Flash 1.1** (catálogo local: `abra_t2v_4s`, 4 s, 720p, uma saída) em conta default, com `RequestId=omni-flash-video-validation-001` e teto inicial de 30 créditos. Conferir preço do próprio Flow; tarifas variam por resolução/variante; não enviar caso o preço ultrapasse 30 ou o backend/provider não esteja pronto. O consentimento não autoriza outro job, troca de conta após bloqueio ou bypass de proteções.

## Gate real
Executar no **Windows** somente depois de reconciliar com as alterações atuais de `adapter.py`, `worker.py`, `flow-cli.mjs`, `start.ps1` e verificar endpoint de preflight, modelo e cotação. Só declarar vídeo validado se job alcançar completed com ID remoto, MP4 íntegro, FFprobe, bytes, SHA-256 e eventos correlacionados no mesmo SQLite. Se não houve geração porque provider ausente/erro 403/429, registrar bloqueio específico e corrigir etapas independentes — não fingir sucesso.

**Não publicar credenciais** do `data/http-sessions` nem token da API. Sem GitHub Actions, Redis, Docker, workers paralelos, CAPTCHA solver, retries de POST ou alterações de código do FlowMusic.

Referências: [RohaanA/google-flow-mcp](https://github.com/RohaanA/google-flow-mcp), [TheSmallHanCat/flow2api](https://github.com/TheSmallHanCat/flow2api), [Playwright auth](https://playwright.dev/docs/auth), [Google Flow credits](https://support.google.com/flow/answer/16526234?hl=pt-BR).

**Correção de segurança:** a prova de vídeo NÃO aceita `-AcceptEstimatedQuote`. Se só existir estimativa local, o Antigravity deve implementar a leitura de cotação observada e interromper a geração até isso estar comprovado. O usuário autorizou uma execução real, não uma cobrança de valor indeterminado.
