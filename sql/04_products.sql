-- Threshold prevents tiny denominators from dominating the action list.
SELECT stock_code,MAX(description) AS description,
  SUM(CASE WHEN line_type='sale' THEN amount_pence ELSE 0 END) AS gross_pence,
  -SUM(CASE WHEN line_type='cancellation' THEN amount_pence ELSE 0 END) AS cancel_pence,
  SUM(amount_pence) AS net_pence,
  COUNT(DISTINCT CASE WHEN line_type='sale' THEN invoice_no END) AS sale_orders,
  ROUND(100.0*-SUM(CASE WHEN line_type='cancellation' THEN amount_pence ELSE 0 END)
       /NULLIF(SUM(CASE WHEN line_type='sale' THEN amount_pence ELSE 0 END),0),2) AS cancellation_value_pct
FROM fact_merchandise GROUP BY stock_code
HAVING SUM(CASE WHEN line_type='sale' THEN amount_pence ELSE 0 END)>=1000000
ORDER BY cancel_pence DESC;
