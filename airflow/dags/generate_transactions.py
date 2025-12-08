"""Airflow DAG for generating synthetic transactions via API.

Генерирует 200 транзакций каждые 2 часа через REST API.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    "owner": "data_engineer",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "generate_transactions",
    default_args=default_args,
    description="Generate 200 synthetic transactions every 2 hours via REST API",
    schedule_interval=timedelta(hours=2),
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["data-generation", "transactions", "bankshield"],
)


def generate_transactions_batch(**context) -> dict:
    """
    Генерация 200 транзакций через REST API.

    Args:
        context: Airflow context

    Returns:
        dict: Результат генерации
    """
    import requests
    from airflow.models import Variable

    # Получаем URL API из переменных Airflow или используем дефолт
    # В Docker Compose API доступен по имени сервиса 'api' на порту 8000 (внутри контейнера)
    api_host = Variable.get("API_HOST", default_var="api")
    api_port = int(Variable.get("API_PORT", default_var="8000"))
    api_url = f"http://{api_host}:{api_port}"

    count = 200

    try:
        print(f"🔗 Вызов API: {api_url}/transactions/batch?count={count}")

        response = requests.post(
            f"{api_url}/transactions/batch",
            params={"count": count},
            timeout=300,
        )
        response.raise_for_status()

        result = response.json()
        inserted = result.get("inserted_count", result.get("generated_count", count))
        print(
            f"✅ Успешно сгенерировано {result.get('generated_count', count)} транзакций"
        )
        print(f"💾 Вставлено в MongoDB: {inserted} транзакций")
        print(f"📊 Сообщение: {result.get('message', '')}")

        return {
            "success": True,
            "generated_count": result.get("generated_count", count),
            "inserted_count": inserted,
            "message": result.get("message", ""),
        }

    except requests.exceptions.ConnectionError as e:
        error_msg = f"Не удалось подключиться к API {api_url}: {e}"
        print(f"❌ {error_msg}")
        print("💡 Проверьте, что сервис 'api' запущен и доступен")
        raise Exception(error_msg) from e
    except requests.exceptions.RequestException as e:
        error_msg = f"Ошибка при вызове API: {e}"
        print(f"❌ {error_msg}")
        if hasattr(e, "response") and e.response is not None:
            print(f"📄 Ответ сервера: {e.response.text}")
        raise Exception(error_msg) from e


# Определяем задачу
generate_task = PythonOperator(
    task_id="generate_transactions_batch",
    python_callable=generate_transactions_batch,
    dag=dag,
)
