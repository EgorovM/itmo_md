#!/bin/bash
# Скрипт для проверки DBT в контейнере Airflow

echo "🔍 Проверка DBT в контейнере Airflow..."
echo ""

# Проверка существования директории
echo "1. Проверка директории /opt/airflow/dbt:"
docker compose exec airflow-webserver ls -la /opt/airflow/dbt 2>&1 | head -10 || echo "❌ Директория не найдена"

echo ""
echo "2. Проверка установки DBT:"
docker compose exec airflow-webserver dbt --version 2>&1 || echo "❌ DBT не установлен"

echo ""
echo "3. Проверка структуры DBT проекта:"
docker compose exec airflow-webserver ls -la /opt/airflow/dbt/models 2>&1 | head -5 || echo "❌ Модели не найдены"

echo ""
echo "4. Проверка profiles.yml:"
docker compose exec airflow-webserver test -f /opt/airflow/dbt/profiles.yml && echo "✅ profiles.yml найден" || echo "❌ profiles.yml не найден"

echo ""
echo "5. Тест команды dbt deps:"
docker compose exec airflow-webserver bash -c "cd /opt/airflow/dbt && dbt deps --profiles-dir ." 2>&1 | tail -10

echo ""
echo "6. Проверка подключения к PostgreSQL:"
docker compose exec airflow-webserver bash -c "cd /opt/airflow/dbt && dbt debug --profiles-dir . --target prod" 2>&1 | tail -15
