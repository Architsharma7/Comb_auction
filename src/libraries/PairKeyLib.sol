// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

library PairKeyLib {
    function pairKey(
        address sell,
        address buy
    ) internal pure returns (bytes32) {
        return keccak256(abi.encodePacked(sell, buy));
    }
}
