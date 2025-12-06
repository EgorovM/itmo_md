-- Custom test: проверка, что сумма транзакций неотрицательна

select
    transaction_date,
    currency,
    transaction_type,
    merchant_category,
    country,
    total_amount,
    avg_amount,
    min_amount,
    max_amount
from {{ ref('dwh_transactions_daily') }}
where total_amount < 0
   or avg_amount < 0
   or min_amount < 0
   or max_amount < 0
