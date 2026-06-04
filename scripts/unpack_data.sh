#!/usr/bin/env bash
# Rozbalí komprimovaná data z data_bundle/ → data/ (reprodukce pipeline).
# Vyžaduje: xz, zstd (brew install xz zstd). Spouštěj z kořene repa.
set -euo pipefail
cd "$(dirname "$0")/.."
echo "→ core (opportunities.jsonl + harvest jsonl + configy + app)"
tar xf data_bundle/core.tar.xz
echo "→ doctext (vytěžený text z dokumentů)"
tar xf data_bundle/doctext.tar.xz
echo "→ wpfull (WordPress korpus)"
tar xf data_bundle/wpfull.tar.xz
if ls data_bundle/originals.tar.zst.part-* >/dev/null 2>&1; then
  echo "→ originals (PDF/xls/doc originály, ~1.8 GB; spojuji split chunky)"
  cat data_bundle/originals.tar.zst.part-* | zstd -d | tar xf -
fi
echo "✓ hotovo — data/ je naplněné"
