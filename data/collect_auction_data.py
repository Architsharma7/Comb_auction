#!/usr/bin/env python3
"""
Collect complete auction data with gas measurements.

Output JSONL with fields:
- auction_id
- num_solutions, num_trades, num_solvers, etc.
- gas_calldata, gas_exec_measured, gas_tx_measured, gas_tx_estimated
- benchmark_method (onchain or forge)
"""

import argparse
import json
from pathlib import Path

from benchmark_auction import benchmark_auction
from fetch import fetch_auctions, compute_split_solutions
from mechanism import aggregate_scores
from winner_selection import encode_args

INTRINSIC_GAS = 21_000

def extract_auction_features(solutions):
    """Extract all relevant auction characteristics."""

    num_solutions = len(solutions)
    num_trades = sum(len(sol.trades) for sol in solutions)
    num_solvers = len(set(sol.solver for sol in solutions))

    all_token_pairs = set()
    multi_pair_count = 0
    single_pair_count = 0

    for sol in solutions:
        scores = aggregate_scores(sol)
        all_token_pairs.update(scores.keys())
        if len(scores) > 1:
            multi_pair_count += 1
        else:
            single_pair_count += 1

    num_unique_token_pairs = len(all_token_pairs)

    avg_trades_per_solution = num_trades / num_solutions if num_solutions else 0

    return {
        "num_solutions": num_solutions,
        "num_trades": num_trades,
        "num_solvers": num_solvers,
        "num_unique_token_pairs": num_unique_token_pairs,
        "multi_pair_solutions": multi_pair_count,
        "single_pair_solutions": single_pair_count,
        "avg_trades_per_solution": avg_trades_per_solution,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Collect auction data with gas measurements"
    )
    parser.add_argument("--auction_start", type=int, required=True)
    parser.add_argument("--auction_end", type=int, required=True)
    parser.add_argument("--outdir", default="auction_outputs")
    parser.add_argument("--output", default="auction_gas_data.jsonl")
    parser.add_argument("--efficiency_loss", type=float, default=0.01)
    parser.add_argument("--approach", default="complete")

    parser.add_argument("--rpc", default=None)
    parser.add_argument("--pk", default=None)
    parser.add_argument("--addr", default=None)
    parser.add_argument("--force-forge", action="store_true")

    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(exist_ok=True)
    
    outdir_abs = outdir.resolve()

    print(f"Fetching auctions {args.auction_start} to {args.auction_end}...")
    solutions_batch = fetch_auctions(args.auction_start, args.auction_end)

    print("Splitting solutions")
    solutions_batch_split = [
        compute_split_solutions(sols, args.efficiency_loss, args.approach)
        for sols in solutions_batch
    ]

    print("Generating calldata files")
    for idx, solutions in enumerate(solutions_batch_split):
        bin_file = outdir_abs / f"solutions_calldata_{idx}.bin"
        encoded = encode_args(solutions)  # Args only (no selector)
        bin_file.write_bytes(encoded)

    print(f"\nBenchmarking {len(solutions_batch_split)} auctions:\n")

    results = []

    for idx, solutions in enumerate(solutions_batch_split):
        features = extract_auction_features(solutions)

        bin_file = str(outdir_abs / f"solutions_calldata_{idx}.bin")
        gas_result = benchmark_auction(
            bin_file, idx, args.rpc, args.pk, args.addr, args.force_forge
        )

        if not gas_result["success"]:
            print(f"Skipping auction {idx}: {gas_result.get('reason')}")
            continue

        gas_calldata = 4 * gas_result["zeros"] + 16 * gas_result["nonzeros"]

        gas_exec_measured = gas_result.get("gas_exec_measured")
        gas_tx_measured = gas_result.get("gas_tx_measured")

        if gas_result["method"] == "forge":
            gas_total = INTRINSIC_GAS + gas_calldata + gas_exec_measured
        else:
            gas_total = gas_tx_measured

        auction_data = {
            "auction_id": idx,
            "auction_actual_id": args.auction_start + idx,
            **features,
            "calldata_len": gas_result["calldata_len"],
            "calldata_zeros": gas_result["zeros"],
            "calldata_nonzeros": gas_result["nonzeros"],
            "gas_intrinsic": INTRINSIC_GAS,
            "gas_calldata": gas_calldata,
            "gas_exec_measured": gas_exec_measured,
            "gas_total": gas_total,
            "benchmark_method": gas_result["method"],
        }

        results.append(auction_data)

        with open(args.output, "a") as f:
            f.write(json.dumps(auction_data) + "\n")

    print(f"\n Collected data for {len(results)} auctions")
    print(f" Saved to {args.output}")

    if results:
        onchain = sum(1 for r in results if r["benchmark_method"] == "onchain")
        forge = sum(1 for r in results if r["benchmark_method"] == "forge")

        print(f"\nBenchmark Methods:")
        print(f"  On-chain: {onchain}")
        print(f"  Forge:    {forge}")

        total_gases = [r["gas_total"] for r in results]

        if total_gases:
            print(f"\nTotal Gas Statistics:")
            print(f"  Average: {sum(total_gases) / len(total_gases):,.0f}")
            print(f"  Min:     {min(total_gases):,}")
            print(f"  Max:     {max(total_gases):,}")


if __name__ == "__main__":
    main()