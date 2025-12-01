#!/bin/bash
# Скрипт для автоматической настройки Airflow Variables

echo "Настройка Airflow Variables..."

# MongoDB variables
docker-compose exec -T airflow-webserver airflow variables set MONGODB_HOST mongodb
docker-compose exec -T airflow-webserver airflow variables set MONGODB_PORT 27017
docker-compose exec -T airflow-webserver airflow variables set MONGODB_USER mongo_user
docker-compose exec -T airflow-webserver airflow variables set MONGODB_PASSWORD mongo_password
docker-compose exec -T airflow-webserver airflow variables set MONGODB_DB banking_data
docker-compose exec -T airflow-webserver airflow variables set MONGODB_COLLECTION transactions

# PostgreSQL variables
docker-compose exec -T airflow-webserver airflow variables set POSTGRES_HOST postgres
docker-compose exec -T airflow-webserver airflow variables set POSTGRES_PORT 5432
docker-compose exec -T airflow-webserver airflow variables set POSTGRES_USER analytics_user
docker-compose exec -T airflow-webserver airflow variables set POSTGRES_PASSWORD analytics_password
docker-compose exec -T airflow-webserver airflow variables set POSTGRES_DB analytics_db

echo "✅ Все переменные настроены!"
echo ""
echo "Проверка переменных:"
docker-compose exec -T airflow-webserver airflow variables list
