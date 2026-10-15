"""Where USAID's Haiti money went, by the prime recipient's registered country.

Reads the USAspending prime-transaction files that fetch.py downloaded, rolls
transactions up to awards, and answers one question: of what USAID obligated
for work performed in Haiti, FY2010-FY2025, how much went directly to
recipients registered in Haiti?

Every total is checked against every other grouping before anything is written.

    python analyze.py                   # reads the newest zip in data/raw
"""
import pathlib
import zipfile

import pandas as pd

ROOT = pathlib.Path(__file__).parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "results"

OBL = "federal_action_obligation"   # net: deobligations are negative and stay in

# A few contract rows carry the country spelled out instead of an ISO code.
COUNTRY_NAMES = {"HAITI": "HTI", "DOMINICAN REPUBLIC": "DOM", "COLOMBIA": "COL"}

# Two groups the registered-country field misdescribes, kept visible instead of hidden:
# recipients USAID withheld by name, and intergovernmental bodies filed at a US address.
UNDISCLOSED = "UNDISCLOSED"
INTERGOV = ("UNITED NATIONS", "WORLD FOOD PROGRAMME", "INTERNATIONAL ORGANIZATION FOR MIGRATION",
            "UNICEF", "WORLD HEALTH ORGANIZATION", "PAN AMERICAN HEALTH", "WORLD BANK",
            "INTERNATIONAL BANK FOR RECONSTRUCTION")


def load() -> pd.DataFrame:
    zpath = sorted(RAW.glob("usaspending_usaid_haiti_*.zip"))[-1]
    frames = []
    with zipfile.ZipFile(zpath) as z:
        for name in z.namelist():
            if "PrimeTransactions" not in name:
                continue   # subaward files: see README, "Limits"
            kind = "contract" if name.startswith("Contracts") else "assistance"
            d = pd.read_csv(z.open(name), low_memory=False)
            key = "contract_award_unique_key" if kind == "contract" else "assistance_award_unique_key"
            frames.append(pd.DataFrame({
                "award_key": d[key],
                "award_kind": kind,
                "fiscal_year": d["action_date_fiscal_year"].astype(int),
                "action_date": pd.to_datetime(d["action_date"]),
                "recipient_name": d["recipient_name"].str.strip(),
                "recipient_country": d["recipient_country_code"].replace(COUNTRY_NAMES),
                "pop_country": d["primary_place_of_performance_country_code"],
                "obligation": d[OBL].astype(float),
            }))
    print(f"source: {zpath.name}")
    return pd.concat(frames, ignore_index=True)


def check(tx: pd.DataFrame, awards: pd.DataFrame, by_country: pd.DataFrame, by_year: pd.DataFrame):
    total = tx["obligation"].sum()
    assert tx["recipient_country"].str.fullmatch(r"[A-Z]{3}").all(), "unmapped recipient country"
    assert (tx["pop_country"] == "HTI").all(), "a transaction performed outside Haiti slipped in"
    for label, frame, col in [("awards", awards, "obligation"),
                              ("by_country", by_country, "obligation"),
                              ("by_year", by_year, "total")]:
        assert abs(frame[col].sum() - total) < 0.01, f"{label} does not reconcile to transactions"
    print(f"checks passed: {len(tx):,} transactions reconcile to ${total:,.2f} in every table")


def main():
    OUT.mkdir(exist_ok=True)
    tx = load()
    tx["haiti_based"] = tx["recipient_country"] == "HTI"
    name = tx["recipient_name"].fillna("").str.upper()
    tx["group"] = "registered " + tx["recipient_country"]
    tx.loc[name.str.contains("|".join(INTERGOV)), "group"] = "intergovernmental (UN etc.)"
    tx.loc[name.str.contains(UNDISCLOSED), "group"] = "name withheld by USAID"

    # one row per award; recipient fields from the award's latest transaction
    latest = tx.sort_values("action_date").groupby("award_key").tail(1).set_index("award_key")
    awards = (tx.groupby("award_key")
                .agg(award_kind=("award_kind", "first"), obligation=("obligation", "sum"),
                     first_fy=("fiscal_year", "min"), last_fy=("fiscal_year", "max"),
                     n_countries=("recipient_country", "nunique"))
                .join(latest[["recipient_name", "recipient_country"]]))
    switched = awards[awards["n_countries"] > 1]

    by_country = (tx.groupby("recipient_country")
                    .agg(obligation=("obligation", "sum"), awards=("award_key", "nunique"))
                    .sort_values("obligation", ascending=False))
    by_country["share"] = by_country["obligation"] / by_country["obligation"].sum()

    by_year = (tx.groupby("fiscal_year")
                 .apply(lambda g: pd.Series({
                     "total": g["obligation"].sum(),
                     "haiti_based": g.loc[g["haiti_based"], "obligation"].sum()}),
                        include_groups=False))
    by_year["haiti_share"] = by_year["haiti_based"] / by_year["total"]

    top = (awards.groupby(["recipient_name", "recipient_country"])["obligation"]
                 .agg(["sum", "count"]).rename(columns={"sum": "obligation", "count": "awards"})
                 .sort_values("obligation", ascending=False).head(25))
    top["share_of_total"] = top["obligation"] / tx["obligation"].sum()

    by_group = (tx.groupby("group")
                  .agg(obligation=("obligation", "sum"), awards=("award_key", "nunique"))
                  .sort_values("obligation", ascending=False))
    by_group["share"] = by_group["obligation"] / by_group["obligation"].sum()

    check(tx, awards, by_country, by_year)
    assert abs(by_group["obligation"].sum() - tx["obligation"].sum()) < 0.01

    by_country.to_csv(OUT / "by_recipient_country.csv", float_format="%.2f")
    by_year.to_csv(OUT / "haiti_share_by_fiscal_year.csv", float_format="%.4f")
    top.to_csv(OUT / "top_25_recipients.csv", float_format="%.2f")
    by_group.to_csv(OUT / "by_recipient_group_sensitivity.csv", float_format="%.4f")
    awards.sort_values("obligation", ascending=False).to_csv(OUT / "awards.csv", float_format="%.2f")

    total = tx["obligation"].sum()
    hti = tx.loc[tx["haiti_based"], "obligation"].sum()
    usa = tx.loc[tx["recipient_country"] == "USA", "obligation"].sum()
    print(f"\nUSAID, performed in Haiti, FY{tx.fiscal_year.min()}-FY{tx.fiscal_year.max()}")
    print(f"  {awards.shape[0]:,} awards ({(awards.award_kind == 'contract').sum():,} contracts, "
          f"{(awards.award_kind == 'assistance').sum():,} assistance), ${total / 1e9:,.3f}B net obligated")
    print(f"  to recipients registered in Haiti:  ${hti / 1e6:,.1f}M  ({hti / total:.1%})")
    print(f"  to recipients registered in the US: ${usa / 1e9:,.3f}B  ({usa / total:.1%})")
    wh = by_group.loc["name withheld by USAID", "obligation"]
    ig = by_group.loc["intergovernmental (UN etc.)", "obligation"]
    us_ng = by_group.loc["registered USA", "obligation"]
    print(f"  sensitivity: withheld-name recipients ${wh / 1e6:,.1f}M; UN/intergovernmental ${ig / 1e6:,.1f}M")
    print(f"    US-registered, excluding both: ${us_ng / 1e9:,.3f}B ({us_ng / total:.1%})")
    print(f"    Haiti share if every withheld recipient were Haitian (ceiling): {(hti + wh) / total:.1%}")
    print(f"  top 10 recipients hold {top['obligation'].head(10).sum() / total:.1%} of the total")
    print(f"  {(tx.obligation < 0).sum():,} deobligation transactions netted in; "
          f"{len(switched)} awards changed recipient country mid-life")


if __name__ == "__main__":
    main()
