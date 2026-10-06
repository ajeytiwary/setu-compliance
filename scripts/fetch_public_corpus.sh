#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIBD_TOOL_DIR="${EUROSETU_SCRIBD_TOOL_DIR:-$(cd "$ROOT_DIR/.." && pwd)/scribd}"
CORPUS_DIR="${EUROSETU_PUBLIC_CORPUS_DIR:-$ROOT_DIR/data/public_corpus/downloads}"
mkdir -p "$CORPUS_DIR"
if [[ ! -f "$SCRIBD_TOOL_DIR/src/download.ts" ]]; then
  echo "Scribd downloader missing: $SCRIBD_TOOL_DIR" >&2
  exit 2
fi
(cd "$SCRIBD_TOOL_DIR" && bun run src/download.ts --file "$ROOT_DIR/data/public_corpus/scribd_ids.csv" --out "$CORPUS_DIR")
EXAMPLES_URL='https://taxation-customs.ec.europa.eu/document/download/8d00a979-e57d-4e53-a11f-8b01370236a9_en?filename=Communication-template-examples.zip'
if [[ ! -f "$CORPUS_DIR/cbam-communication-examples.zip" ]]; then
  curl --fail --location --max-time 60 "$EXAMPLES_URL" -o "$CORPUS_DIR/cbam-communication-examples.zip"
fi
unzip -p "$CORPUS_DIR/cbam-communication-examples.zip" '2 CBAM SEE V2.1_Example Steel 1 Blast furnace_final.xlsx' > "$CORPUS_DIR/cbam-steel-blast-furnace-example.xlsx"
echo "Corpus ready in $CORPUS_DIR"
