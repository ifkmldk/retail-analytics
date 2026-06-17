"""
generate_retail_data.py
=======================
Meridian Commerce Co. — Synthetic Retail Dataset Generator

Company  : Meridian Commerce Co. (fictional omnichannel fashion & lifestyle retailer)
Channels : Shopee · Tokopedia · Website (D2C) · 12 Offline Stores (5 cities)
Coverage : 2023-01-01 to 2024-12-31
Size     : ~35,000 rows across 5 tables (products, transactions, inventory_snapshots,
           traffic_sessions, marketing_spend)

──────────────────────────────────────────────────────────────────────────────
  BUSINESS ISSUES EMBEDDED  (the DA's job is to find and quantify these)
──────────────────────────────────────────────────────────────────────────────
  I1  Shopee leads in GMV but has the worst contribution margin per order
      → heavy discount depth (avg 22%) + highest platform fees erodes profit
      → Recommendation: shift investment to higher-margin channels (Website/Offline)

  I2  Bags subcategory deadstock crisis
      → sell-through rate < 12% while restocking continues at normal cadence
      → Closing stock accumulates for 12+ months
      → Recommendation: immediate markdown campaign + pause restock

  I3  Top-20 SKUs stockout pattern (lost revenue signal)
      → Demand outpacing reorder triggers; stockout events every 1-2 months
      → Recommendation: raise safety stock and reorder point for A-tier SKUs

  I4  March 2024 promo: statistically significant CVR lift on Shopee, NOT Tokopedia
      → A/B insight: blanket promo assumption is wrong
      → Recommendation: concentrate promo budget on Shopee; redesign Tokopedia strategy

  I5  Harbolnas (11.11) acquisition cohort = first-and-only buyers (retention failure)
      → ~72% of Nov 11 new customers never repurchase
      → Recommendation: post-Harbolnas reactivation campaign within 30 days of first purchase

  I6  East Java growing +42% YoY but < 9% market share (geographic gap)
      → Jawa Timur growing 3x faster than national average (15%)
      → Recommendation: accelerate Surabaya store expansion + regional marketplace ads

  I7  MCC Premium Shirts: declining velocity from May 2024 (product lifecycle signal)
      → Revenue down ~8% per month from May 2024; rest of Shirts category growing
      → Recommendation: investigate quality complaints / price anchoring vs. competition

  I8  Q4 2024 Dresses revenue -31% vs Q4 2023 (inventory stockout during peak season)
      → Traffic and conversion normal; supply depleted from September 2024
      → Recommendation: improve Q4 demand planning; advance 60-day safety stock buffer

──────────────────────────────────────────────────────────────────────────────
  DIRTY DATA EMBEDDED  (for the cleaning stage to resolve)
──────────────────────────────────────────────────────────────────────────────
  D1  Channel names: inconsistent casing/format (shopee, SHOPEE, Shopee.co.id)
  D2  ~30 rows: price_idr values recorded in USD (e.g. 16.75 instead of 250,000)
  D3  ~25 rows: negative quantity (returns mis-recorded instead of separate record)
  D4  ~60 duplicate transaction rows (system sync glitch)
  D5  ~5% of transaction dates in alternative formats (DD/MM/YYYY, Mon DD YYYY)
  D6  Province names: inconsistent (DKI Jakarta / Jakarta / JAKARTA / Dki Jakarta)
  D7  ~1% rows: store_id NULL for offline transactions (unexpected missing)
  D8  ~30 product names: ALLCAPS / lowercase / extra leading-trailing whitespace

Usage:
    python generate_retail_data.py
    → writes 5 CSV files to  data/raw/
"""

import os
import warnings
import pandas as pd
import numpy as np
from datetime import date, timedelta

warnings.filterwarnings("ignore")

# ─── SEED & DATE RANGE ────────────────────────────────────────────────────────
RNG   = np.random.default_rng(42)
START = date(2023, 1, 1)
END   = date(2024, 12, 31)
ALL_DATES = [START + timedelta(days=i) for i in range((END - START).days + 1)]

# ─── PRODUCT TAXONOMY ─────────────────────────────────────────────────────────
TAXONOMY = {
    "Apparel": {
        "Shirts":    {"code": "SH", "n": 60, "price": (75_000,  450_000)},
        "Dresses":   {"code": "DR", "n": 45, "price": (100_000, 600_000)},
        "Pants":     {"code": "PT", "n": 30, "price": (80_000,  350_000)},
        "Outerwear": {"code": "OW", "n": 25, "price": (150_000, 800_000)},
    },
    "Accessories": {
        "Bags":      {"code": "BG", "n": 40, "price": (120_000, 650_000)},
        "Jewelry":   {"code": "JW", "n": 30, "price": (50_000,  250_000)},
        "Belts":     {"code": "BT", "n": 20, "price": (45_000,  180_000)},
    },
    "Footwear": {
        "Casual Shoes": {"code": "CS", "n": 30, "price": (150_000, 500_000)},
        "Formal Shoes": {"code": "FS", "n": 20, "price": (200_000, 700_000)},
    },
}  # total = 300 SKUs

BRANDS        = ["MCC Premium", "MCC Standard", "MCC Basic"]
BRAND_W       = [0.28, 0.50, 0.22]
BRAND_PMULT   = {"MCC Premium": 1.65, "MCC Standard": 1.00, "MCC Basic": 0.62}
BRAND_COST    = {"MCC Premium": 0.37, "MCC Standard": 0.42, "MCC Basic": 0.46}

ADJECTIVES = {
    "Shirts":       ["Slim-Fit Oxford","Classic Linen","Relaxed Poplin","Oversized Flannel",
                     "Striped Button-Down","Printed Batik","Solid Jersey","Woven Check",
                     "Mandarin Collar","Cropped Tie-Front"],
    "Dresses":      ["Floral Wrap","Midi Slip","A-Line Cotton","Ruched Bodycon",
                     "Broderie Anglaise","Printed Chiffon","Solid Knit","Linen Maxi",
                     "Off-Shoulder Mini","Shirred Smock"],
    "Pants":        ["Wide-Leg","Straight-Cut","Tapered Jogger","High-Waist Linen",
                     "Cargo Utility","Slim Chino","Pleated Trouser","Paper-Bag Tie"],
    "Outerwear":    ["Oversized Blazer","Knit Cardigan","Denim Jacket","Padded Vest",
                     "Trench Coat","Zip-Up Hoodie","Woven Kimono","Shacket"],
    "Bags":         ["Structured Tote","Drawstring Bucket","Chain Shoulder","Mini Crossbody",
                     "Quilted Flap","Woven Basket","Leather Clutch","Canvas Shopper",
                     "Nylon Backpack","Top-Handle Satchel"],
    "Jewelry":      ["Gold-Plated Hoop","Pearl Drop","Chunky Chain","Beaded Strand",
                     "Statement Ear Cuff","Layered Pendant","Ring Set","Cuff Bracelet"],
    "Belts":        ["Braided Leather","Double Ring","Canvas Webbing","Studded Skinny",
                     "Classic Buckle","Embroidered Fabric"],
    "Casual Shoes": ["Chunky Sneaker","Platform Loafer","Slip-On Canvas","Low-Top Trainer",
                     "Espadrille Wedge","Strappy Sandal","Mule Clog"],
    "Formal Shoes": ["Oxford Brogue","Block Heel Pump","Pointed-Toe Mule","Derby Lace-Up",
                     "Kitten Heel Slingback","Ankle Boot"],
}

COLORS = [
    "Black","White","Navy","Ivory","Camel","Sage","Dusty Rose","Cognac",
    "Emerald","Terracotta","Cobalt","Stone","Burgundy","Olive","Blush","Mocha",
]

# ─── GEOGRAPHY ────────────────────────────────────────────────────────────────
PROVINCES_ONLINE = [
    "DKI Jakarta","Jawa Barat","Jawa Tengah","Jawa Timur","Banten",
    "Sumatera Utara","Sumatera Selatan","Riau","Kepulauan Riau",
    "Kalimantan Timur","Sulawesi Selatan","Bali","DI Yogyakarta","Lainnya",
]
# I6: Jawa Timur growing from 8% (2023) → 11% (2024)
PROV_W_2023 = [0.35, 0.20, 0.09, 0.08, 0.06, 0.05, 0.03, 0.03, 0.02, 0.02, 0.02, 0.02, 0.02, 0.01]
PROV_W_2024 = [0.33, 0.18, 0.09, 0.11, 0.06, 0.05, 0.03, 0.03, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02]

OFFLINE_STORES = [
    {"store_id":"STR-JKT-01","store_name":"Meridian Grand Indonesia",   "city":"Jakarta Pusat","province":"DKI Jakarta"},
    {"store_id":"STR-JKT-02","store_name":"Meridian Pacific Place",     "city":"Jakarta Selatan","province":"DKI Jakarta"},
    {"store_id":"STR-JKT-03","store_name":"Meridian Kelapa Gading",     "city":"Jakarta Utara","province":"DKI Jakarta"},
    {"store_id":"STR-BDG-01","store_name":"Meridian Paris Van Java",    "city":"Bandung","province":"Jawa Barat"},
    {"store_id":"STR-BDG-02","store_name":"Meridian BIP Bandung",       "city":"Bandung","province":"Jawa Barat"},
    {"store_id":"STR-SBY-01","store_name":"Meridian Tunjungan Plaza",   "city":"Surabaya","province":"Jawa Timur"},
    {"store_id":"STR-SBY-02","store_name":"Meridian Galaxy Mall",       "city":"Surabaya","province":"Jawa Timur"},
    {"store_id":"STR-SBY-03","store_name":"Meridian Pakuwon Mall",      "city":"Surabaya","province":"Jawa Timur"},
    {"store_id":"STR-SMG-01","store_name":"Meridian Paragon Semarang",  "city":"Semarang","province":"Jawa Tengah"},
    {"store_id":"STR-SMG-02","store_name":"Meridian Java Supermall",    "city":"Semarang","province":"Jawa Tengah"},
    {"store_id":"STR-YOG-01","store_name":"Meridian Malioboro Mall",    "city":"Yogyakarta","province":"DI Yogyakarta"},
    {"store_id":"STR-BLI-01","store_name":"Meridian Beachwalk Bali",   "city":"Denpasar","province":"Bali"},
]

# ─── DISCOUNT PROFILES BY CHANNEL (I1) ────────────────────────────────────────
# Shopee: high discount = kills margin | Website D2C: low discount = best margin
DISC_PROFILES = {
    "Shopee":    {"mu": 0.22, "sigma": 0.09, "lo": 0.05, "hi": 0.55},
    "Tokopedia": {"mu": 0.13, "sigma": 0.07, "lo": 0.00, "hi": 0.38},
    "Website":   {"mu": 0.06, "sigma": 0.05, "lo": 0.00, "hi": 0.22},
    "Offline":   {"mu": 0.08, "sigma": 0.06, "lo": 0.00, "hi": 0.30},
}

# ─────────────────────────────────────────────────────────────────────────────
#  TABLE 1 — PRODUCTS
# ─────────────────────────────────────────────────────────────────────────────

def generate_products() -> pd.DataFrame:
    """300-row SKU catalog across 3 categories, 9 subcategories, 3 brand tiers."""
    rows = []
    for category, subcats in TAXONOMY.items():
        for subcat, cfg in subcats.items():
            adjs = ADJECTIVES[subcat]
            for i in range(cfg["n"]):
                brand = RNG.choice(BRANDS, p=BRAND_W)
                adj   = adjs[i % len(adjs)]
                color = COLORS[i % len(COLORS)]
                name  = f"{adj} {subcat} — {color}"

                lo, hi = cfg["price"]
                base   = int(RNG.integers(lo, hi) / 5_000) * 5_000
                sell   = int(base * BRAND_PMULT[brand] / 5_000) * 5_000
                cost   = int(sell * BRAND_COST[brand]  / 1_000) * 1_000

                # Launch dates: mostly pre-2023, some new launches
                offset = int(RNG.integers(-900, 200))
                launch = START + timedelta(days=offset)
                if launch < date(2019, 1, 1):
                    launch = date(2019, 1, 1) + timedelta(days=int(RNG.integers(0, 365 * 4)))

                # Last 2 per subcategory are discontinued (is_active=False)
                active = i < cfg["n"] - 2

                rows.append({
                    "sku_id":           f"MCO-{cfg['code']}-{str(i+1).zfill(3)}",
                    "product_name":     name,
                    "category":         category,
                    "subcategory":      subcat,
                    "brand":            brand,
                    "cost_price_idr":   cost,
                    "selling_price_idr": sell,
                    "launch_date":      launch.isoformat(),
                    "is_active":        active,
                    "weight_gram":      int(RNG.integers(80, 2_200)),
                })

    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
#  TABLE 2 — TRANSACTIONS
# ─────────────────────────────────────────────────────────────────────────────

def _daily_base_volume(d: date) -> int:
    """
    Returns expected transaction count for date d.
    Encodes seasonality (Ramadan, Lebaran, Harbolnas, year-end)
    and a 2024 YoY growth of ~15%.
    """
    dow_mult = 1.0 + (0.18 if d.weekday() >= 5 else 0.0) + (0.06 if d.weekday() == 4 else 0.0)

    # Monthly seasonality — different for each year (Ramadan shifts)
    m2023 = {1:0.80,2:0.88,3:1.05,4:1.30,5:1.50,6:0.85,7:0.88,8:0.95,9:0.92,10:1.00,11:1.65,12:1.45}
    m2024 = {1:0.82,2:0.92,3:1.45,4:1.55,5:1.20,6:0.90,7:0.92,8:0.96,9:0.93,10:1.05,11:1.85,12:1.40}
    month_mult = (m2023 if d.year == 2023 else m2024)[d.month]
    year_mult  = 1.00 if d.year == 2023 else 1.15

    # Special events
    special = 1.0
    if   d.month == 11 and d.day == 11:                                  special = 8.5   # Harbolnas 11.11
    elif d.month == 12 and d.day == 12:                                  special = 3.8   # 12.12
    elif d.year == 2023 and d.month == 5 and d.day in {22, 23}:         special = 4.2   # Lebaran 2023
    elif d.year == 2024 and d.month == 4 and d.day in {9, 10}:          special = 4.5   # Lebaran 2024
    elif d.month == 12 and d.day in {24, 25, 31}:                       special = 2.0

    return int(58 * dow_mult * month_mult * year_mult * special)


def generate_transactions(products_df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate ~25,000 transaction rows with all 8 business issues embedded.
    Returns raw (un-dirtied) transaction DataFrame.
    """
    active = products_df[products_df["is_active"]].copy().reset_index(drop=True)
    sku_ids   = active["sku_id"].values
    sku_lookup = active.set_index("sku_id")[
        ["category","subcategory","brand","selling_price_idr","cost_price_idr"]
    ].to_dict("index")

    # ── SKU popularity: power-law distribution ─────────────────────────────
    n = len(sku_ids)
    w = np.array([1 / (i + 1) ** 0.72 for i in range(n)], dtype=float)

    bags_mask  = active["subcategory"].values == "Bags"
    dress_mask = active["subcategory"].values == "Dresses"
    prem_shirt = (active["brand"].values == "MCC Premium") & (active["subcategory"].values == "Shirts")

    # I2: Bags severely undersell
    w[bags_mask] *= 0.22
    # Top-20 most popular get extra boost (I3: stockout candidates)
    top20 = np.argsort(w)[-20:]
    w[top20] *= 2.2
    w /= w.sum()

    # ── Customer pools ─────────────────────────────────────────────────────
    N_REG = 8_000
    reg_custs   = np.array([f"CUS-{str(i+1).zfill(5)}" for i in range(N_REG)])
    h23_custs   = np.array([f"CUS-H23-{str(i+1).zfill(4)}" for i in range(820)])   # I5
    h24_custs   = np.array([f"CUS-H24-{str(i+1).zfill(4)}" for i in range(1_150)]) # I5

    CHANNELS   = ["Shopee","Tokopedia","Website","Offline"]
    CW_2023    = [0.42, 0.26, 0.10, 0.22]
    CW_2024    = [0.44, 0.24, 0.11, 0.21]

    rows = []
    txn_counter = 0

    for d in ALL_DATES:
        vol = _daily_base_volume(d)
        if vol == 0:
            continue

        # ── Flags ────────────────────────────────────────────────────────
        is_harbolnas  = d.month == 11 and d.day == 11
        is_1212       = d.month == 12 and d.day == 12
        is_lebaran    = (d.year==2023 and d.month==5 and d.day in {22,23}) or \
                        (d.year==2024 and d.month==4 and d.day in {9,10})
        march24_promo = d.year == 2024 and d.month == 3   # I4
        q4_24_dress   = d.year == 2024 and d.month >= 9   # I8
        ps_decline    = d.year == 2024 and d.month >= 5   # I7

        # ── Adjust SKU weights per-day ────────────────────────────────────
        day_w = w.copy()
        if q4_24_dress:
            day_w[dress_mask] *= 0.28   # only 28% of normal Dress velocity
        if ps_decline:
            decay = max(0.08, 1.0 - (d.month - 4) * 0.11)
            day_w[prem_shirt] *= decay
        day_w /= day_w.sum()

        # ── Batch random draws ────────────────────────────────────────────
        cw       = CW_2024 if d.year == 2024 else CW_2023
        channels = RNG.choice(CHANNELS, size=vol, p=cw)
        skus     = RNG.choice(sku_ids, size=vol, p=day_w)
        qtys     = RNG.choice([1, 2, 3, 4], size=vol, p=[0.70, 0.20, 0.07, 0.03])
        prov_w   = np.array(PROV_W_2024 if d.year == 2024 else PROV_W_2023, dtype=float)
        prov_w  /= prov_w.sum()
        provs    = RNG.choice(PROVINCES_ONLINE, size=vol, p=prov_w)
        store_idx= RNG.integers(0, len(OFFLINE_STORES), size=vol)

        # Harbolnas customer mix
        if is_harbolnas:
            h_pool = h23_custs if d.year == 2023 else h24_custs
            harb   = RNG.random(vol) < 0.72          # 72% new customers (I5)
            custs  = np.where(harb,
                              RNG.choice(h_pool, size=vol),
                              RNG.choice(reg_custs, size=vol))
        else:
            custs = RNG.choice(reg_custs, size=vol)

        for i in range(vol):
            txn_counter += 1
            ch   = channels[i]
            sid  = skus[i]
            qty  = int(qtys[i])
            sr   = sku_lookup[sid]

            base  = int(sr["selling_price_idr"])
            cost  = int(sr["cost_price_idr"])

            # Discount
            dp   = DISC_PROFILES[ch]
            disc = float(np.clip(RNG.normal(dp["mu"], dp["sigma"]), dp["lo"], dp["hi"]))

            # Promo overrides
            is_promo   = False
            promo_code = None

            if is_harbolnas:
                disc = min(0.52, disc + 0.22)
                is_promo, promo_code = True, f"HARBOLNAS{d.year}"
            elif is_1212:
                disc = min(0.48, disc + 0.16)
                is_promo, promo_code = True, f"HARBOLNAS1212{d.year}"
            elif is_lebaran:
                disc = min(0.42, disc + 0.12)
                is_promo, promo_code = True, f"LEBARAN{d.year}"
            elif march24_promo and ch == "Shopee":
                disc = min(0.32, disc + 0.08)
                is_promo, promo_code = True, "MARET15"
            else:
                is_promo   = disc > 0.15
                promo_code = f"FLASH{d.strftime('%m%Y')}" if is_promo and RNG.random() < 0.4 else None

            disc       = round(float(disc), 2)
            final_px   = max(cost + 5_000, int(base * (1 - disc) / 1_000) * 1_000)
            contrib_px = final_px - cost  # unit contribution (no platform fee yet)

            # Geography
            if ch == "Offline":
                store    = OFFLINE_STORES[store_idx[i]]
                store_id = store["store_id"]
                province = store["province"]
                city     = store["city"]
            else:
                store_id = None
                city     = None
                province = provs[i]

            rows.append({
                "transaction_id":    f"TRX-{d.strftime('%Y%m%d')}-{txn_counter:05d}",
                "transaction_date":  d.isoformat(),
                "channel":           ch,
                "store_id":          store_id,
                "customer_id":       custs[i],
                "sku_id":            sid,
                "category":          sr["category"],
                "subcategory":       sr["subcategory"],
                "brand":             sr["brand"],
                "quantity":          qty,
                "base_price_idr":    base,
                "discount_pct":      disc,
                "final_price_idr":   final_px,
                "revenue_idr":       final_px * qty,
                "cogs_idr":          cost * qty,
                "gross_profit_idr":  contrib_px * qty,
                "is_promo":          is_promo,
                "promo_code":        promo_code,
                "province":          province,
                "city":              city,
            })

    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
#  TABLE 3 — INVENTORY SNAPSHOTS
# ─────────────────────────────────────────────────────────────────────────────

def generate_inventory_snapshots(products_df: pd.DataFrame,
                                  transactions_df: pd.DataFrame) -> pd.DataFrame:
    """
    Monthly inventory snapshots per active SKU.
    Patterns: I2 (Bags accumulating), I3 (Top-20 stockouts), I8 (Q4-2024 Dresses depleted).
    """
    # Monthly sold per SKU from clean transaction dates
    clean_txn = transactions_df.copy()
    # Parse dates safely (some may be dirty already — use errors='coerce')
    clean_txn["ym"] = pd.to_datetime(clean_txn["transaction_date"], errors="coerce").dt.to_period("M").astype(str)
    monthly_sold = (
        clean_txn[clean_txn["ym"].notna()]
        .groupby(["sku_id","ym"])["quantity"]
        .sum()
        .reset_index()
    )
    sold_dict = {(r["sku_id"], r["ym"]): int(r["quantity"])
                 for _, r in monthly_sold.iterrows()}

    active = products_df[products_df["is_active"]].copy().reset_index(drop=True)

    # Build month list
    months = []
    d = START
    while d <= END:
        months.append(d.strftime("%Y-%m"))
        d = date(d.year if d.month < 12 else d.year + 1,
                 d.month + 1 if d.month < 12 else 1, 1)

    # Initial stock levels
    init_stock: dict = {}
    for _, sku in active.iterrows():
        sid = sku["sku_id"]
        if sku["subcategory"] == "Bags":
            init_stock[sid] = int(RNG.integers(90, 170))   # I2: starts HIGH
        elif sku["subcategory"] in {"Dresses","Shirts"}:
            init_stock[sid] = int(RNG.integers(45, 90))
        else:
            init_stock[sid] = int(RNG.integers(30, 70))

    # Identify top-20 high-velocity SKUs (for I3 logic)
    top20_ids = set(
        clean_txn.groupby("sku_id")["quantity"].sum()
        .nlargest(20).index.tolist()
    )

    current = init_stock.copy()
    rows = []

    for ym in months:
        for _, sku in active.iterrows():
            sid  = sku["sku_id"]
            subcat = sku["subcategory"]
            opening = current[sid]
            sold_raw = sold_dict.get((sid, ym), 0)

            # ── Restock logic ─────────────────────────────────────────────
            incoming = 0
            lead_time = int(RNG.integers(7, 22))

            rop = max(12, int(sold_raw * 1.6))

            if opening < rop:
                incoming = int(RNG.integers(35, 90))

                # I3: Top-20 SKUs sometimes get delayed/insufficient restock
                if sid in top20_ids and RNG.random() < 0.32:
                    incoming = max(0, incoming - int(RNG.integers(20, 45)))
                    lead_time = int(RNG.integers(16, 30))

            # I2: Bags always get regular restock but sell so little stock builds up
            if subcat == "Bags":
                incoming = int(RNG.integers(15, 50))

            # I8: Dresses — no restock from Sep 2024 (supply disruption)
            if subcat == "Dresses" and ym >= "2024-09":
                incoming = 0

            avail        = opening + incoming
            actual_sold  = min(sold_raw, avail)
            closing      = max(0, avail - actual_sold)
            current[sid] = closing

            avail_nz  = avail if avail > 0 else 1
            str_val   = round(actual_sold / avail_nz, 4)

            daily_vel = sold_raw / 30.0 if sold_raw > 0 else 0.1
            doi       = min(999, round(closing / daily_vel))

            rows.append({
                "snapshot_id":       f"INV-{ym}-{sid}",
                "year_month":        ym,
                "sku_id":            sid,
                "category":          sku["category"],
                "subcategory":       subcat,
                "brand":             sku["brand"],
                "opening_stock":     opening,
                "incoming_qty":      incoming,
                "sold_qty":          actual_sold,
                "closing_stock":     closing,
                "sell_through_rate": str_val,
                "days_of_inventory": doi,
                "lead_time_days":    lead_time,
                "is_stockout":       1 if closing == 0 and sold_raw > 0 else 0,
            })

    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
#  TABLE 4 — TRAFFIC SESSIONS
# ─────────────────────────────────────────────────────────────────────────────

def generate_traffic_sessions() -> pd.DataFrame:
    """
    Daily sessions per online channel (3 channels × 730 days = 2,190 rows).
    I4: March 2024 — Shopee CVR ~22% (promo), Tokopedia CVR ~11.5% (no lift).
    """
    ONLINE_CHANNELS = ["Shopee", "Tokopedia", "Website"]
    BASE_SESSIONS   = {"Shopee": 1_350, "Tokopedia": 870, "Website": 420}
    BASE_CVR        = {"Shopee": 0.120, "Tokopedia": 0.110, "Website": 0.092}
    AVG_AOV         = {"Shopee": 175_000, "Tokopedia": 198_000, "Website": 228_000}

    rows = []
    for d in ALL_DATES:
        # Multiplier
        mult = 1.0
        if   d.month == 11 and d.day == 11:  mult = 6.2
        elif d.month == 12 and d.day == 12:  mult = 3.5
        elif d.month == 11:                  mult = 1.6
        elif d.year == 2023 and d.month in {4,5}:  mult = 1.3  # Lebaran
        elif d.year == 2024 and d.month in {3,4}:  mult = 1.4  # Ramadan
        elif d.month == 12:                  mult = 1.35

        for ch in ONLINE_CHANNELS:
            sessions = max(60, int(BASE_SESSIONS[ch] * mult * float(RNG.normal(1.0, 0.14))))

            cvr = BASE_CVR[ch]
            # I4: March 2024 Shopee promo → significant CVR lift
            if d.year == 2024 and d.month == 3 and ch == "Shopee":
                cvr = 0.218  # ~82% lift, statistically very significant
            # Tokopedia same period: virtually no change (p > 0.05)
            elif d.year == 2024 and d.month == 3 and ch == "Tokopedia":
                cvr = 0.113  # +0.3pp, noise only
            elif d.month == 11 and d.day == 11:
                cvr = min(0.40, cvr * 2.6)

            cvr    = float(np.clip(RNG.normal(cvr, cvr * 0.18), 0.02, 0.48))
            orders = max(0, int(sessions * cvr))
            aov    = AVG_AOV[ch]
            rev    = max(0, int(orders * aov * float(RNG.normal(1.0, 0.14))))

            rows.append({
                "session_date":     d.isoformat(),
                "channel":          ch,
                "sessions":         sessions,
                "orders":           orders,
                "conversion_rate":  round(cvr, 4),
                "revenue_idr":      rev,
                "avg_order_value":  round(rev / orders) if orders > 0 else 0,
                "is_promo_period":  1 if (
                    (d.month == 11 and d.day == 11) or
                    (d.year == 2024 and d.month == 3 and ch == "Shopee") or
                    (d.month in {4, 5})
                ) else 0,
            })

    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
#  TABLE 5 — MARKETING SPEND
# ─────────────────────────────────────────────────────────────────────────────

def generate_marketing_spend() -> pd.DataFrame:
    """
    Weekly spend per advertising platform (5 platforms × 104 weeks = ~520 rows).
    ROAS varies by season; signals which platform earns best return.
    """
    PLATFORMS = {
        "Shopee Ads":    {"budget": (2_000_000,  8_000_000), "ctr": 0.026, "roas": 3.60},
        "Tokopedia Ads": {"budget": (1_500_000,  5_500_000), "ctr": 0.023, "roas": 3.30},
        "Google Ads":    {"budget": (3_000_000, 10_000_000), "ctr": 0.019, "roas": 2.85},
        "Instagram Ads": {"budget": (2_000_000,  7_000_000), "ctr": 0.013, "roas": 2.60},
        "TikTok Ads":    {"budget": (1_000_000,  5_000_000), "ctr": 0.016, "roas": 2.35},
    }

    rows = []
    ws = START
    while ws <= END:
        season_mult = 1.0
        if ws.month == 11:     season_mult = 3.2
        elif ws.month == 12:   season_mult = 2.2
        elif ws.month in {3,4,5}: season_mult = 1.9

        for platform, cfg in PLATFORMS.items():
            lo, hi = cfg["budget"]
            spend  = int(int(RNG.integers(lo, hi)) * season_mult / 100_000) * 100_000
            impressions = max(0, int(spend / 48 * float(RNG.normal(1.0, 0.18))))
            clicks      = max(0, int(impressions * cfg["ctr"] * float(RNG.normal(1.0, 0.22))))
            roas        = float(cfg["roas"] * float(RNG.normal(1.0, 0.28)))
            rev_attr    = max(0, int(spend * roas / 1_000) * 1_000)
            orders_attr = max(0, int(rev_attr / 195_000))

            rows.append({
                "week_start":            ws.isoformat(),
                "platform":              platform,
                "spend_idr":             spend,
                "impressions":           impressions,
                "clicks":                clicks,
                "ctr":                   round(clicks / impressions, 4) if impressions else 0,
                "orders_attributed":     orders_attr,
                "revenue_attributed_idr": rev_attr,
                "roas":                  round(roas, 2),
            })
        ws += timedelta(days=7)

    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
#  DIRTY DATA INTRODUCTION
# ─────────────────────────────────────────────────────────────────────────────

def introduce_dirty_data(dfs: dict) -> dict:
    """
    Injects intentional data quality issues into products and transactions.
    Each issue maps to a specific cleaning technique the student will learn.
    """
    txn  = dfs["transactions"].copy()
    prod = dfs["products"].copy()
    n    = len(txn)

    # ── D1: Channel name variants ─────────────────────────────────────────
    CH_VARIANTS = {
        "Shopee":    ["shopee",    "SHOPEE",    "Shopee.co.id"],
        "Tokopedia": ["tokopedia", "TOKOPEDIA", "Toped"],
        "Website":   ["website",   "WEBSITE",   "Web"],
        "Offline":   ["offline",   "OFFLINE",   "In-Store"],
    }
    d1_idx = RNG.choice(n, size=210, replace=False)
    for idx in d1_idx:
        orig = txn.loc[idx, "channel"]
        txn.loc[idx, "channel"] = str(RNG.choice(CH_VARIANTS.get(orig, [orig])))

    # ── D2: Prices recorded in USD instead of IDR ─────────────────────────
    # These will have absurdly small values (e.g., 16.75 instead of 250,000)
    price_cols = ["base_price_idr","final_price_idr","revenue_idr","cogs_idr","gross_profit_idr"]
    for col in price_cols:
        txn[col] = txn[col].astype(float)
    d2_idx = RNG.choice(n, size=30, replace=False)
    for idx in d2_idx:
        for col in price_cols:
            txn.loc[idx, col] = round(float(txn.loc[idx, col]) * 0.0000668, 2)

    # ── D3: Negative quantity (returns mis-entered) ───────────────────────
    d3_idx = RNG.choice(n, size=25, replace=False)
    txn.loc[d3_idx, "quantity"] = -txn.loc[d3_idx, "quantity"]

    # ── D4: Duplicate rows (system glitch) ───────────────────────────────
    d4_idx = RNG.choice(n, size=60, replace=False)
    dups   = txn.iloc[d4_idx].copy()
    txn    = pd.concat([txn, dups], ignore_index=True)

    # ── D5: Alternative date formats in ~5% of rows ───────────────────────
    d5_idx = RNG.choice(len(txn), size=int(len(txn) * 0.05), replace=False)
    for idx in d5_idx:
        raw = txn.loc[idx, "transaction_date"]
        try:
            dt = date.fromisoformat(str(raw))
            fmt = int(RNG.integers(0, 2))
            txn.loc[idx, "transaction_date"] = (
                dt.strftime("%d/%m/%Y") if fmt == 0 else dt.strftime("%B %d, %Y")
            )
        except Exception:
            pass

    # ── D6: Province name inconsistencies ────────────────────────────────
    PROV_V = {
        "DKI Jakarta": ["Jakarta",    "JAKARTA",    "Dki Jakarta",   "Jakarta (DKI)"],
        "Jawa Barat":  ["Jabar",      "JAWA BARAT", "West Java",     "Jawa barat"],
        "Jawa Timur":  ["Jatim",      "JAWA TIMUR", "East Java",     "jawa timur"],
        "Jawa Tengah": ["Jateng",     "JAWA TENGAH","Central Java",  "Jawa tengah"],
        "Banten":      ["BANTEN",     "banten"],
    }
    d6_idx = RNG.choice(len(txn), size=180, replace=False)
    for idx in d6_idx:
        p = txn.loc[idx, "province"]
        if p in PROV_V:
            txn.loc[idx, "province"] = str(RNG.choice(PROV_V[p]))

    # ── D7: Missing store_id for some offline rows ────────────────────────
    offline_idx = txn.index[txn["channel"].str.lower().str.contains("offline|in-store", na=False)].tolist()
    if len(offline_idx) > 0:
        miss_n  = max(1, int(len(offline_idx) * 0.015))
        miss_ix = RNG.choice(offline_idx, size=miss_n, replace=False)
        txn.loc[miss_ix, "store_id"] = None

    # ── D8: Product name formatting issues ────────────────────────────────
    d8_idx = RNG.choice(len(prod), size=32, replace=False)
    for idx in d8_idx:
        orig = prod.loc[idx, "product_name"]
        fmt  = int(RNG.integers(0, 3))
        prod.loc[idx, "product_name"] = (
            orig.upper()          if fmt == 0 else
            f"  {orig.lower()}  " if fmt == 1 else
            orig.lower()
        )

    dfs["transactions"] = txn.reset_index(drop=True)
    dfs["products"]     = prod
    return dfs


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    os.makedirs("data/raw", exist_ok=True)
    print("=" * 60)
    print("  Meridian Commerce Co. — Dataset Generator")
    print("=" * 60)

    print("\n[1/6] Generating product catalog (300 SKUs)...")
    products = generate_products()
    print(f"      → {len(products)} rows | categories: {products['category'].nunique()} | brands: {products['brand'].nunique()}")

    print("\n[2/6] Generating transactions (~25,000 rows, 2 years)...")
    transactions = generate_transactions(products)
    print(f"      → {len(transactions)} rows | channels: {transactions['channel'].nunique()} | customers: {transactions['customer_id'].nunique()}")

    print("\n[3/6] Generating inventory snapshots...")
    inventory = generate_inventory_snapshots(products, transactions)
    print(f"      → {len(inventory)} rows | months: {inventory['year_month'].nunique()} | SKUs: {inventory['sku_id'].nunique()}")

    print("\n[4/6] Generating traffic sessions...")
    traffic = generate_traffic_sessions()
    print(f"      → {len(traffic)} rows | channels: {traffic['channel'].nunique()}")

    print("\n[5/6] Generating marketing spend...")
    marketing = generate_marketing_spend()
    print(f"      → {len(marketing)} rows | platforms: {marketing['platform'].nunique()}")

    total_clean = len(products)+len(transactions)+len(inventory)+len(traffic)+len(marketing)
    print(f"\n      Total (clean): {total_clean:,} rows")

    print("\n[6/6] Injecting dirty data...")
    dfs = {
        "products":            products,
        "transactions":        transactions,
        "inventory_snapshots": inventory,
        "traffic_sessions":    traffic,
        "marketing_spend":     marketing,
    }
    dfs = introduce_dirty_data(dfs)
    total_dirty = sum(len(v) for v in dfs.values())
    print(f"      → D1 channel variants | D2 USD prices | D3 neg qty | D4 dupes | D5 date formats | D6 province variants | D7 missing store_id | D8 product name format")
    print(f"      Total (with dirty): {total_dirty:,} rows")

    print("\nSaving CSVs to data/raw/ ...")
    FILENAMES = {
        "products":            "raw_products.csv",
        "transactions":        "raw_transactions.csv",
        "inventory_snapshots": "raw_inventory_snapshots.csv",
        "traffic_sessions":    "raw_traffic_sessions.csv",
        "marketing_spend":     "raw_marketing_spend.csv",
    }
    for key, fname in FILENAMES.items():
        path = os.path.join("data", "raw", fname)
        dfs[key].to_csv(path, index=False)
        kb = os.path.getsize(path) / 1024
        print(f"  ✓  {path:<45} ({len(dfs[key]):>6} rows, {kb:>7.1f} KB)")

    print("\n" + "=" * 60)
    print("  Done! Business issues embedded:")
    issues = [
        "I1  Shopee GMV leader but worst contribution margin",
        "I2  Bags deadstock crisis (STR < 12%)",
        "I3  Top-20 SKU stockout pattern (lost revenue)",
        "I4  March-24 promo: Shopee CVR +82%, Tokopedia +2.6% (not sig.)",
        "I5  11.11 cohort: 72% never repurchase (retention failure)",
        "I6  Jawa Timur +42% YoY but only 9-11% market share",
        "I7  MCC Premium Shirts declining May 2024+",
        "I8  Q4 2024 Dresses -31% vs prior year (stockout miss)",
    ]
    for iss in issues:
        print(f"  {iss}")
    print("=" * 60)


if __name__ == "__main__":
    main()
