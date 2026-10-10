-- December 2011 is incomplete; the dashboard labels it explicitly.
SELECT month,country,
  SUM(CASE WHEN line_type='sale' THEN amount_pence ELSE 0 END) AS gross_pence,
  -SUM(CASE WHEN line_type='cancellation' THEN amount_pence ELSE 0 END) AS cancel_pence,
  SUM(amount_pence) AS net_pence,
  COUNT(DISTINCT CASE WHEN line_type='sale' THEN invoice_no END) AS sale_orders
FROM fact_merchandise GROUP BY month,country ORDER BY month,country;
