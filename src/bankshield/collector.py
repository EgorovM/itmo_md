"""Transaction collector module for BankShield."""

import logging
import os
import random
import time
from datetime import datetime, timedelta

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

logger = logging.getLogger(__name__)


class TransactionCollector:
    """Класс для сбора и записи транзакций в MongoDB."""

    def __init__(self) -> None:
        """Инициализация подключения к MongoDB."""
        self.mongodb_host = os.getenv("MONGODB_HOST", "localhost")
        self.mongodb_port = int(os.getenv("MONGODB_PORT", "27017"))
        self.mongodb_user = os.getenv("MONGODB_USER", "mongo_user")
        self.mongodb_password = os.getenv("MONGODB_PASSWORD", "mongo_password")
        self.mongodb_db = os.getenv("MONGODB_DB", "banking_data")
        self.mongodb_collection = os.getenv("MONGODB_COLLECTION", "transactions")
        self.collect_interval = int(os.getenv("COLLECT_INTERVAL", "60"))

        self.client: MongoClient | None = None
        self.db = None
        self.collection = None

    def connect(self) -> bool:
        """Подключение к MongoDB."""
        try:
            connection_string = (
                f"mongodb://{self.mongodb_user}:{self.mongodb_password}"
                f"@{self.mongodb_host}:{self.mongodb_port}/"
            )
            self.client = MongoClient(
                connection_string,
                serverSelectionTimeoutMS=5000,
            )
            self.client.admin.command("ping")
            self.db = self.client[self.mongodb_db]
            self.collection = self.db[self.mongodb_collection]
            logger.info(
                f"Успешно подключено к MongoDB: {self.mongodb_host}:{self.mongodb_port}",
            )
            return True
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Ошибка подключения к MongoDB: {e}")
            return False

    def generate_transaction(self) -> dict:
        """
        Генерация синтетической транзакции.
        """
        transaction_types = ["debit", "credit", "transfer", "withdrawal", "deposit"]
        merchant_categories = [
            "grocery",
            "gas_station",
            "restaurant",
            "online",
            "pharmacy",
            "entertainment",
            "travel",
        ]

        # 5% транзакций помечаем как потенциально мошеннические
        is_fraud = random.random() < 0.05

        base_amount = random.uniform(10.0, 1000.0)
        if is_fraud:
            # Мошеннические транзакции обычно больше
            amount = base_amount * random.uniform(2.0, 10.0)
        else:
            amount = base_amount

        return {
            "timestamp": datetime.utcnow()
            - timedelta(
                seconds=random.randint(0, 3600),
            ),
            "transaction_id": f"TXN{random.randint(100000, 999999)}",
            "user_id": f"USER{random.randint(1000, 9999)}",
            "amount": round(amount, 2),
            "currency": random.choice(["USD", "EUR", "RUB"]),
            "transaction_type": random.choice(transaction_types),
            "merchant_category": random.choice(merchant_categories),
            "merchant_name": f"Merchant_{random.randint(1, 100)}",
            "location": {
                "country": random.choice(["USA", "UK", "Germany", "Russia"]),
                "city": f"City_{random.randint(1, 50)}",
                "latitude": round(random.uniform(-90.0, 90.0), 6),
                "longitude": round(random.uniform(-180.0, 180.0), 6),
            },
            "device_info": {
                "device_type": random.choice(["mobile", "desktop", "tablet"]),
                "os": random.choice(["iOS", "Android", "Windows", "macOS"]),
                "ip_address": f"{random.randint(1, 255)}.{random.randint(1, 255)}."
                f"{random.randint(1, 255)}.{random.randint(1, 255)}",
            },
            "is_fraud": is_fraud,
            "risk_score": round(random.uniform(0.0, 1.0), 3),
            "metadata": {
                "session_id": f"SESS{random.randint(10000, 99999)}",
                "user_agent": "Mozilla/5.0...",
            },
        }

    def insert_data(self, data: dict) -> bool:
        """Вставка транзакции в MongoDB."""
        try:
            result = self.collection.insert_one(data)
            logger.info(f"Транзакция записана. ID: {result.inserted_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при записи транзакции: {e}")
            return False

    def run(self) -> None:
        """Основной цикл сбора транзакций."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

        logger.info("Запуск сборщика транзакций BankShield...")

        if not self.connect():
            logger.error("Не удалось подключиться к MongoDB. Завершение работы.")
            return

        logger.info(f"Интервал сбора транзакций: {self.collect_interval} секунд")

        try:
            while True:
                transaction = self.generate_transaction()
                logger.info(
                    f"Транзакция: {transaction['transaction_id']}, "
                    f"Сумма: {transaction['amount']} {transaction['currency']}, "
                    f"Тип: {transaction['transaction_type']}, "
                    f"Мошенничество: {transaction.get('is_fraud', False)}",
                )

                if self.insert_data(transaction):
                    logger.info("Транзакция успешно записана в MongoDB")
                else:
                    logger.warning("Не удалось записать транзакцию")

                time.sleep(self.collect_interval)

        except KeyboardInterrupt:
            logger.info("Получен сигнал остановки. Завершение работы...")
        except Exception as e:
            logger.error(f"Критическая ошибка: {e}")
        finally:
            if self.client:
                self.client.close()
                logger.info("Соединение с MongoDB закрыто")


def main() -> None:
    """Main entry point for the transaction collector."""
    collector = TransactionCollector()
    collector.run()


if __name__ == "__main__":
    main()
