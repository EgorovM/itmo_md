"""Module for loading datasets from Kaggle."""

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from kaggle.api.kaggle_api_extended import KaggleApi

logger = logging.getLogger(__name__)


class KaggleDatasetLoader:
    """Класс для загрузки датасетов с Kaggle."""

    def __init__(self, data_dir: str = "data/raw") -> None:
        """
        Инициализация загрузчика Kaggle.

        Args:
            data_dir: Директория для сохранения данных
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.api: "KaggleApi | None" = None
        self._authenticated = False

    def _authenticate(self) -> None:
        """Аутентификация в Kaggle API (ленивая инициализация)."""
        if self._authenticated and self.api is not None:
            return

        try:
            # Kaggle API ищет credentials в ~/.kaggle/kaggle.json
            # или в переменной окружения KAGGLE_API_TOKEN (формат: username:key)
            kaggle_token = os.getenv("KAGGLE_API_TOKEN")
            if kaggle_token:
                # Если установлен KAGGLE_API_TOKEN, используем его
                # Формат: username:key
                if ":" in kaggle_token:
                    username, key = kaggle_token.split(":", 1)
                    os.environ["KAGGLE_USERNAME"] = username
                    os.environ["KAGGLE_KEY"] = key
                    logger.info("Используется KAGGLE_API_TOKEN для аутентификации")
                else:
                    logger.warning(
                        "KAGGLE_API_TOKEN должен быть в формате username:key. "
                        "Пример: KAGGLE_API_TOKEN=username:your_api_key",
                    )
                    return  # Не пытаемся аутентифицироваться с неверным форматом

            # Пытаемся аутентифицироваться только если есть credentials
            if os.getenv("KAGGLE_USERNAME") and os.getenv("KAGGLE_KEY"):
                # Ленивый импорт KaggleApi только когда он нужен
                from kaggle.api.kaggle_api_extended import KaggleApi  # noqa: PLC0415

                self.api = KaggleApi()
                self.api.authenticate()
                self._authenticated = True
                logger.info("Успешная аутентификация в Kaggle API")
            else:
                logger.info("Kaggle credentials не найдены, аутентификация пропущена")
        except Exception as e:
            logger.warning(
                f"Не удалось аутентифицироваться в Kaggle API: {e}. "
                "Убедитесь, что файл ~/.kaggle/kaggle.json существует "
                "или установлена переменная окружения KAGGLE_API_TOKEN=username:key",
            )

    def download_dataset(
        self,
        dataset: str,
        unzip: bool = True,
        force: bool = False,
    ) -> Path:
        """
        Загрузка датасета с Kaggle.

        Args:
            dataset: Имя датасета в формате 'username/dataset-name'
            unzip: Распаковать архив после загрузки
            force: Перезаписать существующие файлы

        Returns:
            Path к директории с загруженными данными
        """
        # Ленивая аутентификация
        self._authenticate()

        if self.api is None:
            raise RuntimeError(
                "Kaggle API не аутентифицирован. "
                "Установите KAGGLE_API_TOKEN=username:key или создайте ~/.kaggle/kaggle.json"
            )

        dataset_dir = self.data_dir / dataset.replace("/", "_")
        dataset_dir.mkdir(parents=True, exist_ok=True)

        try:
            logger.info(f"Загрузка датасета {dataset}...")
            self.api.dataset_download_files(
                dataset,
                path=str(dataset_dir),
                unzip=unzip,
                force=force,
            )
            logger.info(f"Датасет {dataset} успешно загружен в {dataset_dir}")
            return dataset_dir
        except Exception as e:
            logger.error(f"Ошибка при загрузке датасета {dataset}: {e}")
            raise

    def load_csv(self, dataset: str, filename: str | None = None) -> pd.DataFrame:
        """
        Загрузка CSV файла из датасета.

        Args:
            dataset: Имя датасета в формате 'username/dataset-name'
            filename: Имя CSV файла (если None, загружается первый найденный)

        Returns:
            DataFrame с данными
        """
        dataset_dir = self.download_dataset(dataset)

        if filename:
            csv_path = dataset_dir / filename
        else:
            # Ищем первый CSV файл
            csv_files = list(dataset_dir.glob("*.csv"))
            if not csv_files:
                raise FileNotFoundError(f"CSV файлы не найдены в {dataset_dir}")
            csv_path = csv_files[0]

        logger.info(f"Загрузка CSV файла: {csv_path}")
        return pd.read_csv(csv_path)

    def list_popular_fraud_datasets(self) -> list[str]:
        """
        Возвращает список популярных датасетов для детекции мошенничества.

        Returns:
            Список датасетов в формате 'username/dataset-name'
        """
        return [
            "mlg-ulb/creditcardfraud",  # Credit Card Fraud Detection
            "ntnu-testimon/paysim1",  # Synthetic Financial Dataset For Fraud Detection
            "ealaxi/paysim2",  # PaySim2 - Financial Simulation
            "vishnusairam/credit-card-fraud-detection",  # Credit Card Fraud Detection
            "rupakroy/online-payments-fraud-detection-dataset",  # Online Payments Fraud
        ]


def main() -> None:
    """Пример использования загрузчика Kaggle."""
    loader = KaggleDatasetLoader()

    # Пример загрузки популярного датасета
    datasets = loader.list_popular_fraud_datasets()
    print("Популярные датасеты для детекции мошенничества:")
    for ds in datasets:
        print(f"  - {ds}")

    # Для загрузки датасета раскомментируйте:
    # df = loader.load_csv("mlg-ulb/creditcardfraud")
    # print(df.head())


if __name__ == "__main__":
    main()
