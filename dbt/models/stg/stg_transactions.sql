{{
    config(
        materialized='view',
        tags=['staging', 'stg'],
        schema='stg'
    )
}}

-- Staging model: ПАРСИНГ JSON и очистка транзакций
-- Источник: таблица transactions_raw (RAW данные из MongoDB через Airflow EL)
-- Здесь парсятся JSON поля location_json, device_info_json, metadata_json

with source_data as (
    select
        mongo_id,
        transaction_id,
        user_id,
        amount,
        currency,
        transaction_type,
        merchant_category,
        merchant_name,
        is_fraud,
        risk_score,
        timestamp,
        -- Парсинг JSON полей (вся трансформация в DBT, не в Python!)
        location_json->>'country' as country,
        location_json->>'city' as city,
        (location_json->>'latitude')::decimal(9,6) as latitude,
        (location_json->>'longitude')::decimal(9,6) as longitude,
        device_info_json->>'device_type' as device_type,
        device_info_json->>'os' as os,
        device_info_json->>'ip_address' as ip_address,
        metadata_json->>'session_id' as session_id,
        metadata_json->>'user_agent' as user_agent
    from {{ source('raw', 'transactions_raw') }}
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

        -- Географические данные (парсинг из JSON)
        trim(country) as country,
        trim(city) as city,
        latitude,
        longitude,

        -- Устройство (парсинг из JSON)
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

        -- Метаданные (парсинг из JSON)
        trim(session_id) as session_id,
        trim(user_agent) as user_agent,

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
        user_agent,
        transaction_epoch,
        transaction_hour,
        transaction_day_of_week,
        -- Флаги для валидации
        case when transaction_id is null or transaction_id = '' then false else true end as is_valid_transaction_id,
        case when user_id is null or user_id = '' then false else true end as is_valid_user_id,
        case when amount > 0 then true else false end as is_valid_amount
    from cleaned
)

select * from final
