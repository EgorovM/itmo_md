#!/usr/bin/env python3
"""Script to download datasets from Kaggle."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from bankshield import KaggleDatasetLoader  # noqa: E402


def main() -> None:
    """Download fraud detection datasets from Kaggle."""
    loader = KaggleDatasetLoader()

    print("Доступные датасеты для детекции мошенничества:")
    datasets = loader.list_popular_fraud_datasets()
    for i, ds in enumerate(datasets, 1):
        print(f"{i}. {ds}")

    print("\nДля загрузки датасета используйте:")
    print("  python scripts/download_kaggle_data.py <dataset_name>")
    print("\nПример:")
    print("  python scripts/download_kaggle_data.py mlg-ulb/creditcardfraud")

    if len(sys.argv) > 1:
        dataset = sys.argv[1]
        print(f"\nЗагрузка датасета: {dataset}")
        try:
            df = loader.load_csv(dataset)
            print(f"Успешно загружено {len(df)} записей")
            print(f"Колонки: {list(df.columns)}")
            print("\nПервые 5 строк:")
            print(df.head())
        except Exception as e:
            print(f"Ошибка при загрузке: {e}")


if __name__ == "__main__":
    main()
