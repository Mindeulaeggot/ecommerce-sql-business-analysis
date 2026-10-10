"""Adversarial SQL fixtures; do not depend on the downloaded workbook."""
import importlib.util
from pathlib import Path
import sqlite3
import unittest
from datetime import datetime

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('pipeline',ROOT/'src/pipeline.py')
pipeline=importlib.util.module_from_spec(spec);spec.loader.exec_module(pipeline)

class RetailSQLTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:');self.db.row_factory=sqlite3.Row
        self.db.execute('CREATE TABLE raw_lines(row_id INTEGER PRIMARY KEY,row_hash TEXT,invoice_no TEXT,stock_code TEXT,description TEXT,quantity INTEGER,invoice_date TEXT,unit_price_pence INTEGER,customer_id TEXT,country TEXT,merchandise INTEGER)')
        fixtures=[
            ('100','12345','Widget',2,datetime(2011,1,1),10,1,'UK'),
            ('100','12345','Widget',2,datetime(2011,1,1),10,1,'UK'), # exact duplicate
            ('C101','12345','Widget',-1,datetime(2011,2,1),10,1,'UK'),
            ('102','12345','Widget',3,datetime(2011,2,2),10,None,'UK'), # anonymous sale
            ('103','POST','Postage',1,datetime(2011,2,2),50,1,'UK'),
            ('104','12345','Widget',-1,datetime(2011,2,2),10,1,'UK'), # ambiguous sign
            ('105','12345','Widget',1,datetime(2011,3,1),10,1,'UK'),
            ('106','12345A','Widget variant',1,datetime(2011,12,9),10,2,'France'),
            ('107','12345','Free item',1,datetime(2011,3,1),0,1,'UK'),
        ]
        for i,row in enumerate(fixtures,1):
            record,_=pipeline.normalize(row,i)
            self.db.execute('INSERT INTO raw_lines VALUES(?,?,?,?,?,?,?,?,?,?,?)',record)
        self.results=pipeline.analyze(self.db)
    def tearDown(self):self.db.close()
    def test_exact_duplicate_is_removed(self):
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM canonical_lines').fetchone()[0],8)
    def test_money_and_scope_reconcile(self):
        k=self.results['kpis'][0]
        self.assertEqual((k['gross_pence'],k['cancel_pence'],k['net_pence']),(7000,1000,6000))
        self.assertEqual(k['sale_orders'],4)
    def test_anonymous_sales_stay_in_money_not_customers(self):
        self.assertEqual(self.results['kpis'][0]['anonymous_gross_pence'],3000)
        self.assertEqual(self.results['customers'][0]['buyers'],2)
        self.assertEqual(self.results['customers'][0]['repeat_buyers'],1)
    def test_observed_zero_is_not_unobserved(self):
        cohort={x['month']:x for x in self.results['cohort_retention'] if x['cohort']=='2011-01'}
        self.assertEqual(cohort['2011-02']['active_buyers'],0)
        self.assertEqual(cohort['2011-03']['retention_pct'],100)
        self.assertNotIn('2012-01',cohort)
    def test_partial_month_is_retained_explicitly(self):
        self.assertEqual(self.results['kpis'][0]['last_date'],'2011-12-09 00:00:00')
        self.assertTrue(any(x['month']=='2011-12' for x in self.results['country_month']))
    def test_zero_price_and_nonmerchandise_are_excluded(self):
        types={x['line_type']:x['n'] for x in pipeline.rows(self.db,'SELECT line_type,COUNT(*) n FROM classified_lines GROUP BY line_type')}
        self.assertEqual(types['nonpositive_price'],1)
        self.assertEqual(types['non_merchandise'],1)
        self.assertEqual(types['unclassified_adjustment'],1)
    def test_scenarios_are_assumptions(self):
        scenario=next(x for x in self.results['sensitivity'] if x['reduction_pct']==10 and x['assumed_margin_pct']==35)
        self.assertEqual(scenario['illustrative_retained_revenue_pence'],100)
        self.assertEqual(scenario['illustrative_contribution_pence'],35)
    def test_negative_prices_are_not_sales(self):
        record,_=pipeline.normalize(('108','12345','Negative',1,datetime(2011,1,1),-10,1,'UK'),10)
        self.assertEqual(record[7],-1000)
    def test_fractional_prices_have_visible_rounding(self):
        record,rounded=pipeline.normalize(('108','12345','Fine price',1,datetime(2011,1,1),1.005,1,'UK'),10)
        self.assertTrue(rounded);self.assertEqual(record[7],101)
    def test_invalid_dates_are_quarantinable(self):
        with self.assertRaises(ValueError):pipeline.normalize(('108','12345','Widget',1,'bad',1,1,'UK'),10)

if __name__=='__main__':unittest.main()
