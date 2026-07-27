"""Desktop GUI for testing FlashUSDT across supported networks."""
import logging
import sys
import threading
import time
from pathlib import Path
from tkinter import messagebox
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import customtkinter as ctk

from config import (
    APP_TITLE,
    APP_VERSION,
    COMPATIBILITY_MATRIX,
    DEX_ROUTERS,
    EXCHANGES,
    NATIVE_SYMBOLS,
    SUPPORTED_WALLETS,
    TRADING_PLATFORMS,
)
from core.blockchain import ChainManager, GeneratedToken, SwapRequest

logger = logging.getLogger(__name__)

COLORS = {
    "bg": "#101418",
    "panel": "#171d24",
    "input": "#222a33",
    "accent": "#18c29c",
    "accent_hover": "#12a887",
    "warning": "#f5a524",
    "danger": "#ef4444",
    "ok": "#22c55e",
    "text": "#f4f7fb",
    "muted": "#a9b4c0",
    "line": "#2b3541",
}

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")


class OutputPanel(ctk.CTkFrame):
    def __init__(self, master, title: str):
        super().__init__(master, fg_color=COLORS["panel"])
        ctk.CTkLabel(self, text=title, font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=12, pady=(10, 4))
        self.textbox = ctk.CTkTextbox(self, height=210, fg_color=COLORS["bg"], text_color=COLORS["text"], wrap="word")
        self.textbox.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.write("Ready.")

    def write(self, text: str):
        self.textbox.configure(state="normal")
        self.textbox.delete("0.0", "end")
        self.textbox.insert("0.0", text)
        self.textbox.configure(state="disabled")


class PlatformFrame(ctk.CTkScrollableFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, label_text="Platforms / Exchanges", **kwargs)
        self._labels: dict[str, ctk.CTkLabel] = {}
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="Trading Platforms", text_color=COLORS["muted"], font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(4, 2))
        for name in TRADING_PLATFORMS:
            self._row(name)
        ctk.CTkLabel(self, text="Exchanges", text_color=COLORS["muted"], font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10, 2))
        for name in EXCHANGES:
            self._row(name)

    def _row(self, name: str):
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", pady=1)
        status = ctk.CTkLabel(row, text="-", width=24)
        status.pack(side="left")
        ctk.CTkLabel(row, text=name, anchor="w").pack(side="left", padx=(4, 0))
        self._labels[name] = status

    def update_compatibility(self, network: str):
        matrix = COMPATIBILITY_MATRIX.get(network, {})
        for name, label in self._labels.items():
            ok = matrix.get(name, False)
            label.configure(text="OK" if ok else "NO", text_color=COLORS["ok"] if ok else COLORS["danger"])


class USDTGeneratorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_TITLE} v{APP_VERSION}")
        self.geometry("1080x760")
        self.minsize(980, 700)
        self.configure(fg_color=COLORS["bg"])

        self._chain_mgr: Optional[ChainManager] = None
        self._wallet_address: Optional[str] = None
        self._last_token: Optional[GeneratedToken] = None

        self._build_header()
        self._build_layout()
        self._build_status_bar()
        self._on_network_change()
        self._refresh_wallet_detection()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color=COLORS["panel"], height=58)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(header, text="FlashUSDT", font=ctk.CTkFont(size=24, weight="bold"), text_color=COLORS["accent"]).pack(side="left", padx=(16, 8))
        ctk.CTkLabel(header, text=f"v{APP_VERSION}", text_color=COLORS["muted"]).pack(side="left")
        self._conn_label = ctk.CTkLabel(header, text="Disconnected", text_color=COLORS["muted"])
        self._conn_label.pack(side="right", padx=16)

    def _build_layout(self):
        root = ctk.CTkFrame(self, fg_color=COLORS["bg"])
        root.pack(fill="both", expand=True, padx=12, pady=10)

        left = ctk.CTkFrame(root, fg_color="transparent", width=310)
        left.pack(side="left", fill="y", padx=(0, 10))
        left.pack_propagate(False)
        self._build_wallet_panel(left)
        self._platform_frame = PlatformFrame(left, fg_color=COLORS["panel"], height=330)
        self._platform_frame.pack(fill="both", expand=True, pady=(10, 0))

        right = ctk.CTkFrame(root, fg_color=COLORS["panel"])
        right.pack(side="right", fill="both", expand=True)
        self._tabs = ctk.CTkTabview(right, fg_color=COLORS["panel"], segmented_button_fg_color=COLORS["input"])
        self._tabs.pack(fill="both", expand=True, padx=10, pady=10)
        self._build_generate_tab(self._tabs.add("Generate"))
        self._build_swap_tab(self._tabs.add("Swap"))
        self._build_listing_tab(self._tabs.add("Listing"))
        self._build_status_tab(self._tabs.add("Status"))

    def _build_wallet_panel(self, parent):
        card = ctk.CTkFrame(parent, fg_color=COLORS["panel"])
        card.pack(fill="x")
        ctk.CTkLabel(card, text="Network & Wallet", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=12, pady=(10, 4))

        self._network_var = ctk.StringVar(value="Ethereum Sepolia")
        ctk.CTkOptionMenu(card, values=list(COMPATIBILITY_MATRIX.keys()), variable=self._network_var, command=lambda _: self._on_network_change()).pack(fill="x", padx=12, pady=4)

        self._wallet_mode_var = ctk.StringVar(value="Private Key")
        wallet_modes = ["Private Key", "MetaMask", "Trust Wallet", "WalletConnect", "TronLink", "Custom Provider"]
        ctk.CTkOptionMenu(card, values=wallet_modes, variable=self._wallet_mode_var, command=lambda _: self._refresh_wallet_detection()).pack(fill="x", padx=12, pady=4)

        self._provider_var = ctk.StringVar()
        ctk.CTkEntry(card, placeholder_text="Provider URL or WalletConnect URI", textvariable=self._provider_var, fg_color=COLORS["input"]).pack(fill="x", padx=12, pady=4)

        self._pk_var = ctk.StringVar()
        self._pk_entry = ctk.CTkEntry(card, placeholder_text="Private key for local test signing", textvariable=self._pk_var, show="*", fg_color=COLORS["input"])
        self._pk_entry.pack(fill="x", padx=12, pady=4)

        self._connect_btn = ctk.CTkButton(card, text="Connect / Validate", command=self._on_connect, fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], text_color="#07100d")
        self._connect_btn.pack(fill="x", padx=12, pady=(8, 4))

        self._wallet_label = ctk.CTkLabel(card, text="Wallet: not connected", anchor="w", text_color=COLORS["muted"])
        self._wallet_label.pack(fill="x", padx=12, pady=2)
        self._balance_label = ctk.CTkLabel(card, text="Balance: -", anchor="w", text_color=COLORS["muted"])
        self._balance_label.pack(fill="x", padx=12, pady=(2, 12))

    def _build_generate_tab(self, tab):
        form = ctk.CTkFrame(tab, fg_color="transparent")
        form.pack(fill="x", padx=8, pady=8)
        self._recipient_var = ctk.StringVar()
        self._amount_var = ctk.StringVar(value="1000")
        self._validity_var = ctk.StringVar(value="6 Months")
        ctk.CTkEntry(form, placeholder_text="Recipient wallet address", textvariable=self._recipient_var, fg_color=COLORS["input"]).pack(fill="x", pady=4)
        ctk.CTkEntry(form, placeholder_text="Amount", textvariable=self._amount_var, fg_color=COLORS["input"]).pack(fill="x", pady=4)
        ctk.CTkOptionMenu(form, values=["3 Months", "6 Months"], variable=self._validity_var).pack(fill="x", pady=4)
        self._gen_btn = ctk.CTkButton(form, text="Generate / Mint FlashUSDT", command=self._on_generate, fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], text_color="#07100d")
        self._gen_btn.pack(fill="x", pady=(8, 4))
        self._generate_output = OutputPanel(tab, "Generation Result")
        self._generate_output.pack(fill="both", expand=True, padx=8, pady=8)

    def _build_swap_tab(self, tab):
        form = ctk.CTkFrame(tab, fg_color="transparent")
        form.pack(fill="x", padx=8, pady=8)
        self._swap_from_var = ctk.StringVar()
        self._swap_to_var = ctk.StringVar()
        self._swap_amount_var = ctk.StringVar(value="10")
        self._slippage_var = ctk.StringVar(value="1")
        ctk.CTkEntry(form, placeholder_text="From token address", textvariable=self._swap_from_var, fg_color=COLORS["input"]).pack(fill="x", pady=4)
        ctk.CTkEntry(form, placeholder_text="To token address", textvariable=self._swap_to_var, fg_color=COLORS["input"]).pack(fill="x", pady=4)
        ctk.CTkEntry(form, placeholder_text="Amount", textvariable=self._swap_amount_var, fg_color=COLORS["input"]).pack(fill="x", pady=4)
        ctk.CTkEntry(form, placeholder_text="Slippage %", textvariable=self._slippage_var, fg_color=COLORS["input"]).pack(fill="x", pady=4)
        ctk.CTkButton(form, text="Prepare Swap", command=self._on_prepare_swap, fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], text_color="#07100d").pack(fill="x", pady=(8, 4))
        self._swap_output = OutputPanel(tab, "Swap Preparation")
        self._swap_output.pack(fill="both", expand=True, padx=8, pady=8)

    def _build_listing_tab(self, tab):
        form = ctk.CTkFrame(tab, fg_color="transparent")
        form.pack(fill="x", padx=8, pady=8)
        self._exchange_var = ctk.StringVar(value="Binance")
        self._listing_token_var = ctk.StringVar()
        ctk.CTkOptionMenu(form, values=EXCHANGES + TRADING_PLATFORMS, variable=self._exchange_var).pack(fill="x", pady=4)
        ctk.CTkEntry(form, placeholder_text="Token address", textvariable=self._listing_token_var, fg_color=COLORS["input"]).pack(fill="x", pady=4)
        ctk.CTkButton(form, text="Create Listing Checklist", command=self._on_listing_request, fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], text_color="#07100d").pack(fill="x", pady=(8, 4))
        self._listing_output = OutputPanel(tab, "Listing Checklist")
        self._listing_output.pack(fill="both", expand=True, padx=8, pady=8)

    def _build_status_tab(self, tab):
        ctk.CTkButton(tab, text="Refresh Status", command=self._refresh_status, fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], text_color="#07100d").pack(fill="x", padx=8, pady=(8, 4))
        self._status_output = OutputPanel(tab, "Runtime Status")
        self._status_output.pack(fill="both", expand=True, padx=8, pady=8)

    def _build_status_bar(self):
        bar = ctk.CTkFrame(self, fg_color=COLORS["panel"], height=28)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)
        self._status_text = ctk.CTkLabel(bar, text="Ready", text_color=COLORS["muted"])
        self._status_text.pack(side="left", padx=12)
        self._validity_label = ctk.CTkLabel(bar, text="", text_color=COLORS["muted"])
        self._validity_label.pack(side="right", padx=12)

    def _on_network_change(self):
        net = self._network_var.get()
        self._chain_mgr = None
        self._wallet_address = None
        self._platform_frame.update_compatibility(net) if hasattr(self, "_platform_frame") else None
        self._wallet_label.configure(text="Wallet: not connected") if hasattr(self, "_wallet_label") else None
        self._balance_label.configure(text="Balance: -") if hasattr(self, "_balance_label") else None
        self._conn_label.configure(text=f"Selected: {net}") if hasattr(self, "_conn_label") else None
        self.set_status(f"Network changed to {net}") if hasattr(self, "_status_text") else None

    def _refresh_wallet_detection(self):
        provider = self._provider_var.get().strip() if hasattr(self, "_provider_var") else ""
        mode = self._wallet_mode_var.get() if hasattr(self, "_wallet_mode_var") else "Private Key"
        detected = ChainManager.detect_wallet_provider(provider if provider else mode)
        if hasattr(self, "_wallet_label"):
            supported = ", ".join(SUPPORTED_WALLETS[:4]) + ", ..."
            self._wallet_label.configure(text=f"Wallet mode: {detected['detected']} | Supported: {supported}")

    def _on_connect(self):
        net = self._network_var.get()
        mode = self._wallet_mode_var.get()
        pk = self._pk_var.get().strip()
        self._connect_btn.configure(state="disabled", text="Connecting...")
        self.set_status(f"Connecting to {net}...")

        def task():
            try:
                manager = ChainManager(net)
                if mode != "Private Key" and not pk:
                    info = ChainManager.detect_wallet_provider(self._provider_var.get().strip() or mode)
                    self.after(0, lambda: self._on_provider_ready(manager, info))
                    return
                address = manager.derive_address(pk)
                balances = manager.get_balances(address)
                self.after(0, lambda: self._on_connect_success(manager, address, balances))
            except Exception as exc:
                logger.exception("Connect failed")
                self.after(0, lambda: self._on_error("Connection failed", str(exc)))

        threading.Thread(target=task, daemon=True).start()

    def _on_provider_ready(self, manager: ChainManager, info: dict):
        self._chain_mgr = manager
        self._connect_btn.configure(state="normal", text="Connect / Validate")
        self._conn_label.configure(text=f"Provider ready: {manager.network}", text_color=COLORS["warning"])
        self._wallet_label.configure(text=f"Wallet provider: {info['detected']}. Use wallet UI to sign transactions.")
        self._balance_label.configure(text="Balance: connect a wallet session in the GUI adapter")
        self.set_status("Provider mode validated. Private-key signing is disabled until a wallet session is attached.")

    def _on_connect_success(self, manager: ChainManager, address: str, balances: dict):
        self._chain_mgr = manager
        self._wallet_address = address
        self._connect_btn.configure(state="normal", text="Connect / Validate")
        self._conn_label.configure(text=f"Connected: {manager.network}", text_color=COLORS["ok"])
        self._wallet_label.configure(text=f"Wallet: {address[:10]}...{address[-6:]}")
        symbol = NATIVE_SYMBOLS.get(manager.network, "NATIVE")
        self._balance_label.configure(text=f"Balance: {balances['native']} {symbol} | {balances['usdt']} USDT", text_color=COLORS["ok"])
        self.set_status(f"Connected to {manager.network}")
        self._refresh_status()

    def _on_generate(self):
        if not self._chain_mgr or not self._wallet_address:
            messagebox.showwarning("Wallet Required", "Connect with a private key before minting or simulation.")
            return
        self._gen_btn.configure(state="disabled", text="Generating...")
        self.set_status("Generating FlashUSDT...")

        def task():
            try:
                months = 6 if "6" in self._validity_var.get() else 3
                amount = float(self._amount_var.get().strip())
                recipient = self._recipient_var.get().strip()
                pk = self._pk_var.get().strip()
                if self._chain_mgr.flash_usdt_available:
                    token = self._chain_mgr.mint_flash(pk, recipient, amount, months)
                else:
                    token = self._chain_mgr.generate_token(pk, recipient, amount, months)
                self._last_token = token
                self.after(0, lambda: self._show_token(token))
            except Exception as exc:
                logger.exception("Generation failed")
                self.after(0, lambda: self._on_error("Generation failed", str(exc)))
            finally:
                self.after(0, lambda: self._gen_btn.configure(state="normal", text="Generate / Mint FlashUSDT"))

        threading.Thread(target=task, daemon=True).start()

    def _show_token(self, token: GeneratedToken):
        expiry = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(token.expiry))
        remaining = ChainManager.time_remaining(token.expiry)
        self._generate_output.write(
            f"Status: {'valid' if token.is_valid() else 'expired'}\n"
            f"Network: {token.network}\n"
            f"Transaction: {token.tx_hash}\n"
            f"Token: {token.token_address}\n"
            f"Sender: {token.sender}\n"
            f"Recipient: {token.recipient}\n"
            f"Amount: {token.amount:,.6f}\n"
            f"Expiry: {expiry}\n"
            f"Remaining: {remaining}"
        )
        self._validity_label.configure(text=f"Last token: {remaining}", text_color=COLORS["ok"] if token.is_valid() else COLORS["danger"])
        self.set_status("Token flow completed")

    def _on_prepare_swap(self):
        manager = self._require_manager()
        if not manager:
            return
        try:
            request = manager.swap_token(
                self._swap_from_var.get().strip(),
                self._swap_to_var.get().strip(),
                float(self._swap_amount_var.get().strip()),
                float(self._slippage_var.get().strip()),
            )
            self._show_swap(request)
        except Exception as exc:
            self._on_error("Swap preparation failed", str(exc))

    def _show_swap(self, request: SwapRequest):
        self._swap_output.write(
            f"Status: {request.status}\n"
            f"Network: {request.network}\n"
            f"DEX: {request.dex}\n"
            f"Router: {request.router}\n"
            f"From: {request.from_token}\n"
            f"To: {request.to_token}\n"
            f"Amount: {request.amount}\n"
            f"Slippage: {request.slippage}%\n\n"
            f"Next step: {request.instructions}"
        )
        self.set_status("Swap request prepared")

    def _on_listing_request(self):
        manager = self._require_manager()
        if not manager:
            return
        token = self._listing_token_var.get().strip() or (self._last_token.token_address if self._last_token else "")
        try:
            result = manager.list_on_exchange(self._exchange_var.get(), token)
            self._listing_output.write(
                f"Status: {result['status']}\n"
                f"Exchange/platform: {result['exchange']}\n"
                f"Network: {result['network']}\n"
                f"Token: {result['token_address']}\n\n"
                f"Checklist: {result['instructions']}"
            )
            self.set_status("Listing checklist created")
        except Exception as exc:
            self._on_error("Listing request failed", str(exc))

    def _refresh_status(self):
        manager = self._chain_mgr
        if not manager:
            self._status_output.write("No network connected. Select a network and connect or validate a provider.")
            return
        try:
            validity_days = manager.get_validity_window()
        except Exception as exc:
            validity_days = 0
            logger.warning("Validity refresh failed: %s", exc)
        router = DEX_ROUTERS.get(manager.network, {})
        self._status_output.write(
            f"Network: {manager.network}\n"
            f"Connected: {manager.is_connected()}\n"
            f"FlashUSDT configured: {manager.flash_usdt_available}\n"
            f"Remaining deployed validity: {validity_days} day(s)\n"
            f"DEX: {router.get('name', '-')}\n"
            f"Router: {router.get('router', '-') or 'not configured'}\n"
            f"Native symbol: {NATIVE_SYMBOLS.get(manager.network, '-')}\n"
            f"Wallets: {', '.join(SUPPORTED_WALLETS)}"
        )

    def _require_manager(self) -> Optional[ChainManager]:
        if not self._chain_mgr:
            messagebox.showwarning("Network Required", "Connect or validate a network first.")
            return None
        return self._chain_mgr

    def _on_error(self, title: str, message: str):
        self._connect_btn.configure(state="normal", text="Connect / Validate")
        self.set_status(f"{title}: {message}")
        messagebox.showerror(title, message)

    def set_status(self, message: str):
        self._status_text.configure(text=message)


if __name__ == "__main__":
    app = USDTGeneratorApp()
    app.mainloop()
