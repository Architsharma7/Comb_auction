// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test, console2} from "forge-std/Test.sol";
import {Combinatorial} from "../src/Combinatorial.sol";
import {AuctionTypes} from "../src/libraries/Types.sol";

contract CombinatorialAuctionTest is Test {
    Combinatorial internal comb;

    function setUp() public {
        comb = new Combinatorial();
    }

    function test_SelectWinners_matchesPython() public view {
        string memory pathSplit = vm.envString("RELATIVE_BIN_SOLUTIONS");
        string memory pathWinners = vm.envString("RELATIVE_BIN_WINNERS");

        bytes memory rawSplit = vm.readFileBinary(pathSplit);
        bytes memory rawPyWin = vm.readFileBinary(pathWinners);

        AuctionTypes.Solution[] memory splitSols = abi.decode(
            rawSplit,
            (AuctionTypes.Solution[])
        );
        AuctionTypes.Solution[] memory winnersPython = abi.decode(
            rawPyWin,
            (AuctionTypes.Solution[])
        );

        AuctionTypes.Solution[] memory winnersSol = comb.selectWinners(
            splitSols
        );

        console2.log("\n==== Solidity winners ====");
        console2.log("count:");
        console2.logUint(winnersSol.length);
        for (uint256 i = 0; i < winnersSol.length; i++) {
            console2.log("Solution:");
            console2.log(winnersSol[i].id);
            console2.log("solver:");
            console2.logAddress(winnersSol[i].solver);
            console2.log("score:");
            console2.logUint(winnersSol[i].score);
            for (uint256 t = 0; t < winnersSol[i].trades.length; t++) {
                console2.log("trade id:");
                console2.log(winnersSol[i].trades[t].id);
                console2.log("sell:");
                console2.logAddress(winnersSol[i].trades[t].sellToken);
                console2.log("buy:");
                console2.logAddress(winnersSol[i].trades[t].buyToken);
                console2.log("score:");
                console2.logUint(winnersSol[i].trades[t].score);
            }
        }

        console2.log("\n==== Python winners ====");
        console2.log("count:");
        console2.logUint(winnersPython.length);
        for (uint256 i = 0; i < winnersPython.length; i++) {
            console2.log("Solution:");
            console2.log(winnersPython[i].id);
            console2.log("solver:");
            console2.logAddress(winnersPython[i].solver);
            console2.log("score:");
            console2.logUint(winnersPython[i].score);
            for (uint256 t = 0; t < winnersPython[i].trades.length; t++) {
                console2.log("tradeid:");
                console2.log(winnersPython[i].trades[t].id);
                console2.log("sell:");
                console2.logAddress(winnersPython[i].trades[t].sellToken);
                console2.log("buy:");
                console2.logAddress(winnersPython[i].trades[t].buyToken);
                console2.log("score:");
                console2.logUint(winnersPython[i].trades[t].score);
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
                    winnersSol[i].trades[t].id,
                    winnersPython[i].trades[t].id,
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
