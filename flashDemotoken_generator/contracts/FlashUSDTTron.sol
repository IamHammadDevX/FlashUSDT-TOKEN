// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "./FlashUSDT.sol";

/**
 * @title FlashUSDTTron
 * @notice TRC-20 compatible deployment target. TRC-20 mirrors ERC-20's ABI, so
 *         this contract keeps the same callable surface for Tron deployments.
 *         Name: Tether USD, Symbol: USDT, Decimals: 6.
 */
contract FlashUSDTTron is FlashUSDT {
    constructor(uint256 initialSupply) FlashUSDT(initialSupply) {}
}
