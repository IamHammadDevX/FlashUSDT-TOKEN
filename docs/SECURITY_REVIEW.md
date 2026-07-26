# FlashUSDT Internal Security Review

This document is an internal pre-audit checklist. It is not a replacement for an independent third-party audit.

## Reviewed Controls

- Owner-only mint and burn.
- ReentrancyGuard on mint, burn, and ERC-20 rescue operations.
- Pausable mint/transfer path.
- Expiry cannot be set in the past.
- Expiry extension is bounded to the 3-6 month validity window.
- User transfers revert after expiry.
- External ERC-20 recovery uses SafeERC20.
- Flash holder status is cleared when balance reaches zero and set on mint/transfer receipt.
- Python backend validates amount, slippage, EVM addresses, Tron addresses, and validity choices.
- Deployment writes per-network JSON records instead of mutating secrets.

## Production Deployment Gates

- Use a multisig owner before mainnet deployment.
- Verify source code on each chain explorer.
- Run Slither/Mythril or equivalent static analysis.
- Run a professional third-party audit and remediate findings.
- Confirm router addresses from official DEX documentation before enabling swaps.
- Keep deployer and owner keys separate.
- Rehearse pause, unpause, expiry extension, mint, burn, and rescue flows on testnets.

## Known External Dependencies

- Exchange listings require official platform review and cannot be automated.
- WalletConnect and injected-wallet signing require GUI/session adapter work for real wallet transaction signing.
- Tron deployment requires TronWeb, a funded Tron wallet, and TronGrid/Shasta access.
