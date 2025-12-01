#!/usr/bin/env python3
"""Entry point script for running the transaction collector."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from bankshield import TransactionCollector  # noqa: E402

if __name__ == "__main__":
    collector = TransactionCollector()
    collector.run()
