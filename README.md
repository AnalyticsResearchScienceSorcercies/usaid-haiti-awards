# Where USAID's Haiti money went, FY2010–FY2025

**Finding:** Of the **$3.64 billion** USAID obligated for work performed in Haiti from FY2010 through FY2025, **$153.4 million (4.2%)** went directly to prime recipients registered in Haiti. US-registered recipients received **$3.27 billion (90.0%)**.

That 90% needs two corrections before it can be printed, and the analysis makes both visible instead of burying them:

| Group | Net obligations | Share | Awards |
|---|---:|---:|---:|
| US-registered recipients (contractors, US NGOs) | $2,540.5M | 69.9% | 934 |
| UN and other intergovernmental bodies (filed at US addresses) | $584.7M | 16.1% | 103 |
| Recipients whose names USAID withheld | $212.6M | 5.8% | 199 |
| Haiti-registered recipients | $153.4M | 4.2% | 256 |
| All other countries | $144.6M | 4.0% | 65 |

- **The ceiling:** if every recipient USAID withheld by name were Haitian, which is not known, the direct-to-Haiti share would still be **10.1%**.
- **Concentration:** the 10 largest recipients took 46.2% of all obligations.
- **Trend:** the Haiti-registered share was 0.01% in FY2010, the earthquake year. It has not been above 15% in any year since. See `results/haiti_share_by_fiscal_year.csv`.

## Source

[USAspending.gov](https://www.usaspending.gov), the federal government's official spending database. The data comes from its public custom-download API, filtered to:

- awarding agency: U.S. Agency for International Development
- place of performance: Haiti
- action dates: Oct 1, 2009 to Sep 30, 2025 (FY2010–FY2025)
- award types: contracts (A–D) and all assistance types (grants, cooperative agreements, other). Indefinite-delivery vehicles are excluded, because the obligations sit on the orders under them.

The raw zip as downloaded on 2026-10-15 is committed in `data/raw/`, with the exact request beside it.

## Method

1. `fetch.py` requests the download and saves the zip. Run it again to pull fresh data.
2. `analyze.py` reads the contract and assistance prime-transaction files, which hold 4,939 transactions.
3. **The unit is the net obligation.** Each transaction's `federal_action_obligation` is summed. Deobligations (843 negative transactions) stay in, so totals are what was actually left committed. These are obligations, not outlays.
4. **"Registered in Haiti"** means the recipient's `recipient_country_code` is `HTI`. That is the address the recipient registered with the federal government, not the nationality of its staff or where its work was done.
5. **Fixing the country field:**
   - 120 contract rows had the country spelled out ("HAITI", "DOMINICAN REPUBLIC", "COLOMBIA") instead of coded, and are mapped to ISO codes.
   - 6 awards changed recipient country partway through. For the by-country tables each transaction keeps its own country; the awards table uses the recipient on the award's latest transaction.
6. **Checks run before any file is written:**
   - Every transaction has a valid country code.
   - Every transaction's place of performance is Haiti.
   - The award table, the country table, the fiscal-year table and the sensitivity table each add back to the same $3,635,778,371.03.

## Limits

- **Prime awards only.** Money a US prime passed to a Haitian subcontractor or subgrantee does not count as Haitian here. The subaward files in this pull came back empty for the same filter. Subaward reporting through FSRS is known to be incomplete, so this analysis does not try to measure the second tier.
- **Withheld recipients.** USAID withholds some recipient names for security reasons. They appear as "DOMESTIC AWARDEES (UNDISCLOSED)" and similar, so their country is unknowable from this data. They are shown as their own group and used only for the ceiling figure.
- **Place-of-performance coding.** An award performed in several countries, or coded to a US headquarters, can be left out. This is a floor on Haiti-related obligations, not a census.
- **Registered address is not nationality.** A US-registered NGO may employ mostly Haitian staff. This analysis measures who held the award, not who did the work.

## Reproduce

```
pip install -r requirements.txt
python fetch.py      # optional: pulls fresh data to data/raw/
python analyze.py    # writes results/*.csv and prints the headline
```

## Outputs (`results/`)

| File | What it is |
|---|---|
| `by_recipient_country.csv` | net obligations, share and award count by registered country |
| `by_recipient_group_sensitivity.csv` | the table above: withheld and intergovernmental recipients split out |
| `haiti_share_by_fiscal_year.csv` | total and Haiti-registered obligations, by fiscal year |
| `top_25_recipients.csv` | largest recipients by net obligations |
| `awards.csv` | one row per award (1,552) |

Code: MIT license. Data: public domain (U.S. government work).
