"""footprint.py — Eixo C (footprint estático, sem hardware real).

Cross-compila (sem flashar) as 4 combinações BT/FSM × tamper on/off para um
alvo Cortex-M real — o toolchain arm-zephyr-eabi do Zephyr SDK já está
disponível neste ambiente, então isso roda sem precisar de placa física nem
da Fase 7 (coleta ao vivo, descartada). Lê .text/.rodata/.data/.bss do
.elf via pyelftools. Números de native_sim não entram aqui: o binário
nativo carrega código de simulação do host, não é representativo de
footprint embarcado real.
"""

from __future__ import annotations

import csv
import subprocess
from pathlib import Path

import typer
from elftools.elf.elffile import ELFFile

REPO_ROOT = Path(__file__).resolve().parents[2]
APP_DIR = REPO_ROOT / "app"
RESULTS_DIR = REPO_ROOT / "results"
BUILD_ROOT = REPO_ROOT / "build" / "footprint"

BOARD = "native_sim"
SECTIONS = (".text", ".rodata", ".data", ".bss")

app = typer.Typer()


def build(policy: str, tamper: bool, build_dir: Path, board: str = BOARD) -> Path:
    conf_files = [f"tracker_{policy}.conf"]
    if tamper:
        conf_files.append("tamper.conf")
    cmd = [
        "west",
        "build",
        "-b",
        board,
        str(APP_DIR),
        "-d",
        str(build_dir),
        "--",
        f"-DEXTRA_CONF_FILE={';'.join(conf_files)}",
        # Measurement builds must not carry the trace probe (CLAUDE.md
        # rule 6) — it's extra code, and its listeners run synchronously
        # in the publisher's context.
        "-DCONFIG_TRACKER_TRACE=n",
    ]
    subprocess.run(cmd, cwd=REPO_ROOT, check=True)
    # native_sim produces zephyr.exe; real boards produce zephyr.elf
    exe = build_dir / "zephyr" / "zephyr.exe"
    elf = build_dir / "zephyr" / "zephyr.elf"
    return exe if exe.exists() else elf


def section_sizes(elf_path: Path) -> dict[str, int]:
    sizes = dict.fromkeys(SECTIONS, 0)
    with elf_path.open("rb") as f:
        elf = ELFFile(f)
        for section in elf.iter_sections():
            if section.name in sizes:
                sizes[section.name] = section["sh_size"]
            elif f".{section.name}" in sizes:
                sizes[f".{section.name}"] = section["sh_size"]
            elif section.name == "datas":
                sizes[".data"] = section["sh_size"]
    return sizes


def get_archive_size(archive_path: Path) -> dict[str, int]:
    if not archive_path.exists():
        return {".text": 0, ".data": 0, ".bss": 0}
    try:
        output = subprocess.check_output(["size", "-t", str(archive_path)], text=True)
        for line in output.splitlines():
            if "(TOTALS)" in line:
                parts = line.split()
                return {
                    ".text": int(parts[0]),
                    ".data": int(parts[1]),
                    ".bss": int(parts[2]),
                }
    except Exception:
        pass
    return {".text": 0, ".data": 0, ".bss": 0}


@app.command()
def run(build_root: Path = BUILD_ROOT, skip_build: bool = False,
        board: str = BOARD) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    variants = [("bt", False), ("bt", True), ("fsm", False), ("fsm", True)]

    rows = []
    for policy, tamper in variants:
        tag = f"{policy}_{'tamper' if tamper else 'base'}"
        build_dir = build_root / tag
        elf_path = (
            next(
                p for p in [
                    build_dir / "zephyr" / "zephyr.exe",
                    build_dir / "zephyr" / "zephyr.elf",
                ]
                if p.exists()
            ) if skip_build
            else build(policy, tamper, build_dir, board=board)
        )
        sizes = section_sizes(elf_path)
        flash_total = sizes[".text"] + sizes[".rodata"] + sizes[".data"]
        ram_total = sizes[".data"] + sizes[".bss"]
        rows.append(
            [
                tag,
                sizes[".text"],
                sizes[".rodata"],
                sizes[".data"],
                sizes[".bss"],
                flash_total,
                ram_total,
            ]
        )

    out_path = RESULTS_DIR / "footprint.csv"
    with out_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["variant", "text", "rodata", "data", "bss", "flash_total", "ram_total"])
        writer.writerows(rows)

    typer.echo(f"wrote {out_path} (board={board})")

    engine_rows = []
    for policy, tamper in variants:
        tag = f"{policy}_{'tamper' if tamper else 'base'}"
        build_dir = build_root / tag
        
        if policy == "bt":
            archive_path = build_dir / "lib" / "libBTreeFy-Src.a"
        else:
            archive_path = build_dir / "zephyr" / "lib" / "smf" / "liblib__smf.a"
            
        e_sizes = get_archive_size(archive_path)
        flash_total = e_sizes[".text"] + e_sizes[".data"]
        ram_total = e_sizes[".data"] + e_sizes[".bss"]
        
        engine_rows.append(
            [
                tag,
                e_sizes[".text"],
                e_sizes[".data"],
                e_sizes[".bss"],
                flash_total,
                ram_total,
            ]
        )

    out_engine_path = RESULTS_DIR / "engine_footprint.csv"
    with out_engine_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["variant", "text", "data", "bss", "flash_total", "ram_total"])
        writer.writerows(engine_rows)
        
    typer.echo(f"wrote {out_engine_path} (board={board})")


if __name__ == "__main__":
    app()
