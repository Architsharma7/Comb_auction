#!/usr/bin/env bash
set -euo pipefail

# This script benchmarks the gas cost of calling selectWinners() on-chain
# using real calldata from a real auction solution. 
# What “gasUsed” includes:
#   Full transaction gas (intrinsic + calldata + execution − refunds).
#   You can split it later (intrinsic+calldata vs execution) using the
#   zeros/nonzeros counts: 21000 + 4*zeros + 16*nonzeros.
# Usage:
#   bash scripts/bench_selectwinners.sh \
#     --rpc   <RPC URL> of anvil node\
#     --pk    <PRIVATE_KEY> of anvil\
#     --addr  <DEPLOYED_COMBINATORIAL_ADDRESS> deployed on anvil\
#     --bin   <PATH_TO_solutions_calldata_XXXX.bin> same as in SelectWinners_Benchmark.ts.sol \
#     --auction-id <NUMBER_FOR_YOUR_RECORDS> just to keep record of auction index\
#     --out   <OUTPUT_NDJSON_PATH> 

while [[ $# -gt 0 ]]; do
  case "$1" in
    --rpc) RPC="$2"; shift 2 ;;
    --pk) PK="$2"; shift 2 ;;
    --addr) ADDR="$2"; shift 2 ;;
    --bin) BIN="$2"; shift 2 ;;
    --auction-id) AID="${2:-0}"; shift 2 ;;
    --out) OUT="${2:-data/gas_snapshot.ndjson}"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

: "${RPC:?--rpc required}"; : "${PK:?--pk required}"
: "${ADDR:?--addr required}"; : "${BIN:?--bin required}"
: "${AID:=0}"; : "${OUT:=./gas_snapshot.ndjson}"

SIG='selectWinners((string,address,uint256,(string,address,address,uint256)[])[])'
SEL=$(cast sig "$SIG")
SEL=${SEL#0x}

CALDATA=$(python3 - <<'PY' "$BIN" "$SEL"
import sys, binascii
bin_path, sel = sys.argv[1], sys.argv[2]
raw = open(bin_path,'rb').read()
print("0x"+sel+binascii.hexlify(raw).decode())
PY
)

echo "SEL=$SEL"
echo "CAL prefix=${CALDATA:0:12}"
echo "bytes_len=$(( (${#CALDATA}-2)/2 ))"

# quick static call (will revert if calldata/addr are wrong)
cast call "$ADDR" "$CALDATA" --rpc-url "$RPC" > /dev/null

# send (skip estimator; older cast: pass raw calldata as positional arg)
TXHASH=$(cast send "$ADDR" "$CALDATA" \
  --private-key "$PK" \
  --rpc-url "$RPC" \
  --gas-limit 20000000 \
  --legacy \
  --async | tail -n1)

# Get receipt JSON
RCPT_JSON=$(cast receipt "$TXHASH" --rpc-url "$RPC" --json)

# gasUsed (hex)
GAS_USED_HEX=$(echo "$RCPT_JSON" | jq -r '.gasUsed')          
GAS_USED_DEC=$(python3 - "$GAS_USED_HEX" <<'PY'
import sys
h = sys.argv[1]
print(int(h, 16))
PY
)

STATUS_HEX=$(echo "$RCPT_JSON" | jq -r '.status')
STATUS=$([ "$STATUS_HEX" = "0x1" ] && echo 1 || echo 0)

# Byte stats for calldata
HEX=${CALDATA:2}
BYTES_LEN=$(( ${#HEX} / 2 ))
ZEROS=$(echo "$HEX" | grep -o '..' | awk '{if($1=="00") z++} END{print z+0}')
NONZEROS=$(( BYTES_LEN - ZEROS ))

# Append NDJSON snapshot
mkdir -p "$(dirname "$OUT")"
jq -n \
  --arg addr "$ADDR" \
  --arg bin "$BIN" \
  --arg tx "$TXHASH" \
  --arg sel "$SEL" \
  --argjson aid "$AID" \
  --argjson bytes "$BYTES_LEN" \
  --argjson zeros "$ZEROS" \
  --argjson nonzeros "$NONZEROS" \
  --argjson gasUsed "$GAS_USED_DEC" \
  --argjson status "$STATUS" \
  '{auction_id:$aid,contract:$addr,tx:$tx,selector:$sel,calldata_len:$bytes,zeros:$zeros,nonzeros:$nonzeros,gas_used:$gasUsed,status:$status}' \
  >> "$OUT"

echo "Wrote snapshot → $OUT"
echo "tx: $TXHASH | status: $STATUS_HEX | gasUsed(dec): $GAS_USED_DEC | calldata bytes: $BYTES_LEN (zeros: $ZEROS, nonzeros: $NONZEROS)"
