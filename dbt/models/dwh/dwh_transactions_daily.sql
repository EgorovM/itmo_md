{{
    config(
        materialized='incremental',
        unique_key='unique_key',
        tags=['dwh', 'warehouse', 'incremental'],
        schema='dwh',
        incremental_strategy='merge',
        on_schema_change='append_new_columns'
    )
}}

-- DWH model: ежедневная агрегация транзакций
-- Инкрементальная загрузка по дате (merge strategy)

with ods_transactions as (
    select * from {{ ref('ods_transactions') }}
),

daily_aggregates as (
    select
        transaction_date,
        currency,
        transaction_type,
        merchant_category,
        country,

        -- Количество транзакций
        count(*) as total_transactions,
        count(distinct user_id) as unique_users,
        count(distinct merchant_name) as unique_merchants,

        -- Финансовые метрики
        sum(amount) as total_amount,
        avg(amount) as avg_amount,
        min(amount) as min_amount,
        max(amount) as max_amount,
        percentile_cont(0.5) within group (order by amount) as median_amount,

        -- Фрод метрики
        sum(case when is_fraud then 1 else 0 end) as fraud_transactions,
        sum(case when is_fraud then amount else 0 end) as fraud_amount,
        avg(case when is_fraud then 1.0 else 0.0 end) as fraud_rate,
        avg(risk_score) as avg_risk_score,
        max(risk_score) as max_risk_score,

        -- Категоризация по сумме
        sum(case when amount_category = 'high' then 1 else 0 end) as high_amount_transactions,
        sum(case when amount_category = 'medium' then 1 else 0 end) as medium_amount_transactions,
        sum(case when amount_category = 'low' then 1 else 0 end) as low_amount_transactions,

        -- Категоризация по риску
        sum(case when risk_category = 'high_risk' then 1 else 0 end) as high_risk_transactions,
        sum(case when risk_category = 'medium_risk' then 1 else 0 end) as medium_risk_transactions,
        sum(case when risk_category = 'low_risk' then 1 else 0 end) as low_risk_transactions,

        -- Устройства
        count(distinct device_type) as unique_device_types,
        count(distinct os) as unique_os,

        -- Время загрузки
        max(loaded_at) as last_loaded_at,

        -- Составной ключ для уникальности (для merge strategy)
        transaction_date || '-' || coalesce(currency, 'NULL') || '-' || coalesce(transaction_type, 'NULL') || '-' || coalesce(merchant_category, 'NULL') || '-' || coalesce(country, 'NULL') as unique_key

    from ods_transactions
    group by
        transaction_date,
        currency,
        transaction_type,
        merchant_category,
        country
)

select * from daily_aggregates

{% if is_incremental() %}
    -- Инкрементальная логика: обновляем только новые/измененные даты
    where transaction_date >= (select max(transaction_date) from {{ this }})
{% endif %}
