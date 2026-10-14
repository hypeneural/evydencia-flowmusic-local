# Antigravity / Gemini 3.8 Flash — design minimalista

Documentação conferida em 2026-10-14:
- https://www.antigravity.google/docs/rules/
- https://www.antigravity.google/docs/skills
- https://www.antigravity.google/docs/migration/workflows-to-skills/
- https://www.antigravity.google/docs/agent-settings

## Princípios aplicados
1. `AGENTS.md` é always-on; mantê-lo curto com invariantes e mapa de arquivos. Regras específicas usam `.agents/rules` com frontmatter `trigger: model_decision` para evitar inchar contexto.
2. Skills `.agents/skills/<name>/SKILL.md` são descobertas por `name/description` e carregadas sob demanda (progressive disclosure). Uma skill por tarefa, não três em todas as interações.
3. Não usar `.agents/workflows`: migração recomendada pela documentação atual.
4. Custom agent `.agents/agents/mvp-operator/agent.md` é opcional para reduzir deriva; não criar subagentes paralelos para pequenas correções.
5. O `agent.cmd` agora roda **apenas verificação rápida offline** por padrão; `agent.cmd test` roda pytest + npm test somente sob demanda.
6. Diagnóstico operacional no Windows: `scripts/windows/mvp.ps1` com etapas check -> login -> account -> generate, logs JSONL que não incluem segredos.
7. Testes: uma verificação focada quando muda lógica; CI mínimo Windows na PR; suite ampla somente por alteração transversal ou antes do merge.
8. Políticas de execução Windows pertencem às configurações do Antigravity (Request Review/Proceed in Sandbox/Always Proceed); **não** inventar uma configuração no repo. Preferir revisão de comandos que fazem login ou gastam créditos.

## Ciclo operacional
**hipótese -> chamada real deliberada -> evento e arquivo -> decisão**, sem dar novos envios automaticamente em caso de falha.
