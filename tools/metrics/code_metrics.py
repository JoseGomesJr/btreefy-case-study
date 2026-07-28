"""code_metrics.py — Eixo B (custo estrutural de modificação).

BT/FSM and tamper on/off are compilation flags now, not commits (see the
plan) — there's no `git diff` to measure "cost of the change" with. The
structural proxy used instead: count non-blank lines inside
`#ifdef CONFIG_TRACKER_WITH_TAMPER` blocks per implementation (how much
code each side needed to add the feature) plus McCabe cyclomatic
complexity via `lizard` on the relevant files (always available, no git
needed either).
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

import lizard
import typer

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO_ROOT / "results"

BT_FILES = [
    REPO_ROOT / "lib" / "tracker_bt" / "src" / "tracker_bt_actions.c",
    REPO_ROOT / "lib" / "tracker_bt" / "src" / "tracker_bt_policy.c",
]
FSM_FILES = [
    REPO_ROOT / "lib" / "tracker_fsm" / "src" / "tracker_fsm_states.c",
    REPO_ROOT / "lib" / "tracker_fsm" / "src" / "tracker_fsm_policy.c",
]

app = typer.Typer()

_IFDEF_RE = re.compile(r"^\s*#\s*ifdef\s+CONFIG_TRACKER_WITH_TAMPER\b")
_ENDIF_RE = re.compile(r"^\s*#\s*endif\b")


def count_tamper_ifdef_lines(path: Path) -> int:
    """Non-blank lines inside #ifdef CONFIG_TRACKER_WITH_TAMPER ... #endif.

    Handles simple, non-nested occurrences of this one macro — the only
    ifdef this codebase uses for feature selection (CLAUDE.md rule 3 bans
    #ifdef for scenario coexistence in general; this specific macro is the
    one deliberate exception the user asked for, see the plan).
    """
    depth = 0
    count = 0
    for line in path.read_text().splitlines():
        if _IFDEF_RE.match(line):
            depth += 1
            continue
        if depth > 0 and _ENDIF_RE.match(line):
            depth -= 1
            continue
        if depth > 0 and line.strip():
            count += 1
    return count


def lizard_functions(paths: list[Path]) -> list[lizard.FunctionInfo]:
    functions = []
    for path in paths:
        analysis = lizard.analyze_file(str(path))
        functions.extend(analysis.function_list)
    return functions


def cc_summary(functions: list[lizard.FunctionInfo]) -> dict:
    if not functions:
        return {"n_functions": 0, "cc_mean": 0.0, "cc_max": 0}
    ccs = [f.cyclomatic_complexity for f in functions]
    return {
        "n_functions": len(functions),
        "cc_mean": round(sum(ccs) / len(ccs), 2),
        "cc_max": max(ccs),
    }


@app.command()
def run() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    bt_ifdef_loc = sum(count_tamper_ifdef_lines(p) for p in BT_FILES if p.exists())
    fsm_ifdef_loc = sum(count_tamper_ifdef_lines(p) for p in FSM_FILES if p.exists())

    bt_summary = cc_summary(lizard_functions([p for p in BT_FILES if p.exists()]))
    fsm_summary = cc_summary(lizard_functions([p for p in FSM_FILES if p.exists()]))

    out_path = RESULTS_DIR / "code.csv"
    with out_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["implementation", "tamper_ifdef_loc", "n_functions", "cc_mean", "cc_max"]
        )
        writer.writerow(
            ["bt", bt_ifdef_loc, bt_summary["n_functions"], bt_summary["cc_mean"],
             bt_summary["cc_max"]]
        )
        writer.writerow(
            ["fsm", fsm_ifdef_loc, fsm_summary["n_functions"], fsm_summary["cc_mean"],
             fsm_summary["cc_max"]]
        )

    typer.echo(f"wrote {out_path}")
    typer.echo(f"tamper ifdef LOC — BT: {bt_ifdef_loc}, FSM: {fsm_ifdef_loc}")


if __name__ == "__main__":
    app()
