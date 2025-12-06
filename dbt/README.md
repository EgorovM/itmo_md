# BankShield DBT Project

DBT проект для трансформации данных транзакций BankShield.

## Структура проекта

```
dbt/
├── models/
│   ├── stg/          # Staging - очистка и парсинг
│   ├── ods/          # Operational Data Store - нормализация
│   ├── dwh/          # Data Warehouse - агрегаты (инкрементальные)
│   └── dm/           # Data Marts - бизнес-витрины
├── tests/            # Кастомные тесты
├── macros/           # Макросы DBT
├── seeds/            # Seed данные
└── snapshots/        # Snapshots
```

## Установка

1. Установите зависимости:
```bash
dbt deps
```

2. Настройте профиль (скопируйте `profiles.yml.example` в `profiles.yml` и настройте подключение)

3. Запустите модели:
```bash
# Все модели
dbt run

# Только STG
dbt run --select stg.*

# Только инкрементальные
dbt run --select dwh.*
```

## Тестирование

```bash
# Все тесты
dbt test

# Тесты для конкретного слоя
dbt test --select stg.*

# Кастомные тесты
dbt test --select test_type:data
```

## Документация

```bash
# Генерация документации
dbt docs generate

# Запуск сервера документации
dbt docs serve
```

## Инкрементальная загрузка

Проект использует два вида инкрементальной загрузки:

1. **dwh_transactions_daily** - merge strategy по `transaction_date`
2. **dwh_user_transactions** - merge strategy по `user_id`

## Elementary

Elementary настроен для мониторинга качества данных. Запуск:

```bash
dbt run-operation elementary.run_anomaly_detection
```

## Airflow интеграция

DBT пайплайны запускаются через Airflow DAG `dbt_transformations` каждый час.
