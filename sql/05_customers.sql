-- Unknown IDs remain in sales totals but never form a synthetic customer.
WITH buyers AS (
 SELECT customer_id,COUNT(DISTINCT invoice_no) AS orders,
        SUM(amount_pence) AS gross_pence,
        MIN(invoice_date) AS first_purchase, MAX(invoice_date) AS last_purchase
 FROM fact_merchandise WHERE line_type='sale' AND customer_id IS NOT NULL
 GROUP BY customer_id
), ranked AS (
 SELECT *,ROW_NUMBER() OVER(ORDER BY gross_pence DESC,customer_id) AS rn,
          COUNT(*) OVER() AS buyer_count
 FROM buyers
)
SELECT COUNT(*) AS buyers,
 SUM(CASE WHEN orders>=2 THEN 1 ELSE 0 END) AS repeat_buyers,
 SUM(gross_pence) AS identified_gross_pence,
 SUM(CASE WHEN orders>=2 THEN gross_pence ELSE 0 END) AS repeat_gross_pence,
 SUM(CASE WHEN rn<=CAST((buyer_count+9)/10 AS INTEGER) THEN gross_pence ELSE 0 END) AS top_decile_gross_pence
FROM ranked;
