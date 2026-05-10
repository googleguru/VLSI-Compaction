# Technical Report: Rule-Based CA Compaction Framework

**Title:** Rule-Based Cellular Automata Compaction Framework for VLSI Physical Design  
**Method:** CA-enhanced Cell-Based Layout Compaction  
**Backend:** Modified segment-tree compactor (Perl, upstream BSD license)

---

## 1. Problem Statement

VLSI layout compaction reduces the physical area of a placed design by moving
geometries as close together as design rules allow. The upstream backend
(cellCompaction.pl) performs efficient cell-based compaction using a modified
segment-tree algorithm with configurable shrink factors (Xshrf, Yshrf) and
iteration counts. However, the quality of compaction depends critically on the
choice of these parameters and the ordering in which cells are processed.

This work adds a rule-based 2D cellular automata layer that analyzes the layout
geometry before each backend call and derives improved compaction parameters.

---

## 2. Method

### 2.1 CA Grid

The layout geometry is rasterized into a 2D integer occupancy grid at a
configurable resolution (default: 1 grid cell per 10 CIF units). Each grid cell
has state:

- `EMPTY (0)`, `OCCUPIED (1)`, `KEEPOUT (2)`, `BOUNDARY (3)` — occupancy
- `x_pressure`, `y_pressure` — directional compaction pressure in [-1, 1]
- `conflict_density` — local occupancy density (via uniform filter)
- `free_space_score` — local empty fraction
- `mobility` — movement eligibility score
- `compaction_eligible` — binary flag

### 2.2 CA Rules

Seven deterministic rules are composed into a single policy per epoch:

**Free-space attraction**: Computes the free-space gradient (via np.roll) and
increases directional pressure toward less-occupied neighborhoods. Applied only
to occupied, eligible cells with local free-space score above threshold.

**Conflict repulsion**: Reduces pressure magnitude for cells in high-occupancy
neighborhoods (conflict density > threshold). Prevents overcrowding in the
requested direction.

**Connectivity preservation**: Aligns each cell's pressure with the
neighborhood-average pressure using a smoothed kernel, preserving topological
coupling across geometrically adjacent cells.

**Boundary guard**: Forces boundary-facing pressure components to zero at layout
margins, preventing illegal geometry collapse against the design outline.

**Alternating-axis schedule**: On even epochs, suppresses Y-pressure by 50%.
On odd epochs, suppresses X-pressure by 50%. This mirrors the backend's typical
alternating horizontal/vertical compaction pattern and stabilizes the overall
pressure field.

**Shrink adaptation**: Computes per-epoch conflict density and stores it in the
state tensor for use by the epoch scheduler's shrink-factor derivation.

**Stabilization**: Cells whose (xp, yp) pair has changed by less than a
threshold vs. the previous epoch are marked ineligible, stopping unnecessary
updates and accelerating convergence.

### 2.3 Epoch Scheduler and Convergence

The scheduler runs up to `max_epochs` (default: 20) CA iterations per layout.
Convergence is detected when the mean absolute change in (xp, yp) across the
grid falls below `convergence_threshold` (default: 0.01). Upon convergence or
timeout, the scheduler extracts:

- **Suggested Xshrf, Yshrf**: Derived as `max_shrink - pressure_magnitude * scale
  - conflict * 0.05`, clipped to [0.80, 0.99].
- **Backend iteration count**: `max(2, min(base_iters, ca_epochs_run))` for
  fast-converging layouts; `base_iters + 2` for slow.

### 2.4 Best-Practice Policy

Based on the composite rule design, the best practical rule-based CA for this
framework is not a single Wolfram-style rule but a **composite deterministic
policy** combining:

1. Free-space attraction
2. Conflict repulsion
3. Alternating-axis scheduling
4. Boundary guarding

This is the default `full_composite` policy. Ablations (`backend_only`,
`simple_directional`, `free_space_repulsion`, `adaptive_shrink`) measure the
contribution of each rule group.

---

## 3. Repository Structure

See README.md for the annotated directory tree.

Key design decisions:

- **Separation of concerns**: CIF I/O, CA planning, backend invocation, metrics
  collection, and visualization are in strictly separate Python modules with no
  circular imports.
- **No fabricated results**: All metrics are measured from actual backend output.
  Benchmarks without valid CIF input are explicitly skipped with logged reasons.
- **Deterministic seeds**: NumPy random state is seeded from `configs/default.yaml`
  (`experiment.seed: 42`). The CA rules themselves are fully deterministic (no
  stochastic sampling).
- **Backend as black box**: The CA layer communicates with the Perl backend only
  via CLI arguments (iter, Xshrf, Yshrf) and file I/O. No Perl internals are
  modified or assumed.

---

## 4. Reproduction Flow

### 4.1 Quick start (demo, no external prerequisites)

```bash
# 1. Install dependencies
make install

# 2. Place the upstream Perl script
mkdir -p vendor
git clone https://github.com/AmeerAbdelhadi/Cell-Based-Layout-Compaction tmp
cp tmp/cellCompaction.pl vendor/
rm -rf tmp

# 3. Run baseline on demo layouts
make baseline

# 4. Run CA-enhanced ablation
make ablation

# 5. Generate figures and update README
make report
```

### 4.2 Docker (fully reproducible)

```bash
make docker-build
docker compose -f docker/docker-compose.yml run --rm compaction full-run
```

### 4.3 Adding real benchmarks

1. Place IPSD CIF files in `data/benchmarks/ipsd/`
2. Place converted ISCAS CIF files in `data/benchmarks/iscas/`
3. Configure ASAP7 PDK path in `configs/asap7.yaml`
4. Re-run `make ablation report`

---

## 5. Benchmark Status

| Benchmark Suite | Status | Reason |
|---|---|---|
| Demo (synthetic) | Available | Included in repository |
| IPSD | Not available | Layout-ready CIF not publicly distributed |
| ISCAS-85/89 | Not available | Requires external synthesis + P&R |
| ASAP7 | Not available | Requires academic PDK license |

All adapter code, conversion hooks, and skip-reporting logic is implemented.
The framework runs end-to-end on demo layouts without external prerequisites.

---

## 6. Outputs

After `make ablation report`:

```
outputs/
  tables/
    baseline_results.csv
    ca_results_full_composite.csv
    ablation_results.csv
    ablation_pivot.csv
  figures/
    area_reduction.png
    width_height_reduction.png
    ablation_comparison.png
    demo_simple_occupancy.png
    demo_simple_pressure.png
    demo_simple_convergence.png
    demo_complex_*
  reports/
    summary.md
```

---

## 7. License and Attribution

The upstream compaction engine is copyright Ameer M.S. Abdelhadi and distributed
under a BSD-style license. See `UPSTREAM_LICENSE` for the full notice.

This framework (src/, scripts/, docker/, configs/) is original work and released
under MIT License. Upstream copyright notices are preserved in all contexts where
the Perl backend is invoked.

---

## 8. Known Limitations and Future Work

- **Full DRC**: Spacing violations are estimated via bbox edge spacing. A
  technology DRC engine would provide precise rule checking.
- **Learned policy**: The current CA is fully rule-based. A future variant could
  learn pressure weights from compaction outcome feedback using lightweight RL.
- **Non-rectangular geometry**: The grid discretizer uses bbox approximations for
  polygonal geometry. Exact polygon rasterization would improve CA accuracy for
  complex shapes.
- **Parallel backend calls**: Multiple benchmarks are processed serially. A future
  version could parallelize backend invocations across benchmarks.
- **Transform support in CIF reader**: Mirror and rotation CIF transforms are not
  yet implemented.
