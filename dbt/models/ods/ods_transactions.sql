{{
    config(
        materialized='table',
        tags=['ods', 'operational'],
        schema='ods',
        indexes=[
            {'columns': ['transaction_id'], 'unique': True},
            {'columns': ['user_id']},
            {'columns': ['transaction_timestamp']},
            {'columns': ['is_fraud']}
        ]
    )
}}

-- ODS model: нормализованные транзакции
-- Источник: stg_transactions

with stg_transactions as (
    select * from {{ ref('stg_transactions') }}
),

normalized as (
    select
        -- Основные идентификаторы
        transaction_id,
        user_id,

        -- Финансовые данные
        amount,
        currency,
        transaction_type,

        -- Мерчант информация
        merchant_category,
        merchant_name,

        -- Географические данные
        country,
        city,
        latitude,
        longitude,

        -- Устройство
        device_type,
        os,
        ip_address,

        -- Фрод-индикаторы
        is_fraud,
        risk_score,

        -- Временные метки
        transaction_timestamp,
        transaction_epoch,
        transaction_hour,
        transaction_day_of_week,

        -- Сессия
        session_id,
        user_agent,

        -- Валидационные флаги
        is_valid_transaction_id,
        is_valid_user_id,
        is_valid_amount,

        -- Дополнительные вычисляемые поля
        case
            when amount >= 1000 then 'high'
            when amount >= 100 then 'medium'
            else 'low'
        end as amount_category,

        case
            when risk_score >= 0.7 then 'high_risk'
            when risk_score >= 0.4 then 'medium_risk'
            else 'low_risk'
        end as risk_category,

        -- Дата партиционирования
        date(transaction_timestamp) as transaction_date,

        -- Время загрузки
        current_timestamp as loaded_at

    from stg_transactions
    where is_valid_transaction_id
      and is_valid_user_id
      and is_valid_amount
)

select * from normalized
