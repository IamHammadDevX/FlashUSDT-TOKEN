# FlashUSDT — USDT Clone

A multi-network **Tether USD (USDT) clone** with owner mint/burn. The contract mirrors real USDT:
**name: "Tether USD"**, **symbol: "USDT"**, **decimals: 6**, and the official Trust Wallet logo URI.

Once the contract address is added to MetaMask (one-time), it displays identically to real USDT with logo.

> ⚠️ This is an independent token — NOT official Tether USDT. Exchange listing requires
> official review, KYC, audits, liquidity, and business approval.

## Features

- **USDT-compatible** — name `Tether USD`, symbol `USDT`, decimals `6`, official logo URI.
- **Owner-only mint** — deployer can mint tokens to any address.
- **Public burn** — anyone can burn their own tokens.
- **No expiry** — tokens are valid permanently (no expiry mechanism).
- **ERC-20 / TRC-20** — works on Ethereum, Polygon, BSC, and Tron.
- **Per-network deployment records** in `flashDemotoken_generator/deployments/`.
- **Desktop GUI** — mint, transfer, swap preparation, listing checklist.
- **Swap preparation** for Uniswap V2 / QuickSwap V2 / PancakeSwap V2 routers.

## Install

```powershell
python -m pip install -r flashDemotoken_generator/requirements.txt pytest
cd flashDemotoken_generator
npm ci
```

Copy `.env.example` to `.env` in the repository root and fill in only the values you need.

> **MetaMask note:** After deployment, each receiver must add the token contract address
> in MetaMask **once**. After that, it shows as "Tether USD" with the official logo
> permanently. This is required for ANY custom token — MetaMask cannot auto-discover
> new contracts.

## Environment Keys

Create `.env` next to `.env.example`.

Required for deployment:

- `PRIVATE_KEY`: EVM deployer private key. Fund with native gas.
- `TRON_PRIVATE_KEY`: Tron deployer private key funded with TRX.

Recommended RPC/API values:

- `INFURA_PROJECT_ID`, `ETHERSCAN_API_KEY`, `POLYGONSCAN_API_KEY`, `BSCSCAN_API_KEY`
- `ETHEREUM_RPC_URL`, `SEPOLIA_RPC_URL`, `POLYGON_RPC_URL`, `BSC_RPC_URL`
- `TRON_PRO_API_KEY`, `TRON_FULL_HOST`

Optional:

- `FLASH_USDT_ADDRESS`, `FLASH_USDT_ETHEREUM_ADDRESS`, `FLASH_USDT_POLYGON_ADDRESS`, `FLASH_USDT_BSC_ADDRESS`, `FLASH_USDT_TRON_ADDRESS`
- `SEPOLIA_ROUTER_ADDRESS`, `POLYGON_ROUTER_ADDRESS`, `BSC_ROUTER_ADDRESS`, `TRON_DEX_ROUTER_ADDRESS`

## Contract Commands

```powershell
cd flashDemotoken_generator
npx hardhat compile
npx hardhat test
```

Deploy:

```powershell
npx hardhat deploy-flash --network sepolia
npx hardhat deploy-flash --network polygon
npx hardhat deploy-flash --network bsc
```

Each deployment writes:

```text
flashDemotoken_generator/deployments/flashusdt.<network>.json
```

Verify:

```powershell
npm run verify:v2 -- sepolia
```

## Tron Deployment

```powershell
cd flashDemotoken_generator
npx hardhat compile
node scripts/deploy_tron.js
```

```env
TRON_FULL_HOST=https://api.shasta.trongrid.io
TRON_PRIVATE_KEY=...
TRON_PRO_API_KEY=...
```

After deployment:

```powershell
npm run tron:info
npm run tron:mint -- TRecipientAddress 100
npm run tron:balance -- TRecipientAddress
```

## Swap Support

- Ethereum: Uniswap V2
- Polygon: QuickSwap V2
- BSC: PancakeSwap V2
- Tron: TronTrade-compatible router

## Tests

```powershell
python -m pytest
cd flashDemotoken_generator
npx hardhat test
```

Full local verification:

```powershell
.\run_local_checks.ps1
```

## GUI

```powershell
python flashDemotoken_generator/main.py
```

Tabs: Generate (mint), Transfer, Swap (prepare), Listing (checklist), Status.

## Production Gates

- Use testnets first.
- Verify contract source on explorers.
- Transfer ownership to a multisig before mainnet.
- Run Slither/Mythril + third-party audit.
- Never promise exchange acceptance or official USDT status.
