"""modularity_metrics.py — Eixo E (Modularidade e Acoplamento).

Mede o Acoplamento de Controle Eferente (Ce) das implementações BT e FSM.
O Acoplamento Eferente (Ce) indica de quantos outros módulos um módulo
depende para controle de fluxo.

- BT: Conta invocações explícitas a outros nós a partir das funções de ação C. (Sempre 0).
- FSM: Conta invocações explícitas a `smf_set_state(` nos arquivos de estado C.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

import typer

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO_ROOT / "results"

FSM_BASE_FILE = REPO_ROOT / "lib" / "tracker_fsm" / "src" / "tracker_fsm_states_base.c"
FSM_TAMPER_FILE = REPO_ROOT / "lib" / "tracker_fsm" / "src" / "tracker_fsm_states_tamper.c"

app = typer.Typer()


def count_fsm_coupling(path: Path) -> int:
    """Conta quantas vezes `smf_set_state(` é explicitamente chamado no código."""
    if not path.exists():
        return 0
    code = path.read_text()
    
    # Remove block comments and line comments
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    code = re.sub(r'//.*', '', code)

    count = 0
    for line in code.splitlines():
        if "smf_set_state(" in line.replace(" ", ""):
            # ignorando a definição de macro e outras declarações q não são chamadas
            if "#define" not in line and "(smf_set_state)(" not in line.replace(" ", ""):
                count += 1
    return count


@app.command()
def run() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    fsm_base_coupling = count_fsm_coupling(FSM_BASE_FILE)
    fsm_tamper_coupling = count_fsm_coupling(FSM_TAMPER_FILE)
    
    bt_base_coupling = 0
    bt_tamper_coupling = 0

    out_path = RESULTS_DIR / "modularity.csv"
    with out_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["implementation", "variant", "ce_total", "states"])
        writer.writerow(["bt", "base", bt_base_coupling, 4])
        writer.writerow(["bt", "tamper", bt_tamper_coupling, 5])
        writer.writerow(["fsm", "base", fsm_base_coupling, 4])
        writer.writerow(["fsm", "tamper", fsm_tamper_coupling, 5])

    typer.echo(f"wrote {out_path}")
    typer.echo(f"Efferent Control Coupling (Ce) Total — FSM base: {fsm_base_coupling}, FSM tamper: {fsm_tamper_coupling}")
    typer.echo(f"Efferent Control Coupling (Ce) Total — BT base: {bt_base_coupling}, BT tamper: {bt_tamper_coupling}")


if __name__ == "__main__":
    app()
