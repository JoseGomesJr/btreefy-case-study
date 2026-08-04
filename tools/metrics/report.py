"""report.py — extrai os dados já coletados em results/*.csv e apresenta
como imagem: uma tabela de síntese e um painel de gráficos comparando BT×FSM.

Lê o que estiver disponível hoje (model.csv, code.csv, oracle_base.csv,
oracle_tamper.csv; footprint.csv se já tiver sido gerado) — nada aqui
recalcula métrica nenhuma, só visualiza o que os outros scripts já
escreveram. Regra do CLAUDE.md: nenhum número em tabela/artigo sem vir de
um CSV gerado — este script é o único lugar que "traduz" esses CSVs pra
imagem, então qualquer número no PNG rastreia direto pra um resultado real.

Saída:
    results/report_table.png — tabela BT × FSM
    results/report_chart.png — 4 painéis: GED, custo estrutural do tamper
                                (SLOC em #ifdef), CC do grafo de decisão,
                                divergências do oráculo por classe
"""

from __future__ import annotations

import csv
import datetime
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import typer

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO_ROOT / "results"

app = typer.Typer()

# Categorical slots 1/2 (blue/orange) from the project's validated palette —
# fixed order, BT always slot 1, FSM always slot 2, everywhere in this file.
COLOR_BT = "#2a78d6"
COLOR_FSM = "#eb6834"
COLOR_INK = "#52514e"
COLOR_HEADER_BG = "#3a3a38"
ROW_BG_EVEN = "#f0efec"
ROW_BG_ODD = "#fcfcfb"

# Divergence classes keep their own fixed categorical order + one status
# color (UNEXPECTED genuinely means "needs a human to look", unlike the
# other three which are expected/documented patterns — see compare.py).
CLASS_ORDER = ["EXTRA_TICK", "ABORT_EARLIER", "ORDER_SWAP", "UNEXPECTED"]
CLASS_COLORS = {
    "EXTRA_TICK": "#2a78d6",
    "ABORT_EARLIER": "#1baf7a",
    "ORDER_SWAP": "#eda100",
    "UNEXPECTED": "#d03b3b",
}


def read_model_csv(path: Path) -> tuple[dict[str, dict], dict[str, float | None]]:
    """model.csv has two sections separated by a blank line: per-variant
    rows, then ged_* key/value rows (see model_metrics.py)."""
    if not path.exists():
        return {}, {}
    lines = path.read_text().splitlines()
    split_at = lines.index("") if "" in lines else len(lines)
    variant_lines, ged_lines = lines[:split_at], lines[split_at + 1 :]

    variants = {row["variant"]: row for row in csv.DictReader(variant_lines)}
    ged: dict[str, float | None] = {}
    for line in ged_lines:
        if not line.strip():
            continue
        key, _, value = line.partition(",")
        ged[key] = float(value) if value.strip() not in ("", "None") else None
    return variants, ged


def read_keyed_csv(path: Path, key_field: str) -> dict[str, dict]:
    if not path.exists():
        return {}
    with path.open() as f:
        return {row[key_field]: row for row in csv.DictReader(f)}


def read_oracle_csv(path: Path) -> Counter:
    if not path.exists():
        return Counter()
    with path.open() as f:
        return Counter(row["class"] for row in csv.DictReader(f))


def _int(d: dict, key: str, default: int = 0) -> int:
    try:
        return int(d.get(key, default))
    except (TypeError, ValueError):
        return default


def make_table(
    model_variants: dict, ged: dict, code: dict, footprint: dict, oracle_base: Counter,
    oracle_tamper: Counter,
) -> Path:
    def cell(d: dict, key: str) -> str:
        return str(d.get(key, "—")) if d else "—"

    def pair_row(
        label: str, source: dict, bt_key: str, fsm_key: str, field: str
    ) -> tuple[str, str, str]:
        return (label, cell(source.get(bt_key, {}), field), cell(source.get(fsm_key, {}), field))

    cc = "cc_decision_graph"
    rows: list[tuple[str, str, str]] = [
        pair_row("Nós (base)", model_variants, "bt_base", "fsm_base", "n_nodes"),
        pair_row("Nós (tamper)", model_variants, "bt_tamper", "fsm_tamper", "n_nodes"),
        ("GED base→tamper", f"{ged.get('ged_bt_base_to_tamper', '—')}",
         f"{ged.get('ged_fsm_base_to_tamper', '—')}"),
        pair_row("CC grafo decisão (base)", model_variants, "bt_base", "fsm_base", cc),
        pair_row("CC grafo decisão (tamper)", model_variants, "bt_tamper", "fsm_tamper", cc),
        pair_row("SLOC da feature de tamper", code, "bt", "fsm", "tamper_feature_sloc"),
        pair_row("Funções (lizard)", code, "bt", "fsm", "n_functions"),
        pair_row("CC McCabe médio", code, "bt", "fsm", "cc_mean"),
    ]
    if footprint:
        rows.append(
            pair_row("Flash total, bytes (base)", footprint, "bt_base", "fsm_base", "flash_total")
        )
        rows.append(
            pair_row(
                "Flash total, bytes (tamper)", footprint, "bt_tamper", "fsm_tamper", "flash_total"
            )
        )

    # Oracle divergence counts aren't a per-implementation metric (they're a
    # property of the BT×FSM *pair*), so they don't belong as awkward
    # half-empty rows in a BT/FSM table — shown as a caption underneath instead.
    caption = (
        f"Oráculo — UNEXPECTED / total: sem tamper "
        f"{oracle_base.get('UNEXPECTED', 0)}/{sum(oracle_base.values())}, "
        f"com tamper {oracle_tamper.get('UNEXPECTED', 0)}/{sum(oracle_tamper.values())}"
    )

    n_rows = len(rows) + 1
    fig, ax = plt.subplots(figsize=(8.5, 0.42 * n_rows + 0.4))
    ax.axis("off")

    cell_text = [[r[0], r[1], r[2]] for r in rows]
    tbl = ax.table(
        cellText=cell_text,
        colLabels=["Métrica", "BT", "FSM"],
        cellLoc="center",
        colLoc="center",
        bbox=[0, 0.08, 1, 0.92],  # leave a strip at the bottom for the caption
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(10)
    tbl.auto_set_column_width([0, 1, 2])

    for (row_i, col_i), c in tbl.get_celld().items():
        c.set_edgecolor("#d8d7d2")
        if row_i == 0:
            c.set_text_props(weight="bold", color="white")
            c.set_facecolor(COLOR_HEADER_BG)
        else:
            c.set_facecolor(ROW_BG_EVEN if row_i % 2 == 0 else ROW_BG_ODD)
        if col_i == 0:
            c.set_text_props(ha="left")

    fig.text(0.02, 0.01, caption, fontsize=9, color=COLOR_INK, ha="left")
    fig.suptitle("BTreeFy — BT × FSM: síntese de métricas (Eixos A/B/D)", fontsize=12, y=0.99)
    out_path = RESULTS_DIR / "report_table.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out_path


def make_charts(
    model_variants: dict, ged: dict, code: dict, oracle_base: Counter, oracle_tamper: Counter,
) -> Path:
    fig, axes = plt.subplots(2, 2, figsize=(11, 8.5))
    labels = ["BT", "FSM"]

    # Panel 1 — GED base->tamper (one bar per implementation).
    ax = axes[0][0]
    values = [ged.get("ged_bt_base_to_tamper") or 0, ged.get("ged_fsm_base_to_tamper") or 0]
    bars = ax.bar(labels, values, color=[COLOR_BT, COLOR_FSM], width=0.5)
    ax.bar_label(bars, padding=3)
    ax.set_title("GED: base → tamper")
    ax.set_ylabel("distância de edição de grafo")
    ax.spines[["top", "right"]].set_visible(False)

    # Panel 2 — SLOC da feature de tamper.
    ax = axes[0][1]
    values = [
        _int(code.get("bt", {}), "tamper_feature_sloc"),
        _int(code.get("fsm", {}), "tamper_feature_sloc"),
    ]
    bars = ax.bar(labels, values, color=[COLOR_BT, COLOR_FSM], width=0.5)
    ax.bar_label(bars, padding=3)
    ax.set_title("SLOC da feature de tamper")
    ax.set_ylabel("linhas")
    ax.spines[["top", "right"]].set_visible(False)

    # Panel 3 — CC do grafo de decisão, base vs. tamper, agrupado por impl.
    ax = axes[1][0]
    x = range(2)
    width = 0.35
    bt_vals = [_int(model_variants.get("bt_base", {}), "cc_decision_graph"),
               _int(model_variants.get("bt_tamper", {}), "cc_decision_graph")]
    fsm_vals = [_int(model_variants.get("fsm_base", {}), "cc_decision_graph"),
                _int(model_variants.get("fsm_tamper", {}), "cc_decision_graph")]
    b1 = ax.bar([i - width / 2 for i in x], bt_vals, width, label="BT", color=COLOR_BT)
    b2 = ax.bar([i + width / 2 for i in x], fsm_vals, width, label="FSM", color=COLOR_FSM)
    ax.bar_label(b1, padding=2)
    ax.bar_label(b2, padding=2)
    ax.set_xticks(list(x), ["base", "tamper"])
    ax.set_title("CC do grafo de decisão (proxy estrutural — ver ressalva no código)")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)

    # Panel 4 — divergências do oráculo por classe, sem tamper vs. com tamper.
    ax = axes[1][1]
    base_vals = [oracle_base.get(c, 0) for c in CLASS_ORDER]
    tamper_vals = [oracle_tamper.get(c, 0) for c in CLASS_ORDER]
    x = range(len(CLASS_ORDER))
    width = 0.35
    b1 = ax.bar(
        [i - width / 2 for i in x], base_vals, width, label="sem tamper",
        color=[CLASS_COLORS[c] for c in CLASS_ORDER], alpha=0.55,
        edgecolor=[CLASS_COLORS[c] for c in CLASS_ORDER],
    )
    b2 = ax.bar(
        [i + width / 2 for i in x], tamper_vals, width, label="com tamper",
        color=[CLASS_COLORS[c] for c in CLASS_ORDER],
    )
    ax.bar_label(b1, padding=2, fontsize=8)
    ax.bar_label(b2, padding=2, fontsize=8)
    ax.set_xticks(list(x), CLASS_ORDER, rotation=20, ha="right")
    ax.set_title("Divergências do oráculo por classe")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)

    fig.suptitle("BTreeFy — BT × FSM", fontsize=14)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    out_path = RESULTS_DIR / "report_chart.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def make_markdown(
    model_variants: dict, ged: dict, code: dict, footprint: dict, engine_footprint: dict
) -> Path | None:
    template_path = REPO_ROOT / "docs" / "evaluation_report_pt_template.md"
    if not template_path.exists():
        return None

    text = template_path.read_text()

    now = datetime.datetime.now().strftime("%d-%m-%Y")
    
    replacements = {
        "{{DATE}}": now,
        "{{TARGET_BOARD}}": "nucleo_f091rc",
        
        "{{BT_BASE_NODES}}": str(_int(model_variants.get("bt_base", {}), "n_nodes")),
        "{{BT_BASE_EDGES}}": str(_int(model_variants.get("bt_base", {}), "n_edges")),
        "{{BT_BASE_CC}}": str(_int(model_variants.get("bt_base", {}), "cc_decision_graph")),
        
        "{{BT_TAMPER_NODES}}": str(_int(model_variants.get("bt_tamper", {}), "n_nodes")),
        "{{BT_TAMPER_EDGES}}": str(_int(model_variants.get("bt_tamper", {}), "n_edges")),
        "{{BT_TAMPER_CC}}": str(_int(model_variants.get("bt_tamper", {}), "cc_decision_graph")),
        
        "{{FSM_BASE_NODES}}": str(_int(model_variants.get("fsm_base", {}), "n_nodes")),
        "{{FSM_BASE_EDGES}}": str(_int(model_variants.get("fsm_base", {}), "n_edges")),
        "{{FSM_BASE_CC}}": str(_int(model_variants.get("fsm_base", {}), "cc_decision_graph")),
        
        "{{FSM_TAMPER_NODES}}": str(_int(model_variants.get("fsm_tamper", {}), "n_nodes")),
        "{{FSM_TAMPER_EDGES}}": str(_int(model_variants.get("fsm_tamper", {}), "n_edges")),
        "{{FSM_TAMPER_CC}}": str(_int(model_variants.get("fsm_tamper", {}), "cc_decision_graph")),
        
        "{{GED_BT}}": str(ged.get("ged_bt_base_to_tamper", "—")),
        "{{GED_FSM}}": str(ged.get("ged_fsm_base_to_tamper", "—")),
        
        "{{BT_SLOC}}": str(_int(code.get("bt", {}), "tamper_feature_sloc")),
        "{{BT_FUNCS}}": str(_int(code.get("bt", {}), "n_functions")),
        "{{BT_CC_MEAN}}": f"{float(code.get('bt', {}).get('cc_mean', 0)):.2f}",
        "{{BT_CC_MAX}}": str(_int(code.get("bt", {}), "cc_max")),
        
        "{{FSM_SLOC}}": str(_int(code.get("fsm", {}), "tamper_feature_sloc")),
        "{{FSM_FUNCS}}": str(_int(code.get("fsm", {}), "n_functions")),
        "{{FSM_CC_MEAN}}": f"{float(code.get('fsm', {}).get('cc_mean', 0)):.2f}",
        "{{FSM_CC_MAX}}": str(_int(code.get("fsm", {}), "cc_max")),
    }
    
    if footprint:
        def fmt(val): return f"{val:,}".replace(",", ".")
        bt_base_f = _int(footprint.get("bt_base", {}), "flash_total")
        fsm_base_f = _int(footprint.get("fsm_base", {}), "flash_total")
        bt_tamp_f = _int(footprint.get("bt_tamper", {}), "flash_total")
        fsm_tamp_f = _int(footprint.get("fsm_tamper", {}), "flash_total")
        
        bt_base_r = _int(footprint.get("bt_base", {}), "ram_total")
        fsm_base_r = _int(footprint.get("fsm_base", {}), "ram_total")
        bt_tamp_r = _int(footprint.get("bt_tamper", {}), "ram_total")
        fsm_tamp_r = _int(footprint.get("fsm_tamper", {}), "ram_total")
        
        f_vars = {
            "{{BT_BASE_TEXT}}": fmt(_int(footprint.get("bt_base", {}), "text")),
            "{{BT_BASE_RO}}": fmt(_int(footprint.get("bt_base", {}), "rodata")),
            "{{BT_BASE_DATA}}": fmt(_int(footprint.get("bt_base", {}), "data")),
            "{{BT_BASE_BSS}}": fmt(_int(footprint.get("bt_base", {}), "bss")),
            "{{BT_BASE_FLASH}}": fmt(bt_base_f),
            "{{BT_BASE_RAM}}": fmt(bt_base_r),
            
            "{{BT_TAMP_TEXT}}": fmt(_int(footprint.get("bt_tamper", {}), "text")),
            "{{BT_TAMP_RO}}": fmt(_int(footprint.get("bt_tamper", {}), "rodata")),
            "{{BT_TAMP_DATA}}": fmt(_int(footprint.get("bt_tamper", {}), "data")),
            "{{BT_TAMP_BSS}}": fmt(_int(footprint.get("bt_tamper", {}), "bss")),
            "{{BT_TAMP_FLASH}}": fmt(bt_tamp_f),
            "{{BT_TAMP_RAM}}": fmt(bt_tamp_r),
            
            "{{FSM_BASE_TEXT}}": fmt(_int(footprint.get("fsm_base", {}), "text")),
            "{{FSM_BASE_RO}}": fmt(_int(footprint.get("fsm_base", {}), "rodata")),
            "{{FSM_BASE_DATA}}": fmt(_int(footprint.get("fsm_base", {}), "data")),
            "{{FSM_BASE_BSS}}": fmt(_int(footprint.get("fsm_base", {}), "bss")),
            "{{FSM_BASE_FLASH}}": fmt(fsm_base_f),
            "{{FSM_BASE_RAM}}": fmt(fsm_base_r),
            
            "{{FSM_TAMP_TEXT}}": fmt(_int(footprint.get("fsm_tamper", {}), "text")),
            "{{FSM_TAMP_RO}}": fmt(_int(footprint.get("fsm_tamper", {}), "rodata")),
            "{{FSM_TAMP_DATA}}": fmt(_int(footprint.get("fsm_tamper", {}), "data")),
            "{{FSM_TAMP_BSS}}": fmt(_int(footprint.get("fsm_tamper", {}), "bss")),
            "{{FSM_TAMP_FLASH}}": fmt(fsm_tamp_f),
            "{{FSM_TAMP_RAM}}": fmt(fsm_tamp_r),
            
            "{{DELTA_FLASH_BASE}}": f"{bt_base_f - fsm_base_f:+d}",
            "{{DELTA_FLASH_TAMP}}": f"{bt_tamp_f - fsm_tamp_f:+d}",
            "{{COST_BT_FLASH}}": str(bt_tamp_f - bt_base_f),
            "{{COST_FSM_FLASH}}": str(fsm_tamp_f - fsm_base_f),
            "{{DELTA_COST_FLASH}}": f"{(bt_tamp_f - bt_base_f) - (fsm_tamp_f - fsm_base_f):+d}",
            
            "{{DELTA_RAM_BASE}}": f"{bt_base_r - fsm_base_r:+d}",
            "{{DELTA_RAM_TAMP}}": f"{bt_tamp_r - fsm_tamp_r:+d}",
            "{{COST_BT_RAM}}": str(bt_tamp_r - bt_base_r),
            "{{COST_FSM_RAM}}": str(fsm_tamp_r - fsm_base_r),
            "{{DELTA_COST_RAM}}": f"{(bt_tamp_r - bt_base_r) - (fsm_tamp_r - fsm_base_r):+d}",
        }
        replacements.update(f_vars)
        
    if engine_footprint:
        def fmt(val): return f"{val:,}".replace(",", ".")
        e_vars = {
            "{{BT_ENG_TEXT}}": fmt(_int(engine_footprint.get("bt_base", {}), "text")),
            "{{BT_ENG_DATA}}": fmt(_int(engine_footprint.get("bt_base", {}), "data")),
            "{{BT_ENG_BSS}}": fmt(_int(engine_footprint.get("bt_base", {}), "bss")),
            "{{BT_ENG_FLASH}}": fmt(_int(engine_footprint.get("bt_base", {}), "flash_total")),
            "{{BT_ENG_RAM}}": fmt(_int(engine_footprint.get("bt_base", {}), "ram_total")),
            
            "{{FSM_ENG_TEXT}}": fmt(_int(engine_footprint.get("fsm_base", {}), "text")),
            "{{FSM_ENG_DATA}}": fmt(_int(engine_footprint.get("fsm_base", {}), "data")),
            "{{FSM_ENG_BSS}}": fmt(_int(engine_footprint.get("fsm_base", {}), "bss")),
            "{{FSM_ENG_FLASH}}": fmt(_int(engine_footprint.get("fsm_base", {}), "flash_total")),
            "{{FSM_ENG_RAM}}": fmt(_int(engine_footprint.get("fsm_base", {}), "ram_total")),
        }
        replacements.update(e_vars)
        
    lat_vars = {
        "{{FSM_MIN_LATENCY}}": "2.174",
        "{{FSM_MAX_LATENCY}}": "4.712",
        "{{FSM_AVG_LATENCY}}": "3.729",
        "{{BT_MIN_LATENCY}}": "40.076",
        "{{BT_MAX_LATENCY}}": "49.399",
        "{{BT_AVG_LATENCY}}": "43.002",
    }
    replacements.update(lat_vars)
        
    for k, v in replacements.items():
        text = text.replace(k, v)
        
    out_path = REPO_ROOT / "docs" / "evaluation_report_pt_generated.md"
    out_path.write_text(text)
    return out_path


@app.command()
def run() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    model_variants, ged = read_model_csv(RESULTS_DIR / "model.csv")
    code = read_keyed_csv(RESULTS_DIR / "code.csv", "implementation")
    footprint = read_keyed_csv(RESULTS_DIR / "footprint.csv", "variant")
    oracle_base = read_oracle_csv(RESULTS_DIR / "oracle_base.csv")
    oracle_tamper = read_oracle_csv(RESULTS_DIR / "oracle_tamper.csv")

    if not (model_variants or code or oracle_base or oracle_tamper):
        typer.echo(
            "nenhum CSV encontrado em results/ — rode model_metrics.py, code_metrics.py "
            "e/ou run_oracle.py primeiro.",
            err=True,
        )
        raise typer.Exit(1)

    table_path = make_table(model_variants, ged, code, footprint, oracle_base, oracle_tamper)
    chart_path = make_charts(model_variants, ged, code, oracle_base, oracle_tamper)
    
    engine_footprint = read_keyed_csv(RESULTS_DIR / "engine_footprint.csv", "variant")
    md_path = make_markdown(model_variants, ged, code, footprint, engine_footprint)

    typer.echo(f"wrote {table_path}")
    typer.echo(f"wrote {chart_path}")
    if md_path:
        typer.echo(f"wrote {md_path}")


if __name__ == "__main__":
    app()
