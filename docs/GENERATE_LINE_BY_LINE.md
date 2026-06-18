# GENERATE_LINE_BY_LINE.md
# `scripts/generate_retail_data.py` — Retail Analytics
# Penjelasan baris per baris untuk belajar

> Script ini berbeda dari dua file lainnya — fungsinya bukan "cleaning" tapi
> "generating" data sintetis. Di portfolio real, script ini tidak akan ada
> (data datang dari sistem nyata). Tapi karena kita tidak punya data Meridian
> yang asli, kita generate data yang cukup realistis untuk latihan.

---

## DESAIN FILOSOFI: Synthetic Data

**Kenapa kita perlu generate data sendiri?**
Kita tidak punya akses ke data retail asli. Tapi kita bisa buat data yang:
1. Strukturnya realistis (5 tabel relasional seperti sistem nyata)
2. Punya pola bisnis yang masuk akal (seasonality, channel mix, dsb.)
3. Punya "masalah" yang sengaja ditanam untuk ditemukan saat analisis
4. Punya dirty data yang sengaja ditanam untuk dipraktekkan cleaning-nya

Inilah yang disebut **synthetic data**: data buatan yang dirancang untuk meniru data nyata.

---

## SEED DAN RANDOM NUMBER GENERATOR

```python
RNG = np.random.default_rng(42)
```

**`np.random.default_rng(seed)`**
- `default_rng` = default random number generator, versi modern dari `np.random`
- Lebih baik dari `np.random.seed(42)` lama karena lebih thread-safe dan statistik yang lebih baik
- `seed=42` = "starting point" untuk sequence angka random

**Kenapa kita perlu seed?**
- Random number generator di komputer sebenarnya "pseudo-random" — mereka tidak benar-benar random, tapi menggunakan algoritma deterministik
- Seed menentukan starting point. Seed yang sama = sequence angka yang sama setiap kali
- Tanpa seed: setiap run generate_retail_data.py akan menghasilkan data berbeda
- Dengan `seed=42`: setiap run menghasilkan data yang SAMA PERSIS → reproducibility

> **Kenapa 42?** Convention komunitas data science/ML — angka 42 populer karena referensi
> "Hitchhiker's Guide to the Galaxy". Tidak ada alasan teknis; bisa pakai angka apapun.

```python
START = date(2023, 1, 1)
END   = date(2024, 12, 31)
ALL_DATES = [START + timedelta(days=i) for i in range((END - START).days + 1)]
```

**`date(year, month, day)`**
- Membuat object tanggal dari library `datetime`
- `date` (bukan `datetime`) karena kita hanya butuh tanggal, bukan jam/menit/detik

**`timedelta(days=i)`**
- `timedelta` = selisih waktu. `timedelta(days=1)` = 1 hari
- `START + timedelta(days=i)` = tanggal START ditambah i hari

**List comprehension:**
```python
ALL_DATES = [START + timedelta(days=i) for i in range(...)]
```
- Ini equivalent dengan:
```python
ALL_DATES = []
for i in range(...):
    ALL_DATES.append(START + timedelta(days=i))
```
- List comprehension: cara Python yang lebih ringkas dan cepat untuk buat list dengan loop
- `(END - START).days` = jumlah hari antara kedua tanggal = 730 hari (2 tahun)
- `+ 1` karena kita mau include hari terakhir (range exclusive di akhir)

---

## PRODUCT TAXONOMY

```python
TAXONOMY = {
    "Apparel": {
        "Shirts": {"code": "SH", "n": 60, "price": (75_000, 450_000)},
        ...
    },
    ...
}
```

**Nested dictionary**
- Dictionary di dalam dictionary di dalam dictionary
- Level 1: Category (Apparel, Accessories, Footwear)
- Level 2: Subcategory (Shirts, Dresses, dll.)
- Level 3: Config per subcategory (code, jumlah SKU, range harga)

**`75_000`**
- Python 3.6+: bisa pakai underscore sebagai visual separator dalam angka
- `75_000` = 75000 (sama persis). Lebih mudah dibaca untuk angka besar

---

## FUNCTION: `_daily_base_volume`

```python
def _daily_base_volume(d: date) -> int:
    dow_mult = 1.0 + (0.18 if d.weekday() >= 5 else 0.0) + (0.06 if d.weekday() == 4 else 0.0)
```

**`d.weekday()`**
- Method dari date object: return integer 0 (Monday) sampai 6 (Sunday)
- `>= 5` = Saturday (5) atau Sunday (6) = weekend
- `== 4` = Friday

**Ternary expression dalam addition:**
- `0.18 if d.weekday() >= 5 else 0.0` = kalau weekend, tambah 18% volume; kalau bukan, tambah 0%
- Ini memodelkan pola nyata: orang lebih banyak belanja online di akhir pekan

```python
    special = 1.0
    if   d.month == 11 and d.day == 11: special = 8.5   # Harbolnas 11.11
    elif d.month == 12 and d.day == 12: special = 3.8   # 12.12
    elif d.year == 2023 and d.month == 5 and d.day in {22, 23}: special = 4.2
```

**`d.day in {22, 23}`**
- `in` operator: cek apakah nilai ada di collection
- `{22, 23}` adalah Python set (bukan dict — tidak ada `:`) → lebih cepat dari list untuk `in` check
- Set membership check: O(1), list check: O(n)

**Multiplier values:**
- Harbolnas 11.11: 8.5x volume normal → ini realistic. Shopee/Tokopedia hari Harbolnas bisa 10x+ traffic biasa
- Lebaran: 4.2x → puncak shopping season di Indonesia

---

## FUNCTION: `generate_transactions`

```python
w = np.array([1 / (i + 1) ** 0.72 for i in range(n)], dtype=float)
```

**Power-law distribution:**
- SKU ke-0 (paling populer): weight = 1/1^0.72 = 1.0
- SKU ke-1: weight = 1/2^0.72 = 0.607
- SKU ke-99: weight = 1/100^0.72 = 0.023
- SKU ke-299: weight = 1/300^0.72 = 0.010

**Kenapa power-law?**
- Realitas retail: 20% SKU menghasilkan 80% penjualan (Pareto principle)
- Power-law menghasilkan distribusi seperti ini: beberapa SKU sangat populer, banyak SKU jarang terjual
- Exponent 0.72 dikalibrasi untuk menghasilkan "cukup flat tapi masih power-law"

**`np.array([...], dtype=float)`**
- Konversi list comprehension ke numpy array dengan tipe float
- Numpy array lebih efisien untuk operasi matematika (vectorized) daripada Python list

```python
w[bags_mask] *= 0.22
```

**In-place multiplication dengan boolean mask:**
- `bags_mask` = boolean array: True untuk index yang subcategorynya "Bags"
- `w[bags_mask]` = subset dari w untuk index Bags saja
- `*= 0.22` = kalikan dengan 0.22 (turunkan ke 22% dari nilai semula)
- Ini implement Issue I2: Bags punya demand rendah (deadstock issue)

```python
w /= w.sum()
```

**Normalisasi ke probability distribution:**
- Setelah kita adjust weights, jumlahnya bukan 1.0 lagi
- Dibagi dengan sum-nya → semua weight jadi 0 sampai 1 dan total = 1.0
- `RNG.choice(sku_ids, p=w)` butuh probability yang sum = 1

```python
channels = RNG.choice(CHANNELS, size=vol, p=cw)
skus     = RNG.choice(sku_ids, size=vol, p=day_w)
qtys     = RNG.choice([1, 2, 3, 4], size=vol, p=[0.70, 0.20, 0.07, 0.03])
```

**`RNG.choice(array, size=n, p=probabilities)`**
- Pilih secara random dari `array`, sebanyak `size` kali
- `p` = probability untuk setiap element. Harus sum = 1
- `size=vol` = generate langsung `vol` pilihan sekaligus (vectorized, lebih cepat dari loop)

**Kenapa batch, bukan per-transaksi?**
- Kalau kita panggil `RNG.choice()` 30,000 kali (satu per transaksi), overhead per-call besar
- Dengan `size=vol`, kita panggil sekali per hari untuk semua transaksi hari itu → jauh lebih cepat

---

## DIRTY DATA INTRODUCTION

```python
def introduce_dirty_data(dfs: dict) -> dict:
```

**Kenapa function terpisah untuk dirty data?**
- Clean dan dirty adalah dua phase yang jelas terpisah
- Memudahkan debugging: kalau data bersih tapi perlu dirty, panggil fungsi ini
- Mudah di-disable: kalau perlu generate clean dataset (untuk benchmark), hapus call ke fungsi ini

```python
    price_cols = ["base_price_idr", "final_price_idr", "revenue_idr", "cogs_idr", "gross_profit_idr"]
    for col in price_cols:
        txn[col] = txn[col].astype(float)
    d2_idx = RNG.choice(n, size=30, replace=False)
    for idx in d2_idx:
        for col in price_cols:
            txn.loc[idx, col] = round(float(txn.loc[idx, col]) * 0.0000668, 2)
```

**`astype(float)` sebelum assignment:**
- Kolom integer tidak bisa menyimpan float seperti 16.75
- Kita convert ke float dulu supaya bisa isi nilai USD yang desimal

**`RNG.choice(n, size=30, replace=False)`**
- `replace=False` = sampling tanpa pengembalian. Index yang dipilih tidak bisa muncul dua kali
- Ini memastikan 30 baris BERBEDA yang dapat error USD, bukan baris yang sama 30 kali

**`0.0000668`**
- 1 USD ≈ 14.970 IDR (approximate rate 2023-2024)
- 1 / 14.970 ≈ 0.0000668
- Jadi `250,000 IDR × 0.0000668 ≈ 16.70 USD` — ini yang kita mau simulasikan sebagai error

```python
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
```

**`int(len(txn) * 0.05)`**
- 5% dari total rows → jumlah baris yang akan dapat format tanggal berbeda

**`date.fromisoformat(str)`**
- Parse string ISO date ke date object. Hanya works untuk format YYYY-MM-DD
- Kita perlu ini karena kita mau konversi ISO → format lain, jadi harus parse dulu

**`try/except Exception: pass`**
- Kalau parse gagal (misalnya row yang sudah dapat dirty data sebelumnya), skip
- `pass` = tidak melakukan apa-apa, lanjut ke iterasi berikutnya

---

## FUNGSI MAIN

```python
def main():
    os.makedirs("data/raw", exist_ok=True)
```

**Kenapa `"data/raw"` (relative) bukan `os.path.join(__file__, ...)`?**
- Di generate script, intent-nya adalah dijalankan dari ROOT folder project
- User menjalankan `python scripts/generate_retail_data.py` dari folder `retail-analytics/`
- Jadi `"data/raw"` relative ke current working directory = `retail-analytics/data/raw/`
- Berbeda dengan `clean_retail_data.py` yang pakai `__file__` untuk path — itu lebih robust
- Ini adalah slight inconsistency yang bisa diperbaiki di versi production

---

## KEY CONCEPTS DARI SCRIPT INI

| Concept | Contoh di kode |
|---|---|
| Reproducibility | `np.random.default_rng(seed=42)` |
| Power-law distribution | SKU weight = 1/(rank^0.72) |
| Normalisasi | `w /= w.sum()` setelah adjust |
| Batch generation | `RNG.choice(array, size=vol)` |
| Intentional dirty data | `introduce_dirty_data()` function |
| Business pattern encoding | `day_w[dress_idx] *= 0.28` untuk I8 |

---

## CATATAN: Script Ini Bukan Best Practice Production

Generate script ini dirancang untuk **educational/portfolio** purpose:
- Di real company, data datang dari operational systems (ERP, WMS, POS)
- Tidak ada yang "generate" data bisnis sendiri
- Script ini ada di repo untuk menunjukkan pemahaman tentang struktur data retail,
  bukan sebagai contoh production code

Yang BISA diklaim di interview: "I designed the dataset schema and embedded realistic
business patterns to enable meaningful analysis" — itu adalah skill yang genuine.
