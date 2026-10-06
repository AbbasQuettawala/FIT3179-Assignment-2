#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
npx --yes mapshaper@0.6.113 -i data/au_states.geojson name=states -clean rewind -o data/au_states.geojson format=geojson force -simplify 30% keep-shapes -o data/au_states.topojson format=topojson
