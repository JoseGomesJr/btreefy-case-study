import re
import sys
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(REPO_ROOT / "tests" / "oracle"))
import run_oracle

def parse_stack_usage(binary: Path, target_thread: str) -> tuple[int, int]:
    # Run the oracle binary natively and capture output
    lines = run_oracle.run_and_capture(binary)
    max_used = 0
    size = 0
    
    # Thread Analyzer output format looks something like:
    # tracker_fsm_thread   : unused 1234 usage 814 / 2048 (39 %)
    for line in lines:
        if "usage" in line.lower() or target_thread in line:
            print(f"RAW: {line}")
        if target_thread in line and "usage" in line.lower():
            # E.g. "tracker_fsm_thr: unused 1776 usage 272 / 2048 (13 %)"
            match = re.search(r"usage\s+(\d+)\s+/\s+(\d+)", line)
            if match:
                used = int(match.group(1))
                tot = int(match.group(2))
                size = tot
                if used > max_used:
                    max_used = used
                    
    return max_used, size

def build_with_stack_conf(policy: str, tamper: bool, build_dir: Path) -> Path:
    conf_files = [f"tracker_{policy}.conf"]
    if tamper:
        conf_files.append("tamper.conf")
    conf_files.append("oracle.conf")
    conf_files.append("stack.conf")  # Added stack config
    extra_conf = ";".join(conf_files)

    cmd = [
        "west",
        "build",
        "-b",
        "native_sim",
        str(REPO_ROOT / "app"),
        "-d",
        str(build_dir),
        "--",
        f"-DEXTRA_CONF_FILE={extra_conf}",
    ]
    subprocess.run(cmd, cwd=REPO_ROOT, check=True)
    return build_dir / "zephyr" / "zephyr.exe"

def main():
    print("Building FSM with Thread Analyzer...")
    fsm_bin = build_with_stack_conf("fsm", True, REPO_ROOT / "build/oracle/fsm_stack")
    
    print("Building BT with Thread Analyzer...")
    bt_bin = build_with_stack_conf("bt", True, REPO_ROOT / "build/oracle/bt_stack")

    print("Running and extracting maximum stack depth...")
    fsm_max, fsm_size = parse_stack_usage(fsm_bin, "tracker_fsm_thr")
    bt_max, bt_size = parse_stack_usage(bt_bin, "tracker_bt_thre")
    
    print(f"FSM (Tamper) -> Max Stack Usage: {fsm_max} bytes / {fsm_size} bytes")
    print(f"BT (Tamper)  -> Max Stack Usage: {bt_max} bytes / {bt_size} bytes")

if __name__ == "__main__":
    main()
