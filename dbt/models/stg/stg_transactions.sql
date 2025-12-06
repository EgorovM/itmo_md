{{
    config(
        materialized='view',
        tags=['staging', 'stg'],
        schema='stg'
    )
}}

-- Staging model: очистка и парсинг транзакций из PostgreSQL
-- Источник: таблица transactions (загружена из MongoDB через Airflow)

with source_data as (
    select
        transaction_id,
        user_id,
        amount,
        currency,
        transaction_type,
        merchant_category,
        merchant_name,
        country,
        city,
        latitude,
        longitude,
        device_type,
        os,
        ip_address,
        is_fraud,
        risk_score,
        timestamp,
        session_id
    from {{ source('raw', 'transactions') }}
),

cleaned as (
    select
        -- Очистка и валидация transaction_id
        trim(transaction_id) as transaction_id,

        -- Очистка user_id
        trim(user_id) as user_id,

        -- Валидация и очистка amount
        case
            when amount is null then 0.0
            when amount < 0 then abs(amount)
            else amount
        end as amount,

        -- Нормализация currency
        upper(trim(currency)) as currency,

        -- Нормализация transaction_type
        lower(trim(transaction_type)) as transaction_type,

        -- Нормализация merchant_category
        lower(trim(merchant_category)) as merchant_category,

        -- Очистка merchant_name
        trim(merchant_name) as merchant_name,

        -- Географические данные (уже распарсены)
        trim(country) as country,
        trim(city) as city,
        latitude,
        longitude,

        -- Устройство (уже распарсено)
        lower(trim(device_type)) as device_type,
        trim(os) as os,
        trim(ip_address) as ip_address,

        -- Булево значение is_fraud
        coalesce(is_fraud, false) as is_fraud,

        -- Валидация risk_score (0-1)
        case
            when risk_score is null then 0.0
            when risk_score < 0 then 0.0
            when risk_score > 1 then 1.0
            else risk_score
        end as risk_score,

        -- Нормализация timestamp
        case
            when timestamp is null then current_timestamp
            else timestamp::timestamp
        end as transaction_timestamp,

        -- Сессия
        trim(session_id) as session_id,

        -- Дополнительные вычисляемые поля
        extract(epoch from (case when timestamp is null then current_timestamp else timestamp::timestamp end)) as transaction_epoch,
        extract(hour from (case when timestamp is null then current_timestamp else timestamp::timestamp end)) as transaction_hour,
        extract(dow from (case when timestamp is null then current_timestamp else timestamp::timestamp end)) as transaction_day_of_week

    from source_data
),

final as (
    select
        transaction_id,
        user_id,
        amount,
        currency,
        transaction_type,
        merchant_category,
        merchant_name,
        country,
        city,
        latitude,
        longitude,
        device_type,
        os,
        ip_address,
        is_fraud,
        risk_score,
        transaction_timestamp,
        session_id,
        transaction_epoch,
        transaction_hour,
        transaction_day_of_week,
        -- Флаги для валидации
        case when transaction_id is null or transaction_id = '' then false else true end as is_valid_transaction_id,
        case when user_id is null or user_id = '' then false else true end as is_valid_user_id,
        case when amount > 0 then true else false end as is_valid_amount,
        -- user_agent отсутствует в таблице, используем NULL
        null::varchar as user_agent
    from cleaned
)

select * from final
