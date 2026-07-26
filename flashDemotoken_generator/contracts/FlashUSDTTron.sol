// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./FlashUSDT.sol";

/**
 * @title FlashUSDTTron
 * @notice TRC-20 compatible deployment target. TRC-20 mirrors ERC-20's ABI, so
 *         this contract keeps the same callable surface for Tron deployments.
 */
contract FlashUSDTTron is FlashUSDT {
    constructor(
        string memory name_,
        string memory symbol_,
        uint256 expiry_
    ) FlashUSDT(name_, symbol_, expiry_) {}
}
