WITH active AS (
 SELECT DISTINCT customer_id,month
 FROM fact_merchandise WHERE line_type='sale' AND customer_id IS NOT NULL
), first_seen AS (
 SELECT customer_id,MIN(month) AS cohort FROM active GROUP BY customer_id
), sizes AS (
 SELECT cohort,COUNT(*) AS cohort_size FROM first_seen GROUP BY cohort
), months AS (
 SELECT DISTINCT month FROM fact_merchandise
), activity AS (
 SELECT f.cohort,a.month,COUNT(*) AS active_buyers
 FROM active a JOIN first_seen f USING(customer_id) GROUP BY f.cohort,a.month
)
SELECT s.cohort,m.month,
 (CAST(SUBSTR(m.month,1,4) AS INTEGER)-CAST(SUBSTR(s.cohort,1,4) AS INTEGER))*12
 +CAST(SUBSTR(m.month,6,2) AS INTEGER)-CAST(SUBSTR(s.cohort,6,2) AS INTEGER) AS month_index,
 s.cohort_size,COALESCE(a.active_buyers,0) AS active_buyers,
 ROUND(100.0*COALESCE(a.active_buyers,0)/s.cohort_size,2) AS retention_pct
FROM sizes s CROSS JOIN months m
LEFT JOIN activity a ON a.cohort=s.cohort AND a.month=m.month
WHERE m.month>=s.cohort ORDER BY s.cohort,m.month;
