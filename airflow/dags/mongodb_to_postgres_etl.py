"""ETL DAG for extracting data from MongoDB and loading into PostgreSQL."""

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
    "mongodb_to_postgres_etl",
    default_args=default_args,
    description="ETL process: Extract from MongoDB, Load to PostgreSQL",
    schedule_interval=timedelta(minutes=30),
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["etl", "mongodb", "postgresql"],
)


def extract_from_mongodb(**context) -> List[Dict]:
    """
    Extract data from MongoDB.

    Returns:
        List of documents from MongoDB
    """
    from airflow.models import Variable
    from pymongo import MongoClient

    # MongoDB connection parameters
    mongo_host = Variable.get("MONGODB_HOST", default_var="mongodb")
    mongo_port = int(Variable.get("MONGODB_PORT", default_var="27017"))
    mongo_user = Variable.get("MONGODB_USER", default_var="mongo_user")
    mongo_password = Variable.get("MONGODB_PASSWORD", default_var="mongo_password")
    mongo_db = Variable.get("MONGODB_DB", default_var="weather_data")
    mongo_collection = Variable.get(
        "MONGODB_COLLECTION",
        default_var="sensor_data",
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
        print(f"Extracted {len(documents)} documents from MongoDB")

        # Convert ObjectId to string for JSON serialization
        for doc in documents:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])

        return documents
    finally:
        client.close()


def load_to_postgresql(**context) -> None:
    """
    Load data into PostgreSQL.

    Args:
        context: Airflow context containing task instance
    """
    from airflow.models import Variable
    from psycopg2 import connect
    from psycopg2.extras import execute_values

    # Get data from previous task
    ti = context["ti"]
    documents = ti.xcom_pull(task_ids="extract_from_mongodb")

    if not documents:
        print("No data to load")
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
        CREATE TABLE IF NOT EXISTS sensor_data (
            id SERIAL PRIMARY KEY,
            mongo_id VARCHAR(255) UNIQUE,
            timestamp TIMESTAMP NOT NULL,
            temperature DECIMAL(5, 2),
            humidity DECIMAL(5, 2),
            pm2_5 DECIMAL(6, 2),
            pm10 DECIMAL(6, 2),
            co2 DECIMAL(6, 2),
            aqi INTEGER,
            latitude DECIMAL(9, 6),
            longitude DECIMAL(9, 6),
            sensor_id VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        cursor.execute(create_table_query)

        # Prepare data for insertion
        values = []
        for doc in documents:
            values.append(
                (
                    doc.get("_id"),
                    doc.get("timestamp"),
                    doc.get("temperature"),
                    doc.get("humidity"),
                    doc.get("air_quality", {}).get("pm2_5"),
                    doc.get("air_quality", {}).get("pm10"),
                    doc.get("air_quality", {}).get("co2"),
                    doc.get("air_quality", {}).get("aqi"),
                    doc.get("location", {}).get("latitude"),
                    doc.get("location", {}).get("longitude"),
                    doc.get("sensor_id"),
                )
            )

        # Insert data (using ON CONFLICT to avoid duplicates)
        insert_query = """
        INSERT INTO sensor_data (
            mongo_id, timestamp, temperature, humidity,
            pm2_5, pm10, co2, aqi, latitude, longitude, sensor_id
        ) VALUES %s
        ON CONFLICT (mongo_id) DO NOTHING
        """
        execute_values(cursor, insert_query, values)
        conn.commit()

        print(f"Loaded {len(values)} records into PostgreSQL")
    finally:
        cursor.close()
        conn.close()


# Define tasks
extract_task = PythonOperator(
    task_id="extract_from_mongodb",
    python_callable=extract_from_mongodb,
    dag=dag,
)

load_task = PythonOperator(
    task_id="load_to_postgresql",
    python_callable=load_to_postgresql,
    dag=dag,
)

# Set task dependencies
extract_task >> load_task
