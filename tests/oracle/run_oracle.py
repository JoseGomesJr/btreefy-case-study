"""Oracle runner (Fase C): builds (or reuses) the BT and FSM oracle-mode
binaries with an identical seed, runs both on native_sim, and diffs their
traces via compare.py.

No git tags/commits involved — CONFIG_TRACKER_WITH_TAMPER already selects
between the two variants being compared (see the plan and CLAUDE.md):

    --seq no-tamper   -> BT/FSM built WITHOUT the tamper feature
                         (results/oracle_base.{txt,csv})
    --seq tamper      -> BT/FSM built WITH the tamper feature
                         (results/oracle_tamper.{txt,csv})

Pass means zero UNEXPECTED divergences, for BOTH sequences — not zero
divergences. A first run of --seq no-tamper surfaced a real, explainable
BT-vs-FSM difference (BT re-evaluates blackboard state fresh every tick and
never misses a change; FSM only reacts to a field when its current state's
run() checks it, so events can be invisible until a later state looks) —
see compare.write_report's docstring. That's an expected, classified
divergence, not a bug, so it doesn't fail the run; only UNEXPECTED does.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

from compare import classify_diff, write_report

REPO_ROOT = Path(__file__).resolve().parents[2]
APP_DIR = REPO_ROOT / "app"
RESULTS_DIR = REPO_ROOT / "results"

DONE_MARKER = "ORACLE_DONE"


def build(policy: str, tamper: bool, build_dir: Path) -> Path:
    conf_files = [f"tracker_{policy}.conf"]
    if tamper:
        conf_files.append("tamper.conf")
    conf_files.append("oracle.conf")
    extra_conf = ";".join(conf_files)

    cmd = [
        "west",
        "build",
        "-b",
        "native_sim",
        str(APP_DIR),
        "-d",
        str(build_dir),
        "--",
        f"-DEXTRA_CONF_FILE={extra_conf}",
    ]
    subprocess.run(cmd, cwd=REPO_ROOT, check=True)
    return build_dir / "zephyr" / "zephyr.exe"


def run_and_capture(binary: Path, timeout: float = 60.0) -> list[str]:
    # native_sim keeps running (idle loop) after main() returns — there's no
    # natural exit, so stream stdout and kill the process as soon as
    # ORACLE_DONE shows up, rather than waiting for it to terminate on its
    # own (it won't).
    proc = subprocess.Popen(
        [str(binary)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    lines: list[str] = []
    start = time.monotonic()
    try:
        for line in proc.stdout:
            lines.append(line.rstrip("\n"))
            if line.strip() == DONE_MARKER:
                break
            if time.monotonic() - start > timeout:
                raise TimeoutError(f"{binary} did not print {DONE_MARKER} within {timeout}s")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seq", choices=["no-tamper", "tamper"], required=True)
    parser.add_argument(
        "--build-root",
        type=Path,
        default=REPO_ROOT / "build" / "oracle",
        help="Where to put/find the two build directories (default: build/oracle/)",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Reuse existing build dirs instead of invoking `west build`",
    )
    args = parser.parse_args()

    tamper = args.seq == "tamper"
    bt_dir = args.build_root / f"bt_{args.seq}"
    fsm_dir = args.build_root / f"fsm_{args.seq}"

    if args.skip_build:
        bt_bin = bt_dir / "zephyr" / "zephyr.exe"
        fsm_bin = fsm_dir / "zephyr" / "zephyr.exe"
    else:
        bt_bin = build("bt", tamper, bt_dir)
        fsm_bin = build("fsm", tamper, fsm_dir)

    bt_trace = run_and_capture(bt_bin)
    fsm_trace = run_and_capture(fsm_bin)

    diffs = classify_diff(bt_trace, fsm_trace)
    report_path = write_report(args.seq, diffs, RESULTS_DIR)

    unexpected = [d for d in diffs if d["class"] == "UNEXPECTED"]
    print(f"{len(diffs)} divergence(s), {len(unexpected)} UNEXPECTED — report: {report_path}")
    for d in unexpected:
        print(f"  UNEXPECTED at event {d['event_index']}: bt={d['bt_cmds']} fsm={d['fsm_cmds']}")

    return 1 if unexpected else 0


if __name__ == "__main__":
    sys.exit(main())
