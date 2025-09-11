// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AuctionTypes} from "./Types.sol";
import {PairKeyLib} from "./PairKeyLib.sol";

library AggregateLib {
    /**  @dev Aggregate scores by directed (sell,buy) pairs.
     * The function iterates through the trades, summing the scores for trades with the same token pair.
     * Uses an in-memory map (array + linear scan). Ordering of results is insertion
     * order (first time a pair is seen). There are no duplicate keys.
     * @param trades The trades array.
     * @return out Array of unique pair aggregates where:
        - out[i].key = keccak256(abi.encodePacked(sellToken, buyToken)) for that directed pair
        - out[i].score = sum of Trade.score over all trades with that exact (sellToken, buyToken)
    */
    function aggregatePairs(
        AuctionTypes.Trade[] calldata trades
    ) internal pure returns (AuctionTypes.PairScore[] memory out) {
        AuctionTypes.PairScore[] memory tmp = new AuctionTypes.PairScore[](
            trades.length
        );
        uint256 len = 0;

        for (uint256 i = 0; i < trades.length; ++i) {
            bytes32 k = PairKeyLib.pairKey(
                trades[i].sellToken,
                trades[i].buyToken
            );
            uint256 s = trades[i].score;

            bool found = false;
            for (uint256 j = 0; j < len; ++j) {
                if (tmp[j].key == k) {
                    tmp[j].score += s;
                    found = true;
                    break;
                }
            }
            if (!found) {
                tmp[len] = AuctionTypes.PairScore({key: k, score: s});
                len++;
            }
        }
        out = new AuctionTypes.PairScore[](len);
        for (uint256 i = 0; i < len; ++i) out[i] = tmp[i];
    }

    /** @dev Return the set of unique directed token pairs used by the given trades.
     * @param trades The trades to inspect.
     * @return keys Array of unique directed pair keys present in `trades`.
     */
    function uniquePairs(
        AuctionTypes.Trade[] calldata trades
    ) internal pure returns (bytes32[] memory keys) {
        AuctionTypes.PairScore[] memory agg = aggregatePairs(trades);
        keys = new bytes32[](agg.length);
        for (uint256 i = 0; i < agg.length; ++i) keys[i] = agg[i].key;
    }

    /** @dev Lookup the baseline (best single-pair) aggregate score for a directed token pair.
     * Intended to be used by the BaselineFilter
     * @param baselines Array of baseline entries built from single-pair solutions only.
     * @param key Directed pair key (keccak256(sellToken, buyToken)) to query.
     * @return baseline The baseline aggregate score for `key` or 0 if not found.
     */
    function lookupBaseline(
        AuctionTypes.PairScore[] memory baselines,
        bytes32 key
    ) internal pure returns (uint256) {
        for (uint256 i = 0; i < baselines.length; ++i)
            if (baselines[i].key == key) return baselines[i].score;
        return 0;
    }
}
