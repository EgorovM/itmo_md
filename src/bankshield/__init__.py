"""BankShield - Transaction analysis for fraud detection."""

from bankshield.collector import TransactionCollector
from bankshield.kaggle_loader import KaggleDatasetLoader

__all__ = ["TransactionCollector", "KaggleDatasetLoader"]
__version__ = "1.0.0"
