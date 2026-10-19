#!/bin/sh
# Znovu stáhne účty a přegeneruje docs/data.json. Použití: ./rebuild.sh [--fetch]
set -e
cd "$(dirname "$0")"
if [ "$1" = "--fetch" ]; then
  rm -f data/raw/ucty/tx/fio_*.html
  python3 -I scripts/fetch_fio.py data/ucty.json data/raw/ucty/tx
  python3 -I scripts/fetch_kb.py data/ucty.json data/raw/ucty/tx
  python3 -I scripts/fetch_csas.py data/ucty.json data/raw/ucty/tx
  python3 -I scripts/fetch_rb.py data/raw/ucty/tx
  python3 -I scripts/fetch_moneta.py data/ucty.json data/raw/ucty/tx
fi
python3 -I scripts/parse_darci.py
python3 -I scripts/build.py
python3 -I scripts/analyze.py
