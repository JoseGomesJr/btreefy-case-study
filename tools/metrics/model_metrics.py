"""model_metrics.py — Eixo A (custo de modificação do modelo).

Two independent sides, since BT and FSM expose their structure very
differently:

- BT: the tree is the XML itself (models/tracker_base.xml,
  models/tracker_tamper.xml) — GED is computed directly between the two
  files, no build needed.
- FSM: there's no separate "model" artifact — the state graph only exists
  as compiled behavior, so it's reconstructed from the FSM_TR,<t>,<from>,<to>
  lines that tracker_fsm_step() already prints (see
  lib/tracker_fsm/src/tracker_fsm_policy.c) while running the oracle-mode
  binary. This is the same technique the fluxo_v2 design doc calls for:
  the graph comes from exhaustive execution, not a hand-drawn diagram.
"""

from __future__ import annotations

import csv
import re
import subprocess
import time
from pathlib import Path

import networkx as nx
import typer
from lxml import etree

REPO_ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = REPO_ROOT / "models"
APP_DIR = REPO_ROOT / "app"
RESULTS_DIR = REPO_ROOT / "results"
BUILD_ROOT = REPO_ROOT / "build" / "metrics"

DONE_MARKER = "ORACLE_DONE"

app = typer.Typer()


# --- BT side: GED straight from the two XML files -------------------------


def load_bt_graph(xml_path: Path) -> nx.DiGraph:
    """Parses a Groot BehaviorTree XML into a parent->child graph, matching
    the traversal btf_groot_parser.py itself performs (root.find(...)[0] is
    the actual tree root, everything under it is a control/leaf node)."""
    tree = etree.parse(str(xml_path))
    root = tree.getroot()
    bt_elem = root.find("BehaviorTree")
    graph = nx.DiGraph()

    def add(elem, parent_id: str | None, path: str) -> None:
        label = elem.get("name", elem.tag)
        graph.add_node(path, label=label)
        if parent_id is not None:
            graph.add_edge(parent_id, path)
        for i, child in enumerate(elem):
            add(child, path, f"{path}/{i}:{child.get('name', child.tag)}")

    add(bt_elem[0], None, f"0:{bt_elem[0].get('name', bt_elem[0].tag)}")
    return graph


# --- FSM side: reconstruct the graph from an actual run --------------------

_FSM_TR_RE = re.compile(r"FSM_TR,\d+,(\d+),(\d+)")


def build_fsm_oracle(tamper: bool, build_dir: Path) -> Path:
    conf_files = ["tracker_fsm.conf"]
    if tamper:
        conf_files.append("tamper.conf")
    conf_files.append("oracle.conf")
    cmd = [
        "west",
        "build",
        "-b",
        "native_sim",
        str(APP_DIR),
        "-d",
        str(build_dir),
        "--",
        f"-DEXTRA_CONF_FILE={';'.join(conf_files)}",
        "-DCONFIG_TRACKER_ORACLE_N_EVENTS=500",
    ]
    subprocess.run(cmd, cwd=REPO_ROOT, check=True)
    return build_dir / "zephyr" / "zephyr.exe"


def run_and_capture(binary: Path, timeout: float = 60.0) -> list[str]:
    proc = subprocess.Popen(
        [str(binary)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    lines: list[str] = []
    start = time.monotonic()
    try:
        for line in proc.stdout:
            lines.append(line.rstrip("\n"))
            if line.strip() == DONE_MARKER or time.monotonic() - start > timeout:
                break
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
    return lines


def load_fsm_graph(trace_lines: list[str]) -> nx.DiGraph:
    graph = nx.DiGraph()
    for line in trace_lines:
        m = _FSM_TR_RE.search(line)
        if m:
            graph.add_edge(m.group(1), m.group(2))
    return graph


# --- Shared metrics ---------------------------------------------------------


def cc_decision_graph(graph: nx.DiGraph) -> int:
    """CC = a + s - n + 1 (Biggar, Zamani, Shames), the formulation used by
    Iovino et al.

    CAVEAT: the theoretical "CC = 1 for any well-formed BT, regardless of
    size" result holds for the graph *transformed* to a single-entry/
    single-exit control-flow automaton (success/failure outcome edges,
    etc.) — not for the raw parent->child tree this function is actually
    given (load_bt_graph() just mirrors the XML structure). Treat the
    values this returns as a directional/relative proxy (does it grow when
    a feature is added, and by how much, compared between BT and FSM) —
    not as the rigorous invariant from the methodology doc. Implementing
    the full transformation was judged out of scope for this round; flagged
    here so it isn't mistaken for the textbook number.
    """
    a = graph.number_of_edges()
    s = sum(1 for v in graph if graph.out_degree(v) == 0)
    n = graph.number_of_nodes()
    return a + s - n + 1


def ged(g1: nx.DiGraph, g2: nx.DiGraph, timeout: float = 60.0) -> float | None:
    return nx.graph_edit_distance(g1.to_undirected(), g2.to_undirected(), timeout=timeout)


@app.command()
def run(build_root: Path = BUILD_ROOT, skip_fsm_build: bool = False) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    bt_base = load_bt_graph(MODELS_DIR / "tracker_base.xml")
    bt_tamper = load_bt_graph(MODELS_DIR / "tracker_tamper.xml")

    if skip_fsm_build:
        fsm_base_bin = build_root / "fsm_base" / "zephyr" / "zephyr.exe"
        fsm_tamper_bin = build_root / "fsm_tamper" / "zephyr" / "zephyr.exe"
    else:
        fsm_base_bin = build_fsm_oracle(False, build_root / "fsm_base")
        fsm_tamper_bin = build_fsm_oracle(True, build_root / "fsm_tamper")

    fsm_base = load_fsm_graph(run_and_capture(fsm_base_bin))
    fsm_tamper = load_fsm_graph(run_and_capture(fsm_tamper_bin))

    rows = [
        ("bt_base", bt_base.number_of_nodes(), bt_base.number_of_edges(),
         cc_decision_graph(bt_base)),
        ("bt_tamper", bt_tamper.number_of_nodes(), bt_tamper.number_of_edges(),
         cc_decision_graph(bt_tamper)),
        ("fsm_base", fsm_base.number_of_nodes(), fsm_base.number_of_edges(),
         cc_decision_graph(fsm_base)),
        ("fsm_tamper", fsm_tamper.number_of_nodes(), fsm_tamper.number_of_edges(),
         cc_decision_graph(fsm_tamper)),
    ]

    bt_ged = ged(bt_base, bt_tamper)
    fsm_ged = ged(fsm_base, fsm_tamper)

    out_path = RESULTS_DIR / "model.csv"
    with out_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["variant", "n_nodes", "n_edges", "cc_decision_graph"])
        writer.writerows(rows)
        writer.writerow([])
        writer.writerow(["ged_bt_base_to_tamper", bt_ged])
        writer.writerow(["ged_fsm_base_to_tamper", fsm_ged])

    typer.echo(f"wrote {out_path}")
    typer.echo(f"GED (BT base->tamper): {bt_ged}")
    typer.echo(f"GED (FSM base->tamper): {fsm_ged}")
    if fsm_base.number_of_nodes() == 0 or fsm_tamper.number_of_nodes() == 0:
        typer.echo(
            "warning: FSM graph is empty — the oracle run may not have exercised any "
            "transitions; try a larger CONFIG_TRACKER_ORACLE_N_EVENTS.",
            err=True,
        )


if __name__ == "__main__":
    app()
