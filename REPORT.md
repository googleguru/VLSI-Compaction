# Technical Report: Rule-110 CA Guided Layout Compaction

## Method

### 1. Synthesis (Yosys)

RTL or gate-level Verilog inputs are processed by Yosys:

```
read_verilog → hierarchy → proc → opt → techmap → opt
→ (dfflibmap + abc -liberty if Liberty present)
→ stat → write_verilog
```

Outputs: gate-level netlist (`outputs/netlists/<design>_synth.v`) and cell
statistics.  When Yosys is unavailable, the pipeline falls back to synthetic
cell geometry templates.

### 2. Geometry Construction

`NetlistMapper` converts each cell instance to a bounding box using dimensions
from `data/synth/cell_templates.yaml` (generic 180 nm approximation).  Cells
are placed in a row-based floorplan with configurable target aspect ratio.
`SyntheticGenerator` is available for reproducible demo layouts when neither
a synthesized netlist nor PDK cell views are present.

### 3. Rule-110 CA Planning

The occupancy grid (H × W binary array) is evolved using exact Rule 110:

```
neighbourhood index: idx = 4·L + 2·C + R
lookup:  [0, 1, 1, 1, 0, 1, 1, 0][idx]   (= Wolfram code 110)
```

**2-D lift**:
- Even epoch → row pass (Rule 110 applied to each row independently)
- Odd epoch  → column pass (applied to each column independently)
- Damping after each pass: `state ← α·rule110(state) + (1−α)·state`

**Pressure extraction**:
- `col_pressure[c] = mean(state[:, c])` → X-axis pressure
- `row_pressure[r] = mean(state[r, :])` → Y-axis pressure
- `xshrf = max_shrink − mean(col_pressure) × (max_shrink − min_shrink)`
- `yshrf = max_shrink − mean(row_pressure) × (max_shrink − min_shrink)`

### 4. Compaction Backend

`PerlCompactor` invokes:

```
perl vendor/cellCompaction.pl \
  -iter N -Xshrf xshrf -Yshrf yshrf \
  -input in.cif -comp out.cif
```

The backend uses a segment-tree algorithm on CIF geometry.  Rule 110 provides
`xshrf` and `yshrf`; the backend performs the geometric legality work.

---

## Ablation Study Design

Five Rule-110 policies are compared against a backend-only baseline and the
legacy 7-rule composite CA (kept for cross-framework comparison):

| Policy | Rule-110 passes | Adaptive shrink |
|--------|----------------|-----------------|
| backend_only | none | no |
| r110_row_only | row | no |
| r110_col_only | col | no |
| r110_alternating | row + col | no |
| r110_alternating_adaptive | row + col | yes (wider range) |

All policies use clamped boundary conditions and 20 epochs.

---

## Reproduction

```bash
# 1. Install
pip install -e . -r requirements.txt

# 2. (Optional) Place cellCompaction.pl at vendor/cellCompaction.pl

# 3. Synthesize
make synth          # produces outputs/netlists/

# 4. Ablation
make ablation       # produces outputs/tables/ablation_results.csv

# 5. Figures
make figures        # produces outputs/figures/*.png

# Or all at once in Docker
make docker-build
docker compose -f docker/docker-compose.yml run --rm compaction full-run
```

---

## Benchmark Status

| Benchmark | Collateral | Status |
|-----------|-----------|--------|
| demo_simple | Synthetic CIF | Runs |
| demo_complex | Synthetic CIF | Runs |
| iscas_c17 | Verilog (public domain) | Runs with Yosys |
| iscas_s27 | Verilog (public domain) | Runs with Yosys |
| ipsd_c17 | IPSD CIF (not redistributed) | SKIP |
| asap7_inv_chain | ASAP7 PDK (academic license) | SKIP |

---

## Limitations and Honest Reporting

- All compaction results require the Perl backend.  CA planning outputs
  (shrink recommendations, convergence curves, pressure heatmaps) are
  produced even without the backend.
- IPSD and ASAP7 numbers are not reported here because the required
  collateral is not publicly available.  No results are fabricated.
- Rule 110 is a 1-D rule lifted to 2-D; it does not model wirelength,
  timing, or multi-layer routing constraints.
- The geometry templates in `data/synth/cell_templates.yaml` approximate a
  generic 180 nm process.  For accurate area numbers, replace them with
  PDK-accurate values.
