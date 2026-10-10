-- Two transaction codes have very large same-product sales/cancellations.
-- This is a robustness check, NOT an automatic data correction.
SELECT CASE WHEN ABS(quantity)>10000 THEN 'extreme_line' ELSE 'other_line' END AS slice,
 SUM(CASE WHEN line_type='sale' THEN amount_pence ELSE 0 END) AS gross_pence,
 -SUM(CASE WHEN line_type='cancellation' THEN amount_pence ELSE 0 END) AS cancel_pence,
 SUM(amount_pence) AS net_pence,COUNT(*) AS lines
FROM fact_merchandise GROUP BY slice;
