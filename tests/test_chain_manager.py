import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "flashDemotoken_generator"))

from core import blockchain
from core.blockchain import ChainManager, EVMChainManager, SwapRequest, base58check_encode, validate_tron_address


class FakeImpl:
    network = "Ethereum"

    def is_connected(self):
        return True

    def swap_token(self, from_token, to_token, amount, slippage):
        return SwapRequest(
            network="Ethereum",
            dex="Uniswap V2",
            router="0x0000000000000000000000000000000000000001",
            from_token=from_token,
            to_token=to_token,
            amount=float(amount),
            slippage=float(slippage),
            status="prepared",
            instructions="mock swap",
        )


def test_detect_wallet_provider_walletconnect():
    detected = ChainManager.detect_wallet_provider("wc:abc@2")

    assert detected["detected"] == "WalletConnect"
    assert "MetaMask" in detected["supported_wallets"]
    assert "Trust Wallet" in detected["supported_wallets"]


def test_list_on_exchange_returns_manual_instructions(monkeypatch):
    monkeypatch.setattr(blockchain, "EVMChainManager", lambda network: FakeImpl())
    manager = ChainManager("Ethereum")

    result = manager.list_on_exchange("Binance", "0x0000000000000000000000000000000000000001")

    assert result["status"] == "manual_review_required"
    assert result["exchange"] == "Binance"
    assert "official listing form" in result["instructions"]


def test_swap_token_validates_amount(monkeypatch):
    monkeypatch.setattr(blockchain, "EVMChainManager", lambda network: FakeImpl())
    manager = ChainManager("Ethereum")

    with pytest.raises(ValueError, match="Amount"):
        manager.swap_token(
            "0x0000000000000000000000000000000000000001",
            "0x0000000000000000000000000000000000000002",
            0,
            1,
        )


def test_evm_swap_token_prepares_router_request(monkeypatch):
    manager = EVMChainManager.__new__(EVMChainManager)
    manager.network = "BSC"
    manager.w3 = None

    request = manager.swap_token(
        "0x0000000000000000000000000000000000000001",
        "0x0000000000000000000000000000000000000002",
        25,
        1,
    )

    assert request.status == "prepared"
    assert request.dex == "PancakeSwap V2"
    assert request.amount == 25


def test_validity_helpers():
    assert ChainManager.check_validity({"expiry": 1}) is False
    assert ChainManager.time_remaining(1) == "Expired"


def test_tron_address_validation_checks_base58_checksum():
    valid_address = base58check_encode(bytes.fromhex("41" + "00" * 20))

    assert validate_tron_address(valid_address) == valid_address
    with pytest.raises(ValueError, match="Invalid Tron address"):
        validate_tron_address(valid_address[:-1] + "1")
