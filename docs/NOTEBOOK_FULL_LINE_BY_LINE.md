# NOTEBOOK_FULL_LINE_BY_LINE.md
# `notebooks/01_data_cleaning.ipynb` — Retail Analytics
# Penjelasan baris per baris untuk belajar

> File ini adalah learning notes pribadi. Tujuannya bukan dokumentasi teknis,
> tapi memahami *kenapa* setiap baris kode ditulis, bukan hanya *apa* yang dilakukan.

---

## SETUP — Cell 3: Import Libraries

```python
import pandas as pd
import numpy as np
import os
import warnings
from datetime import datetime
```

### Penjelasan per baris:

**`import pandas as pd`**
- `pandas` adalah library utama untuk manipulasi data berbentuk tabel (mirip Excel tapi di Python)
- `as pd` = alias. Setiap kali kita mau pakai pandas, kita tulis `pd.something` bukan `pandas.something`
- Kenapa `pd`? Konvensi komunitas Python data — semua orang pakai alias ini, jadi kode lebih mudah dibaca orang lain

**`import numpy as np`**
- `numpy` = numerical Python. Library untuk operasi matematika dan array
- Kita pakai ini terutama untuk `np.nan` (nilai "kosong" dalam konteks numerik) dan `np.clip()` (membatasi nilai dalam range tertentu)
- `as np` = alias standar, sama seperti pd

**`import os`**
- `os` = operating system interface. Dipakai untuk hal-hal seperti buat folder (`os.makedirs`) dan buat path file (`os.path.join`)
- Kenapa `os.path.join` bukan langsung tulis `"data/raw/file.csv"`? Karena `/` (Linux/Mac) vs `\\` (Windows) berbeda. `os.path.join` otomatis pakai separator yang benar untuk sistem operasi apapun

**`import warnings`**
- Library bawaan Python untuk mengatur peringatan (warning messages)
- Kita pakai `warnings.filterwarnings("ignore")` untuk suppress peringatan minor dari pandas yang tidak penting tapi akan bikin output berantakan

**`from datetime import datetime`**
- Kita import class `datetime` dari library `datetime`
- Kenapa bukan `import datetime` saja? Kalau `import datetime`, kita harus tulis `datetime.datetime.strptime(...)` — double nama. Dengan `from datetime import datetime`, kita bisa langsung tulis `datetime.strptime(...)`

```python
pd.set_option("display.max_columns", 30)
pd.set_option("display.max_rows", 50)
pd.set_option("display.float_format", "{:,.2f}".format)
```

**`pd.set_option(key, value)`**
- Mengatur global setting untuk tampilan pandas di Jupyter
- `"display.max_columns", 30` → tampilkan sampai 30 kolom sebelum kolom di-truncate. Default pandas hanya 10-20, kita naikkan supaya semua kolom terlihat
- `"display.max_rows", 50` → tampilkan sampai 50 baris sebelum di-truncate
- `"display.float_format", "{:,.2f}".format` → format tampilan angka float: titik ribuan dan 2 desimal. Jadi `250000.0` tampil sebagai `250,000.00` bukan `2.5e+05`
- Ini hanya mempengaruhi TAMPILAN di notebook, tidak mengubah data aslinya

---

## SETUP — Cell 4: Load Data

```python
RAW_DIR = "../data/raw"
```

**`RAW_DIR = "../data/raw"`**
- `../` artinya "naik satu folder ke atas" dari lokasi notebook
- Notebook ada di `notebooks/`, jadi `../data/raw` mengarah ke `data/raw/` di root project
- Kenapa disimpan di variable? Supaya kalau path berubah, kita hanya ubah di satu tempat (prinsip DRY: Don't Repeat Yourself)

```python
products = pd.read_csv(os.path.join(RAW_DIR, "raw_products.csv"), dtype=str)
```

**`pd.read_csv(filepath, dtype=str)`**
- `pd.read_csv()` membaca file CSV dan mengembalikan DataFrame (tabel data pandas)
- **Argument `filepath`**: path ke file CSV. Kita pakai `os.path.join(RAW_DIR, filename)` supaya path-nya cross-platform
- **Argument `dtype=str`**: paksa SEMUA kolom dibaca sebagai string (teks), bukan dibiarkan pandas tebak tipe datanya

> **PENTING — Kenapa `dtype=str`?**
>
> Default pandas: kalau kolom berisi `1,2,3` dia akan otomatis jadi integer. Kalau ada `2023-01-15` dia akan coba jadi datetime. Masalahnya:
> - Kalau ada satu nilai "25/06/2023" di kolom yang mayoritas "2023-06-25", pandas akan FAIL atau coerce ke NaT (null)
> - Kalau ada harga "16.75" (USD error) di kolom yang mayoritas integer IDR, pandas akan buat kolom jadi float, dan kita kehilangan kemampuan detect anomali
>
> Dengan `dtype=str`, kita melihat data apa adanya. Lalu kita yang memutuskan konversi tipe di akhir setelah data bersih.
> Ini prinsip: **"Load dulu, clean, baru convert"**

```python
print(f"{'Table':<25} {'Rows':>8} {'Columns':>10}")
```

**f-string dengan format spec:**
- `f"..."` = formatted string literal. Kita bisa embed ekspresi Python di dalam `{}`
- `{'Table':<25}` = string `'Table'` diformat dengan lebar 25 karakter, rata kiri (`<`)
- `{'Rows':>8}` = string `'Rows'` dengan lebar 8, rata kanan (`>`)
- Ini untuk bikin tabel teks yang rapi dan aligned di output

---

## INITIAL EXPLORATION — Cell 6-14: Head & Overview

```python
products.head(5)
```

**`.head(n)`**
- Menampilkan n baris pertama DataFrame. Default n=5
- Ini bukan untuk analisis — ini untuk "visual sanity check". Kita lihat: apakah kolom-kolomnya masuk akal? Apakah ada nilai aneh yang langsung kelihatan?
- Biasanya kita mulai dengan `.head()` di setiap tabel baru yang kita dapat

```python
print("Unique channels (raw):", txn["channel"].nunique(), "—", txn["channel"].unique().tolist())
```

**`txn["channel"]`**
- Mengakses kolom "channel" dari DataFrame txn. Hasilnya adalah pandas Series (seperti satu kolom)

**`.nunique()`**
- `n` = number, `unique` = unik → jumlah nilai unik. `nunique()` mengembalikan integer
- Bedanya dengan `.unique()`: `.nunique()` hanya kasih jumlahnya, `.unique()` kasih semua nilainya

**`.unique().tolist()`**
- `.unique()` mengembalikan numpy array dari nilai-nilai unik
- `.tolist()` mengkonversi numpy array ke Python list biasa supaya tampil lebih rapi di print

**`.value_counts()`** (dipakai di beberapa cell)
- Menghitung berapa kali setiap nilai unik muncul, diurutkan dari yang paling sering
- Sangat berguna untuk lihat distribusi data kategoris (channel, province, subcategory, dll.)

---

## SECTION 2.1 — Cell 19: Duplicate Check (ALL Tables)

```python
for name, df in tables.items():
    n_total  = len(df)
    n_dupes  = df.duplicated().sum()
    dupe_pct = n_dupes / n_total * 100 if n_total > 0 else 0
    status   = "WARNING HAS DUPLICATES" if n_dupes > 0 else "clean"
    print(f"  {name:<25} {n_dupes:>6} / {n_total:>7} duplicates ({dupe_pct:.2f}%)  {status}")
```

**`tables.items()`**
- `tables` adalah dictionary: `{"products": df1, "transactions": df2, ...}`
- `.items()` mengembalikan pasangan (key, value) → di sini (name, df)
- Pattern `for name, df in tables.items()` = loop setiap tabel sekaligus dapet nama dan dataframe-nya

**`df.duplicated()`**
- Mengembalikan boolean Series: `True` untuk setiap baris yang merupakan duplikat dari baris sebelumnya
- Default: baris pertama dari setiap duplikat dianggap TIDAK duplikat (Original), baris kedua dan seterusnya = True

**`.sum()` pada boolean Series**
- Di Python, `True = 1` dan `False = 0`. Jadi `.sum()` pada boolean Series menghitung berapa banyak `True`
- `df.duplicated().sum()` = jumlah baris duplikat

**`if n_total > 0 else 0`**
- Ternary expression: "kalau n_total > 0, hitung persen; kalau tidak, return 0"
- Guard clause untuk menghindari division by zero error

---

## SECTION 2.1 — Cell 20: Investigate Duplicates

```python
dupe_mask = txn.duplicated(keep=False)
dupe_rows = txn[dupe_mask].copy()
```

**`df.duplicated(keep=...)`**
- **`keep="first"` (default)**: tandai baris KEDUA dan seterusnya sebagai duplikat. Baris pertama dianggap original
- **`keep="last"`**: tandai semua kecuali baris TERAKHIR
- **`keep=False`**: tandai SEMUA baris yang terlibat dalam duplikasi, termasuk yang pertama
- Di sini kita pakai `keep=False` karena kita mau LIHAT semua copy dari row yang duplikat, bukan hanya yang kedua

**`txn[dupe_mask]`**
- Boolean indexing: dari txn, ambil hanya baris yang `dupe_mask`-nya `True`
- Ini adalah cara paling umum untuk filter DataFrame di pandas

**`.copy()`**
- Membuat salinan DataFrame. Kalau tidak, `dupe_rows` hanya "view" dari `txn` — mengubah `dupe_rows` bisa mengubah `txn` juga (pandas SettingWithCopyWarning)
- Kapan pakai `.copy()`: selalu saat kita buat subset dari DataFrame yang mau kita modifikasi

```python
exact_dupes = txn.duplicated(keep="first").sum()
```
- Di sini kita switch ke `keep="first"` untuk hitung berapa baris yang *akan* dihapus kalau kita `drop_duplicates(keep="first")`
- Hasilnya = baris kedua, ketiga, dst dari setiap set duplikat

---

## SECTION 2.1 — Cell 21: Fix Duplicates

```python
txn = txn.drop_duplicates(keep="first").reset_index(drop=True)
```

**`df.drop_duplicates(keep="first")`**
- Menghapus baris duplikat, MEMPERTAHANKAN kemunculan pertama
- Returns new DataFrame (tidak mengubah in-place kecuali ada `inplace=True`)
- Kita reassign ke `txn` untuk mengganti yang lama

**`.reset_index(drop=True)`**
- Setelah drop, index DataFrame jadi tidak berurutan (misal: 0, 1, 5, 8, 12...) karena baris di tengah sudah dihapus
- `.reset_index()` membuat ulang index dari 0, 1, 2, 3... secara berurutan
- **`drop=True`**: jangan jadikan index lama sebagai kolom baru. Kalau `drop=False`, pandas akan tambah kolom "index" berisi nomor index lama — kita tidak perlu itu

> **Pattern penting**: `df = df.drop_duplicates().reset_index(drop=True)` adalah pattern standard. Hampir selalu dipakai bersama setelah hapus baris apapun.

---

## SECTION 2.2 — Cell 24: Missing Value Check

```python
for name, df in tables.items():
    missing = df.isnull().sum()
    missing = missing[missing > 0]
```

**`df.isnull()`**
- Mengembalikan DataFrame boolean: `True` di setiap cell yang nilainya null/NaN/None
- `.isna()` adalah alias yang sama persis. Bisa pakai salah satu

**`df.isnull().sum()`**
- `.sum()` di DataFrame: menjumlahkan per kolom (axis=0 default)
- Hasilnya: Series di mana index = nama kolom, value = jumlah null di kolom itu

**`missing[missing > 0]`**
- Filter Series: hanya tampilkan kolom yang punya > 0 null
- `missing > 0` menghasilkan boolean Series, lalu kita pakai untuk indexing missing itu sendiri

```python
pct = count / len(df) * 100
```
- Hitung persentase: berapa persen baris di kolom ini yang null?

---

## SECTION 2.2 — Cell 25: Analyze Missing in Context

```python
txn_check["channel_lower"] = txn_check["channel"].str.lower().str.strip()
online_mask = txn_check["channel_lower"].isin(["shopee", "shopee.co.id", "tokopedia", "toped", "website", "web"])
```

**`.str.lower()`**
- Accessor `.str` memungkinkan kita pakai string methods di seluruh kolom pandas sekaligus
- `.lower()` = konversi semua ke huruf kecil. Ini untuk normalisasi sementara sebelum kita cek

**`.str.strip()`**
- Hapus whitespace (spasi, tab, newline) di depan dan belakang string
- Dichain setelah `.lower()` untuk double-clean

**`.isin(list)`**
- Cek apakah setiap value ada di dalam list yang diberikan
- Returns boolean Series: `True` kalau ada, `False` kalau tidak
- Lebih ringkas dari menulis `(col == "shopee") | (col == "tokopedia") | ...`

```python
store_null = txn_check["store_id"].isnull()
print(f"  Online transactions with NULL store_id:  {(online_mask & store_null).sum():,}  EXPECTED")
```

**`online_mask & store_null`**
- `&` = AND operator untuk boolean Series di pandas
- "Online AND null store_id" → baris yang KEDUANYA true
- `:,` dalam f-string = format angka dengan separator ribuan (1234 → 1,234)

> **Logika bisnis di sini:**
> Store_id yang null di online transaction = NORMAL (tidak ada toko fisik)
> Store_id yang null di offline transaction = MASALAH (harusnya ada store_id)
> Inilah yang disebut "context-dependent" missing value — kita tidak bisa judge null itu salah tanpa lihat konteksnya

---

## SECTION 2.3 — Cell 28-30: Channel Standardization

```python
CHANNEL_MAP = {
    "shopee":       "Shopee",
    "SHOPEE":       "Shopee",
    "Shopee.co.id": "Shopee",
    ...
}
```

**Dictionary untuk mapping**
- Key = nilai kotor (yang ada di data), Value = nilai bersih (standar yang kita mau)
- Pendekatan ini lebih maintainable dari `if/elif` chains
- Kalau ada variant baru, kita hanya tambah satu baris di dictionary

```python
txn["channel"] = txn["channel"].map(CHANNEL_MAP)
```

**`.map(dict_or_function)`**
- Menerapkan mapping ke setiap nilai di Series
- Kalau value ada di dictionary → diganti dengan value dictionary
- Kalau value TIDAK ada di dictionary → hasilnya `NaN` (ini bahaya! makanya kita perlu include nilai yang sudah bersih di dictionary juga)

> **`.map()` vs `.replace()`:**
> - `.map(dict)`: nilai yang tidak ada di dict → NaN (strict)
> - `.replace(dict)`: nilai yang tidak ada di dict → dibiarkan apa adanya (lenient)
> - Kita pakai `.map()` di sini supaya kalau ada nilai yang tidak ter-handle, kita langsung tau (muncul sebagai null) daripada diam-diam dibiarkan kotor

```python
n_unmapped = txn["channel"].isnull().sum()
```
- Ini adalah "verification step": cek apakah ada nilai yang tidak ter-map (jadi null)
- Pattern: selalu cek null setelah `.map()` dengan dict untuk pastikan semua nilai ter-handle

---

## SECTION 2.4 — Cell 32-36: Price Anomaly Detection

```python
for col in price_cols:
    txn[col] = pd.to_numeric(txn[col], errors="coerce")
```

**`pd.to_numeric(series, errors=...)`**
- Konversi Series ke tipe numerik
- **`errors="raise"` (default)**: kalau ada nilai yang tidak bisa dikonversi, throw error
- **`errors="coerce"`**: kalau ada nilai yang tidak bisa dikonversi → jadikan `NaN` (null). Ini yang kita mau: data kotor jadi null, bukan crash
- **`errors="ignore"`**: kalau gagal, kembalikan input aslinya (tidak dikonversi) — jarang dipakai karena silent failure

```python
q1    = txn[col].quantile(0.25)
q3    = txn[col].quantile(0.75)
iqr   = q3 - q1
lower_fence = q1 - 1.5 * iqr
upper_fence = q3 + 1.5 * iqr
```

**`.quantile(q)`**
- Mengembalikan nilai di percentile ke-q
- `quantile(0.25)` = Q1 = nilai dimana 25% data ada di bawahnya
- `quantile(0.75)` = Q3 = nilai dimana 75% data ada di bawahnya

**IQR (Interquartile Range)**
- `IQR = Q3 - Q1` = "lebar" dari 50% data di tengah
- **Lower fence = Q1 - 1.5 × IQR**: apapun di bawah ini = outlier bawah
- **Upper fence = Q3 + 1.5 × IQR**: apapun di atas ini = outlier atas
- Angka `1.5` adalah konvensi statistik (dari John Tukey, penemu boxplot). Kenapa 1.5? Secara empiris, untuk distribusi normal, fence ini menangkap ~99.3% data. Di luar itu = unusual enough to investigate

> **Kenapa IQR dan bukan mean + 3σ (z-score)?**
> IQR lebih ROBUST terhadap extreme outlier. Kalau ada 5 baris dengan harga IDR 16.75 (USD error),
> nilai itu akan menarik mean ke bawah dan σ akan besar. Z-score mungkin tidak flag mereka sebagai outlier.
> IQR tidak terpengaruh outlier karena hanya menggunakan Q1 dan Q3, bukan semua data.

```python
usd_mask = txn[txn[col] < lower_fence]
```

- Boolean mask: semua baris dimana `base_price_idr` lebih kecil dari lower fence
- Kita menggunakan lower fence sebagai proxy untuk "kemungkinan USD" karena:
  - Normal IDR price: 50,000+
  - USD-converted price: 5-50 (16.75, 6.68, dll.)
  - Lower fence akan berada di kisaran ribuan → semua di bawah itu clearly abnormal

---

## SECTION 2.5 — Cell 38-40: Negative Quantities

```python
neg_rows["quantity"].value_counts().sort_index()
```

**`.sort_index()`**
- `.value_counts()` default mengurutkan dari yang paling sering
- `.sort_index()` mengurutkan berdasarkan INDEX (di sini = nilai quantity: -4, -3, -2, -1)
- Kita mau lihat distribusi negatifnya, bukan frekuensinya

**Kenapa `df[txn["quantity"] > 0]` bukan `df[txn["quantity"] >= 0]`?**
- Kita eksplisit tidak mau kuantitas = 0 juga. Transaksi dengan qty 0 tidak masuk akal secara bisnis — tidak ada yang terjual, tidak ada yang dikembalikan. Kita hanya mau > 0 (positive sales)

---

## SECTION 2.6 — Cell 42-46: Date Format Parsing

```python
test_parse = pd.to_datetime(txn["transaction_date"], format="%Y-%m-%d", errors="coerce")
```

**`pd.to_datetime(series, format=..., errors=...)`**
- Konversi Series ke datetime type
- **`format="%Y-%m-%d"`**: spesifikasikan format yang diharapkan
  - `%Y` = tahun 4 digit (2023, 2024)
  - `%m` = bulan 2 digit dengan leading zero (01-12)
  - `%d` = hari 2 digit dengan leading zero (01-31)
- **`errors="coerce"`**: nilai yang tidak match format → `NaT` (Not a Time = null untuk datetime)

> **Kenapa bukan biarkan pandas detect otomatis?**
> `pd.to_datetime("05/06/2024")` — pandas tidak tau apakah ini 5 Juni atau 6 Mei.
> Default pandas menggunakan format US (MM/DD), tapi data Indonesia biasanya DD/MM.
> Menetapkan format eksplisit = tidak ada ambiguitas.

```python
def parse_date(value: str) -> str:
    if pd.isna(value) or str(value).strip() == "":
        return np.nan
    value = str(value).strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            continue
    return np.nan
```

**`pd.isna(value)`**
- Cek apakah value adalah null/NaN/None/NaT. Lebih reliable dari `value is None` karena juga handle numpy NaN
- Kita cek ini di awal supaya kita tidak coba parse null value (akan error)

**`str(value).strip()`**
- Konversi ke string dulu (value mungkin bukan string, misalnya float NaN), lalu strip whitespace
- Cek `== ""` untuk handle string kosong

**`datetime.strptime(value, fmt)`**
- `strptime` = "string parse time"
- Convert string ke datetime object berdasarkan format pattern
- Kalau string tidak match format → raise `ValueError`

**`datetime.strftime("%Y-%m-%d")`**
- `strftime` = "string format time"
- Convert datetime object ke string dengan format yang ditentukan
- Kita return ISO format ("%Y-%m-%d") supaya konsisten

**`try/except (ValueError, TypeError): continue`**
- `try`: coba jalankan kode di dalam blok
- `except ValueError, TypeError`: kalau throw salah satu dari dua error ini...
- `continue`: skip ke iterasi loop berikutnya (coba format berikutnya)
- Kenapa DUAN error? `ValueError` = format tidak cocok. `TypeError` = type bukan string (edge case)
- Pattern: "coba semua format, pakai yang pertama berhasil, kalau semua gagal return NaN"

```python
txn["transaction_date"] = txn["transaction_date"].apply(parse_date)
```

**`.apply(function)`**
- Jalankan `function` untuk setiap elemen di Series
- Equivalent dengan `for value in series: function(value)` tapi lebih pythonic
- Hasilnya = Series baru dengan hasil function untuk tiap elemen
- Ini lebih lambat dari vectorized operations (`.str.method()`) tapi jauh lebih flexible untuk custom logic

> **Kapan pakai `.apply()` vs vectorized?**
> - `.apply()`: logic kompleks, multi-format, perlu try/except per baris
> - Vectorized (`.str.replace()`, `pd.to_datetime()`): operasi sederhana yang sama untuk semua baris
> - Di sini kita perlu `.apply()` karena setiap baris mungkin punya format berbeda

---

## SECTION 2.7 — Cell 47-49: Province Standardization

```python
PROVINCE_MAP = {
    "DKI Jakarta": "DKI Jakarta",
    "Jakarta":     "DKI Jakarta",
    "JAKARTA":     "DKI Jakarta",
    ...
}
```

**Kenapa nilai yang sudah bersih juga di-include di mapping?**
- Karena `.map(dict)` menghasilkan `NaN` untuk nilai yang tidak ada di dict
- Kalau kita tidak include `"DKI Jakarta": "DKI Jakarta"`, baris yang sudah bersih akan jadi null
- Rule: **semua possible values harus ada di dict** kalau pakai `.map()`

> **Retail context — kenapa province penting?**
> Di analisis retail, province = unit geografis terkecil yang useful untuk:
> - Market share analysis: "berapa persen penjualan kita dari Jawa Timur?"
> - Expansion decisions: "province mana yang growing tapi underpenetrated?"
> - Logistics planning: "perlu warehouse baru di region mana?"
> Kalau "Jawa Timur" terpecah jadi "Jatim", "jawa timur", "East Java", semua analisis geografis salah

---

## SECTION 2.8 — Cell 50-52: Product Name Formatting

```python
products["name_upper"] = products["product_name"] == products["product_name"].str.upper()
```

- **`str.upper()`**: konversi semua ke UPPERCASE
- Kita bandingkan original dengan uppercase-nya: kalau sama, artinya original memang sudah ALLCAPS
- Hasilnya: boolean column `True` untuk baris yang ALLCAPS

```python
products["product_name"] = products["product_name"].str.strip().str.title()
```

**`.str.strip()`**
- Hapus whitespace (spasi, tab) di AWAL dan AKHIR string
- `" Slim-Fit Shirt "` → `"Slim-Fit Shirt"`
- Tidak mengubah spasi di DALAM string (antara kata)

**`.str.title()`**
- Title case: huruf pertama setiap kata jadi kapital, sisanya lowercase
- `"slim-fit shirt — navy"` → `"Slim-Fit Shirt — Navy"`
- `"SLIM-FIT SHIRT"` → `"Slim-Fit Shirt"`

> **Gotcha `.str.title()`:**
> Ada edge case: `"Men's"` → `"Men'S"` (huruf setelah apostrophe juga di-capitalize)
> Untuk dataset ini hal ini acceptable. Di production dengan banyak apostrophes,
> kita perlu custom title function.

---

## SECTION 3 — Cell 54-56: Referential Integrity

```python
valid_skus      = set(products["sku_id"].dropna())
txn_skus        = set(txn["sku_id"].dropna())
orphan_skus_txn = txn_skus - valid_skus
```

**`set(series)`**
- Konversi pandas Series ke Python set (himpunan)
- Set: collection tanpa duplikat, operasi matematika himpunan sangat cepat

**`.dropna()`**
- Hapus null values sebelum dikonversi ke set. Kalau tidak, `np.nan` akan masuk ke set dan merusak operasi `-`

**`txn_skus - valid_skus`**
- Set difference (pengurangan himpunan): element yang ada di `txn_skus` tapi TIDAK ada di `valid_skus`
- Ini = "orphan SKUs" — transaksi yang mereferensikan produk yang tidak ada di catalog

> **Terminologi: Referential Integrity**
> Dalam database, ini adalah aturan: nilai di kolom FK (foreign key) HARUS ada di tabel parent
> Transactions.sku_id adalah FK → Products.sku_id adalah PK (primary key)
> Kalau ada transaksi dengan sku_id yang tidak ada di products, itu "orphan record"
> Di SQL ini biasanya dikontrol dengan `FOREIGN KEY CONSTRAINT`. Di Python/pandas, kita cek manual dengan set difference

---

## SECTION 4 — Cell 57-61: Statistical Sanity Checks

```python
assert len(orphans_txn) == 0, (
    f"Referential integrity FAIL: {len(orphans_txn)} SKUs..."
)
```

**`assert condition, message`**
- `assert` adalah Python statement untuk validasi: "saya assert (klaim) kondisi ini harus True"
- Kalau `condition` = False → throw `AssertionError` dengan `message`
- Dipakai di cleaning/validation untuk "fail loudly" — kalau data tidak memenuhi expectation, stop dan kasih tau
- Lebih baik dari diam-diam lanjut dengan data yang salah

```python
checks = [
    ("transactions.discount_pct", transactions["discount_pct"].dropna(), 0, 1),
    ...
]
for name, series, lo, hi in checks:
    out_of_range = ((series < lo) | (series > hi)).sum()
```

**`(series < lo) | (series > hi)`**
- `|` = OR operator untuk boolean Series
- "nilai di bawah minimum ATAU di atas maximum" = semua yang out of range
- Hasilnya boolean Series, `.sum()` menghitung berapa banyak yang True

---

## SECTION 2.9 — Cell 62-63: Type Casting

```python
txn["quantity"] = pd.to_numeric(txn["quantity"], errors="coerce").astype("Int64")
```

**`.astype("Int64")` vs `.astype("int64")`**
- `"int64"` (lowercase): integer biasa. TIDAK bisa menyimpan null/NaN. Kalau ada NaN, akan error
- `"Int64"` (capital I): pandas nullable integer. BISA menyimpan NaN. Ini yang kita mau karena data kotor mungkin punya missing values
- Convention: pakai `"Int64"` untuk integer yang bisa null setelah coerce

```python
txn["transaction_date"] = pd.to_datetime(txn["transaction_date"], errors="coerce")
```

- Setelah `parse_date()` semua tanggal sudah dalam format ISO string (YYYY-MM-DD)
- Sekarang kita konversi ke proper datetime object supaya bisa operasi: filter by date, extract month/year, dll.

```python
txn["is_promo"] = txn["is_promo"].map({"True": True, "False": False})
```

- Kita load semua sebagai string, jadi `is_promo` berisi string `"True"` dan `"False"`, bukan boolean
- `.map({"True": True, "False": False})` konversi ke Python boolean
- Kenapa perlu? Karena `"False" == True` dalam Python (string non-kosong = truthy). Kalau kita biarkan string, filter `df[df["is_promo"] == True]` akan salah

---

## FINAL — Cell 64-65: Save Clean Data

```python
os.makedirs(CLEAN_DIR, exist_ok=True)
```

**`os.makedirs(path, exist_ok=True)`**
- Buat directory (folder) beserta semua parent directories yang diperlukan
- `exist_ok=True`: kalau folder sudah ada, JANGAN throw error. Kalau `exist_ok=False` dan folder sudah ada → error

```python
df.to_csv(path, index=False)
```

**`df.to_csv(filepath, index=False)`**
- Simpan DataFrame ke file CSV
- **`index=False`**: JANGAN include index (0, 1, 2, ...) sebagai kolom pertama di CSV. Ini hampir selalu yang kita mau karena index tidak berisi informasi berguna — hanya nomor urut baris

---

## RINGKASAN: Pattern-Pattern Kunci yang Perlu Diingat

| Pattern | Kapan dipakai |
|---|---|
| `df.duplicated(keep=False)` | Lihat semua baris yang terlibat duplikat |
| `df.drop_duplicates().reset_index(drop=True)` | Fix duplikat, selalu pair kedua fungsi ini |
| `df[col].isnull().sum()` | Hitung missing values per kolom |
| `df[boolean_mask].copy()` | Subset + `.copy()` untuk hindari SettingWithCopyWarning |
| `col.map(dict)` | Replace values dengan dict, strict (unmapped → NaN) |
| `col.replace(dict)` | Replace values dengan dict, lenient (unmapped → tetap asli) |
| `pd.to_numeric(col, errors="coerce")` | Convert ke numeric, error → NaN |
| `pd.to_datetime(col, errors="coerce")` | Convert ke datetime, error → NaT |
| `.astype("Int64")` | Cast ke nullable integer (bisa handle NaN) |
| `set(a) - set(b)` | Cari orphan records (referential integrity check) |
| `col.apply(func)` | Custom per-row transformation yang tidak bisa divectorize |
| `assert condition, msg` | Validation yang fail loudly kalau data tidak sesuai |
