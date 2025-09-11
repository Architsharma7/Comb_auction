// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

library AuctionTypes {
    struct Trade {
        bytes32 id;
        address sellToken;
        address buyToken;
        uint256 score;
    }

    struct Solution {
        bytes32 id;
        address solver;
        uint256 score;
        Trade[] trades;
    }

    /**
    @dev Keyed by directed pair (sellToken,buyToken). Used only in memory.
    * key => keccak256(abi.encodePacked(sellToken,buyToken))
    * score => aggregated score for that directed pair
    */
    struct PairScore {
        bytes32 key;
        uint256 score;
    }
}
