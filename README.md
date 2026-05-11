# Rule-110 Cellular Automata Guided Layout Compaction Framework

**Yosys + Cell-Based-Layout-Compaction + Rule 110 CA planner + Magic VLSI**

A production-grade research framework for VLSI physical design compaction.
Yosys synthesizes RTL or benchmark Verilog into gate-level structure; a
Rule-110 cellular automaton plans directional compaction pressure; the
[Cell-Based-Layout-Compaction](https://github.com/AmeerAbdelhadi/Cell-Based-Layout-Compaction)
Perl engine performs segment-tree-based detailed compaction on CIF geometry;
and [Magic VLSI](http://opencircuitdesign.com/magic/) provides DRC validation,
CIF/MAG/GDS format conversion, and technology-aware rendering.

---

## Results at a Glance

### Area Reduction by Policy
![Area Reduction](outputs/figures/area_reduction.png)

### Width & Height Reduction
![Width and Height Reduction](outputs/figures/width_height_reduction.png)

### Ablation Policy Comparison
![Ablation Comparison](outputs/figures/ablation_comparison.png)

---

## Layout Renderings

### demo_complex — Standard & Magic-style

| Standard CIF Layout | Magic-style (SCMOS palette + hatch) |
|---|---|
| ![demo_complex layout](outputs/figures/demo_complex_layout.png) | ![demo_complex magic layout](outputs/figures/demo_complex_magic_layout.png) |

### demo_simple — Standard & Magic-style

| Standard CIF Layout | Magic-style (SCMOS palette + hatch) |
|---|---|
| ![demo_simple layout](outputs/figures/demo_simple_layout.png) | ![demo_simple magic layout](outputs/figures/demo_simple_magic_layout.png) |

---

## CA Analysis — demo_complex

### Convergence Curve (full_composite policy, 20 epochs)
![Convergence demo_complex](outputs/figures/demo_complex_convergence.png)

### Multi-Policy Pressure Comparison
![Policy Comparison demo_complex](outputs/figures/demo_complex_policy_comparison.png)

### CA Shrink Savings & Epoch Profile
| Shrink Savings | Epoch Profile |
|---|---|
| ![CA Shrink Savings demo_complex](outputs/figures/demo_complex_ca_shrink_savings.png) | ![CA Epoch Profile demo_complex](outputs/figures/demo_complex_ca_epoch_profile.png) |

### Heatmaps
| Occupancy | Pressure | Congestion |
|---|---|---|
| ![Occupancy demo_complex](outputs/figures/demo_complex_occupancy.png) | ![Pressure demo_complex](outputs/figures/demo_complex_pressure.png) | ![Congestion demo_complex](outputs/figures/demo_complex_congestion.png) |

---

## CA Analysis — demo_simple

### Convergence Curve (full_composite policy, 20 epochs)
![Convergence demo_simple](outputs/figures/demo_simple_convergence.png)

### Multi-Policy Pressure Comparison
![Policy Comparison demo_simple](outputs/figures/demo_simple_policy_comparison.png)

### CA Shrink Savings & Epoch Profile
| Shrink Savings | Epoch Profile |
|---|---|
| ![CA Shrink Savings demo_simple](outputs/figures/demo_simple_ca_shrink_savings.png) | ![CA Epoch Profile demo_simple](outputs/figures/demo_simple_ca_epoch_profile.png) |

### Heatmaps
| Occupancy | Pressure | Congestion |
|---|---|---|
| ![Occupancy demo_simple](outputs/figures/demo_simple_occupancy.png) | ![Pressure demo_simple](outputs/figures/demo_simple_pressure.png) | ![Congestion demo_simple](outputs/figures/demo_simple_congestion.png) |

---

## Rule-110 Detailed Analysis — demo_complex

### Dashboard (state · pressure · shrink · activity · column pressure)
![Rule-110 Dashboard demo_complex](outputs/figures/demo_complex_r110_dashboard.png)

### State Evolution (CA grid snapshots across 6 epochs)
![Rule-110 Evolution demo_complex](outputs/figures/demo_complex_r110_evolution.png)

### Pressure Map Evolution
![Rule-110 Pressure Evolution demo_complex](outputs/figures/demo_complex_r110_pressure_evolution.png)

### Shrink Trajectory & Activity Curve
| X/Y Shrink Factors | Active Cell Fraction |
|---|---|
| ![Rule-110 Shrink demo_complex](outputs/figures/demo_complex_r110_shrink.png) | ![Rule-110 Activity demo_complex](outputs/figures/demo_complex_r110_activity.png) |

### Column & Row Pressure Profiles
![Rule-110 Pressure Profiles demo_complex](outputs/figures/demo_complex_r110_pressure_profiles.png)

### Policy Matrix (mode × boundary condition)
![Rule-110 Policy Matrix demo_complex](outputs/figures/demo_complex_r110_policy_matrix.png)

### Shrink Comparison Across Modes
![Rule-110 Shrink Comparison demo_complex](outputs/figures/demo_complex_r110_shrink_comparison.png)

---

## Rule-110 Detailed Analysis — demo_simple

### Dashboard
![Rule-110 Dashboard demo_simple](outputs/figures/demo_simple_r110_dashboard.png)

### State Evolution
![Rule-110 Evolution demo_simple](outputs/figures/demo_simple_r110_evolution.png)

### Pressure Map Evolution
![Rule-110 Pressure Evolution demo_simple](outputs/figures/demo_simple_r110_pressure_evolution.png)

### Shrink Trajectory & Activity Curve
| X/Y Shrink Factors | Active Cell Fraction |
|---|---|
| ![Rule-110 Shrink demo_simple](outputs/figures/demo_simple_r110_shrink.png) | ![Rule-110 Activity demo_simple](outputs/figures/demo_simple_r110_activity.png) |

### Column & Row Pressure Profiles
![Rule-110 Pressure Profiles demo_simple](outputs/figures/demo_simple_r110_pressure_profiles.png)

### Policy Matrix (mode × boundary condition)
![Rule-110 Policy Matrix demo_simple](outputs/figures/demo_simple_r110_policy_matrix.png)

### Shrink Comparison Across Modes
![Rule-110 Shrink Comparison demo_simple](outputs/figures/demo_simple_r110_shrink_comparison.png)

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
    ┌─────▼────────────────────────┐
    │  Magic VLSI (optional)        │  DRC validation, .mag / GDS2 export,
    │  + Evaluation + Figures       │  area/width/height metrics, figures
    └──────────────────────────────┘
```

**Key principle**: Yosys does NOT perform layout compaction.
The Perl backend does the compaction.  Rule 110 is a *planning* layer only.

---

## Repository Structure

```
src/
  synth/      YosysRunner, LibertyHandler, NetlistParser
  ca/         rule110.py (exact 1-D updater), Rule110Scheduler (2-D lift),
              grid_discretizer, epoch_scheduler, state_encoder, rule_engine
  geometry/   CellTemplateLoader, NetlistMapper, SyntheticGenerator,
              overlap_estimator, polygon_utils, spatial_metrics
  planning/   directional_pressure, shrink_factor_planner, move_ordering
  layout/     magic_runner (batch DRC/export), tech_handler (layer maps)
  backend/    perl_wrapper, command_runner, output_parser
  eval/       rule110_eval, ablation_runner, baseline_eval, metrics_reporter,
              magic_drc_helper
  viz/        chart_generator, figure_exporter, heatmap_plotter,
              layout_plotter (Magic-style rendering), rule110_visualizer
  io/         cif_reader, cif_writer, mag_reader, mag_writer
configs/
  rule110.yaml        Rule-110 ablation policies
  ca_rules.yaml       Legacy composite policies (comparison baseline)
  default.yaml        Global config (synth, geometry, CA, layout, backend)
  magic.yaml          Magic technology settings (scmos / sky130A/B / gf180mcu)
  benchmarks.yaml     Benchmark registry with skip logic
data/
  demo/               demo_simple.cif, demo_complex.cif
  demo/iscas/         c17.v, s27.v, c432.v (ISCAS-85/89 benchmarks)
  synth/              cell_templates.yaml (generic 180nm approximation)
docker/       Dockerfile (yosys + magic + ghostscript), docker-compose.yml
scripts/      run_synth.sh, run_compaction.sh, run_magic_drc.sh,
              export_gds.sh, build_docker.sh, make_report.sh
tests/        test_rule110.py (36), test_cif_io.py, test_geometry.py,
              test_ca_engine.py, test_magic.py (37)
outputs/
  figures/    37 publication-ready PNG figures (committed)
```

---

## Quick Start

### Local

```bash
pip install -e . -r requirements.txt

# Synthesize ISCAS benchmarks (requires yosys on PATH)
make synth

# Rule-110 guided compaction
make compact

# Full ablation (Rule-110 + legacy composite comparison)
make ablation

# Export all figures
make figures

# Run Magic DRC on compacted layouts (requires magic on PATH)
make drc

# Export GDS2 (requires magic on PATH)
make gds-export
```

### Docker

```bash
make docker-build   # builds image with yosys + magic + ghostscript

docker compose -f docker/docker-compose.yml run --rm compaction full-run
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

---

## Magic VLSI Integration

Magic is an optional dependency — all features degrade gracefully when absent.

| Feature | With Magic | Without Magic |
|---------|-----------|---------------|
| DRC | Real Magic DRC count | Bounding-box overlap estimator |
| Format export | `.mag` flat + hierarchical, GDS2 | CIF only |
| Technology | scmos / sky130A / sky130B / gf180mcu | Layer name aliases |
| Rendering | Tech-aware hatch patterns | Solid fill |

```bash
# Batch DRC on all compacted layouts
make drc TECH=scmos

# Export to GDS2
make gds-export TECH=scmos
```

---

## Rule-110 Ablation Policies

Defined in `configs/rule110.yaml`:

| Policy | Mode | Description |
|--------|------|-------------|
| `r110_row_only` | row_only | Horizontal passes only |
| `r110_col_only` | col_only | Vertical passes only |
| `r110_alternating` | alternating | Alternating row + column |
| `r110_alternating_adaptive` | alternating | Full policy, wider shrink range |
| `r110_periodic` | alternating | Periodic boundary condition |

Legacy 7-rule composite policies from `configs/ca_rules.yaml` are also run
for comparison and clearly labelled in all output tables.

---

## Compaction Backend

Place `cellCompaction.pl` at `vendor/cellCompaction.pl`.
([AmeerAbdelhadi/Cell-Based-Layout-Compaction](https://github.com/AmeerAbdelhadi/Cell-Based-Layout-Compaction))

| Flag | Description |
|------|-------------|
| `-iter N` | Compaction iterations |
| `-Xshrf a` | X shrink factor (Rule-110 derived) |
| `-Yshrf b` | Y shrink factor (Rule-110 derived) |
| `-input in.cif` | Input CIF |
| `-comp out.cif` | Compacted output CIF |

---

## Test Suite

```
tests/test_rule110.py    36 tests — Rule-110 truth table, 1-D updater, 2-D passes,
                                    scheduler modes, damping, boundary conditions
tests/test_magic.py      37 tests — TechHandler, MagReader, MagWriter, MagicRunner
                                    graceful fallback, layout_plotter rendering
tests/test_cif_io.py      7 tests — CIF read/write round-trip
tests/test_geometry.py   16 tests — bbox, polygon, overlap, spatial metrics
tests/test_ca_engine.py  10 tests — discretizer, rule engine, epoch scheduler
─────────────────────────────────────────
Total                   106 tests — all passing
```

---

## Citation

```
Rule-110 Cellular Automata Guided Layout Compaction Framework
using Yosys + Cell-Based-Layout-Compaction, 2025.
```

Upstream tools:
- Yosys — https://github.com/YosysHQ/yosys
- Cell-Based-Layout-Compaction — https://github.com/AmeerAbdelhadi/Cell-Based-Layout-Compaction
- Magic VLSI — http://opencircuitdesign.com/magic/
