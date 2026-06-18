# Data Dictionary — Meridian Commerce Co. Retail Dataset

A synthetic but realistic retail dataset for a fictional Indonesian omnichannel
fashion & lifestyle retailer, **Meridian Commerce Co.**
(~58,700 transactions across 2 years, snapshot period: 2023-01-01 to 2024-12-31).

The data is provided in two forms:
- **`data/raw/`** — data as it arrives from source systems: inconsistent channel
  names, prices recorded in USD instead of IDR, negative quantities, mixed date
  formats, province name variants, duplicate transaction rows. This is the *input*
  to the cleaning project.
- **`data/clean/`** — the internally consistent, analysis-ready version after cleaning.

> All company names, transactions, SKUs, and figures are fabricated.
> Any resemblance to real companies or people is coincidental.

---

## Schema Overview

```
products    (1) ──< transactions        (many, one line-item per row)
products    (1) ──< inventory_snapshots (many, one per SKU per month)
transactions share channel dimension with traffic_sessions
traffic_sessions and marketing_spend share channel/platform dimension
```

---

## `raw_products.csv` — 300 rows

Master SKU catalog. One row per active or discontinued product variant.

| Column | Type | Description |
|---|---|---|
| sku_id | text | Primary key. Format: `MCO-{code}-{###}` e.g. `MCO-SH-001` |
| product_name | text | Full product name. *(raw: some ALLCAPS, some lowercase, some extra whitespace)* |
| category | text | Top-level category: `Apparel` / `Accessories` / `Footwear` |
| subcategory | text | `Shirts` / `Dresses` / `Pants` / `Outerwear` / `Bags` / `Jewelry` / `Belts` / `Casual Shoes` / `Formal Shoes` |
| brand | text | Brand tier: `MCC Premium` / `MCC Standard` / `MCC Basic` |
| cost_price_idr | int | Unit production/procurement cost (IDR) |
| selling_price_idr | int | Standard retail selling price (IDR) |
| launch_date | date | Date SKU was first made available. *(raw: mixed formats)* |
| is_active | bool | `True` = currently sold. `False` = discontinued |
| weight_gram | int | Product weight in grams (used for logistics analysis) |

---

## `raw_transactions.csv` — ~58,700 rows

Core sales transaction table. One row = one product sold (line item).
Multiple line items from the same order will share a `customer_id` and date
but have different `sku_id` and `transaction_id`.

| Column | Type | Description |
|---|---|---|
| transaction_id | text | Primary key. Format: `TRX-YYYYMMDD-#####`. *(raw: ~60 duplicate rows from system sync glitch)* |
| transaction_date | date | Date of sale. *(raw: ~5% of rows in `DD/MM/YYYY` or `Month DD, YYYY` format)* |
| channel | text | Sales channel. *(raw: inconsistent casing — `shopee`, `SHOPEE`, `Shopee.co.id`, `Toped`, `OFFLINE`, `In-Store`, etc.)* Clean values: `Shopee` / `Tokopedia` / `Website` / `Offline` |
| store_id | text | Physical store identifier for Offline channel. NULL for online. Format: `STR-{city}-{##}`. *(raw: ~1.5% of Offline rows have unexpected NULL)* |
| customer_id | text | Customer identifier. Regular customers: `CUS-XXXXX`. Harbolnas (11.11) cohort: `CUS-H23-XXXX` / `CUS-H24-XXXX` |
| sku_id | text | FK → products.sku_id |
| category | text | Denormalized from products for convenience |
| subcategory | text | Denormalized from products |
| brand | text | Denormalized from products |
| quantity | int | Units sold. *(raw: ~25 rows have negative quantity — mis-recorded returns)* |
| base_price_idr | float | Standard selling price at time of transaction (IDR). *(raw: ~30 rows recorded in USD — e.g. `16.75` instead of `250000`)* |
| discount_pct | float | Discount applied. Range: 0.00–0.52. Higher discounts on Shopee (avg 0.22) vs Website (avg 0.06) |
| final_price_idr | float | `base_price × (1 − discount_pct)`. *(raw: affected by same USD error as base_price)* |
| revenue_idr | float | `final_price × quantity`. *(raw: affected by USD error)* |
| cogs_idr | float | `cost_price × quantity`. *(raw: affected by USD error)* |
| gross_profit_idr | float | `revenue − cogs`. Pre-platform-fee, pre-shipping profit. *(raw: affected by USD error)* |
| is_promo | bool | Whether this transaction was part of a promotional campaign |
| promo_code | text | Promo code used. NULL if no promo. e.g. `HARBOLNAS2023`, `MARET15`, `LEBARAN2024` |
| province | text | Delivery province for online; store province for offline. *(raw: ~180 rows with variants — `Jakarta`, `JAKARTA`, `Dki Jakarta`, `Jatim`, `East Java`, etc.)* |
| city | text | City name for Offline transactions only. NULL for online |

---

## `raw_inventory_snapshots.csv` — ~6,800 rows

Monthly stock-level snapshots per active SKU.
One row = one SKU in one month. Generated from transaction velocity + restocking logic.

| Column | Type | Description |
|---|---|---|
| snapshot_id | text | Primary key. Format: `INV-YYYY-MM-MCO-{code}-{###}` |
| year_month | text | Snapshot month. Format: `YYYY-MM` e.g. `2024-03` |
| sku_id | text | FK → products.sku_id |
| category | text | Denormalized from products |
| subcategory | text | Denormalized from products |
| brand | text | Denormalized from products |
| opening_stock | int | Units available at start of month |
| incoming_qty | int | Units received from restock this month |
| sold_qty | int | Units sold this month (from transactions) |
| closing_stock | int | `opening + incoming − sold`. Units remaining at end of month |
| sell_through_rate | float | `sold / (opening + incoming)`. Range 0–1. Low STR = slow-moving inventory |
| days_of_inventory | int | `closing / avg_daily_sales`. How many days until stockout at current pace. Capped at 999 |
| lead_time_days | int | Days from restock order to delivery for this SKU |
| is_stockout | int | `1` if `closing_stock = 0` AND `sold_qty > 0` (ran out while demand existed). `0` otherwise |

**Embedded business issues to find:**
- `Bags` subcategory: STR consistently < 5% → deadstock accumulating
- Top-20 high-velocity SKUs: `is_stockout = 1` recurring every 1–2 months
- `Dresses` in `year_month >= 2024-09`: `incoming_qty = 0` (supply disruption) → stockout heading into Q4

---

## `raw_traffic_sessions.csv` — ~2,200 rows

Daily session and conversion data per online channel.
One row = one channel on one day. Offline channel not included (no session tracking).

| Column | Type | Description |
|---|---|---|
| session_date | date | Date of the sessions |
| channel | text | `Shopee` / `Tokopedia` / `Website` |
| sessions | int | Total sessions (visits) to the storefront on this channel-day |
| orders | int | Total completed orders from this channel-day |
| conversion_rate | float | `orders / sessions`. Range 0–1. Benchmark: 0.10–0.13 baseline; spikes during promos |
| revenue_idr | int | Approximate revenue from this channel-day (from transactions) |
| avg_order_value | int | `revenue / orders`. 0 if orders = 0 |
| is_promo_period | int | `1` if this day had an active promotion (Harbolnas, MARET15, Lebaran, etc.). `0` otherwise |

**Embedded business issue to find (A/B test):**
- Shopee February 2024 baseline CVR: ~11.2%
- Shopee March 2024 (promo MARET15): CVR ~21.2% → statistically significant lift
- Tokopedia February 2024 baseline CVR: ~11.1%
- Tokopedia March 2024 (same promo period): CVR ~11.6% → NOT statistically significant

---

## `raw_marketing_spend.csv` — ~525 rows

Weekly advertising spend per platform.
One row = one platform in one week.

| Column | Type | Description |
|---|---|---|
| week_start | date | Monday of the campaign week |
| platform | text | `Shopee Ads` / `Tokopedia Ads` / `Google Ads` / `Instagram Ads` / `TikTok Ads` |
| spend_idr | int | Total ad spend for the week (IDR) |
| impressions | int | Total ad impressions (how many times the ad was shown) |
| clicks | int | Total ad clicks |
| ctr | float | `clicks / impressions`. Click-through rate |
| orders_attributed | int | Orders credited to this platform via last-touch attribution |
| revenue_attributed_idr | int | Revenue credited to this platform |
| roas | float | `revenue_attributed / spend`. Return on ad spend |

---

## Known Data Quality Issues in `raw/` (what to fix in cleaning stage)

| Code | Issue | Affected table | Affected column(s) | Fix |
|---|---|---|---|---|
| D1 | Channel name variants (shopee, SHOPEE, Shopee.co.id, Toped, In-Store…) | transactions, traffic_sessions | `channel` | Mapping dictionary |
| D2 | ~30 rows: prices recorded in USD instead of IDR (e.g. 16.75 instead of 250,000) | transactions | `base_price_idr`, `final_price_idr`, `revenue_idr`, `cogs_idr`, `gross_profit_idr` | Detect via IQR / threshold, drop rows |
| D3 | ~25 rows: negative quantity (returns mis-recorded as negative sales) | transactions | `quantity` | Drop rows |
| D4 | ~60 duplicate transaction rows (system sync glitch) | transactions | all | `drop_duplicates(keep="first")` |
| D5 | ~5% of dates in non-ISO format (`DD/MM/YYYY` or `Month DD, YYYY`) | transactions | `transaction_date` | Custom `parse_date()` with multi-format fallback |
| D6 | Province name variants (Jakarta, JAKARTA, Dki Jakarta, Jatim, East Java…) | transactions | `province` | Mapping dictionary |
| D7 | ~1.5% of Offline rows missing `store_id` unexpectedly | transactions | `store_id` | Flag with `data_quality_flag` column, keep row |
| D8 | ~32 product names in ALLCAPS / all lowercase / extra whitespace | products | `product_name` | `str.strip().str.title()` |

---

## Offline Store Reference

| store_id | store_name | city | province |
|---|---|---|---|
| STR-JKT-01 | Meridian Grand Indonesia | Jakarta Pusat | DKI Jakarta |
| STR-JKT-02 | Meridian Pacific Place | Jakarta Selatan | DKI Jakarta |
| STR-JKT-03 | Meridian Kelapa Gading | Jakarta Utara | DKI Jakarta |
| STR-BDG-01 | Meridian Paris Van Java | Bandung | Jawa Barat |
| STR-BDG-02 | Meridian BIP Bandung | Bandung | Jawa Barat |
| STR-SBY-01 | Meridian Tunjungan Plaza | Surabaya | Jawa Timur |
| STR-SBY-02 | Meridian Galaxy Mall | Surabaya | Jawa Timur |
| STR-SBY-03 | Meridian Pakuwon Mall | Surabaya | Jawa Timur |
| STR-SMG-01 | Meridian Paragon Semarang | Semarang | Jawa Tengah |
| STR-SMG-02 | Meridian Java Supermall | Semarang | Jawa Tengah |
| STR-YOG-01 | Meridian Malioboro Mall | Yogyakarta | DI Yogyakarta |
| STR-BLI-01 | Meridian Beachwalk Bali | Denpasar | Bali |
