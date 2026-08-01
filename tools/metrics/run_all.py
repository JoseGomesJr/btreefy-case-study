"""run_all.py — Fase D entry point: runs model_metrics, code_metrics, and
footprint, writing every CSV into results/. No git/hardware dependency for
any of them (see the plan)."""

from __future__ import annotations

import subprocess

import typer

import code_metrics
import footprint
import model_metrics
import modularity_metrics
import report

app = typer.Typer()


@app.command()
def run(
    skip_fsm_build: bool = False,
    skip_footprint_build: bool = False,
    skip_footprint: bool = False,
) -> None:
    typer.echo("=== model_metrics ===")
    model_metrics.run(skip_fsm_build=skip_fsm_build)

    typer.echo("=== code_metrics ===")
    code_metrics.run()

    typer.echo("=== modularity_metrics ===")
    modularity_metrics.run()

    wrote_footprint = False
    if skip_footprint:
        typer.echo("=== footprint === skipped (--skip-footprint)")
    else:
        typer.echo("=== footprint ===")
        try:
            footprint.run(skip_build=skip_footprint_build)
            wrote_footprint = True
        except subprocess.CalledProcessError as exc:
            typer.echo(
                f"footprint build failed ({exc}) — leaving results/footprint.csv untouched. "
                "Known issue as of this writing: nrf52840dk/nrf52840 hits a pre-existing "
                "Kconfig inconsistency between vendored cmsis/imxrt and nordic modules in "
                "this Zephyr checkout, unrelated to this project's code. Re-run "
                "`uv run python footprint.py` directly once resolved, or point BOARD at a "
                "different Cortex-M target.",
                err=True,
            )

    written = "results/model.csv, results/code.csv, results/modularity.csv" + (
        ", results/footprint.csv" if wrote_footprint else " (footprint.csv skipped)"
    )
    typer.echo(f"{written} atualizados")

    typer.echo("=== report ===")
    report.run()


if __name__ == "__main__":
    app()
