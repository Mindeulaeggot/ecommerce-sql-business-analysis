-- Illustrative retained revenue only; neither realized profit nor a causal estimate.
WITH totals AS (
 SELECT -SUM(CASE WHEN line_type='cancellation' THEN amount_pence ELSE 0 END) AS cancelled
 FROM fact_merchandise
), rates(reduction_pct) AS (VALUES(5),(10),(20)),
 margins(assumed_margin_pct) AS (VALUES(20),(35),(50))
SELECT reduction_pct,assumed_margin_pct,
 ROUND(cancelled*reduction_pct/100.0) AS illustrative_retained_revenue_pence,
 ROUND(cancelled*reduction_pct/100.0*assumed_margin_pct/100.0) AS illustrative_contribution_pence
FROM totals CROSS JOIN rates CROSS JOIN margins;
