-- Custom test: проверка, что fraud_rate не превышает 1.0

select
    transaction_date,
    currency,
    transaction_type,
    merchant_category,
    country,
    fraud_rate
from {{ ref('dwh_transactions_daily') }}
where fraud_rate > 1.0
