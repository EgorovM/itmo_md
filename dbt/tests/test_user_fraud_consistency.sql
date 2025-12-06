-- Custom test: проверка консистентности фрод-метрик на уровне пользователя

select
    user_id,
    total_transactions,
    fraud_transactions_count,
    fraud_rate,
    round(fraud_transactions_count::numeric / nullif(total_transactions, 0), 4) as calculated_fraud_rate
from {{ ref('dwh_user_transactions') }}
where abs(fraud_rate - round(fraud_transactions_count::numeric / nullif(total_transactions, 0), 4)) > 0.01
