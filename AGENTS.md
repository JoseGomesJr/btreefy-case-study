# AGENTS.md — BTreeFy SBESC Case Study

This document is the authoritative reference for any agent (human or AI) working on this repository.
It describes the project's purpose, architecture, build system, evaluation pipeline, and the rules that
govern how code changes should be made.

---

## 1. Project Overview

This is a **Zephyr RTOS workspace** containing a case study that compares two implementations of a
simple asset-tracking application:

| Implementation | Library                          | Decision Model              |
|----------------|----------------------------------|-----------------------------|
| **Impl-BT**    | BTreeFy (custom Behavior Tree)   | XML model → generated C array |
| **Impl-FSM**   | Zephyr SMF (`<zephyr/smf.h>`)   | C state machine (explicit)  |

The goal of the case study is to evaluate the BTreeFy framework along three axes:

- **Axis A — Model modifiability**: How much does the model (graph) change when a feature (tamper
  detection) is added? Measured via Graph Edit Distance (GED) and node/edge counts.
- **Axis B — Code modifiability**: How much code changes when the tamper feature is added? Measured
  via lines of code inside `#ifdef CONFIG_TRACKER_WITH_TAMPER` blocks and McCabe cyclomatic complexity.
- **Axis C — Flash/RAM footprint**: What is the static memory footprint for each implementation?
  Measured by cross-compiling for `nrf52840dk/nrf52840` and reading ELF section sizes.
- **Axis D — Behavioral equivalence**: Do both implementations react identically to the same event
  sequence? Validated by an equivalence oracle that runs both binaries on `native_sim` with a shared
  seeded PRNG and classifies behavioral divergences.

---

## 2. Workspace Layout

```
sbesc-case-study/              <- Zephyr west workspace root
├── .west/config               <- west configuration (path = btreefy-model-test)
├── btreefy-model-test/        <- THIS repository (the application and all tooling)
│   ├── app/                   <- Zephyr application (firmware entry points)
│   │   ├── conf/              <- Kconfig overlay files (.conf)
│   │   └── src/
│   │       ├── main.c         <- Smoke-test main (fixed event sequence)
│   │       └── oracle_main.c  <- Oracle main (CONFIG_TRACKER_ORACLE_MODE)
│   ├── lib/
│   │   ├── common/            <- Shared code: blackboard, events, trace probe
│   │   ├── tracker_bt/        <- Impl-BT: BTreeFy-based tracker policy
│   │   └── tracker_fsm/       <- Impl-FSM: Zephyr SMF-based tracker policy
│   ├── models/
│   │   ├── tracker_base.xml   <- BT model WITHOUT tamper detection
│   │   └── tracker_tamper.xml <- BT model WITH tamper detection
│   ├── tests/
│   │   └── oracle/            <- Equivalence oracle scripts (Axis D)
│   ├── tools/
│   │   └── metrics/           <- Metrics collection scripts (Axes A/B/C)
│   ├── results/               <- Generated output (CSVs, PNGs) — gitignored
│   └── west.yml               <- West manifest (declares Zephyr + BTreeFy deps)
├── modules/lib/btreefy/       <- BTreeFy framework source (fetched by west)
└── zephyr/                    <- Zephyr RTOS source (fetched by west)
```

---

## 3. Key Concepts

### 3.1 Blackboard (`lib/common/`)

Both implementations share a single static struct `g_tracker_bb` (see
`lib/common/include/tracker/tracker_bb.h`). It holds sensor state, GNSS/radio status, and the
position-request flag. Neither policy ever talks to a driver directly — they only read the
blackboard and publish to `chan_tracker_cmd`.

### 3.2 Zbus Channels (`lib/common/include/tracker/tracker_events.h`)

All inter-component communication flows through Zephyr's Zbus:

| Channel              | Direction               | Payload          |
|----------------------|-------------------------|------------------|
| `chan_gnss_evt`      | driver -> policy        | `gnss_evt`       |
| `chan_radio_evt`     | driver -> policy        | `radio_evt`      |
| `chan_sensor_evt`    | driver -> policy        | `sensor_evt`     |
| `chan_request_evt`   | test/oracle -> policy   | `request_evt`    |
| `chan_tracker_cmd`   | policy -> actuator      | `tracker_cmd`    |

The `sub_policy` subscriber observes all input channels. Both Impl-BT and Impl-FSM wait on it
inside their policy threads.

### 3.3 Trace Probe (`lib/common/src/trace_probe.c`)

When `CONFIG_TRACKER_TRACE=y`, a Zbus listener (`trace_probe`) attaches to all channels and prints:

```
TR,<cycle>,<channel_name>,<cmd_name>    (for chan_tracker_cmd)
TR,<cycle>,<channel_name>               (for all other channels)
FSM_TR,<cycle>,<from_state>,<to_state>  (FSM only, from tracker_fsm_policy.c)
```

**Important**: The trace probe is disabled for footprint measurements (adds code to binary) and
for oracle builds (the oracle uses its own `EV,...` / `ORACLE_DONE` markers instead).

### 3.4 Oracle Mode (`app/src/oracle_main.c`)

When `CONFIG_TRACKER_ORACLE_MODE=y` (via `app/conf/oracle.conf`), the oracle entry point is
compiled instead of `main.c`. It:
1. Seeds a deterministic PRNG (`xorshift32`) with `CONFIG_TRACKER_ORACLE_SEED`.
2. Generates `CONFIG_TRACKER_ORACLE_N_EVENTS` random events (REQUEST toggle, GNSS fix/fail,
   RADIO ok/fail, and optionally TAMPER toggle).
3. Injects each event through the fake drivers and prints `EV,<i>,<kind>` markers.
4. Prints `ORACLE_DONE` at the end.

The same seed produces the **identical** event sequence for both Impl-BT and Impl-FSM binaries,
making cross-implementation comparison valid.

### 3.5 Fake Drivers (`lib/common/src/drivers_fake.c`)

Hardware-independent driver stubs (`fake_sensor_set_*`, `fake_gnss_finish`, `fake_radio_finish`)
publish events directly onto the Zbus channels. They are always compiled in — neither
implementation ever needs real hardware to run on `native_sim`.

### 3.6 Feature Variants

The tamper feature is selected entirely via Kconfig:

| Kconfig flag                   | Effect                                                             |
|--------------------------------|--------------------------------------------------------------------|
| `CONFIG_TRACKER_WITH_TAMPER=y` | Compiles tamper guards (FSM) / tamper BT nodes (BT) into the build |
| `CONFIG_TRACKER_POLICY_BT=y`   | Links Impl-BT                                                      |
| `CONFIG_TRACKER_POLICY_FSM=y`  | Links Impl-FSM                                                     |
| `CONFIG_TRACKER_ORACLE_MODE=y` | Compiles `oracle_main.c` instead of `main.c`                       |
| `CONFIG_TRACKER_TRACE=y`       | Enables the trace probe (default on; disabled for oracle/footprint) |

There are no git branches or commits needed — each variant is a different `west build` invocation
using different `.conf` overlays.

---

## 4. Configuration Files (`.conf` overlays)

Located in `app/conf/`:

| File               | Purpose                                                    |
|--------------------|------------------------------------------------------------|
| `prj.conf`         | Base project config: debug optimizations, trace, Zbus      |
| `tracker_bt.conf`  | Selects `CONFIG_TRACKER_POLICY_BT=y`                       |
| `tracker_fsm.conf` | Selects `CONFIG_TRACKER_POLICY_FSM=y`                      |
| `tamper.conf`      | Sets `CONFIG_TRACKER_WITH_TAMPER=y`                        |
| `oracle.conf`      | Sets `CONFIG_TRACKER_ORACLE_MODE=y`, disables trace probe  |

Overlays are combined with `-DEXTRA_CONF_FILE="file1.conf;file2.conf"` at build time.

---

## 5. BT Model Code Generation

For Impl-BT, the XML model is **never hand-edited after initial design**. The build pipeline is:

```
models/tracker_base.xml (or tracker_tamper.xml)
        |  btf_groot_parser.py  (from modules/lib/btreefy/scripts/)
        v
btf_nodes_generated.c + btf_action_functions_generated.h
        |  Zephyr build
        v
zephyr.elf / zephyr.exe
```

`CONFIG_TRACKER_WITH_TAMPER` determines which XML is used. The C files are regenerated on every
`west build` — **never edit them manually**.

---

## 6. Evaluation Scripts

### 6.1 Oracle Scripts (`tests/oracle/`)

These scripts implement **Axis D** (behavioral equivalence testing).

#### `run_oracle.py` — Main oracle runner

Builds both Impl-BT and Impl-FSM oracle binaries, runs them on `native_sim`, and compares their
`chan_tracker_cmd` outputs event-by-event.

```bash
# From btreefy-model-test/tests/oracle/
python run_oracle.py --seq no-tamper             # base scenario
python run_oracle.py --seq tamper                # tamper scenario

# Reuse already-built binaries (skip compilation):
python run_oracle.py --seq no-tamper --skip-build
python run_oracle.py --seq tamper    --skip-build

# Custom build directory:
python run_oracle.py --seq no-tamper --build-root /path/to/build/dir
```

**Outputs** (written to `results/`):
- `oracle_base.csv` / `oracle_tamper.csv` — per-event divergence table (columns: `event_index`,
  `class`, `bt_cmds`, `fsm_cmds`)
- `oracle_base.txt` / `oracle_tamper.txt` — PASS/FAIL summary

**Exit code**: `0` = PASS (zero UNEXPECTED divergences), `1` = FAIL.

#### `compare.py` — Trace comparator (library module)

Used internally by `run_oracle.py` and `compare_captures.py`. Provides:
- `segment_by_event()` — groups trace lines by `EV,<i>,...` marker
- `extract_cmds()` — extracts `chan_tracker_cmd` operations from a block
- `classify()` — classifies a divergence into one of four named classes:

| Class           | Meaning                                                                     |
|-----------------|-----------------------------------------------------------------------------|
| `EXTRA_TICK`    | One side published a command the other did not (BT re-evaluates every tick) |
| `ORDER_SWAP`    | Same commands, different order                                               |
| `ABORT_EARLIER` | One side published a strict prefix of the other's commands                  |
| `UNEXPECTED`    | Anything else — **requires manual inspection**                              |

> **PASS criterion**: zero `UNEXPECTED` divergences. Expected divergences (`EXTRA_TICK`,
> `ORDER_SWAP`, `ABORT_EARLIER`) are documented behavioral differences, not bugs.

#### `serial_capture.py` — Hardware-in-the-loop (HIL) trace capture

Captures trace output from a real board over a serial port and saves it to `results/hil/`.

```bash
# Capture BT trace from a real nRF52840DK:
uv run tests/oracle/serial_capture.py --port /dev/ttyACM0 --impl bt --variant base

# Capture with tamper feature and DTR reset:
uv run tests/oracle/serial_capture.py --port /dev/ttyACM0 --impl fsm --variant tamper --reset-dtr

# Custom timeout (default: 60s):
uv run tests/oracle/serial_capture.py --port /dev/ttyACM0 --impl bt --variant base --timeout 120
```

#### `compare_captures.py` — Compare two HIL captures

Compares two pre-captured trace files (from separate flash/capture sessions) using the same
classification logic as the oracle.

```bash
uv run tests/oracle/compare_captures.py \
    --bt  results/hil/bt_base_1730000000.log \
    --fsm results/hil/fsm_base_1730000120.log \
    --seq no-tamper
```

---

### 6.2 Metrics Scripts (`tools/metrics/`)

These scripts implement **Axes A, B, and C**. All scripts are run via `uv run` from the
`tools/metrics/` directory (which contains its own `pyproject.toml`).

**Install dependencies once:**
```bash
cd tools/metrics
uv sync
```

#### `model_metrics.py` — Axis A: Model modifiability

Computes graph metrics for both BT models (from XML) and FSM models (reconstructed from a live
oracle run).

```bash
cd tools/metrics

# Full run (builds FSM oracle binaries, then extracts metrics):
uv run python model_metrics.py

# Reuse existing FSM oracle builds:
uv run python model_metrics.py --skip-fsm-build

# Custom build directory:
uv run python model_metrics.py --build-root /path/to/build
```

**Output**: `results/model.csv`
- Per-variant rows: `variant`, `n_nodes`, `n_edges`, `cc_decision_graph`
- GED rows: `ged_bt_base_to_tamper`, `ged_fsm_base_to_tamper`

#### `code_metrics.py` — Axis B: Code modifiability

Counts lines inside `#ifdef CONFIG_TRACKER_WITH_TAMPER` blocks and computes McCabe cyclomatic
complexity via `lizard` on the BT and FSM source files.

```bash
cd tools/metrics
uv run python code_metrics.py
```

**Output**: `results/code.csv`
Columns: `implementation`, `tamper_ifdef_loc`, `n_functions`, `cc_mean`, `cc_max`

#### `footprint.py` — Axis C: Flash/RAM footprint

Cross-compiles the 4 variants (BT/FSM x base/tamper) for `nrf52840dk/nrf52840` (Cortex-M target)
and reads ELF section sizes. Requires the Zephyr SDK's `arm-zephyr-eabi` toolchain.

```bash
cd tools/metrics

# Full run (builds all 4 variants):
uv run python footprint.py

# Skip build, read ELF from existing build dirs:
uv run python footprint.py --skip-build

# Custom build root:
uv run python footprint.py --build-root /path/to/build/footprint
```

**Output**: `results/footprint.csv`
Columns: `variant`, `text`, `rodata`, `data`, `bss`, `flash_total`, `ram_total`

#### `report.py` — Generate visual summary

Reads all available `results/*.csv` files and produces visualizations. No data is recomputed —
it purely visualizes what the other scripts have written.

```bash
cd tools/metrics
uv run python report.py
```

**Outputs**:
- `results/report_table.png` — BT x FSM synthesis table
- `results/report_chart.png` — 4-panel chart (GED, tamper LOC, CC, oracle divergences)

#### `run_all.py` — Full evaluation pipeline (single entry point)

Runs `model_metrics`, `code_metrics`, `footprint`, and `report` in sequence.

```bash
cd tools/metrics

# Full run (all axes, including footprint cross-compilation):
uv run python run_all.py

# Skip FSM oracle build for model metrics (reuse existing):
uv run python run_all.py --skip-fsm-build

# Skip footprint build (reuse existing ELFs):
uv run python run_all.py --skip-footprint-build

# Skip footprint entirely (no Cortex-M toolchain available):
uv run python run_all.py --skip-footprint
```

---

## 7. Complete Evaluation Workflow

The recommended order for a full evaluation from scratch:

```bash
# 0. Ensure dependencies are installed
cd btreefy-model-test/tools/metrics
uv sync

# 1. Axis D — Oracle (behavioral equivalence)
cd ../../tests/oracle
python run_oracle.py --seq no-tamper   # -> results/oracle_base.{csv,txt}
python run_oracle.py --seq tamper      # -> results/oracle_tamper.{csv,txt}

# 2. Axes A/B/C — Metrics
cd ../../tools/metrics
uv run python run_all.py --skip-footprint   # if no Cortex-M toolchain
# OR
uv run python run_all.py                    # full run with footprint

# 3. Review results
ls ../../results/
# oracle_base.csv, oracle_tamper.csv
# model.csv, code.csv, footprint.csv  (optional)
# report_table.png, report_chart.png
```

---

## 8. Results Directory (`results/`)

All generated files land in `btreefy-model-test/results/` (relative to the repo root).
This directory is **gitignored** and must be regenerated by running the scripts.

| File                 | Generated by       | Content                                         |
|----------------------|--------------------|-------------------------------------------------|
| `oracle_base.csv`    | `run_oracle.py`    | Per-event divergence table (no-tamper scenario) |
| `oracle_base.txt`    | `run_oracle.py`    | PASS/FAIL summary (no-tamper)                   |
| `oracle_tamper.csv`  | `run_oracle.py`    | Per-event divergence table (tamper scenario)    |
| `oracle_tamper.txt`  | `run_oracle.py`    | PASS/FAIL summary (tamper)                      |
| `model.csv`          | `model_metrics.py` | Graph metrics and GED for BT and FSM models     |
| `code.csv`           | `code_metrics.py`  | LOC in tamper ifdefs + cyclomatic complexity    |
| `footprint.csv`      | `footprint.py`     | ELF section sizes for all 4 variants            |
| `report_table.png`   | `report.py`        | Synthesis table (BT x FSM)                     |
| `report_chart.png`   | `report.py`        | 4-panel comparison chart                        |
| `hil/*.log`          | `serial_capture.py`| Raw HIL captures from real hardware             |

---

## 9. Coding Rules

1. **Never hand-edit generated files** (`btf_nodes_generated.c`,
   `btf_action_functions_generated.h`). They are regenerated from XML on every build.
2. **No dynamic memory allocation** (`malloc`/`free`). All data structures must be statically
   allocated, consistent with BTreeFy's embedded-first philosophy.
3. **`#ifdef CONFIG_TRACKER_WITH_TAMPER` is the only permitted feature-selection `#ifdef`** in
   the tracker library code. Do not add new ifdefs for other purposes.
4. **Policies never talk to drivers directly.** They only read `g_tracker_bb` and publish to
   `chan_tracker_cmd`.
5. **The trace probe (`CONFIG_TRACKER_TRACE`) must be disabled for all measurement builds**
   (footprint and oracle). It adds code to the binary and runs synchronously in the publisher's
   context.
6. **All reported numbers must trace to a CSV in `results/`**. The `report.py` script is the
   only place that translates CSVs into images/tables.
