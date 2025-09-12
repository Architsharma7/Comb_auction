// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AuctionTypes} from "./libraries/Types.sol";
import {BaselineFilterLib} from "./libraries/BaselineFilterLib.sol";
import {SubsetFilterLib} from "./libraries/SubsetFilterLib.sol";

contract Combinatorial {
    function selectWinners(
        AuctionTypes.Solution[] calldata solutions
    ) external pure returns (AuctionTypes.Solution[] memory winners) {
        if (solutions.length == 0) {
            revert("No solutions");
        }

        AuctionTypes.PairScore[] memory baselines = BaselineFilterLib
            .buildBaselines(solutions);

        bool[] memory isKept = BaselineFilterLib.baselineFilter(
            solutions,
            baselines
        );

        uint256[] memory idxWinners = SubsetFilterLib.select_solutions(
            solutions,
            isKept
        );

        winners = new AuctionTypes.Solution[](idxWinners.length);
        for (uint256 w = 0; w < idxWinners.length; ++w) {
            uint256 i = idxWinners[w];

            uint256 tlen = solutions[i].trades.length;
            AuctionTypes.Trade[] memory copiedTrades = new AuctionTypes.Trade[](
                tlen
            );
            for (uint256 t = 0; t < tlen; ++t) {
                copiedTrades[t] = AuctionTypes.Trade({
                    id: solutions[i].trades[t].id,
                    sellToken: solutions[i].trades[t].sellToken,
                    buyToken: solutions[i].trades[t].buyToken,
                    score: solutions[i].trades[t].score
                });
            }

            winners[w] = AuctionTypes.Solution({
                id: solutions[i].id,
                solver: solutions[i].solver,
                score: solutions[i].score,
                trades: copiedTrades
            });
        }
    }
}
