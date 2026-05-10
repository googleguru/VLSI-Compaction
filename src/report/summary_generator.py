"""
Generates a Markdown summary of evaluation results for embedding in README.
"""

import os
import csv
import glob
import logging
from typing import List

logger = logging.getLogger(__name__)


def generate_summary(out_dir: str) -> str:
    tables_dir = os.path.join(out_dir, "tables")
    lines: List[str] = []

    lines.append("## Results Summary\n")

    # Load ablation CSV if available
    ablation_csv = os.path.join(tables_dir, "ablation_results.csv")
    baseline_csv = os.path.join(tables_dir, "baseline_results.csv")

    primary_csv = ablation_csv if os.path.isfile(ablation_csv) else baseline_csv

    if not os.path.isfile(primary_csv):
        lines.append(
            "> No experiment results found. "
            "Run `make baseline` or `make ablation` to generate results.\n"
        )
        return "\n".join(lines)

    # Parse CSV
    rows = []
    with open(primary_csv) as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rows.append(row)

    if not rows:
        lines.append("> Results CSV is empty.\n")
        return "\n".join(lines)

    # Separate ready vs skipped
    ready   = [r for r in rows if r.get("notes", "") != "SKIPPED"]
    skipped = [r for r in rows if r.get("notes", "") == "SKIPPED"]

    # Summary table header
    lines.append(
        "| Benchmark | Policy | Area Red. (%) | Width Red. (%) | "
        "Height Red. (%) | Overlaps After | Runtime (s) | Backend OK |"
    )
    lines.append("|---|---|---:|---:|---:|---:|---:|:---:|")

    for r in ready:
        ar  = _fmt_float(r.get("area_reduction_pct",   "0"))
        wr  = _fmt_float(r.get("width_reduction_pct",  "0"))
        hr  = _fmt_float(r.get("height_reduction_pct", "0"))
        ov  = r.get("overlap_count_after", "0")
        rt  = _fmt_float(r.get("runtime_seconds", "0"))
        ok  = "yes" if r.get("backend_ok", "").lower() in ("true", "1", "yes") else "no"
        bm  = r.get("benchmark", "")
        pol = r.get("policy", "")
        lines.append(f"| {bm} | {pol} | {ar} | {wr} | {hr} | {ov} | {rt} | {ok} |")

    lines.append("")

    if skipped:
        lines.append("### Skipped Benchmarks\n")
        lines.append("| Benchmark | Policy | Reason |")
        lines.append("|---|---|---|")
        for r in skipped:
            reason = r.get("skip_reason", r.get("notes", "")).replace("\n", " ")[:80]
            lines.append(f"| {r.get('benchmark','')} | {r.get('policy','')} | {reason} |")
        lines.append("")

    return "\n".join(lines)


def _fmt_float(val: str) -> str:
    try:
        return f"{float(val):.2f}"
    except (ValueError, TypeError):
        return val


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="outputs")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    summary = generate_summary(args.out_dir)

    report_dir = os.path.join(args.out_dir, "reports")
    os.makedirs(report_dir, exist_ok=True)
    out_path = os.path.join(report_dir, "summary.md")
    with open(out_path, "w") as fh:
        fh.write(summary)
    logger.info("Summary written to %s", out_path)
    print(summary)


if __name__ == "__main__":
    main()
