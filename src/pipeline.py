"""Reproducible SQL-first retail analysis. Python ingests and presents; SQL computes."""
import argparse
import csv
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import urllib.request
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'https://archive.ics.uci.edu/static/public/352/online+retail.zip'

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def text_id(value):
    if value is None: return None
    return str(int(value)) if isinstance(value,(int,float)) and float(value).is_integer() else str(value).strip()

def normalize(row, row_id):
    invoice,stock,description,qty,date,price,customer,country=row
    if invoice is None or stock is None or not isinstance(date,datetime):
        raise ValueError('Missing invoice/stock or invalid date')
    qty_decimal=Decimal(str(qty)); price_decimal=Decimal(str(price))
    if not qty_decimal.is_finite() or not price_decimal.is_finite() or qty_decimal!=int(qty_decimal):
        raise ValueError('Invalid quantity/price')
    price_pence=int((price_decimal*100).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
    invoice,stock=text_id(invoice),text_id(stock)
    country=str(country or 'Unknown').strip()
    source=[invoice,stock,description,str(qty_decimal),date.isoformat(),str(price_decimal),text_id(customer),country]
    key=hashlib.sha256(json.dumps(source,ensure_ascii=False).encode()).hexdigest()
    return (row_id,key,invoice,stock,str(description or '').strip(),int(qty_decimal),date.isoformat(sep=' '),price_pence,text_id(customer),country,int(bool(re.fullmatch(r'\d{5}[A-Za-z]?',stock)))), price_decimal*100!=price_pence

def download():
    folder=ROOT/'data/raw'; folder.mkdir(parents=True,exist_ok=True)
    archive=folder/'online_retail.zip'
    if not archive.exists():
        print('Downloading UCI archive...',flush=True)
        request=urllib.request.Request(SOURCE,headers={'User-Agent':'RetailPortfolio/1.0'})
        with urllib.request.urlopen(request,timeout=120) as response, archive.with_suffix('.part').open('wb') as target:
            while chunk:=response.read(1024*1024): target.write(chunk)
        archive.with_suffix('.part').replace(archive)
    with ZipFile(archive) as z:
        names=[n for n in z.namelist() if n.lower().endswith('.xlsx')]
        if len(names)!=1: raise RuntimeError('Expected one XLSX workbook in archive')
        dest=folder/'Online Retail.xlsx'
        if not dest.exists():
            with z.open(names[0]) as source,dest.open('wb') as out:
                while chunk:=source.read(1024*1024):out.write(chunk)
    print('Source ready; archive SHA-256 '+sha(archive),flush=True)

def rows(conn,sql): return [dict(r) for r in conn.execute(sql)]

def analyze(conn):
    model=(ROOT/'sql/01_model.sql').read_text()
    # Materialization keeps every analytical query at an explicit stable grain.
    model=model.replace('CREATE VIEW canonical_lines AS','CREATE TABLE canonical_lines AS')
    model=model.replace('CREATE VIEW fact_merchandise AS','CREATE TABLE fact_merchandise AS')
    conn.executescript(model)
    conn.executescript('CREATE INDEX ix_fact_customer ON fact_merchandise(customer_id); CREATE INDEX ix_fact_invoice ON fact_merchandise(invoice_no); CREATE INDEX ix_fact_month ON fact_merchandise(month);')
    result={}
    for filename in sorted((ROOT/'sql').glob('*.sql')):
        if filename.name.startswith('01'): continue
        key=filename.stem[3:]
        result[key]=rows(conn,filename.read_text())
    return result

def validate(conn,result,source_count,rejected,rounding):
    k=result['kpis'][0]
    duplicates=conn.execute('SELECT COUNT(*) FROM raw_lines').fetchone()[0]-conn.execute('SELECT COUNT(*) FROM canonical_lines').fetchone()[0]
    classification=rows(conn,'SELECT line_type,COUNT(*) AS lines FROM classified_lines GROUP BY line_type')
    raw_totals=rows(conn,"SELECT SUM(quantity*unit_price_pence) AS signed_pence FROM raw_lines WHERE merchandise=1 AND unit_price_pence>0 AND ((quantity>0 AND UPPER(invoice_no) NOT LIKE 'C%') OR (quantity<0 AND UPPER(invoice_no) LIKE 'C%'))")[0]
    checks={
        'expected_source_rows':source_count==541909,
        'raw_quarantine_reconciliation':conn.execute('SELECT COUNT(*) FROM raw_lines').fetchone()[0]+len(rejected)==source_count,
        'classification_reconciliation':sum(r['lines'] for r in classification)+duplicates+len(rejected)==source_count,
        'gross_minus_cancellations':k['gross_pence']-k['cancel_pence']==k['net_pence'],
        'monthly_net_additivity':sum(r['net_pence'] for r in result['country_month'])==k['net_pence'],
        'monthly_gross_additivity':sum(r['gross_pence'] for r in result['country_month'])==k['gross_pence'],
        'monthly_cancellation_additivity':sum(r['cancel_pence'] for r in result['country_month'])==k['cancel_pence'],
        'invoice_month_country_grain':not rows(conn,"SELECT invoice_no FROM fact_merchandise GROUP BY invoice_no HAVING COUNT(DISTINCT month||'|'||country)>1"),
        'invoice_count_additivity':sum(r['sale_orders'] for r in result['country_month'])==k['sale_orders'],
        'cohort_denominators':all(0<=r['active_buyers']<=r['cohort_size'] and r['month_index']>=0 for r in result['cohort_retention']),
        'buyer_count_reconciliation':result['customers'][0]['buyers']==k['identified_buyers'],
        'positive_sales_negative_cancellations':not rows(conn,"SELECT * FROM fact_merchandise WHERE (line_type='sale' AND amount_pence<=0) OR (line_type='cancellation' AND amount_pence>=0) LIMIT 1"),
    }
    quality={'source_rows':source_count,'quarantined_rows':len(rejected),'quarantine_examples':rejected[:10], 'duplicate_rows_removed':duplicates,'prices_rounded_to_pence':rounding,'classification':classification,'source_archive_sha256':sha(ROOT/'data/raw/online_retail.zip'),'analytical_gross_pence':k['gross_pence'],'analytical_net_pence':k['net_pence'],'signed_scope_total_including_duplicates_pence':raw_totals['signed_pence'],'checks':checks}
    if not all(checks.values()):raise AssertionError(json.dumps(quality,indent=2))
    return quality

def save_outputs(result,quality):
    reports=ROOT/'reports';reports.mkdir(exist_ok=True)
    for key,data in result.items():
        if not data:continue
        with (reports/(key+'.csv')).open('w',newline='',encoding='utf-8') as f:
            writer=csv.DictWriter(f,fieldnames=list(data[0]));writer.writeheader();writer.writerows(data)
    (reports/'results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    (reports/'data_quality.json').write_text(json.dumps(quality,indent=2),encoding='utf-8')
    from presentation import create_dashboard,create_report,create_readme
    create_dashboard(result,quality)
    create_report(result,quality)
    create_readme(result,quality)
    manifest={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in sorted(reports.glob('*')) if p.is_file() and p.name!='manifest.json'}
    (reports/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--download-only',action='store_true');parser.add_argument('--download',action='store_true');args=parser.parse_args()
    if args.download or args.download_only:download()
    if args.download_only:return
    path=ROOT/'data/raw/Online Retail.xlsx'
    if not path.exists():raise SystemExit('Run python src/pipeline.py --download first')
    from openpyxl import load_workbook
    temp=ROOT/'data/warehouse.build.sqlite'
    if temp.exists():temp.unlink()
    conn=sqlite3.connect(temp);conn.row_factory=sqlite3.Row
    conn.execute('PRAGMA journal_mode=OFF');conn.execute('PRAGMA synchronous=OFF')
    conn.execute('CREATE TABLE raw_lines(row_id INTEGER PRIMARY KEY,row_hash TEXT NOT NULL,invoice_no TEXT NOT NULL,stock_code TEXT NOT NULL,description TEXT,quantity INTEGER NOT NULL,invoice_date TEXT NOT NULL,unit_price_pence INTEGER NOT NULL,customer_id TEXT,country TEXT NOT NULL,merchandise INTEGER NOT NULL)')
    workbook=load_workbook(path,read_only=True,data_only=True)
    sheet=workbook.active
    iterator=sheet.iter_rows(values_only=True);header=next(iterator)
    expected=('InvoiceNo','StockCode','Description','Quantity','InvoiceDate','UnitPrice','CustomerID','Country')
    if tuple(header)!=expected:raise ValueError('Source schema changed')
    batch=[]; rejected=[];rounding=0;count=0
    for count,row in enumerate(iterator,1):
        try:
            record,rounded=normalize(row,count);batch.append(record);rounding+=rounded
        except (ValueError,TypeError,ArithmeticError) as error:rejected.append({'row':count,'reason':str(error)})
        if len(batch)>=20000:
            conn.executemany('INSERT INTO raw_lines VALUES(?,?,?,?,?,?,?,?,?,?,?)',batch);batch=[]
            print('Ingested '+str(count)+' lines',flush=True)
    conn.executemany('INSERT INTO raw_lines VALUES(?,?,?,?,?,?,?,?,?,?,?)',batch)
    workbook.close();conn.execute('CREATE INDEX ix_raw_hash ON raw_lines(row_hash)');conn.commit()
    print('Executing SQL model and analyses...',flush=True)
    result=analyze(conn);quality=validate(conn,result,count,rejected,rounding)
    conn.commit();conn.close();temp.replace(ROOT/'data/warehouse.sqlite')
    save_outputs(result,quality)
    print(json.dumps({'kpis':result['kpis'][0],'checks':quality['checks']},indent=2),flush=True)

if __name__=='__main__':main()
