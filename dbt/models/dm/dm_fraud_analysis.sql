{{
    config(
        materialized='table',
        tags=['dm', 'mart', 'fraud'],
        schema='dm'
    )
}}

-- Data Mart: анализ мошенничества
-- Бизнес-витрина для анализа фрод-транзакций

with daily_fraud as (
    select * from {{ ref('dwh_transactions_daily') }}
),

user_fraud as (
    select * from {{ ref('dwh_user_transactions') }}
),

fraud_summary as (
    select
        -- Временные метрики
        transaction_date,
        currency,
        country,

        -- Общие метрики
        total_transactions,
        fraud_transactions,
        fraud_amount,
        fraud_rate,

        -- Риск метрики
        avg_risk_score,
        max_risk_score,
        high_risk_transactions,

        -- Финансовые метрики
        total_amount,
        avg_amount,
        max_amount,

        -- Процент фрод от общей суммы
        case
            when total_amount > 0 then (fraud_amount / total_amount) * 100
            else 0
        end as fraud_amount_percentage,

        -- Категории мерчантов с фродом
        merchant_category,
        transaction_type,

        -- Время загрузки
        last_loaded_at

    from daily_fraud
    where fraud_transactions > 0
),

high_risk_users as (
    select
        user_id,
        total_transactions,
        fraud_transactions_count,
        fraud_rate,
        avg_risk_score,
        max_risk_score,
        total_spent,
        fraud_amount_total,
        most_common_country,
        most_common_merchant_category,
        last_loaded_at
    from user_fraud
    where fraud_rate > {{ var('fraud_threshold', 0.7) }}
       or max_risk_score > 0.8
)

select
    'daily_fraud' as analysis_type,
    transaction_date::text as dimension_value,
    currency,
    country,
    merchant_category,
    transaction_type,
    total_transactions,
    fraud_transactions as fraud_count,
    fraud_amount,
    fraud_rate,
    avg_risk_score,
    max_risk_score,
    fraud_amount_percentage,
    last_loaded_at
from fraud_summary

union all

select
    'high_risk_users' as analysis_type,
    user_id as dimension_value,
    null as currency,
    most_common_country as country,
    most_common_merchant_category as merchant_category,
    null as transaction_type,
    total_transactions,
    fraud_transactions_count as fraud_count,
    fraud_amount_total as fraud_amount,
    fraud_rate,
    avg_risk_score,
    max_risk_score,
    case
        when total_spent > 0 then (fraud_amount_total / total_spent) * 100
        else 0
    end as fraud_amount_percentage,
    last_loaded_at
from high_risk_users
