"""code_metrics.py — Eixo B (custo estrutural de modificação).

BT and FSM have different architectural approaches to feature toggling:
- BT uses `#ifdef CONFIG_TRACKER_WITH_TAMPER` in `tracker_bt_actions.c`.
- FSM uses two distinct files: `tracker_fsm_states_base.c` and `tracker_fsm_states_tamper.c`.

We measure "cost of the change" structurally:
- BT: True SLOC (Source Lines of Code) inside `#ifdef CONFIG_TRACKER_WITH_TAMPER` blocks.
- FSM: SLOC(`tracker_fsm_states_tamper.c`) - SLOC(`tracker_fsm_states_base.c`).
Plus McCabe cyclomatic complexity via `lizard` on the relevant files.
"""

from __future__ import annotations

import csv
import json
import re
import subprocess
import tempfile
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
    REPO_ROOT / "lib" / "tracker_fsm" / "src" / "tracker_fsm_states_tamper.c",
    REPO_ROOT / "lib" / "tracker_fsm" / "src" / "tracker_fsm_policy.c",
]
FSM_BASE_STATE_FILE = REPO_ROOT / "lib" / "tracker_fsm" / "src" / "tracker_fsm_states_base.c"
FSM_TAMPER_STATE_FILE = REPO_ROOT / "lib" / "tracker_fsm" / "src" / "tracker_fsm_states_tamper.c"

app = typer.Typer()

_IFDEF_RE = re.compile(r"^\s*#\s*ifdef\s+CONFIG_TRACKER_WITH_TAMPER\b")
_ENDIF_RE = re.compile(r"^\s*#\s*endif\b")


def cloc_sloc(path: Path) -> int:
    """Uses cloc to count true SLOC in a file."""
    if not path.exists():
        return 0
    result = subprocess.run(["cloc", "--json", str(path)], capture_output=True, text=True)
    try:
        data = json.loads(result.stdout)
        return data.get("SUM", {}).get("code", 0)
    except Exception:
        return 0


def count_tamper_ifdef_sloc(path: Path) -> int:
    """True SLOC inside #ifdef CONFIG_TRACKER_WITH_TAMPER ... #endif using cloc.

    Extracts the #ifdef blocks into a temporary C file and runs cloc on it
    to ensure comments are stripped correctly by the tool.
    """
    code = path.read_text()
    depth = 0
    ifdef_lines = []
    
    for line in code.splitlines():
        if _IFDEF_RE.match(line):
            depth += 1
            continue
        if depth > 0 and _ENDIF_RE.match(line):
            depth -= 1
            continue
        if depth > 0:
            ifdef_lines.append(line)
            
    if not ifdef_lines:
        return 0
        
    with tempfile.NamedTemporaryFile(mode="w", suffix=".c", delete=False) as f:
        f.write("\n".join(ifdef_lines))
        temp_path = Path(f.name)
        
    try:
        return cloc_sloc(temp_path)
    finally:
        temp_path.unlink(missing_ok=True)


def count_total_sloc(path: Path) -> int:
    """True SLOC in a file using cloc."""
    return cloc_sloc(path)


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

    bt_ifdef_sloc = sum(count_tamper_ifdef_sloc(p) for p in BT_FILES if p.exists())
    
    if FSM_BASE_STATE_FILE.exists() and FSM_TAMPER_STATE_FILE.exists():
        fsm_ifdef_sloc = count_total_sloc(FSM_TAMPER_STATE_FILE) - count_total_sloc(FSM_BASE_STATE_FILE)
    else:
        fsm_ifdef_sloc = 0

    bt_summary = cc_summary(lizard_functions([p for p in BT_FILES if p.exists()]))
    fsm_summary = cc_summary(lizard_functions([p for p in FSM_FILES if p.exists()]))

    out_path = RESULTS_DIR / "code.csv"
    with out_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["implementation", "tamper_feature_sloc", "n_functions", "cc_mean", "cc_max"]
        )
        writer.writerow(
            ["bt", bt_ifdef_sloc, bt_summary["n_functions"], bt_summary["cc_mean"],
             bt_summary["cc_max"]]
        )
        writer.writerow(
            ["fsm", fsm_ifdef_sloc, fsm_summary["n_functions"], fsm_summary["cc_mean"],
             fsm_summary["cc_max"]]
        )

    typer.echo(f"wrote {out_path}")
    typer.echo(f"tamper feature SLOC — BT: {bt_ifdef_sloc}, FSM: {fsm_ifdef_sloc}")


if __name__ == "__main__":
    app()
