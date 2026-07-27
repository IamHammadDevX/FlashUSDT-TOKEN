"""Blockchain access layer for FlashUSDT."""
import hashlib
import logging
import os
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import requests
from web3 import Web3
try:
    from web3.auto import w3 as auto_w3
except Exception:
    auto_w3 = None

from config import (
    ALL_PLATFORMS,
    CHAIN_IDS,
    COMPATIBILITY_MATRIX,
    DEX_ROUTERS,
    FLASH_USDT_ABI,
    NATIVE_SYMBOLS,
    ROUTER_ABI,
    RPC_URLS,
    RPC_URLS_FALLBACK,
    SUPPORTED_WALLETS,
    USDT_ABI,
    USDT_ADDRESSES,
    VALIDITY_MAP,
    load_deployed_flash_address,
)

logger = logging.getLogger(__name__)


@dataclass
class WalletInfo:
    address: str
    network: str
    balance: float = 0.0
    usdt_balance: float = 0.0
    wallet_type: str = "Private Key"


@dataclass
class GeneratedToken:
    tx_hash: str
    token_address: str
    network: str
    sender: str
    recipient: str
    amount: float
    timestamp: int
    expiry: int
    validity_months: int
    status: str = "valid"

    def is_valid(self) -> bool:
        return int(time.time()) < self.expiry

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SwapRequest:
    network: str
    dex: str
    router: str
    from_token: str
    to_token: str
    amount: float
    slippage: float
    status: str
    instructions: str
    tx_hash: Optional[str] = None


class EVMChainManager:
    """Manages Ethereum, Polygon, and BSC compatible networks."""

    def __init__(self, network: str):
        self.network = network
        self.w3: Optional[Web3] = None
        self._connect()

    def _connect(self):
        for url in [RPC_URLS.get(self.network), RPC_URLS_FALLBACK.get(self.network)]:
            if not url:
                continue
            w3 = Web3(Web3.HTTPProvider(url, request_kwargs={"timeout": 15}))
            if w3.is_connected():
                self.w3 = w3
                logger.info("Connected to %s via %s", self.network, url)
                return
        raise ConnectionError(f"Could not connect to {self.network}")

    def is_connected(self) -> bool:
        return self.w3 is not None and self.w3.is_connected()

    def derive_address(self, private_key: str) -> str:
        key = normalize_private_key(private_key)
        return self.w3.eth.account.from_key(key).address

    def get_balances(self, address: str) -> dict:
        checksum_address = validate_evm_address(address)
        native_wei = self.w3.eth.get_balance(checksum_address)
        native = float(Web3.from_wei(native_wei, "ether"))

        usdt = 0.0
        try:
            contract = self.w3.eth.contract(
                address=validate_evm_address(USDT_ADDRESSES[self.network]),
                abi=USDT_ABI,
            )
            decimals = contract.functions.decimals().call()
            raw = contract.functions.balanceOf(checksum_address).call()
            usdt = raw / (10 ** decimals)
        except Exception as error:
            logger.warning("USDT balance fetch failed on %s: %s", self.network, error)

        return {"native": round(native, 6), "usdt": round(usdt, 2)}

    def generate_token(self, private_key: str, recipient: str, amount: float, validity_months: int) -> GeneratedToken:
        validate_amount(amount)
        validate_validity_months(validity_months)
        sender = self.derive_address(private_key)
        recipient = validate_evm_address(recipient)
        now = int(time.time())
        validity_s = VALIDITY_MAP[validity_months]

        raw = f"{sender}{recipient}{amount}{now}{self.network}".encode()
        token_raw = f"flash{self.network}{amount}{now}".encode()
        return GeneratedToken(
            tx_hash="0x" + hashlib.sha3_256(raw).hexdigest(),
            token_address="0x" + hashlib.sha3_256(token_raw).hexdigest()[:40],
            network=self.network,
            sender=sender,
            recipient=recipient,
            amount=float(amount),
            timestamp=now,
            expiry=now + validity_s,
            validity_months=validity_months,
        )

    def mint_flash(self, private_key: str, recipient: str, amount: float, months: int = 6) -> GeneratedToken:
        validate_amount(amount)
        validate_validity_months(months)
        recipient = validate_evm_address(recipient)
        contract_address = load_deployed_flash_address(self.network)
        if not contract_address:
            raise ValueError(f"FlashUSDT contract address is not configured for {self.network}")

        account = self.w3.eth.account.from_key(normalize_private_key(private_key))
        contract = self.w3.eth.contract(address=validate_evm_address(contract_address), abi=FLASH_USDT_ABI)
        decimals = contract.functions.decimals().call()
        amount_wei = int(float(amount) * (10 ** decimals))

        tx = contract.functions.mint(recipient, amount_wei).build_transaction({
            "from": account.address,
            "nonce": self.w3.eth.get_transaction_count(account.address, "pending"),
            "gas": estimate_gas_or_default(contract.functions.mint(recipient, amount_wei), account.address, 200_000),
            "gasPrice": self.w3.eth.gas_price,
            "chainId": CHAIN_IDS[self.network],
        })
        signed = account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        if receipt["status"] != 1:
            raise RuntimeError(f"Mint transaction reverted: {tx_hash.hex()}")

        now = int(time.time())
        try:
            expiry = int(contract.functions.getExpiry().call())
        except Exception:
            expiry = now + VALIDITY_MAP[months]

        return GeneratedToken(
            tx_hash=tx_hash.hex(),
            token_address=contract_address,
            network=self.network,
            sender=account.address,
            recipient=recipient,
            amount=float(amount),
            timestamp=now,
            expiry=expiry,
            validity_months=months,
        )

    def swap_token(self, from_token: str, to_token: str, amount: float, slippage: float) -> SwapRequest:
        validate_amount(amount)
        validate_slippage(slippage)
        from_token = validate_evm_address(from_token)
        to_token = validate_evm_address(to_token)
        router = DEX_ROUTERS[self.network]
        if not router["router"]:
            raise ValueError(f"No DEX router configured for {self.network}")

        return SwapRequest(
            network=self.network,
            dex=router["name"],
            router=router["router"],
            from_token=from_token,
            to_token=to_token,
            amount=float(amount),
            slippage=float(slippage),
            status="prepared",
            instructions=(
                "Approve the router for the input token, then submit "
                "swapExactTokensForTokens through the configured DEX router."
            ),
        )

    def build_swap_transaction(
        self,
        private_key: str,
        from_token: str,
        to_token: str,
        amount_wei: int,
        amount_out_min: int,
        deadline_seconds: int = 1200,
    ) -> dict:
        account = self.w3.eth.account.from_key(normalize_private_key(private_key))
        router_address = validate_evm_address(DEX_ROUTERS[self.network]["router"])
        router = self.w3.eth.contract(address=router_address, abi=ROUTER_ABI)
        deadline = int(time.time()) + deadline_seconds

        return router.functions.swapExactTokensForTokens(
            int(amount_wei),
            int(amount_out_min),
            [validate_evm_address(from_token), validate_evm_address(to_token)],
            account.address,
            deadline,
        ).build_transaction({
            "from": account.address,
            "nonce": self.w3.eth.get_transaction_count(account.address, "pending"),
            "gas": 300_000,
            "gasPrice": self.w3.eth.gas_price,
            "chainId": CHAIN_IDS[self.network],
        })


class TronChainManager:
    """Tron support via TronGrid-compatible HTTP endpoints."""

    def __init__(self):
        self.network = "Tron"
        self._session: Optional[requests.Session] = None
        self._base_url = RPC_URLS["Tron"]
        self._connect()

    def _connect(self):
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        api_key = get_env("TRON_PRO_API_KEY")
        if api_key:
            session.headers.update({"TRON-PRO-API-KEY": api_key})
        try:
            response = session.post(f"{self._base_url}/wallet/getnowblock", json={}, timeout=10)
            response.raise_for_status()
            self._session = session
            logger.info("Connected to Tron via %s", self._base_url)
        except Exception as error:
            logger.warning("Tron connection failed: %s", error)
            self._session = None

    def is_connected(self) -> bool:
        return self._session is not None

    def derive_address(self, private_key: str) -> str:
        from eth_keys import keys

        pk_bytes = bytes.fromhex(normalize_private_key(private_key).removeprefix("0x"))
        public_key = keys.PrivateKey(pk_bytes).public_key.to_bytes()
        address_bytes = b"\x41" + Web3.keccak(public_key)[-20:]
        return base58check_encode(address_bytes)

    def get_balances(self, address: str) -> dict:
        validate_tron_address(address)
        if not self._session:
            return {"native": 0, "usdt": 0}
        try:
            response = self._session.post(f"{self._base_url}/wallet/getaccount", json={"address": address, "visible": True}, timeout=10)
            response.raise_for_status()
            trx_balance = response.json().get("balance", 0) / 1_000_000
            logger.info("TRC-20 USDT balance lookup requires TronWeb ABI encoding in the GUI/runtime adapter")
            return {"native": round(trx_balance, 6), "usdt": 0}
        except Exception as error:
            logger.warning("Tron balance error: %s", error)
            return {"native": 0, "usdt": 0}

    def generate_token(self, private_key: str, recipient: str, amount: float, validity_months: int) -> GeneratedToken:
        validate_amount(amount)
        validate_validity_months(validity_months)
        validate_tron_address(recipient)
        sender = self.derive_address(private_key)
        now = int(time.time())
        raw = f"tron:{sender}{recipient}{amount}{now}".encode()
        return GeneratedToken(
            tx_hash=hashlib.sha3_256(raw).hexdigest(),
            token_address=load_deployed_flash_address("Tron") or "TRON_DEPLOYMENT_REQUIRED",
            network="Tron",
            sender=sender,
            recipient=recipient,
            amount=float(amount),
            timestamp=now,
            expiry=now + VALIDITY_MAP[validity_months],
            validity_months=validity_months,
        )

    def mint_flash(self, private_key: str, recipient: str, amount: float, months: int = 6) -> GeneratedToken:
        validate_amount(amount)
        validate_validity_months(months)
        validate_tron_address(recipient)
        contract_address = load_deployed_flash_address("Tron")
        if not contract_address:
            raise ValueError("FlashUSDT Tron contract address is not configured")

        sender = self.derive_address(private_key)
        project_root = Path(__file__).resolve().parents[1]
        env = os.environ.copy()
        env["TRON_PRIVATE_KEY"] = normalize_private_key(private_key).removeprefix("0x")

        result = subprocess.run(
            ["node", "scripts/tron_flash.js", "mint", recipient, str(amount)],
            cwd=project_root,
            env=env,
            text=True,
            capture_output=True,
            timeout=180,
            check=False,
        )
        if result.returncode != 0:
            message = (result.stderr or result.stdout or "Tron mint failed").strip()
            raise RuntimeError(message)

        tx_hash = ""
        for line in result.stdout.splitlines():
            if line.startswith("Mint submitted:"):
                tx_hash = line.split(":", 1)[1].strip()
                break

        now = int(time.time())
        return GeneratedToken(
            tx_hash=tx_hash,
            token_address=contract_address,
            network="Tron",
            sender=sender,
            recipient=recipient,
            amount=float(amount),
            timestamp=now,
            expiry=now + VALIDITY_MAP[months],
            validity_months=months,
        )

    def swap_token(self, from_token: str, to_token: str, amount: float, slippage: float) -> SwapRequest:
        validate_amount(amount)
        validate_slippage(slippage)
        validate_tron_address(from_token)
        validate_tron_address(to_token)
        router = DEX_ROUTERS["Tron"]
        if not router["router"]:
            raise ValueError("TRON_DEX_ROUTER_ADDRESS is not configured")

        return SwapRequest(
            network="Tron",
            dex=router["name"],
            router=router["router"],
            from_token=from_token,
            to_token=to_token,
            amount=float(amount),
            slippage=float(slippage),
            status="prepared",
            instructions="Use TronWeb to approve the router and submit the TronTrade-compatible swap call.",
        )


class ChainManager:
    """Unified chain facade used by the GUI and tests."""

    def __init__(self, network: str):
        if network not in COMPATIBILITY_MATRIX:
            raise ValueError(f"Unsupported network: {network}")
        self.network = network
        self._impl = TronChainManager() if network == "Tron" else EVMChainManager(network)

    @property
    def impl(self):
        return self._impl

    def is_connected(self) -> bool:
        return self.impl.is_connected()

    def derive_address(self, private_key: str) -> str:
        return self.impl.derive_address(private_key)

    def get_balances(self, address: str) -> dict:
        return self.impl.get_balances(address)

    def generate_token(self, private_key: str, recipient: str, amount: float, validity_months: int) -> GeneratedToken:
        return self.impl.generate_token(private_key, recipient, amount, validity_months)

    def mint_flash(self, private_key: str, recipient: str, amount: float, months: int = 6) -> GeneratedToken:
        if not hasattr(self.impl, "mint_flash"):
            raise NotImplementedError("On-chain minting on Tron is handled by the Tron deployment adapter")
        return self.impl.mint_flash(private_key, recipient, amount, months)

    def swap_token(self, from_token: str, to_token: str, amount: float, slippage: float) -> SwapRequest:
        validate_amount(amount)
        validate_slippage(slippage)
        return self.impl.swap_token(from_token, to_token, amount, slippage)

    def list_on_exchange(self, exchange_name: str, token_address: str) -> dict:
        if exchange_name not in ALL_PLATFORMS:
            raise ValueError(f"Unsupported platform or exchange: {exchange_name}")
        if self.network == "Tron":
            validate_tron_address(token_address)
        else:
            validate_evm_address(token_address)

        logger.info("Manual listing request: exchange=%s token=%s network=%s", exchange_name, token_address, self.network)
        return {
            "exchange": exchange_name,
            "token_address": token_address,
            "network": self.network,
            "status": "manual_review_required",
            "instructions": (
                "Token listing is not automatic. Submit the exchange's official listing form, "
                "include verified contract source, tokenomics, legal entity/KYC details, "
                "liquidity plan, audit report, and market-maker/liquidity documentation."
            ),
        }

    def get_validity_window(self) -> int:
        address = load_deployed_flash_address(self.network)
        if not address or self.network == "Tron":
            return 0
        contract = self.impl.w3.eth.contract(address=validate_evm_address(address), abi=FLASH_USDT_ABI)
        expiry = int(contract.functions.getExpiry().call())
        return max(0, (expiry - int(time.time())) // 86400)

    @staticmethod
    def detect_wallet_provider(provider_url: str = "") -> dict:
        probe = provider_url.strip()
        lowered = probe.lower()
        if lowered.startswith("wc:") or "walletconnect" in lowered:
            wallet = "WalletConnect"
        elif "trust" in lowered:
            wallet = "Trust Wallet"
        elif "metamask" in lowered:
            wallet = "MetaMask"
        elif "tronlink" in lowered:
            wallet = "TronLink"
        elif probe:
            wallet = "Custom RPC / injected provider"
        elif auto_w3 is not None and getattr(auto_w3, "provider", None) is not None:
            wallet = "web3.auto provider"
        else:
            wallet = "Private Key / backend provider"
        return {"detected": wallet, "supported_wallets": SUPPORTED_WALLETS}

    @staticmethod
    def check_validity(tx_data: dict) -> bool:
        return int(time.time()) < int(tx_data.get("expiry", 0))

    @staticmethod
    def get_compatible_platforms(network: str) -> dict[str, bool]:
        return COMPATIBILITY_MATRIX.get(network, {})

    @staticmethod
    def time_remaining(expiry: int) -> str:
        remaining = int(expiry) - int(time.time())
        if remaining <= 0:
            return "Expired"
        days = remaining // 86400
        hours = (remaining % 86400) // 3600
        return f"{days}d {hours}h"

    @property
    def flash_usdt_available(self) -> bool:
        return bool(load_deployed_flash_address(self.network))


def normalize_private_key(private_key: str) -> str:
    key = private_key.strip()
    if not key:
        raise ValueError("Private key is required")
    if not key.startswith("0x"):
        key = "0x" + key
    if len(key) != 66:
        raise ValueError("Private key must be 32 bytes")
    return key


def validate_evm_address(address: str) -> str:
    if not Web3.is_address(address):
        raise ValueError(f"Invalid EVM address: {address}")
    return Web3.to_checksum_address(address)


def validate_tron_address(address: str) -> str:
    if not isinstance(address, str) or not address.startswith("T"):
        raise ValueError(f"Invalid Tron address: {address}")
    try:
        decoded = base58check_decode(address)
    except ValueError as error:
        raise ValueError(f"Invalid Tron address: {address}") from error
    if len(decoded) != 21 or decoded[0] != 0x41:
        raise ValueError(f"Invalid Tron address: {address}")
    return address


def validate_amount(amount: float) -> None:
    try:
        parsed = float(amount)
    except (TypeError, ValueError) as error:
        raise ValueError("Amount must be numeric") from error
    if parsed <= 0:
        raise ValueError("Amount must be greater than zero")


def validate_slippage(slippage: float) -> None:
    parsed = float(slippage)
    if parsed < 0.1 or parsed > 50:
        raise ValueError("Slippage must be between 0.1 and 50 percent")


def validate_validity_months(months: int) -> None:
    if int(months) not in VALIDITY_MAP:
        raise ValueError("Validity must be 3 or 6 months")


def estimate_gas_or_default(contract_function, from_address: str, default: int) -> int:
    try:
        return int(contract_function.estimate_gas({"from": from_address}) * 1.2)
    except Exception as error:
        logger.warning("Gas estimation failed, using default %s: %s", default, error)
        return default


def base58check_encode(data: bytes) -> str:
    checksum = hashlib.sha256(hashlib.sha256(data).digest()).digest()[:4]
    payload = data + checksum
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    number = int.from_bytes(payload, "big")
    encoded = ""
    while number:
        number, remainder = divmod(number, 58)
        encoded = alphabet[remainder] + encoded
    leading_zeroes = len(payload) - len(payload.lstrip(b"\x00"))
    leading = alphabet[0] * leading_zeroes
    return leading + encoded


def base58check_decode(value: str) -> bytes:
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    number = 0
    for char in value:
        if char not in alphabet:
            raise ValueError("Invalid Base58 character")
        number = number * 58 + alphabet.index(char)

    payload = number.to_bytes((number.bit_length() + 7) // 8, "big")
    leading_zeroes = len(value) - len(value.lstrip(alphabet[0]))
    payload = (b"\x00" * leading_zeroes) + payload
    if len(payload) < 5:
        raise ValueError("Base58Check payload is too short")

    data, checksum = payload[:-4], payload[-4:]
    expected = hashlib.sha256(hashlib.sha256(data).digest()).digest()[:4]
    if checksum != expected:
        raise ValueError("Base58Check checksum mismatch")
    return data


def get_env(name: str) -> str:
    import os

    return os.getenv(name, "")



