"""Presentation layer; every reported metric comes from committed SQL output."""
import json
from pathlib import Path
from html import escape

ROOT=Path(__file__).resolve().parents[1]
def pounds(pence):return f'GBP {pence/100:,.0f}'
def ratio(n,d):return 100*n/d if d else 0

def create_dashboard(result,quality):
    template=(ROOT/'dashboard/template.html').read_text(encoding='utf-8')
    data=json.dumps({'results':result,'quality':quality},separators=(',',':')).replace('</','<\\/')
    (ROOT/'dashboard/index.html').write_text(template.replace('__DATA__',data),encoding='utf-8')

def create_report(r,q):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from reportlab.pdfgen import canvas
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph
    from reportlab.lib.colors import HexColor
    figures=ROOT/'reports/figures';figures.mkdir(exist_ok=True)
    months={}
    for row in r['country_month']:
        months[row['month']]=months.get(row['month'],0)+row['net_pence']/100
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,ax=plt.subplots(figsize=(10,3.3));labels=list(months)
    ax.bar(labels,list(months.values()),color=['#0d9488' if m!='2011-12' else '#cbd5e1' for m in labels])
    ax.set_ylabel('Net merchandise revenue (GBP)');ax.tick_params(axis='x',rotation=45)
    ax.set_title('Monthly revenue | December 2011 is partial',loc='left',fontweight='bold')
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x,pos:f'{x/1000000:.1f}m'))
    fig.tight_layout();fig.savefig(figures/'monthly_revenue.png',dpi=170);plt.close(fig)
    products=r['products'][:8]
    fig,ax=plt.subplots(figsize=(10,3.3));ax.barh([x['stock_code'] for x in products][::-1],[x['cancel_pence']/100 for x in products][::-1],color='#0d9488')
    ax.set_xlabel('Cancellation value (GBP)');ax.set_title('Investigation queue | merchandise gross sales >= GBP 10,000',loc='left',fontweight='bold')
    fig.tight_layout();fig.savefig(figures/'cancellation_products.png',dpi=170);plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,3.3));cohorts=sorted({x['cohort'] for x in r['cohort_retention']})
    import numpy as np
    matrix=np.full((len(cohorts),13),np.nan)
    for row in r['cohort_retention']:matrix[cohorts.index(row['cohort']),row['month_index']]=row['retention_pct']
    image=ax.imshow(matrix,aspect='auto',vmin=0,vmax=100,cmap='YlGnBu')
    ax.set_yticks(range(len(cohorts)),cohorts);ax.set_xticks(range(13));ax.set_xlabel('Months since first observed purchase')
    ax.set_title('Observed purchase recurrence | blank cells are unobserved',loc='left',fontweight='bold');fig.colorbar(image,ax=ax,label='% of original cohort')
    fig.tight_layout();fig.savefig(figures/'cohort_retention.png',dpi=170);plt.close(fig)

    k=r['kpis'][0];u=r['customers'][0];outliers={x['slice']:x for x in r['outlier_sensitivity']}
    other=outliers.get('other_line',{'cancel_pence':0,'gross_pence':1});extreme=outliers.get('extreme_line',{'cancel_pence':0,'lines':0})
    cancellation=ratio(k['cancel_pence'],k['gross_pence'])
    report=ROOT/'reports/executive_brief.pdf'
    c=canvas.Canvas(str(report),pagesize=(595.28,841.89),invariant=1)
    c.setTitle('Retail revenue and retention | Executive decision brief');c.setAuthor('Minwoo Jeong')
    style=ParagraphStyle('body',fontName='Helvetica',fontSize=10.3,leading=15,textColor=HexColor('#25364a'))
    pages=[]
    def begin(n,title,kicker):
        c.setFillColor(HexColor('#0f2438'));c.rect(0,740,595.28,102,fill=1,stroke=0)
        c.setFillColor(HexColor('#5eead4'));c.setFont('Helvetica-Bold',9);c.drawString(44,806,kicker.upper())
        c.setFillColor(HexColor('#ffffff'));c.setFont('Helvetica-Bold',21);c.drawString(44,769,title)
        c.setFillColor(HexColor('#64748b'));c.setFont('Helvetica',8)
        c.drawString(44,33,'Independent historical case study | UCI Online Retail | GBP | Minwoo Jeong')
        c.drawRightString(551,33,f'{n} / 5')
        return 710
    def paragraph(text,y,bold=False):
        if bold:text='<b>'+text+'</b>'
        p=Paragraph(text,style);w,h=p.wrap(507,700)
        if y-h<60:raise ValueError('Report text overflow')
        p.drawOn(c,44,y-h);return y-h-13
    def chart(name,y):
        c.drawImage(str(figures/name),44,y-190,width=507,height=190,mask='auto');return y-210
    y=begin(1,'Prioritize revenue quality, then retention','Decision brief / 01')
    y=paragraph(f'The analytical merchandise scope contains {pounds(k["gross_pence"])} in gross sales and {pounds(k["cancel_pence"])} in cancellation adjustments, leaving {pounds(k["net_pence"])} in net merchandise revenue.',y,True)
    y=paragraph('Recommended sequence: validate extreme cancellation pairs, investigate high-value product issues, and test retention outreach with identified repeat buyers. Do not turn cancellation value into a claimed saving without a pilot.',y)
    y=chart('monthly_revenue.png',y)
    y=paragraph(f'Scope: {q["source_rows"]:,} original lines; {q["duplicate_rows_removed"]:,} exact duplicates excluded; {k["sale_orders"]:,} merchandise sales invoices. {ratio(k["anonymous_gross_pence"],k["gross_pence"]):.1f}% of gross sales lacks a customer ID and is excluded from customer analysis only.',y)
    y=paragraph('This is revenue analysis, not profit accounting. Costs, discounts, fulfillment status and matched returns are unavailable. December 2011 covers only through December 9 and should not be compared with a full month.',y)
    c.showPage()
    y=begin(2,'Validate cancellation outliers first','Revenue quality / 02')
    y=paragraph(f'The same-period cancellation-value ratio is {cancellation:.2f}%. Excluding lines with absolute quantity above 10,000, the sensitivity ratio is {ratio(other["cancel_pence"],other["gross_pence"]):.2f}%. This difference matters before sizing a recoverable opportunity.',y,True)
    y=chart('cancellation_products.png',y)
    y=paragraph(f'Extreme lines represent {extreme["lines"]:,} analytical rows and {pounds(extreme["cancel_pence"])} of cancellations. Large equal-and-opposite transactions may be booking corrections or unusual orders. The source cannot establish their cause.',y)
    y=paragraph('Action: reconcile invoice history for the largest stock codes before contacting operations. Then inspect product descriptions, order quantities and cancellation timing. The product action list uses a GBP 10,000 gross-sales floor to avoid small-denominator rankings.',y)
    y=paragraph('A C invoice identifies a cancellation adjustment, not a verified physical return. Cancellations may relate to earlier sales outside the selected window. Some product ratios can exceed 100%; do not interpret them as order-level probabilities.',y)
    c.showPage()
    y=begin(3,'Protect valuable repeat relationships','Customer strategy / 03')
    y=paragraph(f'Among {u["buyers"]:,} identified buyers, {ratio(u["repeat_buyers"],u["buyers"]):.1f}% purchased on two or more invoices and generated {ratio(u["repeat_gross_pence"],u["identified_gross_pence"]):.1f}% of identified gross sales. The top buyer decile contributed {ratio(u["top_decile_gross_pence"],u["identified_gross_pence"]):.1f}%.',y,True)
    y=chart('cohort_retention.png',y)
    y=paragraph('Test a service-led retention pilot with repeat buyers: stock availability notifications or proactive order support. Use an untreated comparison group and measure incremental repeat purchase and net revenue; avoid blanket discounts without cost data.',y)
    y=paragraph('Cohorts are first observed purchase months, not true acquisition cohorts. The earliest cohort is left-censored and later cohorts have less follow-up. Grey/blank cells are unobserved. Anonymous orders remain in total revenue but never become one artificial customer.',y)
    c.showPage()
    y=begin(4,'Treat financial upside as a scenario','Sensitivity / 04')
    y=paragraph('No observed cost or gross-margin fields exist. The following arithmetic is an illustration of assumptions, not measured profit, ROI, or a forecast.',y,True)
    for item in r['sensitivity']:
        if item['assumed_margin_pct']==35:
            y=paragraph(f'If {item["reduction_pct"]}% of observed cancellation value were preventable: retained revenue = {pounds(item["illustrative_retained_revenue_pence"])}; at an assumed 35% contribution margin, illustrative contribution = {pounds(item["illustrative_contribution_pence"])} before intervention costs.',y)
    y=paragraph('The dashboard lets reviewers vary cancellation avoidance from 0-30% and assumed contribution margin from 0-80%. Use the outlier comparison from page 2 before selecting a credible addressable base.',y)
    y=paragraph('Next information to request: original-invoice links, product cost, shipping and handling cost, discount history, reason codes, stock availability and customer contact permissions. Only then build a net-benefit or pricing case.',y)
    y=paragraph('Investment gate: approve a limited pilot only after establishing a measurable eligible population, a credible baseline, incremental operating cost and a stop rule. Scale if the comparison group shows positive incremental contribution after costs.',y)
    c.showPage()
    y=begin(5,'Deliver a focused 30-day investigation','Execution and evidence / 05')
    for text in [
        'Week 1 / Finance + data: reconcile highest-value cancellation pairs and confirm which rows are booking corrections. Deliver an agreed revenue bridge and exclusions register.',
        'Week 2 / Operations: review a sample of high-value product cancellations and map reason codes. Separate availability, order-entry and fulfillment issues before proposing changes.',
        'Week 3 / Customer team: design a controlled outreach test for eligible repeat buyers. Fix success metrics and observation windows before launch.',
        'Week 4 / Sponsor: review reconciliation findings and pilot design. Fund only actions with a clear owner, measurable baseline and plausible incremental benefit.',
        f'Validation: {sum(q["checks"].values())}/{len(q["checks"])} checks passed, including monetary reconciliation, duplicate accounting, invoice grain, cohort denominators, and country-month additivity. SQL outputs and a data-quality register are committed alongside this brief.',
        'Source: Chen, D. (2015), Online Retail, UCI Machine Learning Repository, DOI 10.24432/C5BW33, CC BY 4.0. This project transforms the data through normalization, duplicate removal, scope classification and aggregation.',
        'Reproducibility: run python src/pipeline.py --download, then python -m unittest discover -s tests -v. Open dashboard/index.html locally. Raw data and customer-level records are not committed.',
    ]:y=paragraph(text,y)
    c.save()

def create_readme(r,q):
    k=r['kpis'][0];u=r['customers'][0];others=next(x for x in r['outlier_sensitivity'] if x['slice']=='other_line')
    text=f'''# E-commerce Revenue and Customer Analysis

An independent SQL-first business analytics case study by Minwoo Jeong.
Analyze revenue quality, customer concentration, and observed repeat purchasing
at a UK online retailer; turn findings into a focused investigation plan.

**[Interactive dashboard](dashboard/index.html)** (download and open locally) ·
**[Five-page executive brief](reports/executive_brief.pdf)** ·
**[SQL queries](sql/)** · **[Methodology](docs/methodology.md)**

![Monthly net merchandise revenue](reports/figures/monthly_revenue.png)

## Business questions

1. Which countries and periods drive merchandise revenue?
2. Which products warrant a cancellation investigation, and are outliers driving it?
3. How concentrated is identified-customer revenue, and how do purchase cohorts recur?
4. Under explicit assumptions, how sensitive is potential contribution to cancellation avoidance?

## Measured findings

| Metric | Result |
|---|---:|
| Original transaction lines | {q['source_rows']:,} |
| Exact duplicate lines excluded | {q['duplicate_rows_removed']:,} |
| Merchandise gross sales | {pounds(k['gross_pence'])} |
| Cancellation adjustments | {pounds(k['cancel_pence'])} |
| Net merchandise revenue | {pounds(k['net_pence'])} |
| Merchandise sales invoices | {k['sale_orders']:,} |
| Same-period cancellation-value ratio | {ratio(k['cancel_pence'],k['gross_pence']):.2f}% |
| Ratio excluding absolute line quantities > 10,000 | {ratio(others['cancel_pence'],others['gross_pence']):.2f}% |
| Repeat buyers / identified buyers | {ratio(u['repeat_buyers'],u['buyers']):.1f}% |
| Repeat-buyer share of identified gross sales | {ratio(u['repeat_gross_pence'],u['identified_gross_pence']):.1f}% |
| Top-decile share of identified gross sales | {ratio(u['top_decile_gross_pence'],u['identified_gross_pence']):.1f}% |

The outlier sensitivity is central: validate large transaction/cancellation
pairs before assuming their value is recoverable. Use product-level review and
a controlled service-led retention pilot instead of inferring a causal fix.
No intervention was deployed and no savings are claimed.

## What is built

- Eight readable SQLite scripts: canonical model, KPIs, country/month revenue,
  product priorities, repeat-customer concentration, cohort retention, scenario
  sensitivity, and extreme-quantity robustness.
- Python ingestion of the original workbook, integer-pence monetary calculations,
  exact duplicate tracking, quarantine logging, and {len(q['checks'])} validation checks.
- A self-contained dashboard with country and month filters, monthly charts,
  an all-period product queue, a cohort heatmap, and assumption sliders. No login,
  server, tracking, external scripts, or API keys are required.
- Aggregate CSV/JSON extracts, PNG charts, a five-page PDF management brief,
  methodology, source attribution, and unit tests for edge cases.

## Reproduce

Python 3.10+; SQLite window-function support is included in modern Python.

```bash
python -m venv .venv
# Activate the environment, then:
pip install -r requirements.txt
python src/pipeline.py --download
python -m unittest discover -s tests -v
```

Open `dashboard/index.html` in a browser. The generated HTML embeds aggregate
data, so it works offline without CORS or package setup. To inspect queries:

```python
import sqlite3
from pathlib import Path
con = sqlite3.connect('data/warehouse.sqlite')
print(con.execute(Path('sql/02_kpis.sql').read_text()).fetchall())
```

`--download-only` fetches the original archive without running the model.
Once the raw workbook exists, `python src/pipeline.py` rebuilds offline.
The pipeline recreates only its generated local warehouse and report files.

## Definitions and limitations

- Gross and net values concern the documented merchandise-code scope, not total
  company revenue. Non-product codes and ambiguous sign patterns are counted and
  excluded; see `reports/data_quality.json`.
- C-prefixed invoices identify cancellation adjustments. They are not verified
  physical returns or matched original-order return rates.
- Costs and discount fields are unavailable. Contribution sliders are explicitly
  hypothetical and exclude intervention costs; they are not a profit estimate.
- December 2011 is partial. Cohorts are first observed purchases, with left
  censoring and unequal follow-up. Unobserved cells remain blank.
- Anonymous sales stay in financial totals but are excluded from customer views.
  Customer and product panels use the full period and are labeled accordingly.
- Outliers remain in the primary analysis and are shown separately, not silently
  discarded. Duplicate exclusion is a convention; an alternate total is logged.

## Repository map

```text
src/            Ingestion, validation and presentation
sql/            Auditable analytical queries
dashboard/      Source template and generated offline dashboard
reports/        Aggregate extracts, quality checks, charts and PDF brief
docs/           Analytical choices and interpretation
tests/          Edge-case SQL and ingestion tests
data/           Attribution; downloaded raw files and warehouse are ignored
```

## Source and licensing

Chen, D. (2015). Online Retail [Dataset]. UCI Machine Learning Repository.
https://doi.org/10.24432/C5BW33 — CC BY 4.0. Source coverage is December 2010
through December 9, 2011. See [data provenance](data/README.md) for transformations
and the archive hash. Code is MIT-licensed; source and derived aggregate data
retain CC BY 4.0 attribution. Built with AI assistance; all reported figures are
computed from the source through the committed SQL pipeline.

## Resume description

Built a reproducible SQL analytics pipeline on 541,909 retail transaction lines,
with {len(q['checks'])} reconciliation checks, an interactive dashboard and an executive
brief examining cancellation outliers, revenue concentration and customer cohorts.
'''
    (ROOT/'README.md').write_text(text,encoding='utf-8')
