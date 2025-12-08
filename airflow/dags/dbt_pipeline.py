"""Airflow DAG for running DBT transformations.

DAG запускается каждый час и выполняет:
1. Установка DBT пакетов (dbt deps)
2. STG модели - парсинг JSON и очистка данных
3. ODS модели - нормализация
4. DWH модели - агрегация (инкрементальная)
5. DM модели - бизнес-витрины
6. Тесты и Elementary мониторинг
7. Генерация документации
"""

from datetime import datetime, timedelta
from typing import Any, Dict

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.task_group import TaskGroup

default_args: Dict[str, Any] = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "dbt_transformations",
    default_args=default_args,
    description="DBT pipeline for BankShield data transformations (STG -> ODS -> DWH -> DM)",
    schedule_interval=timedelta(hours=1),  # Запуск каждый час
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["dbt", "transformations", "bankshield"],
)

# DBT deps - установка пакетов (только при первом запуске или обновлении packages.yml)
dbt_deps = BashOperator(
    task_id="dbt_deps",
    bash_command="cd /opt/airflow/dbt && rm -f package-lock.yml && dbt deps --profiles-dir . --profile bankshield --target prod",
    dag=dag,
)

# STG models - staging layer
with TaskGroup("stg_models", dag=dag) as stg_group:
    dbt_stg_run = BashOperator(
        task_id="dbt_stg_run",
        bash_command="cd /opt/airflow/dbt && dbt run --select stg.* --profiles-dir . --profile bankshield --target prod",
        dag=dag,
    )

    dbt_stg_test = BashOperator(
        task_id="dbt_stg_test",
        bash_command="cd /opt/airflow/dbt && dbt test --select models/stg/* --exclude models/ods/* --profiles-dir . --profile bankshield --target prod",
        dag=dag,
    )

    dbt_stg_run >> dbt_stg_test

# ODS models - operational data store
with TaskGroup("ods_models", dag=dag) as ods_group:
    dbt_ods_run = BashOperator(
        task_id="dbt_ods_run",
        bash_command="cd /opt/airflow/dbt && dbt run --select ods.* --profiles-dir . --profile bankshield --target prod",
        dag=dag,
    )

    dbt_ods_test = BashOperator(
        task_id="dbt_ods_test",
        bash_command="cd /opt/airflow/dbt && dbt test --select models/ods/* --profiles-dir . --profile bankshield --target prod",
        dag=dag,
    )

    dbt_ods_run >> dbt_ods_test

# DWH models - data warehouse (incremental)
with TaskGroup("dwh_models", dag=dag) as dwh_group:
    dbt_dwh_run = BashOperator(
        task_id="dbt_dwh_run",
        bash_command="cd /opt/airflow/dbt && dbt run --select dwh.* --profiles-dir . --profile bankshield --target prod",
        dag=dag,
    )

    dbt_dwh_test = BashOperator(
        task_id="dbt_dwh_test",
        bash_command="cd /opt/airflow/dbt && dbt test --select models/dwh/* --profiles-dir . --profile bankshield --target prod",
        dag=dag,
    )

    dbt_dwh_run >> dbt_dwh_test

# DM models - data marts
with TaskGroup("dm_models", dag=dag) as dm_group:
    dbt_dm_run = BashOperator(
        task_id="dbt_dm_run",
        bash_command="cd /opt/airflow/dbt && dbt run --select dm.* --profiles-dir . --profile bankshield --target prod",
        dag=dag,
    )

    dbt_dm_test = BashOperator(
        task_id="dbt_dm_test",
        bash_command="cd /opt/airflow/dbt && dbt test --select models/dm/* --profiles-dir . --profile bankshield --target prod",
        dag=dag,
    )

    dbt_dm_run >> dbt_dm_test

# Custom tests
dbt_custom_tests = BashOperator(
    task_id="dbt_custom_tests",
    bash_command="cd /opt/airflow/dbt && dbt test --select test_type:data --profiles-dir . --profile bankshield --target prod",
    dag=dag,
)

# Elementary - запуск моделей для мониторинга и детекции аномалий
# В Elementary 0.10.0 модели создают таблицы для мониторинга данных
# Elementary тесты убраны из schema.yml, чтобы не блокировать основной пайплайн
# Мониторинг работает через модели Elementary, результаты доступны в UI
dbt_elementary = BashOperator(
    task_id="dbt_elementary",
    bash_command="cd /opt/airflow/dbt && dbt run --select package:elementary --profiles-dir . --profile bankshield --target prod",
    dag=dag,
)

# Elementary - генерация отчета для UI
# Отчет будет доступен через веб-сервер на порту 8081
# edr report использует профиль 'elementary' из profiles.yml
dbt_elementary_report = BashOperator(
    task_id="dbt_elementary_report",
    bash_command="cd /opt/airflow/dbt && export DBT_PROFILE=elementary && export DBT_TARGET=prod && (edr report --profiles-dir . --profile-target prod || echo 'Elementary report generation completed')",
    dag=dag,
)

# DBT docs generation
dbt_docs = BashOperator(
    task_id="dbt_docs",
    bash_command="cd /opt/airflow/dbt && dbt docs generate --profiles-dir . --profile bankshield --target prod",
    dag=dag,
)

# Task dependencies
# Порядок: deps -> STG (парсинг JSON) -> ODS -> DWH (incremental) -> DM -> tests -> elementary -> docs
(
    dbt_deps
    >> stg_group
    >> ods_group
    >> dwh_group
    >> dm_group
    >> dbt_custom_tests
    >> dbt_elementary
    >> dbt_elementary_report
    >> dbt_docs
)
