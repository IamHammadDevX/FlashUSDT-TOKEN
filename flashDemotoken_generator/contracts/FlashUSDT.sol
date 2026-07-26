// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title FlashUSDT
 * @notice ERC-20 compatible token with owner-controlled mint/burn and a global
 *         expiry window. Transfers are blocked after expiry or while paused.
 */
contract FlashUSDT is ERC20, Ownable, Pausable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    uint256 public constant MIN_VALIDITY = 90 days;
    uint256 public constant MAX_VALIDITY = 180 days;

    uint256 public expiry;
    mapping(address => bool) public isFlash;

    event FlashCreated(address indexed to, uint256 amount, uint256 expiry);
    event ExpiryUpdated(uint256 previousExpiry, uint256 newExpiry);
    event ExternalTokenRecovered(address indexed token, address indexed to, uint256 amount);

    constructor(
        string memory name_,
        string memory symbol_,
        uint256 _expiry
    ) ERC20(name_, symbol_) Ownable(msg.sender) {
        _validateExpiry(_expiry);
        expiry = _expiry;
    }

    function mint(address to, uint256 amount) external onlyOwner nonReentrant whenNotPaused {
        require(to != address(0), "FlashUSDT: recipient is zero address");
        require(amount > 0, "FlashUSDT: amount is zero");
        require(!isExpired(), "FlashUSDT: token is expired");

        _mint(to, amount);
        isFlash[to] = true;
        emit FlashCreated(to, amount, expiry);
    }

    function burn(address from, uint256 amount) external onlyOwner nonReentrant {
        require(from != address(0), "FlashUSDT: account is zero address");
        require(amount > 0, "FlashUSDT: amount is zero");

        _burn(from, amount);
        if (balanceOf(from) == 0) {
            isFlash[from] = false;
        }
    }

    function setExpiry(uint256 newExpiry) external onlyOwner {
        require(newExpiry > expiry, "FlashUSDT: expiry can only be extended");
        _validateExpiry(newExpiry);

        uint256 previousExpiry = expiry;
        expiry = newExpiry;
        emit ExpiryUpdated(previousExpiry, newExpiry);
    }

    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }

    function rescueERC20(address token, address to, uint256 amount) external onlyOwner nonReentrant {
        require(token != address(this), "FlashUSDT: cannot rescue self");
        require(to != address(0), "FlashUSDT: recipient is zero address");
        require(amount > 0, "FlashUSDT: amount is zero");

        IERC20(token).safeTransfer(to, amount);
        emit ExternalTokenRecovered(token, to, amount);
    }

    function isExpired() public view returns (bool) {
        return block.timestamp >= expiry;
    }

    function getExpiry() public view returns (uint256) {
        return expiry;
    }

    function _validateExpiry(uint256 newExpiry) internal view {
        require(newExpiry > block.timestamp, "FlashUSDT: expiry must be in the future");
        uint256 validity = newExpiry - block.timestamp;
        require(validity >= MIN_VALIDITY, "FlashUSDT: validity below 3 months");
        require(validity <= MAX_VALIDITY, "FlashUSDT: validity above 6 months");
    }

    function _update(address from, address to, uint256 value) internal override whenNotPaused {
        if (from != address(0) && to != address(0)) {
            require(!isExpired(), "FlashUSDT: token is expired");
        }
        super._update(from, to, value);

        if (from != address(0) && balanceOf(from) == 0) {
            isFlash[from] = false;
        }
        if (to != address(0) && value > 0) {
            isFlash[to] = true;
        }
    }
}
