"""EL DAG for extracting transactions from MongoDB and loading RAW data into PostgreSQL.

EL-процесс: Извлечение данных из MongoDB и загрузка в PostgreSQL БЕЗ трансформации.
Вся трансформация (парсинг JSON, очистка) выполняется в DBT слое STG.
"""

from datetime import datetime, timedelta
from typing import Dict, List

from airflow import DAG
from airflow.operators.python import PythonOperator

# Default arguments for the DAG
default_args = {
    "owner": "data_engineer",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

# DAG definition
dag = DAG(
    "transactions_el",
    default_args=default_args,
    description="EL process: Extract transactions from MongoDB, Load RAW to PostgreSQL (no transformation)",
    schedule_interval=timedelta(minutes=30),
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["el", "mongodb", "postgresql", "bankshield"],
)


def extract_transactions(**context) -> List[Dict]:
    """
    Extract transactions from MongoDB.

    Returns:
        List of transaction documents from MongoDB (RAW, без трансформации)
    """
    import json

    from airflow.models import Variable
    from pymongo import MongoClient

    # MongoDB connection parameters
    mongo_host = Variable.get("MONGODB_HOST", default_var="mongodb")
    mongo_port = int(Variable.get("MONGODB_PORT", default_var="27017"))
    mongo_user = Variable.get("MONGODB_USER", default_var="mongo_user")
    mongo_password = Variable.get("MONGODB_PASSWORD", default_var="mongo_password")
    mongo_db = Variable.get("MONGODB_DB", default_var="banking_data")
    mongo_collection = Variable.get(
        "MONGODB_COLLECTION",
        default_var="transactions",
    )

    # Connect to MongoDB
    connection_string = (
        f"mongodb://{mongo_user}:{mongo_password}@{mongo_host}:{mongo_port}/"
    )
    client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)

    try:
        db = client[mongo_db]
        collection = db[mongo_collection]

        # Get the last execution time to extract only new data
        last_run = context.get("data_interval_start")
        if last_run:
            query = {"timestamp": {"$gte": last_run}}
        else:
            query = {}

        # Extract RAW data without any transformation
        documents = list(collection.find(query))
        print(f"Extracted {len(documents)} transactions from MongoDB")

        # Convert ObjectId to string and nested dicts to JSON strings for PostgreSQL
        for doc in documents:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            # Сохраняем вложенные объекты как JSON строки для последующего парсинга в DBT
            if "location" in doc and isinstance(doc["location"], dict):
                doc["location_json"] = json.dumps(doc["location"])
            if "device_info" in doc and isinstance(doc["device_info"], dict):
                doc["device_info_json"] = json.dumps(doc["device_info"])
            if "metadata" in doc and isinstance(doc["metadata"], dict):
                doc["metadata_json"] = json.dumps(doc["metadata"])

        return documents
    finally:
        client.close()


def load_transactions(**context) -> None:
    """
    Load RAW transactions into PostgreSQL.

    Загружает данные БЕЗ парсинга вложенных объектов.
    Парсинг выполняется в DBT слое STG (stg_transactions model).

    Args:
        context: Airflow context containing task instance
    """
    from airflow.models import Variable
    from psycopg2 import connect
    from psycopg2.extras import execute_values

    # Get data from previous task
    ti = context["ti"]
    documents = ti.xcom_pull(task_ids="extract_transactions")

    if not documents:
        print("No transactions to load")
        return

    # PostgreSQL connection parameters
    pg_host = Variable.get("POSTGRES_HOST", default_var="postgres")
    pg_port = int(Variable.get("POSTGRES_PORT", default_var="5432"))
    pg_user = Variable.get("POSTGRES_USER", default_var="analytics_user")
    pg_password = Variable.get("POSTGRES_PASSWORD", default_var="analytics_password")
    pg_db = Variable.get("POSTGRES_DB", default_var="analytics_db")

    # Connect to PostgreSQL
    conn = connect(
        host=pg_host,
        port=pg_port,
        user=pg_user,
        password=pg_password,
        database=pg_db,
    )

    try:
        cursor = conn.cursor()

        # Create RAW table - хранит данные как есть, без парсинга
        # Парсинг location, device_info, metadata будет в DBT (STG слой)
        create_table_query = """
        CREATE TABLE IF NOT EXISTS transactions_raw (
            id SERIAL PRIMARY KEY,
            mongo_id VARCHAR(255) UNIQUE,
            timestamp TIMESTAMP NOT NULL,
            transaction_id VARCHAR(100),
            user_id VARCHAR(100),
            amount DECIMAL(15, 2),
            currency VARCHAR(10),
            transaction_type VARCHAR(50),
            merchant_category VARCHAR(100),
            merchant_name VARCHAR(255),
            is_fraud BOOLEAN DEFAULT FALSE,
            risk_score DECIMAL(5, 3),
            -- JSON поля для парсинга в DBT
            location_json JSONB,
            device_info_json JSONB,
            metadata_json JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        cursor.execute(create_table_query)

        # Create indexes
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_raw_timestamp ON transactions_raw(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_raw_transaction_id ON transactions_raw(transaction_id)",
            "CREATE INDEX IF NOT EXISTS idx_raw_user_id ON transactions_raw(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_raw_is_fraud ON transactions_raw(is_fraud)",
        ]
        for index_query in indexes:
            try:
                cursor.execute(index_query)
            except Exception as e:
                print(f"Warning: Could not create index: {e}")

        # Prepare RAW data for insertion - NO parsing of nested objects
        values = []
        for doc in documents:
            values.append(
                (
                    doc.get("_id"),
                    doc.get("timestamp"),
                    doc.get("transaction_id"),
                    doc.get("user_id"),
                    doc.get("amount"),
                    doc.get("currency"),
                    doc.get("transaction_type"),
                    doc.get("merchant_category"),
                    doc.get("merchant_name"),
                    doc.get("is_fraud", False),
                    doc.get("risk_score"),
                    # JSON поля сохраняются как есть
                    doc.get("location_json"),
                    doc.get("device_info_json"),
                    doc.get("metadata_json"),
                ),
            )

        # Insert RAW data (using ON CONFLICT to avoid duplicates)
        insert_query = """
        INSERT INTO transactions_raw (
            mongo_id, timestamp, transaction_id, user_id, amount, currency,
            transaction_type, merchant_category, merchant_name,
            is_fraud, risk_score,
            location_json, device_info_json, metadata_json
        ) VALUES %s
        ON CONFLICT (mongo_id) DO NOTHING
        """
        execute_values(cursor, insert_query, values)
        conn.commit()

        fraud_count = sum(1 for doc in documents if doc.get("is_fraud", False))
        print(
            f"Loaded {len(values)} RAW transactions into PostgreSQL "
            f"({fraud_count} fraudulent transactions). "
            f"Parsing will be done in DBT STG layer."
        )
    finally:
        cursor.close()
        conn.close()


# Define tasks
extract_task = PythonOperator(
    task_id="extract_transactions",
    python_callable=extract_transactions,
    dag=dag,
)

load_task = PythonOperator(
    task_id="load_transactions",
    python_callable=load_transactions,
    dag=dag,
)

# Set task dependencies: Extract -> Load
# Transformation is done separately in DBT (dbt_transformations DAG)
extract_task >> load_task
