// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AuctionTypes} from "./Types.sol";
import {AggregateLib} from "./AggregateLib.sol";

library SubsetFilterLib {
    /**
     * @dev Sort by total score (descending) and keep only eligible items.
     * Builds an identity index array [0..n-1], insertion-sorts it by solutions[i].score
     * Applies the isKept[i] flags to that order and returns the filtered indices
     * @param solutions Candidate solutions (read from calldata for scores)
     * @param isKept Eligibility flags parallel to solutions (true = keep)
     * @return kept Indices into solutions in score-desc order, filtered by isKept
     */
    function sortAndCompose(
        AuctionTypes.Solution[] calldata solutions,
        bool[] memory isKept
    ) internal pure returns (uint256[] memory kept) {
        uint256 n = solutions.length;

        uint256[] memory idx = new uint256[](n);
        for (uint256 i = 0; i < n; ++i) idx[i] = i;

        for (uint256 i = 1; i < n; ++i) {
            uint256 key = idx[i];
            uint256 j = i;
            while (j > 0) {
                uint256 prevIdx = idx[j - 1];
                if (solutions[prevIdx].score >= solutions[key].score) break;
                idx[j] = prevIdx;
                --j;
            }
            idx[j] = key;
        }

        uint256 k;
        for (uint256 i = 0; i < n; ++i) if (isKept[idx[i]]) ++k;

        kept = new uint256[](k);
        uint256 p;
        for (uint256 i = 0; i < n; ++i) {
            uint256 ix = idx[i];
            if (isKept[ix]) {
                kept[p] = ix;
                ++p;
            }
        }
    }

    /**
     * @dev Full greedy-selection with fairness filtering
     * Sort by score and drop ineligible indices (isKept)
     * Greedy pick in that order subject to DirectedTokenPairs compatibility:
     * For each candidate, compute unique (sell,buy) keys
     * - Select iff none of those keys were used by previous winners
     * - Non-cumulative: only selected winners reserve keys
     * @param solutions Candidate solutions (calldata)
     * @param isKept Eligibility flags parallel to solutions (e.g., from baseline filter)
     * @return winners Indices into solutions of selected winners in pick order
     */
    function select_solutions(
        AuctionTypes.Solution[] calldata solutions,
        bool[] memory isKept
    ) internal pure returns (uint256[] memory winners) {
        uint256[] memory kept = sortAndCompose(solutions, isKept);

        uint256 cap;
        for (uint256 c = 0; c < kept.length; ++c)
            cap += solutions[kept[c]].trades.length;
        bytes32[] memory used = new bytes32[](cap);
        uint256 ulen = 0;

        uint256[] memory tmp = new uint256[](kept.length);
        uint256 wlen = 0;

        for (uint256 ci = 0; ci < kept.length; ++ci) {
            uint256 i = kept[ci];

            bytes32[] memory pairs = AggregateLib.uniquePairs(
                solutions[i].trades
            );

            bool conflict = false;
            for (uint256 a = 0; a < pairs.length && !conflict; ++a) {
                for (uint256 b = 0; b < ulen; ++b) {
                    if (pairs[a] == used[b]) {
                        conflict = true;
                        break;
                    }
                }
            }

            if (!conflict) {
                tmp[wlen++] = i;
                for (uint256 a = 0; a < pairs.length; ++a)
                    used[ulen++] = pairs[a];
            }
        }

        winners = new uint256[](wlen);
        for (uint256 k = 0; k < wlen; ++k) winners[k] = tmp[k];
    }
}
