#!/usr/bin/env python3
"""
Multi-Chain USDT Wallet & Generator — Desktop App
Entry point. Run `python main.py` to launch.
"""
import sys
import logging
from pathlib import Path

# Ensure the project root is on sys.path so all imports resolve
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

def main():
    # Late import so logging is configured first
    from ui.gui import USDTGeneratorApp

    app = USDTGeneratorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
