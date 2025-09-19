// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import {Combinatorial} from "../src/Combinatorial.sol";

contract SelectWinnersBenchmark is Test {
    bytes4 constant SELECT_WINNERS_SEL =
        bytes4(
            keccak256(
                "selectWinners((string,address,uint256,(string,address,address,uint256)[])[])"
            )
        );

    Combinatorial comb;

    // ENV example:
    // RELATIVE_BIN_SOLUTIONS=./data/auction_outputs/solutions_calldata_1987.bin
    function setUp() public {
        comb = new Combinatorial();
    }

    function test_selectWinners_gas() public view {
        string memory binPath = vm.envString("RELATIVE_BIN_SOLUTIONS");

        bytes memory rawArgs = vm.readFileBinary(binPath);

        bytes memory txData = abi.encodePacked(SELECT_WINNERS_SEL, rawArgs);

        (bool ok /* bytes memory ret */, ) = address(comb).staticcall(txData);
        require(ok, "selectWinners failed");

        console2.log("bin:", binPath);
        console2.log("calldata_len:", txData.length);
    }

    function _envUint(string memory k) external view returns (uint256) {
        return vm.envUint(k);
    }
}
