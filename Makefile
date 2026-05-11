.PHONY: build docker-build synth compact baseline eval ablation report \
        clean install lint test figures drc gds-export render-magic

PYTHON      := python3
SCRIPTS     := scripts
CONFIG      := configs/default.yaml
R110_CONFIG := configs/rule110.yaml
BENCHMARKS  := configs/benchmarks.yaml
MAGIC_CFG   := configs/magic.yaml
OUT         := outputs
POLICY      ?= r110_alternating_adaptive
TECH        ?= scmos

# ── local environment ────────────────────────────────────────────────────────

install:
	pip install -e . -r requirements.txt

lint:
	$(PYTHON) -m py_compile \
	    src/ca/rule110.py \
	    src/ca/rule110_scheduler.py \
	    src/synth/yosys_runner.py \
	    src/synth/liberty_handler.py \
	    src/synth/netlist_parser.py \
	    src/geometry/cell_template_loader.py \
	    src/geometry/netlist_mapper.py \
	    src/geometry/synthetic_generator.py \
	    src/eval/rule110_eval.py \
	    src/eval/ablation_runner.py \
	    2>&1 | grep -v '^$$' || true

test:
	$(PYTHON) -m pytest tests/ -v

build: install

# ── docker ───────────────────────────────────────────────────────────────────

docker-build:
	bash $(SCRIPTS)/build_docker.sh

docker-synth:
	docker compose -f docker/docker-compose.yml run --rm compaction synth

docker-compact:
	docker compose -f docker/docker-compose.yml run --rm compaction compact

docker-ablation:
	docker compose -f docker/docker-compose.yml run --rm compaction ablation

docker-report:
	docker compose -f docker/docker-compose.yml run --rm compaction report

docker-full:
	docker compose -f docker/docker-compose.yml run --rm compaction full-run

# ── runs (local) ─────────────────────────────────────────────────────────────

synth:
	bash $(SCRIPTS)/run_synth.sh $(CONFIG)

compact:
	bash $(SCRIPTS)/run_compaction.sh $(POLICY) $(CONFIG)

baseline:
	bash $(SCRIPTS)/run_baseline.sh

ablation:
	$(PYTHON) -m src.eval.ablation_runner \
	    --config $(CONFIG) \
	    --rule110-config $(R110_CONFIG) \
	    --benchmarks $(BENCHMARKS) \
	    --out-dir $(OUT)

eval: ablation

figures:
	$(PYTHON) -m src.viz.figure_exporter --config $(CONFIG) --out-dir $(OUT)

report:
	bash $(SCRIPTS)/make_report.sh

# ── Magic VLSI ───────────────────────────────────────────────────────────────

drc:
	bash $(SCRIPTS)/run_magic_drc.sh $(CONFIG) $(TECH)

gds-export:
	bash $(SCRIPTS)/export_gds.sh $(TECH) $(OUT)/compacted/gds

render-magic:
	$(PYTHON) -c "\
import glob, os; \
from src.io.cif_reader import read_cif; \
from src.viz.layout_plotter import plot_magic_layout; \
[plot_magic_layout(read_cif(f), tech='$(TECH)', \
    out_path='$(OUT)/figures/' + os.path.splitext(os.path.basename(f))[0] + '_magic.png') \
 for f in glob.glob('$(OUT)/compacted/*.cif')]"

# ── cleanup ──────────────────────────────────────────────────────────────────

clean:
	rm -rf $(OUT)/figures/* $(OUT)/compacted/* $(OUT)/compacted_layouts/* \
	       $(OUT)/tables/* $(OUT)/logs/* $(OUT)/reports/* \
	       $(OUT)/netlists/* $(OUT)/geometry/* \
	       $(OUT)/compacted/mag/* $(OUT)/compacted/gds/* \
	       __pycache__ src/**/__pycache__ *.egg-info dist build
	find . -name "*.pyc" -delete
