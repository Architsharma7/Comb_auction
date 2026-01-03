# Combinatorial Auction
This is the implementation of [fair combinatorial auctions](https://arxiv.org/abs/2408.12225) in solidity to test the correctness and benchmark gas consumption of combinatorial auction using smart contracts.
It derives correctness based on the [previous implementation](https://github.com/fhenneke/comb_auctions).

# Result
Gas analysis over 350 randomly chosen auctions. Can be seen [here](data/gas_analysis.png). Run benchmarks yourself as instructed [here](#how-to-test-and-benchmark).

<img width="5940" height="4769" alt="gas_analysis" src="https://github.com/user-attachments/assets/74c27eb2-20ff-46a9-9f62-b24e62f3d0d9" />

## Components

* **Data pipeline (Python)** for fetching auctions, computing per-trade scores, splitting multi-pair solutions, and selecting winners.
  Outputs:
  * `./data/auction_outputs/solutions_calldata_{AUCTION_INDEX}.bin` - ABI-encoded `(Solution[])` ready to pass as Solidity calldata.
  * `./data/auction_outputs/winners_python_{AUCTION_INDEX}.bin` - ABI-encoded `(Solution[])` winners from Python.
 
* **Gas Benchmarking pipeline** for measuring and analyzing gas costs at scale and collecting metadata.
  Outputs:
  * `./data/auction_gas_data.jsonl` - One line per auction with gas + metadata.
  * `.data/gas_analysis.png` - 6-plot analysis from JSONL data.

* **Solidity implementation** mirroring the Python logic:
  * `AggregateLib.sol` - aggregate scores by **directed pair** `(sell, buy)` using **pair keys** (keccak of the 2 addresses). Chosen to **avoid copying large calldata into memory** repeatedly when comparing pairs. Results in lower gas in `aggregatePairs`, baseline lookup, and compatibility checks.
  * `BaselineFilterLib.sol` - builds single-pair baselines and filters multi-pair solutions that underperform those baselines (matches Python `BaselineFilter`).
  * `SubsetFilterLib.sol` - greedy selection by total score with **DirectedTokenPairs** compatibility (no pair conflicts); non-cumulative key reservation to mirror Python's `SubsetFilteringSelection`.
  * `Types.sol` - minimal structs for `Trade`, `Solution`, `PairScore`.
  * `Combinatorial.sol` - `selectWinners((Solution[]) calldata)` wiring libs together, returns Solidity winners equivalent to Python.

* **Tests**
  1. **Combinatorial_auction.t.sol**: asserts Solidity winners ≡ Python winners for a given `AUCTION_INDEX`.
     * Reads: `RELATIVE_BIN_SOLUTIONS`, `RELATIVE_BIN_WINNERS`
     * Validates solution IDs, scores, trade details, solver addresses match exactly
  2. **SelectWinners_Benchmark.t.sol**: benchmarks the gas cost for execution of the `selectWinners` function.
     * Calls `selectWinners` with **exact** calldata; reports **execution gas** (no intrinsic/calldata)
     * Updates `gas_snapshot.txt` via `--gas-report`

* **Script** `scripts/anvil.sh`
  *  Start anvil chain with custom block gas limit = `60M`

## How to test and benchmark

### Prerequisites
Must have [uv](https://docs.astral.sh/uv/guides/install-python/) and [foundry](https://getfoundry.sh/introduction/installation/) installed.

### 1) Generate data (Python)

```bash
cd data
uv run winner_selection.py --auction_index {AUCTION_INDEX:-1987} \
  --auction_start {START?} --auction_end {END?}
# Writes:
#   ./data/auction_outputs/solutions_calldata_{AUCTION_INDEX}.bin
#   ./data/auction_outputs/winners_python_{AUCTION_INDEX}.bin
```

> Note: **auction_index ≠ auction_id**; it's the index within the fetched range.

### 2) Run tests (parity + execution gas)

```bash
export RELATIVE_BIN_SOLUTIONS=./data/auction_outputs/solutions_calldata_{AUCTION_INDEX}.bin
export RELATIVE_BIN_WINNERS=./data/auction_outputs/winners_python_{AUCTION_INDEX}.bin
forge test --gas-report -vv | tee gas_snapshot.txt
# gas_snapshot.txt now has the execution gas for this auction index.
```

### 3) Full on-chain gas (intrinsic + calldata + execution)

```bash
# Start a local chain and deploy
bash ../script/anvil.sh
# in a seperate terminal
export RPC_URL=http://127.0.0.1:8545
export PK=<one_anvil_private_key>
forge build
forge create src/Combinatorial.sol:Combinatorial --rpc-url $RPC_URL --private-key $PK --broadcast
export COMB_ADDR=<deployed_address>

# We have 2 options now: Benchmark Batch gas (recommended) and Benchmark gas for single auction

## Benchmark Batch gas collection for multiple auctions (recommended)

uv run collect_auction_data.py \                                       
    --auction_start {$AUCTION_START} \
    --auction_end {$AUCTION_END} \
    --rpc "$RPC_URL" \
    --pk "$PK" \
    --addr $COMB_ADDR"
    --output auction_gas_data.jsonl

## Benchmark gas for single auction

uv run benchmark_auction.py \
  --bin ./auction_outputs/solutions_calldata_{AUCTION_INDEX}.bin \
  --auction-id {AUCTION_INDEX}
  --rpc "$RPC_URL" \
  --pk  "$PK" \
  --addr "$COMB_ADDR" \
  --bin  ./data/auction_outputs/solutions_calldata_{AUCTION_INDEX}.bin \
  --auction-id {AUCTION_INDEX} \
```

Sample output for benchmarking the gas consmpution using batch gas collection
```
{
  "auction_id": 0,
  "auction_actual_id": 10322100,
  "num_solutions": 16,
  "num_trades": 22,
  "num_solvers": 8,
  "num_unique_token_pairs": 3,
  "multi_pair_solutions": 5,
  "single_pair_solutions": 11,
  "gas_total": 401118,
  "gas_exec": null,
  "gas_calldata": 121672,
  "benchmark_method": "onchain"
}
```

### 4) Visualize gas analysis
```bash
# Generate 6-plot visualization
uv run plot.py \
  --input auction_gas_data.jsonl \
  --output gas_analysis.png

# View results
open gas_analysis.png
```


## What this doesn't include

* **On-chain bid splitting and score calculation**: Bids are split off-chain and trade scores are computed off-chain as they require native token prices for surplus calculations. The Solidity implementation takes pre-calculated scores and split solutions as input.

* **Score validity proofs**: To prevent high gas costs while maintaining on-chain validity, a future enhancement could include **Merkle proofs** for proving score calculations on-chain without recomputing them.

