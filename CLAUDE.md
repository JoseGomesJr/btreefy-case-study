# BTreeFy Tracker Eval — contexto para o Claude Code

Workspace west de avaliação: compara Impl-BT (`app/tracker_bt/`) e Impl-FSM
(`app/tracker_fsm/`) da mesma aplicação de rastreamento, sobre a mesma
camada de drivers (`app/common/`), consumindo a biblioteca `btreefy` via
`modules/lib/btreefy` (revisão fixada no `west.yml` deste workspace).

## Comandos de verificação (rode SEMPRE antes de dizer que terminou — cwd = raiz deste repo)
- `west build -b native_sim app`   → build de cada implementação, deve ficar verde
- `uv run pytest tools/metrics`     → testes dos scripts de métrica
- `uv run ruff check tools/`        → lint Python

## Regras invioláveis
1. NUNCA edite `btf_nodes_generated.[ch]` — regenere com o
   `btf_groot_parser.py` de `modules/lib/btreefy/scripts/`.
2. NUNCA introduza `malloc`/`free`/`k_malloc`. Alocação é estática, sem exceção.
3. NUNCA implemente os cenários V0..V5 com `#ifdef`. Cada cenário é um commit
   real que modifica código real — a métrica de churn depende disso.
4. A política (BT ou FSM) NUNCA chama driver diretamente. Só publica em
   `chan_tracker_cmd` e lê o blackboard.
5. Números de métrica vêm de `tools/metrics/*` deste repo (Eixos A/B/C) ou de
   `modules/lib/btreefy/tools/metrics/roundtrip.py` (Eixo E). Nunca escreva um
   valor à mão em tabela, README ou artigo.
6. Builds usados para medir tempo/footprint têm `CONFIG_TRACKER_TRACE=n`.

## Onde procurar antes de criar arquivo novo
`app/common/` para canais zbus, blackboard e drivers fake; `app/tracker_bt/`
e `app/tracker_fsm/` para as duas políticas (nunca abra o diff de uma
implementação ao trabalhar isoladamente na outra); `tools/metrics/` para
qualquer coisa que produza CSV; `tests/oracle/` para traços de referência do
oráculo de equivalência.
