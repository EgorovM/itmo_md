# BankShield - Transaction Analysis & Fraud Detection

Проект для анализа транзакций и выявления аномалий и мошенничества с использованием ETL-процессов.

## Описание

BankShield - это система для сбора, обработки и анализа банковских транзакций с целью выявления мошеннических операций. Проект включает:

- **REST API** с автодокументацией Swagger для генерации и управления транзакциями
- Сбор транзакций (синтетические данные или загрузка с Kaggle)
- Хранение в MongoDB (источник данных)
- ETL-процесс для загрузки в PostgreSQL (аналитическая БД)
- DBT для трансформации данных (STG -> ODS -> DWH -> DM)
- Elementary для мониторинга качества данных
- Интеграция с Apache Airflow для оркестрации
- Grafana дашборды для визуализации

## Структура проекта

```
.
├── src/
│   └── bankshield/              # Основной пакет приложения
│       ├── __init__.py
│       ├── collector.py         # Класс для сбора транзакций
│       └── kaggle_loader.py     # Загрузчик датасетов с Kaggle
├── tests/                        # Тесты
│   └── test_collector.py
├── scripts/                      # Скрипты запуска
│   ├── run_collector.py         # Запуск сборщика транзакций
│   └── download_kaggle_data.py  # Загрузка датасетов с Kaggle
├── airflow/                      # Airflow конфигурация
│   ├── dags/                    # DAG файлы
│   │   └── transactions_etl.py  # ETL для транзакций
│   ├── logs/                    # Логи Airflow
│   └── plugins/                 # Плагины Airflow
├── data/                         # Данные (Kaggle датасеты)
├── docker-compose.yml            # Docker Compose конфигурация
├── Dockerfile                    # Dockerfile для transaction-collector
├── pyproject.toml                # Конфигурация проекта и зависимостей
└── .pre-commit-config.yaml       # Pre-commit hooks
```

## Технологии

- **Python 3.11+**
- **MongoDB** - источник данных (продовое приложение)
- **PostgreSQL** - целевая база для аналитики
- **Apache Airflow** - оркестрация ETL-процессов
- **Kaggle API** - загрузка датасетов для анализа мошенничества
- **Pandas & NumPy** - обработка данных
- **Docker & Docker Compose** - контейнеризация
- **uv** - пакетный менеджер
- **ruff** - линтер и форматтер
- **pre-commit** - git hooks для проверки кода

## Установка и настройка

### Предварительные требования

- Docker и Docker Compose
- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (для локальной разработки)
- [Kaggle API credentials](https://www.kaggle.com/docs/api) (опционально, для загрузки датасетов)

### Настройка Kaggle API (опционально)

1. Зарегистрируйтесь на [Kaggle](https://www.kaggle.com/)
2. Создайте API token: Account -> API -> Create New Token

```bash
export KAGGLE_API_TOKEN=username:your_api_key
```

Для использования в Docker Compose, установите переменную окружения перед запуском:
```bash
export KAGGLE_API_TOKEN=username:your_api_key
docker-compose up -d
```

### Локальная разработка

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd md
```

2. Установите зависимости через uv:
```bash
uv sync
```

3. Установите pre-commit hooks:
```bash
uv run pre-commit install
```

4. Запустите линтер и форматтер:
```bash
uv run ruff check .
uv run ruff format .
```

5. Запустите тесты:
```bash
uv run pytest
```

## Запуск через Docker Compose

1. Запустите все сервисы:
```bash
docker-compose up -d
```

2. Проверьте статус сервисов:
```bash
docker-compose ps
```

3. Просмотрите логи transaction-collector:
```bash
docker-compose logs -f data-collector
```

4. Откройте Airflow UI:
   - URL: http://localhost:8080
   - Username: `airflow`
   - Password: `airflow` (по умолчанию)

5. Откройте BankShield API (Swagger):
   - URL: http://localhost:8100/docs
   - ReDoc: http://localhost:8100/redoc

6. Откройте Grafana:
   - URL: http://localhost:3001
   - Username: `admin`
   - Password: `admin`

7. Откройте Elementary EDR (Data Quality Monitoring):
   - URL: http://localhost:8081
   - Показывает результаты мониторинга качества данных, аномалии и метрики
   - Данные обновляются после выполнения DBT пайплайна в Airflow

## REST API

BankShield предоставляет REST API для управления транзакциями.

### Endpoints

| Method | Endpoint | Описание |
|--------|----------|----------|
| GET | `/health` | Проверка состояния сервиса |
| GET | `/transactions/generate` | Генерация одной транзакции (без сохранения) |
| POST | `/transactions` | Создание и сохранение транзакции |
| POST | `/transactions/batch?count=N` | Генерация N транзакций |
| GET | `/transactions/stats` | Статистика по транзакциям |
| GET | `/transactions/recent?limit=N` | Последние N транзакций |

## Конфигурация

### Переменные окружения для transaction-collector

- `MONGODB_HOST` - хост MongoDB (по умолчанию: `localhost`)
- `MONGODB_PORT` - порт MongoDB (по умолчанию: `27017`)
- `MONGODB_USER` - пользователь MongoDB (по умолчанию: `mongo_user`)
- `MONGODB_PASSWORD` - пароль MongoDB (по умолчанию: `mongo_password`)
- `MONGODB_DB` - имя базы данных (по умолчанию: `banking_data`)
- `MONGODB_COLLECTION` - имя коллекции (по умолчанию: `transactions`)
- `COLLECT_INTERVAL` - интервал сбора транзакций в секундах (по умолчанию: `60`)
- `USE_KAGGLE_DATA` - использовать данные с Kaggle (по умолчанию: `false`)
- `KAGGLE_DATASET` - имя датасета с Kaggle (например: `mlg-ulb/creditcardfraud`)

### Airflow Variables

Настройте следующие переменные в Airflow UI (Admin -> Variables):

- `MONGODB_HOST` - хост MongoDB
- `MONGODB_PORT` - порт MongoDB
- `MONGODB_USER` - пользователь MongoDB
- `MONGODB_PASSWORD` - пароль MongoDB
- `MONGODB_DB` - имя базы данных MongoDB
- `MONGODB_COLLECTION` - имя коллекции MongoDB
- `POSTGRES_HOST` - хост PostgreSQL
- `POSTGRES_PORT` - порт PostgreSQL
- `POSTGRES_USER` - пользователь PostgreSQL
- `POSTGRES_PASSWORD` - пароль PostgreSQL
- `POSTGRES_DB` - имя базы данных PostgreSQL

## Использование

### Запуск transaction-collector локально

```bash
uv run python -m bankshield.collector
```

или

```bash
uv run python scripts/run_collector.py
```

### Загрузка датасетов с Kaggle

```bash
uv run python scripts/download_kaggle_data.py
```

Для загрузки конкретного датасета:
```bash
uv run python scripts/download_kaggle_data.py mlg-ulb/creditcardfraud
```

Популярные датасеты для детекции мошенничества:
- `mlg-ulb/creditcardfraud` - Credit Card Fraud Detection
- `ntnu-testimon/paysim1` - Synthetic Financial Dataset
- `ealaxi/paysim2` - PaySim2 Financial Simulation
- `vishnusairam/credit-card-fraud-detection` - Credit Card Fraud
- `rupakroy/online-payments-fraud-detection-dataset` - Online Payments Fraud

### Проверка данных в MongoDB

```bash
docker-compose exec mongodb mongosh -u mongo_user -p mongo_password
```

```javascript
use banking_data
db.transactions.find().limit(5).pretty()
db.transactions.countDocuments({is_fraud: true})
```

### Проверка данных в PostgreSQL

```bash
docker-compose exec postgres psql -U analytics_user -d analytics_db
```

```sql
-- Просмотр транзакций
SELECT * FROM transactions ORDER BY timestamp DESC LIMIT 10;

-- Статистика по мошенничеству
SELECT
    COUNT(*) as total_transactions,
    SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END) as fraudulent_transactions,
    ROUND(100.0 * SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END) / COUNT(*), 2) as fraud_percentage
FROM transactions;

-- Топ пользователей по количеству транзакций
SELECT user_id, COUNT(*) as transaction_count
FROM transactions
GROUP BY user_id
ORDER BY transaction_count DESC
LIMIT 10;

-- Средний риск-скор по категориям мерчантов
SELECT merchant_category,
       AVG(risk_score) as avg_risk_score,
       COUNT(*) as transaction_count
FROM transactions
GROUP BY merchant_category
ORDER BY avg_risk_score DESC;
```

## ETL-процесс

Airflow DAG `transactions_etl` автоматически:

1. **Extract** - извлекает транзакции из MongoDB
2. **Load** - загружает транзакции в PostgreSQL

DAG запускается каждые 30 минут и обрабатывает только новые транзакции (на основе timestamp).

Схема таблицы `transactions` в PostgreSQL включает:
- Основные поля транзакции (ID, сумма, валюта, тип)
- Информацию о пользователе и мерчанте
- Геолокацию
- Информацию об устройстве
- Флаг мошенничества и риск-скор
- Индексы для быстрого поиска

## Развертывание на сервере

1. Скопируйте проект на сервер:
```bash
scp -r . user@server:/path/to/project
```

2. На сервере запустите:
```bash
docker-compose up -d
```

3. Проверьте логи:
```bash
docker-compose logs -f
```

## Разработка

### Добавление зависимостей

```bash
uv add <package-name>
```

### Добавление dev-зависимостей

```bash
uv add --dev <package-name>
```

### Запуск линтера

```bash
uv run ruff check .
```

### Форматирование кода

```bash
uv run ruff format .
```

### Запуск тестов с покрытием

```bash
uv run pytest --cov=bankshield --cov-report=html
```

## Структура транзакции

Пример транзакции в MongoDB:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "transaction_id": "TXN123456",
  "user_id": "USER1234",
  "amount": 150.50,
  "currency": "USD",
  "transaction_type": "debit",
  "merchant_category": "grocery",
  "merchant_name": "Merchant_42",
  "location": {
    "country": "USA",
    "city": "New York",
    "latitude": 40.7128,
    "longitude": -74.0060
  },
  "device_info": {
    "device_type": "mobile",
    "os": "iOS",
    "ip_address": "192.168.1.1"
  },
  "is_fraud": false,
  "risk_score": 0.234,
  "metadata": {
    "session_id": "SESS12345",
    "user_agent": "Mozilla/5.0..."
  }
}
```

## Лицензия

MIT
