"""
Auto-updates README.md with the latest experiment summary and figure references.
Replaces content between sentinel markers without touching the static header.
"""

import os
import re
import glob
import logging
from .summary_generator import generate_summary

logger = logging.getLogger(__name__)

_BEGIN_MARKER = "<!-- RESULTS-BEGIN -->"
_END_MARKER   = "<!-- RESULTS-END -->"


def update_readme(root: str) -> None:
    readme_path = os.path.join(root, "README.md")
    if not os.path.isfile(readme_path):
        logger.error("README.md not found at %s", readme_path)
        return

    out_dir = os.path.join(root, "outputs")
    summary = generate_summary(out_dir)
    figure_section = _build_figure_section(out_dir)

    new_content = summary + "\n" + figure_section

    with open(readme_path) as fh:
        original = fh.read()

    if _BEGIN_MARKER in original and _END_MARKER in original:
        updated = re.sub(
            re.escape(_BEGIN_MARKER) + r".*?" + re.escape(_END_MARKER),
            _BEGIN_MARKER + "\n" + new_content + "\n" + _END_MARKER,
            original,
            flags=re.DOTALL,
        )
    else:
        updated = original.rstrip() + "\n\n" + _BEGIN_MARKER + "\n" + new_content + "\n" + _END_MARKER + "\n"

    with open(readme_path, "w") as fh:
        fh.write(updated)

    logger.info("README.md updated with latest results")


def _build_figure_section(out_dir: str) -> str:
    figures_dir = os.path.join(out_dir, "figures")
    if not os.path.isdir(figures_dir):
        return ""

    lines = ["## Figures\n"]
    figure_order = [
        ("area_reduction.png",        "Area Reduction by Policy"),
        ("width_height_reduction.png","Width and Height Reduction"),
        ("ablation_comparison.png",   "Ablation Study Comparison"),
    ]

    # Fixed figures first
    for fname, caption in figure_order:
        fpath = os.path.join(figures_dir, fname)
        if os.path.isfile(fpath):
            rel = os.path.relpath(fpath)
            lines.append(f"### {caption}\n")
            lines.append(f"![{caption}]({rel})\n")

    # Per-benchmark snapshots
    for fpath in sorted(glob.glob(os.path.join(figures_dir, "*_before_after.png"))):
        name = os.path.basename(fpath).replace("_before_after.png", "")
        rel  = os.path.relpath(fpath)
        lines.append(f"### Layout Snapshot: {name}\n")
        lines.append(f"![{name} before/after]({rel})\n")

    for fpath in sorted(glob.glob(os.path.join(figures_dir, "*_convergence.png"))):
        name = os.path.basename(fpath).replace("_convergence.png", "")
        rel  = os.path.relpath(fpath)
        lines.append(f"### CA Convergence: {name}\n")
        lines.append(f"![{name} convergence]({rel})\n")

    for fpath in sorted(glob.glob(os.path.join(figures_dir, "*_pressure.png"))):
        name = os.path.basename(fpath).replace("_pressure.png", "")
        rel  = os.path.relpath(fpath)
        lines.append(f"### Pressure Field: {name}\n")
        lines.append(f"![{name} pressure]({rel})\n")

    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    update_readme(args.root)


if __name__ == "__main__":
    main()
