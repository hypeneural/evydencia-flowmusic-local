# FlowMusic — contrato de letras personalizadas (Natal 2026)

A branch base Linux rejeitava `lyrics` com HTTP 422 e não encaminhava `title`. Este patch encaminha os campos inline ao `mvp_probe.py` e ao `flowmusic.mjs gen`. Nenhum POST LIVE, login, rebuild da VPS ou consumo de créditos é executado por este patch.

O operador usa `POST /v1/media/audio` via gateway, com `request_id` persistido antes da solicitação, `approve_live=true`, `instrumental=false`, `model="Lyria 3.5"`, `lyrics`, `title`, `prompt`, `duration_seconds` (60–600) e `account_profile`.

O conteúdo de `lyrics` é texto inline com seções como `[Verse]`, nunca uma referência `@arquivo`. O título também não pode começar com `@`. Não gravar letra, nome do cliente, telefone, tokens, base64 nem URLs assinadas em logs. O modelo é probabilístico: conferência humana de nome, contagem e frase sobre revelação continua necessária antes do envio real.

Em timeout ou resposta remota incerta: consultar pelo `request_id` original, não alternar a conta e não refazer a geração automaticamente. Em `409` de créditos/autenticação ou `507` de disco antes de submissão comprovada, marcar a música como indisponível, sem bloquear envio de fotos/galeria/Drive. Somente executar geração após consentimento operacional apropriado e validação de condições de uso dos serviços envolvidos.

## Verificação dirigida
```powershell
python -m pytest tests/test_music_lyrics_contract.py -q
python -m pytest tests/test_queue.py tests/test_api.py -q
```
A homologação em Windows e na VPS deve validar o SHA realmente implantado sem repetir o WAV já gerado.
