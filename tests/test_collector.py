"""Tests for transaction collector module."""

import os
from unittest.mock import MagicMock, patch


from bankshield import TransactionCollector


class TestTransactionCollector:
    """Test suite for TransactionCollector class."""

    def test_init_default_values(self) -> None:
        """Test TransactionCollector initialization with default values."""
        collector = TransactionCollector()
        assert collector.mongodb_host == "localhost"
        assert collector.mongodb_port == 27017
        assert collector.mongodb_user == "mongo_user"
        assert collector.mongodb_db == "banking_data"
        assert collector.collect_interval == 60

    def test_init_from_env(self) -> None:
        """Test TransactionCollector initialization from environment variables."""
        with patch.dict(
            os.environ,
            {
                "MONGODB_HOST": "test_host",
                "MONGODB_PORT": "27018",
                "MONGODB_USER": "test_user",
                "MONGODB_PASSWORD": "test_pass",
                "MONGODB_DB": "test_db",
                "MONGODB_COLLECTION": "test_collection",
                "COLLECT_INTERVAL": "30",
                "USE_KAGGLE_DATA": "true",
                "KAGGLE_DATASET": "test/dataset",
            },
        ):
            collector = TransactionCollector()
            assert collector.mongodb_host == "test_host"
            assert collector.mongodb_port == 27018
            assert collector.mongodb_user == "test_user"
            assert collector.mongodb_password == "test_pass"
            assert collector.mongodb_db == "test_db"
            assert collector.mongodb_collection == "test_collection"
            assert collector.collect_interval == 30
            assert collector.use_kaggle_data is True
            assert collector.kaggle_dataset == "test/dataset"

    def test_generate_transaction(self) -> None:
        """Test transaction generation."""
        collector = TransactionCollector()
        transaction = collector.generate_transaction()

        assert "timestamp" in transaction
        assert "transaction_id" in transaction
        assert "user_id" in transaction
        assert "amount" in transaction
        assert "currency" in transaction
        assert "transaction_type" in transaction
        assert "merchant_category" in transaction
        assert "location" in transaction
        assert "device_info" in transaction
        assert "is_fraud" in transaction
        assert "risk_score" in transaction

        assert transaction["amount"] > 0
        assert transaction["currency"] in ["USD", "EUR", "RUB"]
        assert transaction["transaction_type"] in [
            "debit",
            "credit",
            "transfer",
            "withdrawal",
            "deposit",
        ]
        assert isinstance(transaction["is_fraud"], bool)
        assert 0.0 <= transaction["risk_score"] <= 1.0

    @patch("bankshield.collector.MongoClient")
    def test_connect_success(self, mock_mongo_client: MagicMock) -> None:
        """Test successful MongoDB connection."""
        mock_client = MagicMock()
        mock_client.admin.command.return_value = True
        mock_mongo_client.return_value = mock_client

        collector = TransactionCollector()
        result = collector.connect()

        assert result is True
        assert collector.client is not None
        mock_mongo_client.assert_called_once()

    @patch("bankshield.collector.MongoClient")
    def test_connect_failure(self, mock_mongo_client: MagicMock) -> None:
        """Test MongoDB connection failure."""
        from pymongo.errors import ConnectionFailure

        mock_mongo_client.side_effect = ConnectionFailure("Connection failed")

        collector = TransactionCollector()
        result = collector.connect()

        assert result is False

    @patch("bankshield.collector.MongoClient")
    def test_insert_data_success(self, mock_mongo_client: MagicMock) -> None:
        """Test successful transaction insertion."""
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_collection.insert_one.return_value = MagicMock(inserted_id="test_id")
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_client.__getitem__.return_value = mock_db
        mock_client.admin.command.return_value = True
        mock_mongo_client.return_value = mock_client

        collector = TransactionCollector()
        collector.connect()
        collector.collection = mock_collection

        test_transaction = {
            "transaction_id": "TXN123456",
            "amount": 100.0,
            "currency": "USD",
        }
        result = collector.insert_data(test_transaction)

        assert result is True
        mock_collection.insert_one.assert_called_once_with(test_transaction)
