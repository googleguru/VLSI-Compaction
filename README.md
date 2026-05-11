# Rule-110 Cellular Automata Guided Layout Compaction Framework

**Yosys + Cell-Based-Layout-Compaction + Rule 110 CA planner**

A production-grade research framework for VLSI physical design compaction.
Yosys synthesizes RTL or benchmark Verilog into gate-level structure; a
Rule-110 cellular automaton plans directional compaction pressure; and the
[Cell-Based-Layout-Compaction](https://github.com/AmeerAbdelhadi/Cell-Based-Layout-Compaction)
Perl engine performs segment-tree-based detailed compaction on CIF geometry.

---

## Why Rule 110?

Rule 110 (Wolfram elementary CA code 110 = 0b01101110) is the **only known
computationally-universal** elementary 1-D cellular automaton.  It sits at
the boundary between order and chaos (Wolfram Class IV), generating complex
but deterministic local interactions — exactly the property needed for an
adaptive pressure-propagation rule during compaction planning.

Truth table:

| L C R | Next |
|-------|------|
| 1 1 1 | 0    |
| 1 1 0 | 1    |
| 1 0 1 | 1    |
| 1 0 0 | 0    |
| 0 1 1 | 1    |
| 0 1 0 | 1    |
| 0 0 1 | 1    |
| 0 0 0 | 0    |

**2-D lift**: alternating horizontal (row) and vertical (column) Rule-110 passes
over the occupancy grid produce x-axis and y-axis pressure fields that bias
compaction ordering and shrink-factor selection.

---

## Pipeline

```
RTL Verilog / benchmark .v
          │
    ┌─────▼──────┐
    │   Yosys    │  read_verilog → proc → techmap → (abc -liberty) → write_verilog
    │  synthesis │  emits cell-count stats and gate-level netlist
    └─────┬──────┘
          │  gate-level netlist
    ┌─────▼──────────┐
    │ Geometry mapper │  CellTemplateLoader + NetlistMapper
    │ / synthetic gen │  → CIF bounding-box layout
    └─────┬──────────┘
          │  CIF layout
    ┌─────▼─────────────┐
    │  Rule-110 planner  │  GridDiscretizer → Rule110Scheduler
    │  (alternating row/ │  → row pressure, col pressure, shrink factors
    │   column passes)   │
    └─────┬─────────────┘
          │  xshrf, yshrf, ordering hints
    ┌─────▼───────────────────────────┐
    │  cellCompaction.pl (Perl backend)│  segment-tree compaction
    │  -iter N -Xshrf a -Yshrf b      │  on CIF geometry
    └─────┬───────────────────────────┘
          │  compacted CIF
    ┌─────▼────────┐
    │  Evaluation  │  area / width / height reduction, spacing violations,
    │  + figures   │  convergence curves, ablation bar charts
    └──────────────┘
```

**Key principle**: Yosys does NOT perform layout compaction.
The Perl backend does the compaction.  Rule 110 is a *planning* layer only.

---

## Repository Structure

```
src/
  synth/      YosysRunner, LibertyHandler, NetlistParser, Yosys .ys scripts
  ca/         rule110.py (exact 1-D updater), Rule110Scheduler (2-D),
              grid_discretizer, epoch_scheduler (legacy composite, kept for
              comparison), state_encoder, neighborhood, rule_engine
  geometry/   CellTemplateLoader, NetlistMapper, SyntheticGenerator,
              overlap_estimator, polygon_utils, spatial_metrics
  planning/   directional_pressure, shrink_factor_planner, move_ordering
              (all updated to consume Rule110RunResult)
  backend/    perl_wrapper, command_runner, output_parser
  eval/       rule110_eval, ablation_runner (Rule-110 + legacy composite),
              baseline_eval, metrics_reporter
  viz/        chart_generator, figure_exporter, heatmap_plotter, layout_plotter
  report/     readme_updater, summary_generator
  io/         cif_reader, cif_writer, geometry_normalizer, benchmark_manifest
configs/
  rule110.yaml        Rule-110 ablation policies
  ca_rules.yaml       Legacy 7-rule composite policies (comparison baseline)
  default.yaml        Global experiment config (synth, geometry, CA, backend)
  benchmarks.yaml     Benchmark registry with skip logic
  asap7.yaml          ASAP7 technology hooks
data/
  demo/       demo_simple.cif, demo_complex.cif
  demo/iscas/ c17.v, s27.v, c432.v (ISCAS-85/89 Verilog benchmarks)
  synth/      cell_templates.yaml (generic 180nm approximation)
docker/       Dockerfile (includes yosys), docker-compose.yml, entrypoint.sh
scripts/      run_synth.sh, run_compaction.sh, run_ablation.sh,
              build_docker.sh, run_baseline.sh, make_report.sh
tests/        test_rule110.py (36 tests), test_cif_io.py, test_geometry.py,
              test_ca_engine.py
```

---

## Quick Start

### Local

```bash
pip install -e . -r requirements.txt

# Synthesize ISCAS benchmarks (requires yosys on PATH)
make synth

# Run Rule-110 guided compaction (demo layouts, no Perl backend required for CA planning)
make compact

# Full ablation (Rule-110 + legacy composite comparison)
make ablation

# Export figures
make figures

# Build report
make report
```

### Docker

```bash
# Build image (includes yosys, perl, python)
make docker-build

# Full pipeline
docker compose -f docker/docker-compose.yml run --rm compaction full-run

# Synthesis only
docker compose -f docker/docker-compose.yml run --rm compaction synth

# Specific policy
POLICY=r110_row_only docker compose -f docker/docker-compose.yml run --rm compaction compact
```

---

## Benchmark Setup

| Benchmark | Type | Status | Notes |
|-----------|------|--------|-------|
| demo_simple | Synthetic CIF | **Ready** | 5 cells |
| demo_complex | Synthetic CIF | **Ready** | 20 cells |
| iscas_c17 | ISCAS-85 Verilog | **Ready** | Synthesized via Yosys |
| iscas_s27 | ISCAS-89 Verilog | **Ready** | Sequential, synthesized |
| ipsd_c17 | IPSD layout CIF | SKIP | Place c17.cif in `data/benchmarks/ipsd/` |
| ipsd_c432 | IPSD layout CIF | SKIP | Same prerequisite |
| asap7_inv_chain | ASAP7 PDK | SKIP | Requires ASAP7 academic license |

To enable IPSD benchmarks: place layout-ready CIF files under
`data/benchmarks/ipsd/`.  The pipeline adapters are fully implemented.

To enable ASAP7: obtain the PDK from the OpenROAD project and run
`scripts/convert_inputs.sh`.

---

## Compaction Backend

The Perl backend ([AmeerAbdelhadi/Cell-Based-Layout-Compaction](https://github.com/AmeerAbdelhadi/Cell-Based-Layout-Compaction))
must be placed at `vendor/cellCompaction.pl`.  Its original copyright and
license are preserved in full.

Parameters surfaced by this framework:

| Flag | Description |
|------|-------------|
| `-iter N` | Number of compaction iterations |
| `-Xshrf a` | X-axis shrink factor (Rule-110 derived) |
| `-Yshrf b` | Y-axis shrink factor (Rule-110 derived) |
| `-input in.cif` | Input CIF layout |
| `-comp out.cif` | Compacted output CIF |

Without the Perl backend, the CA planning stage still runs and produces
shrink recommendations, convergence curves, and pressure heatmaps.

---

## Rule-110 Ablation Policies

Defined in `configs/rule110.yaml`:

| Policy | Mode | Description |
|--------|------|-------------|
| `r110_row_only` | row_only | Horizontal Rule-110 passes only |
| `r110_col_only` | col_only | Vertical Rule-110 passes only |
| `r110_alternating` | alternating | Alternating row + column |
| `r110_alternating_adaptive` | alternating | Full policy, wider shrink range |
| `r110_periodic` | alternating | Periodic boundary condition variant |

Legacy 7-rule composite policies from `configs/ca_rules.yaml` are also run
for comparison and clearly labelled in all output tables.

---

## Outputs

```
outputs/
  netlists/        Yosys gate-level Verilog + synthesis logs
  compacted/       Compacted CIF layouts per policy
  tables/          ablation_results.csv, rule110_comparison.csv, ablation_pivot.csv
  figures/         *_convergence.png, *_pressure.png, *_ca_shrink_savings.png,
                   *_policy_comparison.png, area_reduction.png, ...
  logs/            Per-run logs
```

---

## Metrics

- Bounding-box area before / after (reduction %)
- Width and height reduction (%)
- Overlap count and spacing violations
- CA planning runtime (seconds)
- Total runtime
- Suggested xshrf / yshrf per epoch (convergence curves)

---

## Limitations

- IPSD and ASAP7 results require external collateral not redistributed here.
- Yosys synthesis requires `yosys` on PATH; the pipeline degrades gracefully
  to synthetic geometry when Yosys is absent.
- The Perl compaction backend must be obtained separately.
- Rule 110 is a 1-D CA lifted to 2-D via axis-alternating passes; it does not
  model exact circuit timing or multi-net routing congestion.
- No fabricated results: all tables show real CA planning outputs or clearly
  marked SKIP when the required collateral is absent.

---

## Citation

If you use this framework, please cite:

```
Rule-110 Cellular Automata Guided Layout Compaction Framework
using Yosys + Cell-Based-Layout-Compaction, 2025.
```

And acknowledge the upstream tools:

- Yosys Open SYnthesis Suite — https://github.com/YosysHQ/yosys
- Cell-Based-Layout-Compaction — https://github.com/AmeerAbdelhadi/Cell-Based-Layout-Compaction
