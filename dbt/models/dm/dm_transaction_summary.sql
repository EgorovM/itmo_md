{{
    config(
        materialized='table',
        tags=['dm', 'mart', 'summary'],
        schema='dm'
    )
}}

-- Data Mart: сводка по транзакциям
-- Бизнес-витрина для общего анализа транзакций

with daily_agg as (
    select * from {{ ref('dwh_transactions_daily') }}
),

user_agg as (
    select * from {{ ref('dwh_user_transactions') }}
),

summary as (
    select
        'overall' as summary_type,
        'all_time' as period,
        count(distinct transaction_date) as days_analyzed,
        sum(total_transactions) as total_transactions,
        count(distinct user_id) as total_users,
        sum(total_amount) as total_amount,
        avg(avg_amount) as avg_transaction_amount,
        sum(fraud_transactions) as total_fraud_transactions,
        sum(fraud_amount) as total_fraud_amount,
        avg(fraud_rate) as overall_fraud_rate,
        avg(avg_risk_score) as overall_avg_risk_score,
        max(max_risk_score) as overall_max_risk_score
    from daily_agg
    cross join (select count(distinct user_id) as user_id from user_agg) u
),

by_currency as (
    select
        'by_currency' as summary_type,
        currency as period,
        count(distinct transaction_date) as days_analyzed,
        sum(total_transactions) as total_transactions,
        null::bigint as total_users,
        sum(total_amount) as total_amount,
        avg(avg_amount) as avg_transaction_amount,
        sum(fraud_transactions) as total_fraud_transactions,
        sum(fraud_amount) as total_fraud_amount,
        avg(fraud_rate) as overall_fraud_rate,
        avg(avg_risk_score) as overall_avg_risk_score,
        max(max_risk_score) as overall_max_risk_score
    from daily_agg
    group by currency
),

by_country as (
    select
        'by_country' as summary_type,
        country as period,
        count(distinct transaction_date) as days_analyzed,
        sum(total_transactions) as total_transactions,
        null::bigint as total_users,
        sum(total_amount) as total_amount,
        avg(avg_amount) as avg_transaction_amount,
        sum(fraud_transactions) as total_fraud_transactions,
        sum(fraud_amount) as total_fraud_amount,
        avg(fraud_rate) as overall_fraud_rate,
        avg(avg_risk_score) as overall_avg_risk_score,
        max(max_risk_score) as overall_max_risk_score
    from daily_agg
    group by country
)

select * from summary
union all
select * from by_currency
union all
select * from by_country
