"""
clean_retail_data.py
====================
Meridian Commerce Co. — Production Data Cleaning Pipeline

This script applies all cleaning steps documented in notebooks/01_data_cleaning.ipynb
as a single, reproducible, importable pipeline.

Input:  data/raw/raw_*.csv  (5 files)
Output: data/clean/clean_*.csv  (5 files)

Cleaning steps applied:
  1. Drop duplicate transactions
  2. Standardize channel names (mapping dict)
  3. Remove USD-price anomalies (price < IDR threshold)
  4. Remove negative-quantity rows (mis-recorded returns)
  5. Parse mixed date formats (custom parse_date with multi-format fallback)
  6. Standardize province names (mapping dict)
  7. Format product names (str.strip().str.title())
  8. Cast all columns to correct types
  9. Flag offline rows with missing store_id
 10. Cross-table referential integrity validation (assertion-style)

Usage:
    python scripts/clean_retail_data.py

Author: Irsyad Fadhilah Akmaldika
"""

import os
import warnings
import pandas as pd
import numpy as np
from datetime import datetime

warnings.filterwarnings("ignore")

# ─── PATHS ────────────────────────────────────────────────────────────────────
RAW_DIR   = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
CLEAN_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "clean")

# ─── CONSTANTS / MAPPING DICTIONARIES ─────────────────────────────────────────

CHANNEL_MAP = {
    "shopee": "Shopee", "SHOPEE": "Shopee", "Shopee.co.id": "Shopee", "Shopee": "Shopee",
    "tokopedia": "Tokopedia", "TOKOPEDIA": "Tokopedia", "Toped": "Tokopedia", "Tokopedia": "Tokopedia",
    "website": "Website", "WEBSITE": "Website", "Web": "Website", "Website": "Website",
    "offline": "Offline", "OFFLINE": "Offline", "In-Store": "Offline", "Offline": "Offline",
}

PROVINCE_MAP = {
    "DKI Jakarta": "DKI Jakarta", "Jakarta": "DKI Jakarta", "JAKARTA": "DKI Jakarta",
    "Dki Jakarta": "DKI Jakarta", "Jakarta (DKI)": "DKI Jakarta",
    "Jawa Barat": "Jawa Barat", "Jabar": "Jawa Barat", "JAWA BARAT": "Jawa Barat",
    "West Java": "Jawa Barat", "Jawa barat": "Jawa Barat",
    "Jawa Timur": "Jawa Timur", "Jatim": "Jawa Timur", "JAWA TIMUR": "Jawa Timur",
    "East Java": "Jawa Timur", "jawa timur": "Jawa Timur",
    "Jawa Tengah": "Jawa Tengah", "Jateng": "Jawa Tengah", "JAWA TENGAH": "Jawa Tengah",
    "Central Java": "Jawa Tengah", "Jawa tengah": "Jawa Tengah",
    "Banten": "Banten", "BANTEN": "Banten", "banten": "Banten",
    "Sumatera Utara": "Sumatera Utara", "Sumatera Selatan": "Sumatera Selatan",
    "Riau": "Riau", "Kepulauan Riau": "Kepulauan Riau",
    "Kalimantan Timur": "Kalimantan Timur", "Sulawesi Selatan": "Sulawesi Selatan",
    "Bali": "Bali", "DI Yogyakarta": "DI Yogyakarta", "Lainnya": "Lainnya",
}

# Price threshold for USD detection: any IDR price below this is anomalous
USD_PRICE_THRESHOLD = 1_000

DATE_FORMATS = [
    "%Y-%m-%d",   # ISO standard — try first (unambiguous)
    "%d/%m/%Y",   # European/Indonesian: 25/06/2024
    "%m/%d/%Y",   # US: 06/25/2024
    "%B %d, %Y",  # Long English: June 25, 2024
    "%b %d, %Y",  # Short English: Jun 25, 2024
    "%d-%m-%Y",   # Dashed European: 25-06-2024
]


# ─── UTILITIES ────────────────────────────────────────────────────────────────

def parse_date(value) -> str:
    """
    Parse a date string using multiple format patterns.
    Returns ISO-formatted date string (YYYY-MM-DD) or np.nan.

    Tries formats in order of decreasing unambiguity.
    Returns the first successful parse result.
    """
    if pd.isna(value) or str(value).strip() == "":
        return np.nan
    value = str(value).strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            continue
    return np.nan


def _load_raw(filename: str) -> pd.DataFrame:
    """Load a raw CSV file as all-string dtype."""
    path = os.path.join(RAW_DIR, filename)
    return pd.read_csv(path, dtype=str)


def _save_clean(df: pd.DataFrame, filename: str) -> None:
    """Save a cleaned DataFrame to the clean directory."""
    os.makedirs(CLEAN_DIR, exist_ok=True)
    path = os.path.join(CLEAN_DIR, filename)
    df.to_csv(path, index=False)


def _print_step(step: str, detail: str = "") -> None:
    """Consistent logging helper."""
    print(f"  [{step}] {detail}")


# ─── TABLE-SPECIFIC CLEANERS ──────────────────────────────────────────────────

def clean_products(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean the products table.

    Steps:
    - Strip and title-case product_name (removes ALLCAPS / lowercase / extra whitespace)
    - Cast numeric columns
    - Cast launch_date to datetime → ISO string
    - Cast is_active to bool
    """
    df = df.copy()

    # D8: Product name formatting
    n_dirty = (
        (df["product_name"] == df["product_name"].str.upper()) |
        (df["product_name"] == df["product_name"].str.lower()) |
        (df["product_name"] != df["product_name"].str.strip())
    ).sum()
    df["product_name"] = df["product_name"].str.strip().str.title()
    _print_step("products", f"Fixed {n_dirty} product name formatting issues")

    # Type casting
    df["cost_price_idr"]    = pd.to_numeric(df["cost_price_idr"],    errors="coerce").astype("Int64")
    df["selling_price_idr"] = pd.to_numeric(df["selling_price_idr"], errors="coerce").astype("Int64")
    df["weight_gram"]       = pd.to_numeric(df["weight_gram"],       errors="coerce").astype("Int64")
    df["launch_date"]       = df["launch_date"].apply(parse_date)
    df["launch_date"]       = pd.to_datetime(df["launch_date"], errors="coerce")
    df["is_active"]         = df["is_active"].map({"True": True, "False": False})

    return df


def clean_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean the transactions table.

    Steps:
    D4: Drop exact duplicate rows
    D1: Standardize channel names using CHANNEL_MAP
    D2: Remove USD-price anomalies (base_price_idr < USD_PRICE_THRESHOLD)
    D3: Remove negative quantity rows (mis-recorded returns)
    D5: Parse mixed date formats with parse_date()
    D6: Standardize province names using PROVINCE_MAP
    D7: Flag offline rows with missing store_id
        Type casting for all numeric / datetime / bool columns
    """
    df = df.copy()
    initial_rows = len(df)

    # ── D4: Duplicates ────────────────────────────────────────────────
    n_dupes = df.duplicated().sum()
    df = df.drop_duplicates(keep="first").reset_index(drop=True)
    _print_step("transactions", f"Dropped {n_dupes} duplicate rows")

    # ── D1: Channel names ─────────────────────────────────────────────
    n_before = df["channel"].nunique()
    df["channel"] = df["channel"].map(CHANNEL_MAP)
    n_unmapped = df["channel"].isnull().sum()
    _print_step("transactions", f"Standardized channel names: {n_before} variants → 4 canonical "
                f"({n_unmapped} unmapped)")

    # ── D2: USD price anomalies ───────────────────────────────────────
    price_cols = ["base_price_idr", "final_price_idr", "revenue_idr",
                  "cogs_idr", "gross_profit_idr"]
    for col in price_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    usd_mask = df["base_price_idr"] < USD_PRICE_THRESHOLD
    n_usd    = usd_mask.sum()
    df       = df[~usd_mask].reset_index(drop=True)
    _print_step("transactions", f"Removed {n_usd} USD-price anomaly rows (price < {USD_PRICE_THRESHOLD:,} IDR)")

    # ── D3: Negative quantities ───────────────────────────────────────
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    n_neg  = (df["quantity"] < 0).sum()
    df     = df[df["quantity"] > 0].reset_index(drop=True)
    _print_step("transactions", f"Removed {n_neg} negative-quantity rows (mis-recorded returns)")

    # ── D5: Date formats ──────────────────────────────────────────────
    df["transaction_date"] = df["transaction_date"].apply(parse_date)
    n_failed_dates = df["transaction_date"].isna().sum()
    _print_step("transactions", f"Parsed transaction_date: {n_failed_dates} could not be parsed (set to NaT)")

    # ── D6: Province names ────────────────────────────────────────────
    n_prov_before = df["province"].nunique()
    df["province"] = df["province"].map(PROVINCE_MAP)
    _print_step("transactions", f"Standardized province names: {n_prov_before} variants → "
                f"{df['province'].nunique()} canonical")

    # ── D7: Flag missing store_id for offline ─────────────────────────
    offline_no_store = (df["channel"] == "Offline") & (df["store_id"].isnull())
    n_flagged = offline_no_store.sum()
    if n_flagged > 0:
        df.loc[offline_no_store, "data_quality_flag"] = "missing_store_id"
    _print_step("transactions", f"Flagged {n_flagged} offline rows with missing store_id")

    # ── Type casting ──────────────────────────────────────────────────
    df["transaction_date"]  = pd.to_datetime(df["transaction_date"], errors="coerce")
    df["quantity"]          = df["quantity"].astype("Int64")
    df["base_price_idr"]    = df["base_price_idr"].astype("Int64")
    df["discount_pct"]      = pd.to_numeric(df["discount_pct"], errors="coerce")
    df["final_price_idr"]   = pd.to_numeric(df["final_price_idr"],  errors="coerce").astype("Int64")
    df["revenue_idr"]       = pd.to_numeric(df["revenue_idr"],      errors="coerce").astype("Int64")
    df["cogs_idr"]          = pd.to_numeric(df["cogs_idr"],         errors="coerce").astype("Int64")
    df["gross_profit_idr"]  = pd.to_numeric(df["gross_profit_idr"], errors="coerce").astype("Int64")
    df["is_promo"]          = df["is_promo"].map({"True": True, "False": False})

    removed_total = initial_rows - len(df)
    _print_step("transactions", f"Final: {len(df):,} rows (removed {removed_total:,} total)")
    return df


def clean_inventory_snapshots(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean inventory_snapshots.

    Steps:
    - Trim year_month to YYYY-MM format
    - Cast all numeric columns
    """
    df = df.copy()

    # year_month is already YYYY-MM; ensure no trailing characters
    df["year_month"] = df["year_month"].str[:7].str.strip()

    # Cast numeric columns
    for col in ["opening_stock", "incoming_qty", "sold_qty", "closing_stock",
                "days_of_inventory", "lead_time_days", "is_stockout"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    df["sell_through_rate"] = pd.to_numeric(df["sell_through_rate"], errors="coerce")

    _print_step("inventory_snapshots", f"Cast types. {len(df):,} rows retained.")
    return df


def clean_traffic_sessions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean traffic_sessions.

    Steps:
    - Standardize channel names (same map as transactions)
    - Parse session_date
    - Cast numeric columns
    """
    df = df.copy()

    # Channel standardization (reuse same map)
    df["channel"] = df["channel"].map(CHANNEL_MAP)

    # Date
    df["session_date"] = df["session_date"].apply(parse_date)
    df["session_date"] = pd.to_datetime(df["session_date"], errors="coerce")

    # Numeric cast
    for col in ["sessions", "orders", "avg_order_value", "is_promo_period", "revenue_idr"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    df["conversion_rate"] = pd.to_numeric(df["conversion_rate"], errors="coerce")

    _print_step("traffic_sessions", f"Cleaned. {len(df):,} rows retained.")
    return df


def clean_marketing_spend(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean marketing_spend.

    Steps:
    - Parse week_start date
    - Cast numeric columns
    """
    df = df.copy()

    df["week_start"] = df["week_start"].apply(parse_date)
    df["week_start"] = pd.to_datetime(df["week_start"], errors="coerce")

    for col in ["spend_idr", "impressions", "clicks",
                "orders_attributed", "revenue_attributed_idr"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    df["ctr"]  = pd.to_numeric(df["ctr"],  errors="coerce")
    df["roas"] = pd.to_numeric(df["roas"], errors="coerce")

    _print_step("marketing_spend", f"Cleaned. {len(df):,} rows retained.")
    return df


# ─── VALIDATION ───────────────────────────────────────────────────────────────

def validate_referential_integrity(products: pd.DataFrame,
                                    transactions: pd.DataFrame,
                                    inventory: pd.DataFrame) -> None:
    """
    Assert that FK relationships between tables are intact.

    Raises AssertionError with a descriptive message if any orphans found.
    """
    valid_skus = set(products["sku_id"].dropna())

    orphans_txn = set(transactions["sku_id"].dropna()) - valid_skus
    assert len(orphans_txn) == 0, (
        f"Referential integrity FAIL: {len(orphans_txn)} SKUs in transactions "
        f"don't exist in products: {list(orphans_txn)[:5]}"
    )

    orphans_inv = set(inventory["sku_id"].dropna()) - valid_skus
    assert len(orphans_inv) == 0, (
        f"Referential integrity FAIL: {len(orphans_inv)} SKUs in inventory "
        f"don't exist in products: {list(orphans_inv)[:5]}"
    )

    _print_step("validation", "Referential integrity OK — all SKUs trace back to products catalog")


def validate_value_ranges(transactions: pd.DataFrame,
                           traffic: pd.DataFrame,
                           inventory: pd.DataFrame,
                           marketing: pd.DataFrame) -> None:
    """
    Assert statistical sanity checks on key ratio/rate columns.
    """
    checks = [
        ("transactions.discount_pct",    transactions["discount_pct"].dropna(),    0, 1),
        ("traffic.conversion_rate",       traffic["conversion_rate"].dropna(),      0, 1),
        ("inventory.sell_through_rate",   inventory["sell_through_rate"].dropna(), 0, 1),
    ]
    for name, series, lo, hi in checks:
        out_of_range = ((series < lo) | (series > hi)).sum()
        if out_of_range > 0:
            print(f"  ⚠️  {name}: {out_of_range} values outside [{lo}, {hi}]")
        else:
            _print_step("validation", f"{name} range [{lo},{hi}] OK")

    neg_price = (transactions["base_price_idr"].dropna() < 0).sum()
    if neg_price > 0:
        print(f"  ⚠️  transactions.base_price_idr: {neg_price} negative values")
    else:
        _print_step("validation", "transactions.base_price_idr all non-negative OK")


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  Meridian Commerce Co. — Data Cleaning Pipeline")
    print("=" * 60)

    # ── Load ──────────────────────────────────────────────────────────
    print("\n[1/7] Loading raw data...")
    raw_products  = _load_raw("raw_products.csv")
    raw_txn       = _load_raw("raw_transactions.csv")
    raw_inventory = _load_raw("raw_inventory_snapshots.csv")
    raw_traffic   = _load_raw("raw_traffic_sessions.csv")
    raw_marketing = _load_raw("raw_marketing_spend.csv")
    print(f"  Loaded: products={len(raw_products):,} | txn={len(raw_txn):,} | "
          f"inventory={len(raw_inventory):,} | traffic={len(raw_traffic):,} | "
          f"marketing={len(raw_marketing):,}")

    # ── Clean ─────────────────────────────────────────────────────────
    print("\n[2/7] Cleaning tables...")
    products  = clean_products(raw_products)
    txn       = clean_transactions(raw_txn)
    inventory = clean_inventory_snapshots(raw_inventory)
    traffic   = clean_traffic_sessions(raw_traffic)
    marketing = clean_marketing_spend(raw_marketing)

    # ── Validate ──────────────────────────────────────────────────────
    print("\n[3/7] Referential integrity checks...")
    validate_referential_integrity(products, txn, inventory)

    print("\n[4/7] Statistical sanity checks...")
    validate_value_ranges(txn, traffic, inventory, marketing)

    # ── Save ──────────────────────────────────────────────────────────
    print("\n[5/7] Saving clean files...")
    save_map = {
        "clean_products.csv":            products,
        "clean_transactions.csv":        txn,
        "clean_inventory_snapshots.csv": inventory,
        "clean_traffic_sessions.csv":    traffic,
        "clean_marketing_spend.csv":     marketing,
    }
    os.makedirs(CLEAN_DIR, exist_ok=True)
    for fname, df in save_map.items():
        _save_clean(df, fname)
        path = os.path.join(CLEAN_DIR, fname)
        kb   = os.path.getsize(path) / 1024
        print(f"  ✓  {fname:<45} ({len(df):>6,} rows, {kb:>7.1f} KB)")

    # ── Summary ───────────────────────────────────────────────────────
    print("\n[6/7] Before / after row count:")
    raw_totals   = sum([len(raw_products), len(raw_txn), len(raw_inventory),
                        len(raw_traffic), len(raw_marketing)])
    clean_totals = sum(len(df) for df in save_map.values())
    print(f"  Raw rows:   {raw_totals:,}")
    print(f"  Clean rows: {clean_totals:,}")
    print(f"  Removed:    {raw_totals - clean_totals:,} ({(raw_totals-clean_totals)/raw_totals*100:.2f}%)")

    print("\n[7/7] Done.")
    print("=" * 60)


if __name__ == "__main__":
    main()
