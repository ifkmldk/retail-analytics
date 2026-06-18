# Retail & E-commerce Analytics — Meridian Commerce Co.

**Fictional company:** Meridian Commerce Co. — an omnichannel fashion & lifestyle retailer  
**Channels:** Shopee · Tokopedia · Website (D2C) · 12 Offline Stores  
**Coverage:** January 2023 – December 2024  
**Dataset size:** ~68,500 rows across 5 relational tables

---

## Project Overview

End-to-end retail analytics project covering the full analyst stack:

| Stage | Description | Status |
|---|---|---|
| Data Generation | Synthetic dataset with realistic patterns and dirty data | ✅ Complete |
| Data Cleaning | Python pipeline (notebook + production script) | ✅ Complete |
| SQL Analysis | Inventory, channel, and commercial queries in PostgreSQL | 🔄 In Progress |
| Advanced Analytics | RFM segmentation, cohort analysis, A/B testing, geographic maps | 📋 Planned |
| Dashboard | Looker Studio with geographic visualizations | 📋 Planned |

---

## Business Context

Meridian Commerce Co. is experiencing growth but facing operational and commercial challenges that require data-driven answers. This project surfaces 8 key business issues from the raw data:

| # | Issue | Insight |
|---|---|---|
| I1 | **Channel P&L inversion** | Shopee leads GMV but has the worst contribution margin (46% GP) vs Website (56%). Platform fees widen the gap further. |
| I2 | **Bags deadstock crisis** | Sell-through rate < 3% while regular restocking continues. Inventory has been accumulating for 12+ months. |
| I3 | **Top-20 SKU stockouts** | High-velocity SKUs stockout every 1–2 months. Reorder point set too low for their demand velocity. |
| I4 | **Promo A/B test anomaly** | March 2024 promo lifted Shopee CVR by +10pp (p < 0.001) but Tokopedia CVR by only +0.4pp (not significant). |
| I5 | **Harbolnas retention failure** | 62.6% of customers acquired on 11.11 never made a second purchase. CAC is effectively wasted. |
| I6 | **Jawa Timur growth gap** | +41.5% YoY transaction growth in East Java but only ~10% market share — fastest-growing region, lowest penetration. |
| I7 | **MCC Premium Shirts decline** | Revenue declining ~11% per month from May 2024 while the broader Shirts category grows — product lifecycle signal. |
| I8 | **Q4 2024 Dress revenue miss** | Revenue -59% vs Q4 2023 despite normal traffic. Root cause: inventory depleted from September 2024 (supply disruption). |

---

## Dataset Schema

### `raw_products.csv` — 300 rows
| Column | Type | Notes |
|---|---|---|
| sku_id | string | PK, format: MCO-{code}-{###} |
| product_name | string | **D8: mixed casing, extra whitespace in ~30 rows** |
| category | string | Apparel / Accessories / Footwear |
| subcategory | string | Shirts / Dresses / Pants / Outerwear / Bags / Jewelry / Belts / Casual Shoes / Formal Shoes |
| brand | string | MCC Premium / MCC Standard / MCC Basic |
| cost_price_idr | int | Unit production cost |
| selling_price_idr | int | Standard selling price |
| launch_date | date | ISO format |
| is_active | bool | False = discontinued |
| weight_gram | int | For logistics analysis |

### `raw_transactions.csv` — ~58,700 rows
| Column | Type | Notes |
|---|---|---|
| transaction_id | string | PK — **D4: ~60 duplicate rows** |
| transaction_date | date | **D5: ~5% in DD/MM/YYYY or Month DD, YYYY format** |
| channel | string | **D1: inconsistent casing (shopee / SHOPEE / Shopee.co.id)** |
| store_id | string | Offline only — **D7: ~1.5% unexpected NULL** |
| customer_id | string | CUS-XXXXX (regular) / CUS-H23-XXXX / CUS-H24-XXXX (Harbolnas) |
| sku_id | string | FK → products |
| category | string | Denormalized for convenience |
| subcategory | string | Denormalized |
| brand | string | Denormalized |
| quantity | int | **D3: ~25 rows negative (mis-recorded returns)** |
| base_price_idr | float | **D2: ~30 rows in USD (e.g. 16.75 instead of 250,000)** |
| discount_pct | float | 0.00–0.52 |
| final_price_idr | float | base × (1 − discount) — **D2: also affected** |
| revenue_idr | float | final_price × quantity — **D2: also affected** |
| cogs_idr | float | cost × quantity — **D2: also affected** |
| gross_profit_idr | float | revenue − cogs (pre-platform-fee) — **D2: also affected** |
| is_promo | bool | |
| promo_code | string | nullable |
| province | string | **D6: inconsistent (DKI Jakarta / Jakarta / JAKARTA)** |
| city | string | Offline only |

### `raw_inventory_snapshots.csv` — ~6,800 rows
| Column | Type | Notes |
|---|---|---|
| snapshot_id | string | PK |
| year_month | string | YYYY-MM |
| sku_id | string | FK → products |
| category / subcategory / brand | string | Denormalized |
| opening_stock | int | |
| incoming_qty | int | Restock received this month |
| sold_qty | int | Units sold this month |
| closing_stock | int | |
| sell_through_rate | float | sold / (opening + incoming) |
| days_of_inventory | int | closing / avg_daily_sold |
| lead_time_days | int | Days from PO to delivery |
| is_stockout | int | 1 if closing=0 and demand > 0 |

### `raw_traffic_sessions.csv` — ~2,200 rows
| Column | Type | Notes |
|---|---|---|
| session_date | date | Daily per channel |
| channel | string | Shopee / Tokopedia / Website |
| sessions | int | |
| orders | int | |
| conversion_rate | float | orders / sessions |
| revenue_idr | int | Approximate |
| avg_order_value | int | revenue / orders |
| is_promo_period | int | 1 during promo events |

### `raw_marketing_spend.csv` — ~525 rows
| Column | Type | Notes |
|---|---|---|
| week_start | date | Monday of each week |
| platform | string | Shopee Ads / Tokopedia Ads / Google Ads / Instagram Ads / TikTok Ads |
| spend_idr | int | |
| impressions / clicks / ctr | int/float | |
| orders_attributed | int | Last-touch attribution |
| revenue_attributed_idr | int | |
| roas | float | Revenue attributed / Spend |

---

## Dirty Data Summary

| Code | Issue | Count | Fix |
|---|---|---|---|
| D1 | Channel name variants | ~210 rows | str.strip() + mapping dict |
| D2 | Prices in USD | ~30 rows | detect by value < 1,000, flag for review |
| D3 | Negative quantity | 25 rows | abs() or drop |
| D4 | Duplicate transactions | ~60 rows | drop_duplicates() |
| D5 | Non-ISO date formats | ~5% of rows | custom parse_date() with try/except |
| D6 | Province name variants | ~180 rows | str.title() + mapping dict |
| D7 | Missing store_id (offline) | ~1.5% of offline rows | flag, investigate |
| D8 | Product name formatting | ~32 rows | str.strip().title() |

---

## Tech Stack

| Layer | Tool |
|---|---|
| Data Generation & Cleaning | Python (pandas, numpy) |
| SQL Analysis | PostgreSQL |
| Intermediate Analysis | Google Sheets |
| Advanced Analytics | Python (scipy, plotly, folium) |
| Dashboard | Looker Studio |

---

## Repository Structure

```
retail-analytics/
├── data/
│   ├── raw/                    ← generated dirty CSVs (DO NOT EDIT)
│   └── clean/                  ← output of cleaning stage
├── notebooks/
│   ├── 01_data_cleaning.ipynb  ← cleaning walkthrough
│   └── 02_analysis.ipynb       ← EDA + advanced analytics
├── scripts/
│   ├── generate_retail_data.py ← dataset generator
│   └── clean_retail_data.py    ← production cleaning script
├── sql/
│   └── *.sql                   ← analysis queries
└── README.md
```

---

*This is a synthetic dataset created for portfolio purposes. All company names, transactions, and figures are fictional.*
