"""ETL DAG for extracting transactions from MongoDB and loading into PostgreSQL."""

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
    "transactions_etl",
    default_args=default_args,
    description="ETL process: Extract transactions from MongoDB, Load to PostgreSQL",
    schedule_interval=timedelta(minutes=30),
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["etl", "mongodb", "postgresql", "fraud-detection"],
)


def extract_transactions(**context) -> List[Dict]:
    """
    Extract transactions from MongoDB.

    Returns:
        List of transaction documents from MongoDB
    """
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

        # Extract data
        documents = list(collection.find(query))
        print(f"Extracted {len(documents)} transactions from MongoDB")

        # Convert ObjectId to string for JSON serialization
        for doc in documents:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])

        return documents
    finally:
        client.close()


def load_transactions(**context) -> None:
    """
    Load transactions into PostgreSQL.

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

        # Create table if not exists
        create_table_query = """
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            mongo_id VARCHAR(255) UNIQUE,
            timestamp TIMESTAMP NOT NULL,
            transaction_id VARCHAR(100) UNIQUE,
            user_id VARCHAR(100),
            amount DECIMAL(15, 2) NOT NULL,
            currency VARCHAR(10),
            transaction_type VARCHAR(50),
            merchant_category VARCHAR(100),
            merchant_name VARCHAR(255),
            country VARCHAR(100),
            city VARCHAR(100),
            latitude DECIMAL(9, 6),
            longitude DECIMAL(9, 6),
            device_type VARCHAR(50),
            os VARCHAR(50),
            ip_address VARCHAR(50),
            is_fraud BOOLEAN DEFAULT FALSE,
            risk_score DECIMAL(5, 3),
            session_id VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        cursor.execute(create_table_query)

        # Create indexes if not exists
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_timestamp ON transactions(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_user_id ON transactions(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_is_fraud ON transactions(is_fraud)",
            "CREATE INDEX IF NOT EXISTS idx_transaction_id ON transactions(transaction_id)",
        ]
        for index_query in indexes:
            try:
                cursor.execute(index_query)
            except Exception as e:
                print(f"Warning: Could not create index: {e}")

        # Prepare data for insertion
        values = []
        for doc in documents:
            location = doc.get("location", {})
            device_info = doc.get("device_info", {})
            metadata = doc.get("metadata", {})

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
                    location.get("country"),
                    location.get("city"),
                    location.get("latitude"),
                    location.get("longitude"),
                    device_info.get("device_type"),
                    device_info.get("os"),
                    device_info.get("ip_address"),
                    doc.get("is_fraud", False),
                    doc.get("risk_score"),
                    metadata.get("session_id"),
                ),
            )

        # Insert data (using ON CONFLICT to avoid duplicates)
        insert_query = """
        INSERT INTO transactions (
            mongo_id, timestamp, transaction_id, user_id, amount, currency,
            transaction_type, merchant_category, merchant_name,
            country, city, latitude, longitude,
            device_type, os, ip_address, is_fraud, risk_score, session_id
        ) VALUES %s
        ON CONFLICT (mongo_id) DO NOTHING
        """
        execute_values(cursor, insert_query, values)
        conn.commit()

        fraud_count = sum(1 for doc in documents if doc.get("is_fraud", False))
        print(
            f"Loaded {len(values)} transactions into PostgreSQL "
            f"({fraud_count} fraudulent transactions)",
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

# Set task dependencies
extract_task >> load_task
