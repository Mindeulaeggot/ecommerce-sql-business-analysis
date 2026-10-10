DROP VIEW IF EXISTS fact_merchandise;
DROP VIEW IF EXISTS classified_lines;
DROP VIEW IF EXISTS canonical_lines;
CREATE VIEW canonical_lines AS
WITH numbered AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY row_hash ORDER BY row_id) AS duplicate_rank
  FROM raw_lines
)
SELECT * FROM numbered WHERE duplicate_rank=1;

CREATE VIEW classified_lines AS
SELECT *, CASE
  WHEN NOT merchandise THEN 'non_merchandise'
  WHEN unit_price_pence<=0 THEN 'nonpositive_price'
  WHEN quantity>0 AND UPPER(invoice_no) NOT LIKE 'C%' THEN 'sale'
  WHEN quantity<0 AND UPPER(invoice_no) LIKE 'C%' THEN 'cancellation'
  ELSE 'unclassified_adjustment'
END AS line_type
FROM canonical_lines;

CREATE VIEW fact_merchandise AS
SELECT row_id,invoice_no,stock_code,description,quantity,invoice_date,
       SUBSTR(invoice_date,1,7) AS month,customer_id,country,line_type,
       quantity*unit_price_pence AS amount_pence
FROM classified_lines WHERE line_type IN ('sale','cancellation');
