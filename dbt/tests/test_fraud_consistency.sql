-- Custom test: проверка консистентности между fraud_transactions и fraud_rate

select
    transaction_date,
    currency,
    transaction_type,
    merchant_category,
    country,
    total_transactions,
    fraud_transactions,
    fraud_rate,
    round(fraud_transactions::numeric / nullif(total_transactions, 0), 4) as calculated_fraud_rate
from {{ ref('dwh_transactions_daily') }}
where abs(fraud_rate - round(fraud_transactions::numeric / nullif(total_transactions, 0), 4)) > 0.01
