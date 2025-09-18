import argparse
from dataclasses import asdict
import json, pathlib
from fetch import fetch_auctions, compute_split_solutions
from mechanism import (
    FilterRankRewardMechanism,
    BaselineFilter,
    DirectedTokenPairs,
    DirectSelection,
    NoReward,
    SubsetFilteringSelection,
    run_counter_factual_winners
)
from typing import List, Tuple
from eth_abi import encode
from eth_utils import keccak, to_checksum_address

def solution_to_jsonable(sol):
    return {
        "id": sol.id,                          
        "solver": sol.solver,                  
        "score": int(sol.score),
        "trades": [
            {
                "id": t.id,                    
                "sellToken": t.sell_token,     
                "buyToken": t.buy_token,       
                "score": int(t.score),
            }
            for t in sol.trades
        ],
    }
    
def trade_to_abi_tuple(t) -> Tuple[str, str, str, int]:
    # (string id, address sellToken, address buyToken, uint256 score)
    return (
        str(t.id),
        to_checksum_address(t.sell_token),
        to_checksum_address(t.buy_token),
        int(t.score),
    )

def solution_to_abi_tuple(s) -> Tuple[str, str, int, List[Tuple[str, str, str, int]]]:
    # (string id, address solver, uint256 score, (Trade[]) )
    return (
        str(s.id),
        to_checksum_address(s.solver),
        int(s.score),
        [trade_to_abi_tuple(t) for t in s.trades],
    )
    
_S_TRADE = "(string,address,address,uint256)"
_S_SOLUTION = f"(string,address,uint256,{_S_TRADE}[])"
_S_SOLUTION_ARR = f"{_S_SOLUTION}[]"
    
def encode_selectWinners_args(solutions) -> bytes:
    """ABI-encode ONLY the argument: (Solution[])"""
    abi_solutions = [solution_to_abi_tuple(s) for s in solutions]
    return encode([_S_SOLUTION_ARR], [abi_solutions])


def encode_winners_reference(winners) -> bytes:
    """ABI-encode reference (Solution[]) for Foundry test comparison"""
    abi_winners = [solution_to_abi_tuple(s) for s in winners]
    return encode([_S_SOLUTION_ARR], [abi_winners])


def main():
    """Main function to run winner selection."""
    parser = argparse.ArgumentParser(
        description="Run winner selection on auction solutions."
    )
    parser.add_argument(
        "--auction_start",
        type=int,
        default=10322553 - 50000,
        help="Start block for fetching auctions (default: 10322553 - 50000)",
    )
    parser.add_argument(
        "--auction_end",
        type=int,
        default=10322553,
        help="End block for fetching auctions (default: 10322553)",
    )
    parser.add_argument(
        "--efficiency_loss",
        type=float,
        default=0.01,
        help="Efficiency loss parameter (default: 0.01)",
    )
    parser.add_argument(
        "--approach",
        type=str,
        default="complete",
        help="Approach type for solution splitting (default: complete)",
    )
    parser.add_argument(
        "--auction_index",
        type=int,
        default=1987,
        help="Index of the auction to analyze (default: 1987)",
    )
    parser.add_argument(
        "--outdir",
        type=str,
        default="auction_outputs",
        help="Output directory for files"
    )
    
    args = parser.parse_args()
    outdir = pathlib.Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    auction_start = args.auction_start
    auction_end = args.auction_end
    auction_id = args.auction_index
    print(f"Fetching auctions from {auction_start} to {auction_end}...")
    solutions_batch = fetch_auctions(auction_start, auction_end)
    print(f"single auction solutions for {auction_id} auction index:", solutions_batch[auction_id])
    efficiency_loss = args.efficiency_loss
    approach = args.approach
    print(
        f"Splitting solutions with efficiency loss {efficiency_loss} "
        f'and approach "{approach}"...'
    )
    solutions_batch_split = [
        compute_split_solutions(
            solutions, efficiency_loss=efficiency_loss, approach=approach
        )
        for solutions in solutions_batch
    ]
    print(f"Done fetching and splitting solutions. Solutions after split for {auction_id} auction index:")
    print(solutions_batch_split[auction_id])
    
    mechanism = FilterRankRewardMechanism(
        solution_filter=BaselineFilter(),
        winner_selection=DirectSelection(
        SubsetFilteringSelection(batch_compatibility=DirectedTokenPairs(),
                                 cumulative_filtering=False)
        ),
        reward_mechanism=NoReward(),   
    )

    winners_single_auction = run_counter_factual_winners(
        [solutions_batch_split[auction_id]],
        mechanism,
        remove_executed_orders=True
    )
    winners = winners_single_auction[0]
    
    print(f"Winners for auction index {auction_id}:", winners)
    
    payload = {
    "solutions_batch":       [solution_to_jsonable(s) for s in solutions_batch[auction_id]],
    "solutions_batch_split": [solution_to_jsonable(s) for s in solutions_batch_split[auction_id]],
    "winners_python":        [solution_to_jsonable(s) for s in winners],
    }
    
    out = pathlib.Path(f"auction_snapshot_{auction_id}.json")
    out.write_text(json.dumps(payload, indent=2))
    print("Wrote", out)
    
    split_args = encode_selectWinners_args(solutions_batch_split[auction_id])
    split_args_path = outdir / f"solutions_calldata_{auction_id}.bin"
    split_args_path.write_bytes(split_args)
    print("Wrote ARGS:", split_args_path, f"(len={len(split_args)})")
    
    winners_ref = encode_winners_reference(winners)
    winners_bin_path = outdir / f"winners_python_{auction_id}.bin"
    winners_bin_path.write_bytes(winners_ref)
    print("Wrote REF:", winners_bin_path, f"(len={len(winners_ref)})")
    
    
if __name__ == "__main__":
    main()