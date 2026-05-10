# vendor/

Place `cellCompaction.pl` here before running experiments.

## How to obtain

```bash
git clone https://github.com/AmeerAbdelhadi/Cell-Based-Layout-Compaction _tmp
cp _tmp/cellCompaction.pl .
rm -rf _tmp
```

The framework resolves the script from these locations in order:
1. `vendor/cellCompaction.pl`  (recommended)
2. `Cell-Based-Layout-Compaction/cellCompaction.pl`
3. `cellCompaction.pl`

The script path can also be overridden in `configs/default.yaml` under
`backend.perl_script`.

## Upstream license

See `../UPSTREAM_LICENSE` for attribution requirements.

## Without the backend

The CA planning layer, CIF I/O, geometry analysis, and visualization all run
without the Perl backend. Evaluation of compaction quality requires the backend.
When the backend is unavailable, all results are marked `backend_ok: false` and
skipped benchmarks are logged with an explicit reason.
