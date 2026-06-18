# CLEANING_LINE_BY_LINE.md
# `scripts/clean_retail_data.py` — Retail Analytics
# Penjelasan baris per baris untuk belajar

> Ini versi produksi dari logic di notebook. Bedanya: kode di sini TIDAK berisi
> eksplorasi — hanya cleaning yang sudah dipastikan benar dari notebook,
> dikemas agar bisa dijalankan ulang kapanpun dengan satu command.

---

## FILE HEADER — Docstring

```python
"""
clean_retail_data.py
====================
...
"""
```

**Kenapa ada docstring di paling atas file?**
- Ini adalah module-level docstring: penjelasan singkat tentang apa file ini, input/output-nya, dan cara pakainya
- Kalau orang lain (atau diri sendiri 6 bulan lagi) buka file ini, mereka langsung tau tujuannya tanpa harus baca semua kodenya
- Best practice untuk setiap script Python yang akan dijalankan ulang

---

## IMPORTS & CONSTANTS

```python
import os
import warnings
import pandas as pd
import numpy as np
from datetime import datetime
```

Sama dengan di notebook. Bedanya di script tidak ada `from IPython` atau display-related imports karena script tidak jalan di Jupyter — dia jalan di terminal.

```python
RAW_DIR   = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
CLEAN_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "clean")
```

**`os.path.dirname(__file__)`**
- `__file__` = path absolut ke file Python yang sedang berjalan (dalam hal ini: `scripts/clean_retail_data.py`)
- `os.path.dirname(path)` = ambil folder dari path tersebut → hasilnya: folder `scripts/`
- Kenapa tidak pakai `"../data/raw"` langsung? Karena path relative bergantung dari MANA kamu jalankan script. Kalau jalankan dari root: `../data/raw` tidak benar. Dengan `__file__`, path selalu relative ke lokasi script itu sendiri — bisa dijalankan dari directory manapun

**`os.path.join(a, b, c, ...)`**
- Gabungkan beberapa path component dengan separator yang benar untuk OS
- Di Windows: `\`, di Mac/Linux: `/`
- `os.path.join(dirname, "..", "data", "raw")` = naik satu folder dari `scripts/`, lalu masuk `data/raw/`

```python
CHANNEL_MAP = {
    "shopee": "Shopee",
    "SHOPEE": "Shopee",
    ...
}
```

**Kenapa mapping dict di level module (luar function), bukan di dalam function?**
- Constants yang nilainya tidak berubah: taruh di level module
- Kalau di dalam function, dict dibuat ulang setiap kali function dipanggil (inefficient)
- Naming convention: ALLCAPS = constant yang tidak berubah (`CHANNEL_MAP`, `USD_PRICE_THRESHOLD`)

```python
DATE_FORMATS = [
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%B %d, %Y",
    "%b %d, %Y",
    "%d-%m-%Y",
]
```

**Format codes:**
- `%Y` = 4-digit year (2024)
- `%m` = 2-digit month with leading zero (01-12)
- `%d` = 2-digit day with leading zero (01-31)
- `%B` = full month name ("January", "June")
- `%b` = abbreviated month name ("Jan", "Jun")

**Urutan penting:** ISO format (`%Y-%m-%d`) selalu pertama karena dia paling unambiguous.
Kalau kita taruh `%m/%d/%Y` lebih dulu, `"06/25/2024"` akan dicoba parse sebagai bulan ke-06, tapi `"25/06/2024"` akan FAIL di bulan ke-25 (tidak ada). Dengan ISO dulu, kita handle yang jelas terlebih dahulu.

---

## UTILITIES

```python
def parse_date(value) -> str:
    if pd.isna(value) or str(value).strip() == "":
        return np.nan
```

**`-> str`**
- Type hint: function ini seharusnya mengembalikan string
- Tidak enforce di runtime, tapi dokumentasi yang berguna
- Kenapa `-> str` tapi return `np.nan` (float)? Ini sedikit inconsistent — di production yang strict kita pakai `Optional[str]`

**`pd.isna(value)`**
- Cek apakah value adalah "NA-like": `None`, `np.nan`, `pd.NaT`
- Lebih reliable dari `value is None` karena `float("nan") is None` = False, tapi `pd.isna(float("nan"))` = True

```python
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            continue
    return np.nan
```

**Flow logic:**
1. Loop setiap format di DATE_FORMATS
2. Coba parse value dengan format itu
3. Kalau berhasil (no exception) → langsung return hasil dalam ISO format
4. Kalau gagal (ValueError atau TypeError) → `continue` ke format berikutnya
5. Kalau semua format gagal → return NaN

**Mengapa `return` ada DI DALAM try block?**
- Kalau `strptime` berhasil, function langsung selesai (early return)
- `continue` hanya dieksekusi kalau ada exception — kalau tidak ada exception, `except` block di-skip

**`datetime.strptime(value, fmt).strftime("%Y-%m-%d")`**
- Ini adalah chaining: `strptime` menghasilkan datetime object, langsung dipanggil `.strftime()` di-chain
- Kita tidak perlu simpan datetime object di variable intermediate kalau langsung dikonversi ke string

---

## FUNCTION: `_load_raw`

```python
def _load_raw(filename: str) -> pd.DataFrame:
    path = os.path.join(RAW_DIR, filename)
    return pd.read_csv(path, dtype=str)
```

**Underscore prefix `_load_raw`**
- Konvensi Python: fungsi/variable dengan `_` di depan = "private", intended untuk internal use
- Artinya: "jangan panggil fungsi ini dari luar file ini, ini helper untuk internal"
- Tidak di-enforce Python, tapi sinyal penting untuk pembaca kode

**Kenapa pisahkan jadi fungsi sendiri?**
- DRY principle: daripada tulis `pd.read_csv(os.path.join(RAW_DIR, fname), dtype=str)` 5 kali
- Kalau ada perubahan (misal tambah encoding='utf-8'), ubah di satu tempat

---

## FUNCTION: `clean_products`

```python
def clean_products(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
```

**`df = df.copy()` sebagai baris PERTAMA**
- Ini adalah defensive copy: kita tidak mau mengubah DataFrame asli yang di-pass ke function
- Tanpa ini, kalau kita modifikasi `df` di dalam function, `raw_products` di `main()` juga berubah (mereka share memory)
- Pattern: **SELALU copy di awal cleaning function**

```python
    n_dirty = (
        (df["product_name"] == df["product_name"].str.upper()) |
        (df["product_name"] == df["product_name"].str.lower()) |
        (df["product_name"] != df["product_name"].str.strip())
    ).sum()
```

**Multi-line dengan parentheses**
- Di Python, ekspresi di dalam `()` bisa di-break ke multiple lines
- Lebih readable daripada satu baris panjang

**`|` vs `or`**
- `|` = bitwise OR, bekerja element-wise pada pandas Series
- `or` = Python logical OR, TIDAK bekerja pada Series (akan error atau hasilkan unexpected result)
- Rule: selalu pakai `&`, `|`, `~` (bukan `and`, `or`, `not`) untuk operasi boolean di pandas

```python
    df["cost_price_idr"] = pd.to_numeric(df["cost_price_idr"], errors="coerce").astype("Int64")
```

**Kenapa chain `.astype("Int64")` langsung setelah `pd.to_numeric()`?**
- `pd.to_numeric()` mengembalikan Series dengan tipe float64 (karena NaN hanya bisa exist di float)
- `.astype("Int64")` konversi ke pandas nullable integer
- Kenapa nullable integer lebih baik? Karena harga seharusnya integer (tidak ada Rp175.000,5). Float menyiratkan kita punya precision desimal yang sebenarnya tidak ada

---

## FUNCTION: `clean_transactions` (fungsi terpanjang dan terpenting)

```python
def clean_transactions(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    initial_rows = len(df)
```

**`initial_rows = len(df)`**
- Simpan row count sebelum cleaning
- Dipakai di akhir fungsi untuk hitung total yang dihapus
- Pattern tracking: tahu berapa yang hilang dari setiap step memberi accountability

```python
    n_dupes = df.duplicated().sum()
    df = df.drop_duplicates(keep="first").reset_index(drop=True)
    _print_step("transactions", f"Dropped {n_dupes} duplicate rows")
```

**Hitung dulu, drop kemudian**
- Kita hitung `n_dupes` SEBELUM drop, supaya bisa di-log berapa yang dihapus
- Kalau kita drop dulu baru hitung, kita tidak tau berapa yang terhapus

**`_print_step(context, message)`**
- Helper function untuk consistent logging format
- Semua log punya format yang sama: `  [context] message`
- Memudahkan scan output ketika script selesai running

```python
    n_before = df["channel"].nunique()
    df["channel"] = df["channel"].map(CHANNEL_MAP)
    n_unmapped = df["channel"].isnull().sum()
```

**`n_before` dan `n_unmapped`**
- Tracking metrics: berapa variants sebelum, berapa yang tidak ter-map
- Ini bukan untuk analisis — ini untuk logging yang informatif

```python
    usd_mask = df["base_price_idr"] < USD_PRICE_THRESHOLD
    n_usd    = usd_mask.sum()
    df       = df[~usd_mask].reset_index(drop=True)
```

**`~usd_mask`**
- `~` = NOT operator untuk boolean Series di pandas
- `usd_mask` = True untuk baris USD (yang ingin dihapus)
- `~usd_mask` = True untuk baris yang BUKAN USD (yang ingin dipertahankan)
- `df[~usd_mask]` = ambil hanya baris yang bukan USD

---

## FUNCTION: `validate_referential_integrity`

```python
def validate_referential_integrity(products, transactions, inventory):
    valid_skus     = set(products["sku_id"].dropna())
    orphans_txn    = set(transactions["sku_id"].dropna()) - valid_skus
    assert len(orphans_txn) == 0, (
        f"Referential integrity FAIL: {len(orphans_txn)} SKUs..."
    )
```

**Kenapa fungsi validation terpisah dari fungsi cleaning?**
- Separation of Concerns: cleaning = ubah data, validation = cek data
- Validation bisa dijalankan setelah cleaning DAN juga bisa dijalankan di pipeline lain secara independent
- Kalau validation gagal (assert), script berhenti dengan pesan yang jelas — lebih baik dari silent errors

**`assert` di production code**
- Perdebatan di dunia software: `assert` bisa di-disable dengan flag Python (`python -O script.py`)
- Untuk data pipelines (bukan production API), `assert` adalah cara yang acceptable dan sangat readable
- Alternatif production-grade: custom exception classes + logging framework

---

## FUNCTION: `main`

```python
def main():
    print("=" * 60)
    print("  Meridian Commerce Co. — Data Cleaning Pipeline")
    print("=" * 60)
```

**`"=" * 60`**
- String multiplication di Python: `"=" * 60` menghasilkan string 60 karakter `=`
- Pure cosmetic: bikin output terminal lebih mudah dibaca

```python
if __name__ == "__main__":
    main()
```

**`if __name__ == "__main__"`**
- `__name__` adalah variable built-in Python
- Kalau file di-JALANKAN langsung (`python scripts/clean_retail_data.py`): `__name__ == "__main__"` = True → `main()` jalan
- Kalau file di-IMPORT ke file lain (`from scripts.clean_retail_data import parse_date`): `__name__` = nama module → `main()` TIDAK jalan otomatis
- Pattern wajib untuk semua script Python yang juga ingin bisa di-import

> **Analogi:** Kamu bisa jalankan script sebagai "standalone program" ATAU pakai fungsinya di program lain.
> `if __name__ == "__main__"` adalah switch yang memutuskan kapan `main()` jalan otomatis.

---

## SUMMARY: Perbedaan Script vs Notebook

| Aspek | Notebook | Script |
|---|---|---|
| Tujuan | Eksplorasi, belajar, dokumentasi | Dijalankan ulang, otomasi |
| Output | Visual, teks penjelasan | Log di terminal |
| Struktur | Cell-by-cell, linear | Functions + main() |
| Error handling | Fail per cell, investigasi manual | Assert + logging |
| Untuk siapa | Analyst, stakeholder | Engineer, data pipeline |
| Path | Relative ke notebook location | Relative ke script file via `__file__` |

Keduanya punya logika yang sama — bedanya hanya packaging.
