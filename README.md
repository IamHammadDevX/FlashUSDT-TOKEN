# FlashUSDT

FlashUSDT is a multi-network ERC-20/TRC-20 compatible token project with a Python desktop app, Hardhat deployment tooling, Solidity tests, and Python tests.

Supported networks:

- Ethereum / Sepolia
- Polygon PoS
- Binance Smart Chain
- Tron, through `FlashUSDTTron` and TronWeb deployment tooling

Important: this project deploys an independent token named FlashUSDT/FUSDT. It is not official Tether USDT. Exchange or platform listing is never automatic; listings require official review, KYC/legal review, audits, liquidity, and business approval.

## Features

- ERC-20 compatible FlashUSDT contract.
- TRC-20 compatible `FlashUSDTTron` contract with the same ABI shape.
- Owner-only mint and burn.
- Pausable transfers and mints.
- Expiry enforced on user transfers.
- Owner-only expiry extension, limited to a 3-6 month validity window.
- SafeERC20 external token recovery.
- Per-network deployment records in `flashDemotoken_generator/deployments/`.
- Python backend validation for addresses, amounts, slippage, validity, and listing requests.
- Swap transaction preparation for Uniswap V2 / QuickSwap V2 / PancakeSwap V2 compatible routers.
- Manual exchange/platform listing checklist.

## Install

```powershell
python -m pip install -r flashDemotoken_generator/requirements.txt pytest
cd flashDemotoken_generator
npm ci
```

Copy `.env.example` to `.env` in the repository root and fill in only the values you need. Do not commit private keys.

## Environment Keys

Create `.env` next to `.env.example`.

Required for real deployment:

- `PRIVATE_KEY`: EVM deployer private key. Create a dedicated MetaMask/Trust Wallet account, export its private key, and fund it with native gas token. Never use your main wallet.
- `TRON_PRIVATE_KEY`: Tron deployer private key from a dedicated TronLink wallet funded with TRX.

Recommended RPC/API values:

- `INFURA_PROJECT_ID`: create an Infura account, create a Web3 API key/project, copy the key/project ID.
- `ETHEREUM_RPC_URL`, `SEPOLIA_RPC_URL`, `POLYGON_RPC_URL`, `BSC_RPC_URL`: optional full RPC URLs from Infura, Alchemy, QuickNode, Chainstack, Ankr, or your own node.
- `TRON_PRO_API_KEY`: create a TronGrid account/API key.
- `TRON_FULL_HOST`: use `https://api.shasta.trongrid.io` for Shasta testnet first, then `https://api.trongrid.io` for mainnet.

Optional app values:

- `FLASH_USDT_ADDRESS`, `FLASH_USDT_ETHEREUM_ADDRESS`, `FLASH_USDT_POLYGON_ADDRESS`, `FLASH_USDT_BSC_ADDRESS`, `FLASH_USDT_TRON_ADDRESS`: deployed token addresses. If blank, deployment JSON files are used.
- `SEPOLIA_ROUTER_ADDRESS`, `POLYGON_ROUTER_ADDRESS`, `BSC_ROUTER_ADDRESS`, `TRON_DEX_ROUTER_ADDRESS`: DEX router addresses. Verify from official DEX docs before production.
- `FLASH_VALIDITY_MONTHS`: `3` to `6`.

## Contract Commands

```powershell
cd flashDemotoken_generator
npx hardhat compile
npx hardhat test
```

Deploy with default 6-month validity:

```powershell
npx hardhat deploy-flash --network sepolia
npx hardhat deploy-flash --network polygon
npx hardhat deploy-flash --network bsc
```

Deploy with explicit validity:

```powershell
npx hardhat deploy-flash --network polygon --months 3
```

Each deployment writes a JSON record:

```text
flashDemotoken_generator/deployments/flashusdt.<network>.json
```

## Tron Deployment

Compile first so the Tron artifact exists:

```powershell
cd flashDemotoken_generator
npx hardhat compile
npm install --save-dev tronweb
node scripts/deploy_tron.js
```

Required environment values:

```env
TRON_FULL_HOST=https://api.shasta.trongrid.io
TRON_PRIVATE_KEY=...
TRON_PRO_API_KEY=...
FLASH_VALIDITY_MONTHS=6
```

## Swap And Trade Enablement

The backend prepares swap metadata and transaction parameters, but a wallet must sign and submit the transaction.

- Ethereum: Uniswap V2-compatible router.
- Polygon: QuickSwap V2-compatible router.
- BSC: PancakeSwap V2-compatible router.
- Tron: TronTrade-compatible router via TronWeb.

Before swapping, token holder must approve router, confirm slippage/minimum output, sign the swap transaction, and monitor receipt.

## Wallets

Backend-supported wallet/provider modes:

- Private-key signing for server/test operations.
- Custom RPC providers through `web3.py`.
- WalletConnect detection for GUI integration.
- Trust Wallet, MetaMask, Coinbase Wallet, Rabby, Ledger, Trezor, and TronLink as supported GUI labels.

For browser or desktop wallet flows, keep private keys out of logs and prefer injected wallet/session signing.

## Tests

```powershell
python -m pytest
cd flashDemotoken_generator
npx hardhat test
```

Full local verification from repository root:

```powershell
.\run_local_checks.ps1
```

## GUI Test Flow

Launch desktop app:

```powershell
python flashDemotoken_generator/main.py
```

Use left panel to select Ethereum, Ethereum Sepolia, Polygon, BSC, or Tron. Choose Private Key for local signing, or select MetaMask, Trust Wallet, WalletConnect, TronLink, or Custom Provider to validate provider-mode workflow.

Main tabs:

- Generate: simulate or mint FlashUSDT when deployed address is configured.
- Swap: prepare DEX swap parameters.
- Listing: create manual exchange/platform listing checklist.
- Status: inspect chain connection, router configuration, wallet support, and remaining validity.

## Production Gates

- Use testnets first.
- Fund deployer wallets only with required gas.
- Verify contract source on explorers.
- Transfer ownership to a multisig before mainnet use.
- Run Slither/Mythril plus independent third-party audit.
- Confirm router addresses from official DEX documentation.
- Never promise exchange acceptance, official USDT status, guaranteed value, or real-world liquidity.
