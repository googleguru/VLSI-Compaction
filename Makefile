.PHONY: build docker-build synth compact baseline eval ablation report \
        clean install lint test figures

PYTHON      := python3
SCRIPTS     := scripts
CONFIG      := configs/default.yaml
R110_CONFIG := configs/rule110.yaml
BENCHMARKS  := configs/benchmarks.yaml
OUT         := outputs
POLICY      ?= r110_alternating_adaptive

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

# ── cleanup ──────────────────────────────────────────────────────────────────

clean:
	rm -rf $(OUT)/figures/* $(OUT)/compacted/* $(OUT)/compacted_layouts/* \
	       $(OUT)/tables/* $(OUT)/logs/* $(OUT)/reports/* \
	       $(OUT)/netlists/* $(OUT)/geometry/* \
	       __pycache__ src/**/__pycache__ *.egg-info dist build
	find . -name "*.pyc" -delete
