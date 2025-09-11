// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AuctionTypes} from "./Types.sol";
import {AggregateLib} from "./AggregateLib.sol";

library BaselineFilterLib {
    using AggregateLib for AuctionTypes.Trade[];

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
            uint256 v = agg[0].score;

            bool found = false;
            for (uint256 j = 0; j < blen; ++j) {
                if (tmp[j].key == k) {
                    if (v > tmp[j].score) tmp[j].score = v;
                    found = true;
                    break;
                }
            }
            if (!found) {
                tmp[blen] = AuctionTypes.PairScore({key: k, score: v});
                blen++;
            }
        }

        trimmed = new AuctionTypes.PairScore[](blen);
        for (uint256 i = 0; i < blen; ++i) trimmed[i] = tmp[i];
    }

    function keepMask(
        AuctionTypes.Solution[] calldata solutions,
        AuctionTypes.PairScore[] memory baselines
    ) internal pure returns (bool[] memory mask) {
        mask = new bool[](solutions.length);

        for (uint256 i = 0; i < solutions.length; ++i) {
            AuctionTypes.PairScore[] memory agg = solutions[i]
                .trades
                .aggregatePairs();

            if (agg.length == 1) {
                mask[i] = true;
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
            mask[i] = ok;
        }
    }
}
