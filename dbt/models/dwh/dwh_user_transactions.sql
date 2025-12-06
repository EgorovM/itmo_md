{{
    config(
        materialized='incremental',
        unique_key='user_id',
        tags=['dwh', 'warehouse', 'incremental'],
        schema='dwh',
        incremental_strategy='merge',
        on_schema_change='append_new_columns'
    )
}}

-- DWH model: агрегация транзакций по пользователям
-- Инкрементальная загрузка по user_id (merge strategy)

with ods_transactions as (
    select * from {{ ref('ods_transactions') }}
),

user_aggregates as (
    select
        user_id,

        -- Общие метрики
        count(*) as total_transactions,
        min(transaction_timestamp) as first_transaction_date,
        max(transaction_timestamp) as last_transaction_date,
        date_part('day', max(transaction_timestamp) - min(transaction_timestamp)) as customer_lifetime_days,

        -- Финансовые метрики
        sum(amount) as total_spent,
        avg(amount) as avg_transaction_amount,
        min(amount) as min_transaction_amount,
        max(amount) as max_transaction_amount,

        -- Валюты
        count(distinct currency) as currencies_used,
        mode() within group (order by currency) as most_used_currency,

        -- Типы транзакций
        count(distinct transaction_type) as transaction_types_used,
        mode() within group (order by transaction_type) as most_common_transaction_type,

        -- Мерчанты
        count(distinct merchant_category) as merchant_categories_used,
        count(distinct merchant_name) as unique_merchants,
        mode() within group (order by merchant_category) as most_common_merchant_category,

        -- География
        count(distinct country) as countries_used,
        count(distinct city) as cities_used,
        mode() within group (order by country) as most_common_country,

        -- Фрод метрики
        sum(case when is_fraud then 1 else 0 end) as fraud_transactions_count,
        sum(case when is_fraud then amount else 0 end) as fraud_amount_total,
        avg(case when is_fraud then 1.0 else 0.0 end) as fraud_rate,
        avg(risk_score) as avg_risk_score,
        max(risk_score) as max_risk_score,

        -- Устройства
        count(distinct device_type) as device_types_used,
        count(distinct os) as os_used,
        mode() within group (order by device_type) as most_used_device_type,

        -- Временные паттерны
        mode() within group (order by transaction_hour) as most_active_hour,
        mode() within group (order by transaction_day_of_week) as most_active_day_of_week,

        -- Время загрузки
        max(loaded_at) as last_loaded_at

    from ods_transactions
    group by user_id
)

select * from user_aggregates

{% if is_incremental() %}
    -- Инкрементальная логика: обновляем только пользователей с новыми транзакциями
    where user_id in (
        select distinct user_id
        from ods_transactions
        where loaded_at > (select max(last_loaded_at) from {{ this }})
    )
{% endif %}
