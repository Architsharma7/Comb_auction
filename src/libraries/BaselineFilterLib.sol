// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AuctionTypes} from "./Types.sol";
import {AggregateLib} from "./AggregateLib.sol";

library BaselineFilterLib {
    using AggregateLib for AuctionTypes.Trade[];

    /** 
    @dev Build per-pair baseline scores from the input solutions.
    * - Only single-pair solutions (i.e. those whose aggregate has length 1) contribute
    *   to the baseline, multi-pair solutions are ignored.
    * - For each directed pair key, keeps the maximum aggregated score observed among
    *   single-pair solutions.
    * - If no single-pair solution exists for a pair, that pair does not appear in the result
    *   (equivalent to a baseline score of 0 for filtering).
    * @param solutions Candidate solutions.
    * @return trimmed Array of baseline entries where:
    *         - trimmed[i].key is the directed pair key (sell, buy)
    *         - trimmed[i].score is the best single-pair aggregate score for that pair.
    */
    function buildBaselines(
        AuctionTypes.Solution[] calldata solutions
    ) internal pure returns (AuctionTypes.PairScore[] memory trimmed) {
        AuctionTypes.PairScore[] memory tmp = new AuctionTypes.PairScore[](
            solutions.length
        );
        uint256 blen = 0;

        for (uint256 i = 0; i < solutions.length; ++i) {
            AuctionTypes.PairScore[] memory agg = solutions[i]
                .trades
                .aggregatePairs();
            if (agg.length != 1) continue;

            bytes32 k = agg[0].key;
            uint256 s = agg[0].score;

            bool found = false;
            for (uint256 j = 0; j < blen; ++j) {
                if (tmp[j].key == k) {
                    if (s > tmp[j].score) tmp[j].score = s;
                    found = true;
                    break;
                }
            }
            if (!found) {
                tmp[blen] = AuctionTypes.PairScore({key: k, score: s});
                blen++;
            }
        }

        trimmed = new AuctionTypes.PairScore[](blen);
        for (uint256 i = 0; i < blen; ++i) trimmed[i] = tmp[i];
    }

    /**
    @dev Returns a pass/fail flag for each input solution.
    * For each solution:
    *  - Aggregate trades per directed pair via AggregateLib.aggregatePairs().
    *  - Single-pair: solutions always pass (true).
    *  - Multi-pair: solutions pass iff every directed pair’s aggregate score is
    *    >= that pair’s baseline score. Baselines are looked up, missing entries are treated as 0.
    * @param solutions Candidate solutions.
    * @param baselines Baseline entries {key, bestScore} from single-pair solutions.
    * @return isKept Boolean flags indicating which solutions[i] pass the baseline filter.
    */
    function baselineFilter(
        AuctionTypes.Solution[] calldata solutions,
        AuctionTypes.PairScore[] memory baselines
    ) internal pure returns (bool[] memory isKept) {
        isKept = new bool[](solutions.length);

        for (uint256 i = 0; i < solutions.length; ++i) {
            AuctionTypes.PairScore[] memory agg = solutions[i]
                .trades
                .aggregatePairs();

            if (agg.length == 1) {
                isKept[i] = true;
                continue;
            }

            bool ok = true;
            for (uint256 j = 0; j < agg.length; ++j) {
                if (
                    agg[j].score <
                    AggregateLib.lookupBaseline(baselines, agg[j].key)
                ) {
                    ok = false;
                    break;
                }
            }
            isKept[i] = ok;
        }
    }
}
