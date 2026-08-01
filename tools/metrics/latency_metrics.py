import sys
from pathlib import Path

# Add tests/oracle to sys.path so we can import run_oracle
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(REPO_ROOT / "tests" / "oracle"))

import run_oracle

def parse_cycles(binary: Path) -> tuple[int, float]:
    lines = run_oracle.run_and_capture(binary)
    cycles = []
    for line in lines:
        if line.startswith("[CYCLES]"):
            try:
                cycles.append(int(line.split()[1]))
            except:
                pass
    if not cycles:
        return 0, 0.0
    return max(cycles), sum(cycles) / len(cycles)

def main():
    fsm_bin = REPO_ROOT / "build/oracle/fsm_tamper/zephyr/zephyr.exe"
    bt_bin = REPO_ROOT / "build/oracle/bt_tamper/zephyr/zephyr.exe"
    
    if not fsm_bin.exists() or not bt_bin.exists():
        print("Binaries not found. Building them...")
        run_oracle.build("fsm", True, REPO_ROOT / "build/oracle/fsm_tamper")
        run_oracle.build("bt", True, REPO_ROOT / "build/oracle/bt_tamper")

    print("Running oracle and capturing cycles...")
    fsm_max, fsm_mean = parse_cycles(fsm_bin)
    bt_max, bt_mean = parse_cycles(bt_bin)

    print(f"FSM (Tamper) -> WCET: {fsm_max} cycles, Mean: {fsm_mean:.2f} cycles")
    print(f"BT (Tamper)  -> WCET: {bt_max} cycles, Mean: {bt_mean:.2f} cycles")

if __name__ == "__main__":
    main()
