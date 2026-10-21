#!/usr/bin/env bash
# Regenerate the pydantic models from the bundled internal OpenAPI contract.
#
# Usage (from services/analytics):
#   ./scripts/gen_models.sh
#
# The generated file is committed; CI regenerates it and fails when the
# committed copy is out of date.

set -euo pipefail
cd "$(dirname "$0")/.."

uv run datamodel-codegen \
  --input ../../contracts/openapi/dist/internal.yaml \
  --input-file-type openapi \
  --output src/analytics/api/models_generated.py \
  --output-model-type pydantic_v2.BaseModel \
  --target-python-version 3.12 \
  --snake-case-field \
  --allow-population-by-field-name \
  --use-annotated \
  --use-standard-collections \
  --use-union-operator \
  --use-double-quotes \
  --keep-model-order \
  --disable-timestamp \
  --formatters ruff-format ruff-check
