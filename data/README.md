# Data provenance

Chen, D. (2015). Online Retail [Dataset]. UCI Machine Learning Repository.
https://doi.org/10.24432/C5BW33

Source: https://archive.ics.uci.edu/dataset/352/online+retail
Download: https://archive.ics.uci.edu/static/public/352/online+retail.zip
License: Creative Commons Attribution 4.0 International (CC BY 4.0).
https://creativecommons.org/licenses/by/4.0/

The source describes 541,909 transaction lines at a UK non-store retailer
between December 2010 and December 2011. Amounts are in GBP. Invoice numbers
starting with C denote cancellations. They do not establish verified physical
returns, the original sale, or a causal reason. The source includes customer
identifiers but no names or contact details; row-level customer data is not
published here. Raw files and the local SQLite database are git-ignored.

Aggregate CSV/JSON results are adaptations of this dataset. Transformations:
normalize types, retain original line counts, remove exact eight-field
duplicates for analysis, classify merchandise and non-merchandise entries,
aggregate sales and cancellation adjustments, and derive customer cohorts.
The download archive SHA-256 and measured coverage are saved in
reports/data_quality.json. The analytical conventions are documented in
docs/methodology.md.
