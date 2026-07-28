"""Trace comparator for the equivalence oracle (Fase C).

Aligns the BT and FSM traces by input event index (the `EV,<i>,...` markers
that tests/oracle/../../app/src/oracle_main.c prints — identical between
the two binaries by construction, since they share the same seeded PRNG)
and diffs, per event, which commands actually got published on
chan_tracker_cmd. That's the one channel whose payload represents "what got
actuated" — the other channels just echo the input, so they're not
compared.

classify() is deliberately small and explicit, not statistical (per the
fluxo_v4 document, §5.3): it looks at a pair of command lists and decides
between a handful of named patterns. Anything that doesn't fit is
UNEXPECTED, and UNEXPECTED is meant to be read by a human before trusting
any number downstream.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

_EV_RE = re.compile(r"^EV,(-?\d+),")
_CMD_RE = re.compile(r"^TR,\d+,chan_tracker_cmd,(\w+)")
_NOISE_PREFIXES = ("ORACLE_START", "ORACLE_DONE", "*** Booting", "BT initialized!")


def segment_by_event(trace: list[str]) -> dict[int, list[str]]:
    """Groups trace lines into blocks keyed by the EV index that precedes them.

    Lines before the first EV marker (boot banner, "BT initialized!") are
    collected under key -1 and never compared.
    """
    blocks: dict[int, list[str]] = {-1: []}
    current = -1
    for line in trace:
        m = _EV_RE.match(line)
        if m:
            current = int(m.group(1))
            blocks.setdefault(current, [])
            continue
        if line.startswith(_NOISE_PREFIXES):
            continue
        blocks.setdefault(current, []).append(line)
    return blocks


def extract_cmds(block: list[str]) -> list[str]:
    """Pulls the sequence of CMD_* ops published on chan_tracker_cmd."""
    cmds = []
    for line in block:
        m = _CMD_RE.match(line)
        if m:
            cmds.append(m.group(1))
    return cmds


def classify(bt_cmds: list[str], fsm_cmds: list[str]) -> str:
    """Names the shape of a divergence between two command lists.

    - EXTRA_TICK: one side published something the other didn't at all for
      this event (typically BT reaffirming a leaf action every tick vs FSM
      only signaling on a real transition — see README.md §1.4).
    - ORDER_SWAP: same commands, different order.
    - ABORT_EARLIER: one side has strictly fewer commands, all of which are
      a prefix of the other's — consistent with one implementation
      preempting/aborting a multi-step sequence earlier than the other.
    - UNEXPECTED: anything else. Investigate manually before trusting it.
    """
    if not bt_cmds and fsm_cmds:
        return "EXTRA_TICK"
    if bt_cmds and not fsm_cmds:
        return "EXTRA_TICK"
    if sorted(bt_cmds) == sorted(fsm_cmds):
        return "ORDER_SWAP"
    shorter, longer = (bt_cmds, fsm_cmds) if len(bt_cmds) < len(fsm_cmds) else (fsm_cmds, bt_cmds)
    if shorter and longer[: len(shorter)] == shorter:
        return "ABORT_EARLIER"
    return "UNEXPECTED"


def classify_diff(bt_trace: list[str], fsm_trace: list[str]) -> list[dict]:
    bt_blocks = segment_by_event(bt_trace)
    fsm_blocks = segment_by_event(fsm_trace)

    diffs = []
    for ev in sorted((set(bt_blocks) | set(fsm_blocks)) - {-1}):
        bt_cmds = extract_cmds(bt_blocks.get(ev, []))
        fsm_cmds = extract_cmds(fsm_blocks.get(ev, []))
        if bt_cmds == fsm_cmds:
            continue
        diffs.append(
            {
                "event_index": ev,
                "bt_cmds": bt_cmds,
                "fsm_cmds": fsm_cmds,
                "class": classify(bt_cmds, fsm_cmds),
            }
        )
    return diffs


def write_report(seq: str, diffs: list[dict], results_dir: Path) -> Path:
    """Writes `<prefix>.csv` (every classified divergence) and
    `<prefix>.txt` (PASS/FAIL summary) to results_dir, returning the .txt
    path.

    PASS means zero UNEXPECTED divergences — NOT zero divergences. Running
    the oracle against a genuinely random sequence surfaced a real,
    explainable pattern even on the no-tamper pair: BT re-evaluates every
    relevant blackboard field fresh from the root each tick, so it never
    misses a status change; FSM only reacts to a field when its *current*
    state's run() happens to check it, so an event arriving while sitting
    in an unrelated state is effectively invisible until some later state
    happens to look. That's a real BT-vs-FSM finding (ties directly to the
    article's Section II-D reactivity argument), not a bug — forcing the
    two to be bit-identical would mean bending one implementation into an
    unrealistic shape just to make a diff go quiet. EXTRA_TICK,
    ABORT_EARLIER, and this event-visibility pattern are all expected;
    UNEXPECTED is the one class that still needs a human to look.
    """
    results_dir.mkdir(parents=True, exist_ok=True)
    prefix = "oracle_base" if seq == "no-tamper" else "oracle_tamper"

    csv_path = results_dir / f"{prefix}.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["event_index", "class", "bt_cmds", "fsm_cmds"])
        for d in diffs:
            writer.writerow(
                [d["event_index"], d["class"], "|".join(d["bt_cmds"]), "|".join(d["fsm_cmds"])]
            )

    unexpected = [d for d in diffs if d["class"] == "UNEXPECTED"]
    txt_path = results_dir / f"{prefix}.txt"
    if not unexpected:
        txt_path.write_text(
            f"PASS ({len(diffs)} classified/expected divergence(s), 0 UNEXPECTED) — see {csv_path.name}\n"
        )
    else:
        txt_path.write_text(
            f"FAIL: {len(unexpected)} UNEXPECTED divergence(s) out of {len(diffs)} total — "
            f"see {csv_path.name}\n"
        )
    return txt_path
