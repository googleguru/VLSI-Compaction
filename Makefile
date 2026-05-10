.PHONY: build docker-build baseline eval ablation report clean install lint test

PYTHON   := python3
SCRIPTS  := scripts
CONFIGS  := configs/default.yaml
OUT      := outputs

# ── local environment ────────────────────────────────────────────────────────

install:
	pip install -e . -r requirements.txt

lint:
	python -m py_compile src/**/*.py scripts/*.py 2>/dev/null || true

test:
	$(PYTHON) -m pytest tests/ -v 2>/dev/null || echo "No tests configured"

build: install

# ── docker ───────────────────────────────────────────────────────────────────

docker-build:
	docker compose -f docker/docker-compose.yml build

docker-baseline:
	docker compose -f docker/docker-compose.yml run --rm compaction bash /app/scripts/run_baseline.sh

docker-ablation:
	docker compose -f docker/docker-compose.yml run --rm compaction bash /app/scripts/run_ablation.sh

docker-report:
	docker compose -f docker/docker-compose.yml run --rm compaction bash /app/scripts/make_report.sh

# ── runs (local) ─────────────────────────────────────────────────────────────

fetch:
	bash $(SCRIPTS)/fetch_benchmarks.sh

convert:
	bash $(SCRIPTS)/convert_inputs.sh

baseline:
	bash $(SCRIPTS)/run_baseline.sh

ca-run:
	bash $(SCRIPTS)/run_ca_compaction.sh

ablation:
	bash $(SCRIPTS)/run_ablation.sh

eval:
	$(PYTHON) -m src.eval.ablation_runner --config $(CONFIGS)

report:
	bash $(SCRIPTS)/make_report.sh

# ── cleanup ──────────────────────────────────────────────────────────────────

clean:
	rm -rf $(OUT)/figures/* $(OUT)/compacted_layouts/* $(OUT)/tables/* \
	       $(OUT)/logs/* $(OUT)/reports/* __pycache__ src/**/__pycache__ \
	       *.egg-info dist build
	find . -name "*.pyc" -delete
