-- All money calculations remain integer pence until presentation.
SELECT COUNT(*) AS analytical_lines,
  SUM(CASE WHEN line_type='sale' THEN amount_pence ELSE 0 END) AS gross_pence,
  -SUM(CASE WHEN line_type='cancellation' THEN amount_pence ELSE 0 END) AS cancel_pence,
  SUM(amount_pence) AS net_pence,
  COUNT(DISTINCT CASE WHEN line_type='sale' THEN invoice_no END) AS sale_orders,
  COUNT(DISTINCT CASE WHEN line_type='sale' THEN customer_id END) AS identified_buyers,
  MIN(invoice_date) AS first_date, MAX(invoice_date) AS last_date,
  SUM(CASE WHEN customer_id IS NULL AND line_type='sale' THEN amount_pence ELSE 0 END) AS anonymous_gross_pence
FROM fact_merchandise;
