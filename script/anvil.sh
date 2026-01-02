#!/usr/bin/env bash
set -euo pipefail

BLOCK_GAS_LIMIT="${BLOCK_GAS_LIMIT:-60000000}"

echo "Starting Anvil with block gas limit: $BLOCK_GAS_LIMIT"

exec anvil \
  --gas-limit "$BLOCK_GAS_LIMIT" \
  --no-request-size-limit