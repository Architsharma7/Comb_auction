// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test, console2, stdJson} from "forge-std/Test.sol";
import {Combinatorial} from "../src/Combinatorial.sol";
import {AuctionTypes} from "../src/libraries/Types.sol";

contract CombinatorialAuctionTest is Test {
    Combinatorial internal comb;

    struct TradeJSON {
        address buyToken;
        string id;
        uint256 score;
        address sellToken;
    }

    struct SolutionJSON {
        string id;
        uint256 score;
        address solver;
        TradeJSON[] trades;
    }

    function setUp() public {
        comb = new Combinatorial();
    }

    function test_SelectWinners_matchesPython() public view {
        string memory path = vm.envString("RELATIVE_SNAP_PATH");
        string memory json = vm.readFile(path);

        bytes memory rawSplit = vm.parseJson(json, ".solutions_batch_split");
        SolutionJSON[] memory splitSolsJSON = abi.decode(
            rawSplit,
            (SolutionJSON[])
        );

        AuctionTypes.Solution[] memory splitSols = new AuctionTypes.Solution[](
            splitSolsJSON.length
        );
        for (uint256 i = 0; i < splitSolsJSON.length; i++) {
            TradeJSON[] memory tj = splitSolsJSON[i].trades;
            AuctionTypes.Trade[] memory trades = new AuctionTypes.Trade[](
                tj.length
            );
            for (uint256 t = 0; t < tj.length; t++) {
                trades[t] = AuctionTypes.Trade({
                    id: tj[t].id,
                    sellToken: tj[t].sellToken,
                    buyToken: tj[t].buyToken,
                    score: tj[t].score
                });
            }
            splitSols[i] = AuctionTypes.Solution({
                id: splitSolsJSON[i].id,
                solver: splitSolsJSON[i].solver,
                score: splitSolsJSON[i].score,
                trades: trades
            });
        }

        bytes memory rawWinners = vm.parseJson(json, ".winners_python");
        SolutionJSON[] memory winnersJSON = abi.decode(
            rawWinners,
            (SolutionJSON[])
        );

        AuctionTypes.Solution[]
            memory winnersPython = new AuctionTypes.Solution[](
                winnersJSON.length
            );
        for (uint256 i = 0; i < winnersJSON.length; i++) {
            TradeJSON[] memory tj = winnersJSON[i].trades;
            AuctionTypes.Trade[] memory trades = new AuctionTypes.Trade[](
                tj.length
            );
            for (uint256 t = 0; t < tj.length; t++) {
                trades[t] = AuctionTypes.Trade({
                    id: tj[t].id,
                    sellToken: tj[t].sellToken,
                    buyToken: tj[t].buyToken,
                    score: tj[t].score
                });
            }
            winnersPython[i] = AuctionTypes.Solution({
                id: winnersJSON[i].id,
                solver: winnersJSON[i].solver,
                score: winnersJSON[i].score,
                trades: trades
            });
        }

        console2.log("PYTHON winners");
        console2.log("count", winnersPython.length);
        for (uint256 i = 0; i < winnersPython.length; i++) {
            console2.log("id", winnersPython[i].id);
            console2.log("solver", winnersPython[i].solver);
            console2.log("score", vm.toString(winnersPython[i].score));
            console2.log("trades", winnersPython[i].trades.length);
            for (uint256 t = 0; t < winnersPython[i].trades.length; t++) {
                console2.log("trade", t);
                console2.log("id", winnersPython[i].trades[t].id);
                console2.log("sell", winnersPython[i].trades[t].sellToken);
                console2.log("buy ", winnersPython[i].trades[t].buyToken);
                console2.log(
                    "score",
                    vm.toString(winnersPython[i].trades[t].score)
                );
            }
        }

        AuctionTypes.Solution[] memory winnersSol = comb.selectWinners(
            splitSols
        );

        console2.log("SOLIDITY winners");
        console2.log("count", winnersSol.length);
        for (uint256 i = 0; i < winnersSol.length; i++) {
            console2.log("id", winnersSol[i].id);
            console2.log("solver", winnersSol[i].solver);
            console2.log("score", vm.toString(winnersSol[i].score));
            console2.log("trades", winnersSol[i].trades.length);
            for (uint256 t = 0; t < winnersSol[i].trades.length; t++) {
                console2.log("id", winnersSol[i].trades[t].id);
                console2.log("sell", winnersSol[i].trades[t].sellToken);
                console2.log("buy ", winnersSol[i].trades[t].buyToken);
                console2.log(
                    "score",
                    vm.toString(winnersSol[i].trades[t].score)
                );
            }
        }

        assertEq(winnersSol.length, winnersPython.length, "winner length");

        for (uint256 i = 0; i < winnersSol.length; i++) {
            assertEq(winnersSol[i].score, winnersPython[i].score, "score");
            assertEq(winnersSol[i].solver, winnersPython[i].solver, "solver");
            assertEq(
                keccak256(bytes(winnersSol[i].id)),
                keccak256(bytes(winnersPython[i].id)),
                "solution id"
            );

            assertEq(
                winnersSol[i].trades.length,
                winnersPython[i].trades.length,
                "trade len"
            );
            for (uint256 t = 0; t < winnersSol[i].trades.length; t++) {
                assertEq(
                    keccak256(bytes(winnersSol[i].trades[t].id)),
                    keccak256(bytes(winnersPython[i].trades[t].id)),
                    "trade id"
                );
                assertEq(
                    winnersSol[i].trades[t].sellToken,
                    winnersPython[i].trades[t].sellToken,
                    "sell"
                );
                assertEq(
                    winnersSol[i].trades[t].buyToken,
                    winnersPython[i].trades[t].buyToken,
                    "buy"
                );
                assertEq(
                    winnersSol[i].trades[t].score,
                    winnersPython[i].trades[t].score,
                    "trade score"
                );
            }
        }
    }
}
