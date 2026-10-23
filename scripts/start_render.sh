#!/bin/sh
set -eu
# One worker and one numerical thread fit the Free service; no data/model downloads or training.
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
exec python -m uvicorn src.api:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1 --limit-concurrency 8 --timeout-keep-alive 5
