# /// script
# dependencies = ["pyserial>=3.5"]
# ///
"""Captura de traço via porta serial (HIL) — lê a saída de um firmware BT ou
FSM já flashado num alvo real e salva em results/hil/, com um resumo rápido
específico da implementação.

O firmware do lado do alvo pode ser tanto o modo de fumaça (app/src/main.c)
quanto o modo oráculo (app/src/oracle_main.c, CONFIG_TRACKER_ORACLE_MODE=y)
— o formato do traço (TR,..., FSM_TR,..., EV,..., e ORACLE_DONE só no modo
oráculo) é o mesmo em qualquer caso, só a fonte muda (native_sim vs. porta
serial real); ver lib/common/src/trace_probe.c. Sem ORACLE_DONE, a captura
para no timeout ou em Ctrl-C.

Uso:
    uv run tests/oracle/serial_capture.py --port /dev/ttyACM0 --impl bt --variant tamper
    uv run tests/oracle/serial_capture.py --port /dev/ttyACM0 --impl fsm --variant base --reset-dtr

Depois, para comparar duas capturas (ex.: uma sessão de flash BT, outra de
FSM), use compare_captures.py.
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from collections import Counter
from pathlib import Path

import serial

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO_ROOT / "results" / "hil"

DONE_MARKER = "ORACLE_DONE"
_CMD_RE = re.compile(r"^TR,\d+,chan_tracker_cmd,(\w+)")
_FSM_TR_RE = re.compile(r"FSM_TR,\d+,(\d+),(\d+)")


def capture(port: str, baud: int, timeout: float, reset_dtr: bool) -> list[str]:
    lines: list[str] = []
    with serial.Serial(port, baudrate=baud, timeout=1.0) as ser:
        if reset_dtr:
            # Best-effort reset via DTR toggle — works for many USB-CDC
            # boards (e.g. the nRF52840DK's J-Link VCOM), not universal.
            # If your board needs a physical reset button instead, just
            # press it right after starting this script.
            ser.dtr = False
            time.sleep(0.1)
            ser.dtr = True
            time.sleep(0.5)

        ser.reset_input_buffer()

        start = time.monotonic()
        try:
            while time.monotonic() - start < timeout:
                raw = ser.readline()
                if not raw:
                    continue
                line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                if not line:
                    continue
                print(line)
                lines.append(line)
                if line.strip() == DONE_MARKER:
                    break
            else:
                print(
                    f"warning: timed out after {timeout}s without seeing {DONE_MARKER} "
                    "(fine if this firmware doesn't print one — e.g. the smoke-test main.c)",
                    file=sys.stderr,
                )
        except KeyboardInterrupt:
            print("\ninterrupted, saving what was captured so far", file=sys.stderr)

    return lines


def summarize(impl: str, lines: list[str]) -> None:
    cmds = [m.group(1) for line in lines if (m := _CMD_RE.match(line))]
    print(f"\n{len(lines)} linhas capturadas, {len(cmds)} comandos em chan_tracker_cmd")

    if impl == "fsm":
        transitions = [m.groups() for line in lines if (m := _FSM_TR_RE.search(line))]
        distinct = sorted(set(transitions))
        print(f"{len(transitions)} transições FSM observadas, {len(distinct)} distintas: {distinct}")
    else:
        print(f"distribuição de comandos: {dict(Counter(cmds))}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--port", required=True, help="ex.: /dev/ttyACM0")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--impl", choices=["bt", "fsm"], required=True)
    parser.add_argument("--variant", choices=["base", "tamper"], default="base")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument(
        "--reset-dtr",
        action="store_true",
        help="Tenta resetar a placa via DTR antes de capturar (nem toda placa suporta)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Caminho do arquivo de saída (default: results/hil/<impl>_<variant>_<timestamp>.log)",
    )
    args = parser.parse_args()

    try:
        lines = capture(args.port, args.baud, args.timeout, args.reset_dtr)
    except serial.SerialException as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = args.out or RESULTS_DIR / f"{args.impl}_{args.variant}_{int(time.time())}.log"
    out_path.write_text("\n".join(lines) + "\n")

    summarize(args.impl, lines)
    print(f"\nsalvo em {out_path}")

    return 0 if DONE_MARKER in lines else 1


if __name__ == "__main__":
    sys.exit(main())
