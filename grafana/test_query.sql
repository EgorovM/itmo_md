-- Тестовые SQL запросы для проверки в Grafana

-- 1. Общее количество транзакций
SELECT COUNT(*)::bigint as value FROM transactions;

-- 2. Мошеннические транзакции
SELECT COUNT(*)::bigint as value FROM transactions WHERE is_fraud = true;

-- 3. Процент мошенничества
SELECT COALESCE(ROUND(100.0 * SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END)::numeric / NULLIF(COUNT(*), 0), 2), 0)::numeric as value FROM transactions;

-- 4. Общая сумма
SELECT COALESCE(SUM(amount), 0)::numeric as value FROM transactions;

-- 5. Транзакции по времени (для time series)
SELECT
  timestamp as time,
  COUNT(*)::bigint as transactions
FROM transactions
WHERE timestamp >= NOW() - INTERVAL '24 hours'
GROUP BY timestamp
ORDER BY timestamp;

-- 6. Транзакции по типам
SELECT transaction_type, COUNT(*)::bigint as value FROM transactions GROUP BY transaction_type;

-- 7. Мошенничество по категориям
SELECT merchant_category, SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END)::int as fraud_count
FROM transactions
GROUP BY merchant_category
ORDER BY fraud_count DESC;

-- 8. Последние транзакции
SELECT transaction_id, timestamp, user_id, amount, currency, transaction_type, merchant_category, is_fraud, risk_score
FROM transactions
ORDER BY timestamp DESC
LIMIT 50;
