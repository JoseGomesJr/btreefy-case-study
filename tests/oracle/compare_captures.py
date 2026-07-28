"""Compara dois traços já capturados — de serial_capture.py (HIL) ou de
qualquer outra fonte, desde que sigam o mesmo formato — usando a mesma
classificação do oráculo (compare.py). Útil para comparar duas capturas
feitas em sessões separadas (ex.: flash BT, captura; flash FSM, captura;
depois compara os dois arquivos aqui).

Uso:
    uv run tests/oracle/compare_captures.py \\
        --bt results/hil/bt_tamper_1730000000.log \\
        --fsm results/hil/fsm_tamper_1730000120.log \\
        --seq tamper
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from compare import classify_diff, write_report

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO_ROOT / "results"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--bt", type=Path, required=True, help="Traço capturado da Impl-BT")
    parser.add_argument("--fsm", type=Path, required=True, help="Traço capturado da Impl-FSM")
    parser.add_argument("--seq", choices=["no-tamper", "tamper"], required=True)
    args = parser.parse_args()

    bt_trace = args.bt.read_text().splitlines()
    fsm_trace = args.fsm.read_text().splitlines()

    diffs = classify_diff(bt_trace, fsm_trace)
    report_path = write_report(args.seq, diffs, RESULTS_DIR)

    unexpected = [d for d in diffs if d["class"] == "UNEXPECTED"]
    print(f"{len(diffs)} divergence(s), {len(unexpected)} UNEXPECTED — report: {report_path}")
    for d in unexpected:
        print(f"  UNEXPECTED at event {d['event_index']}: bt={d['bt_cmds']} fsm={d['fsm_cmds']}")

    return 1 if unexpected else 0


if __name__ == "__main__":
    sys.exit(main())
