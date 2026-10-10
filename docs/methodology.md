# Analytical decisions and limitations

## Question

Where should a retailer investigate revenue leakage and prioritize customer
retention? This is an independent historical case study, not a client engagement.
The dataset does not identify cost, discounts, product categories, or fulfillment
status. Consequently this project measures merchandise revenue and cancellation
adjustments, not verified profit, discount effects, or physical return rates.

## Grain and money

The source grain is an invoice-product transaction line. SQLite stores unit
prices and line amounts in integer pence, using decimal half-up conversion from
the workbook. A check reports any source prices requiring rounding. No exchange
rate conversion is needed: the source unit price is sterling for every country.

Exact duplicates across all eight original fields are excluded after retaining
their counts. They could represent legitimate repeated line entries: an alternate
total including duplicates is reported, so the convention is visible.
Rows with invalid mandatory numeric or date fields are quarantined and counted.

## Scope

Merchandise codes must match five digits optionally followed by one letter.
This rule excludes explicit non-product codes such as postage, manual entries,
discounts, and adjustments; it is a documented heuristic, not an official catalog.
Positive-price, positive-quantity lines with non-C invoices are sales. Negative
quantity, positive-price C invoices are cancellation adjustments. Other sign and
invoice combinations are excluded and counted. Null customer IDs remain in all
financial totals, but are excluded from buyer and cohort statistics.

Gross sales = sum of sale-line values. Cancellation value = absolute negative
cancellation-line value. Net merchandise revenue = gross minus cancellations.
Cancellation-value ratio = cancellation value / gross sales in the same window.
It is NOT a matched order return rate: cancellation invoices cannot reliably be
linked to original sales, including sales outside the observation window.

## Time and cohorts

The observation ends December 9, 2011. December 2011 is not a full-month trend
comparison. Default dashboard coverage includes all months and explicitly marks
the partial month. Cohort means first observed purchase, not verified acquisition.
December 2010 has left censoring, and later cohorts have shorter follow-up.
Unobserved cohort months are blank, never zero. Recurrence is purchase activity
in that exact month, not continuous survival. Customer concentration is computed
only among identified buyers; it must not be generalized to anonymous sales.

Invoice counts are grouped by month and country. The pipeline verifies that
each analytical invoice belongs to only one month/country before adding counts
across dashboard selections. All other core financial metrics are additive.
Customer and product panels are explicitly all-period views, independent of
dashboard country/month filters.

## Robustness and business interpretation

Lines with absolute quantities over 10,000 are retained in the primary view and
shown separately in a sensitivity table. Large sale/cancellation pairs can drive
the headline ratio without representing a broad operational problem. The report
therefore recommends validating them before assuming their value is recoverable.

The cost scenario multiplies cancellation value by user-selected avoidance and
contribution-margin assumptions. There are no observed margins, implementation
costs, causal treatment effects, or measured savings. This is a sensitivity
exercise, not an ROI claim. No claim is made that an intervention was deployed.

## Validation

The pipeline checks raw count, duplicate reconciliation, complete classification,
gross-minus-cancellations reconciliation, monthly-country additivity, invoice
grain, null-ID exclusion, cohort denominators, and monetary sign conventions.
Unit tests use adversarial small data for duplicate, unknown-ID, non-product,
partial-month and cohort behavior. Source/aggregate SHA-256 hashes are recorded.
