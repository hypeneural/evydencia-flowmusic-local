# Antigravity / Gemini 3.8 Flash — design minimalista

Documentação conferida em 2026-10-14:
- https://www.antigravity.google/docs/rules/
- https://www.antigravity.google/docs/skills
- https://www.antigravity.google/docs/migration/workflows-to-skills/
- https://www.antigravity.google/docs/agent-settings

## Princípios aplicados
1. `AGENTS.md` é always-on; mantê-lo curto com invariantes e mapa de arquivos. Regras específicas usam `.agents/rules` com frontmatter `trigger: model_decision` para evitar inchar contexto.
2. Skills `.agents/skills/<name>/SKILL.md` são descobertas por `name/description` e carregadas sob demanda (progressive disclosure). Uma skill por tarefa, não três em todas as interações.
3. Não usar `.agents/workflows`: migração recomendada pela doc oficial; horizonte de desativação publicado 19/10/2026 na documentação atual.
4. Custom agent `.agents/agents/mvp-operator/agent.md` é uma opção para reduzir deriva; não criar subagentes paralelos para pequenas correções.
5. Diagnóstico operacional em Windows: scripts PowerShell visíveis e logs JSONL redigidos. Alterar uma coisa, executar um probe real voluntário, interpretar estado e seguir.
6. Testes: 1 verificação focada quando muda a lógica; CI mínimo de Windows na PR; suite ampla somente por alteração transversal ou antes do merge.
7. Políticas de execução do Antigravity Windows são definidas nas configurações do aplicativo (Request Review/Proceed in Sandbox/Always Proceed); **não** inserir uma configuração falsa no repositório. Preferir aprovação explícita para `login` e `generate`.

## Regra de custo
Nunca comparar mock com geração real. O script MVP usa o CLI upstream como ferramenta manual opt-in; o adaptador de API durável fica para PR seguinte, baseado em logs de execução reais.
