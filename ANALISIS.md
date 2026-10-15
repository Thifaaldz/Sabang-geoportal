## Analisis aplikasi acuan: Geoportal BP Batam — Peta Interaktif Utilitas

Sumber: `https://web-gis.bpbatam.go.id/arcgis/apps/webappviewer/index.html?id=1fbd4dcf7c074e0dbde881962c17992f`
Konfigurasi dibaca langsung dari ArcGIS Portal REST API (`/sharing/rest/content/items/<id>/data`) pada 15 Oktober 2026.

### 1. Identitas & arsitektur

| Aspek | Temuan |
|---|---|
| Platform | ArcGIS Enterprise 10.5.1 (Portal + ArcGIS Server), aplikasi **Web AppBuilder 2.4**, 2D |
| Item aplikasi | `1fbd4dcf7c074e0dbde881962c17992f` — "Peta Interaktif - Utilitas", tag `BPBATAM`, publik, dibuat 28 Nov 2023 |
| Web map | `f5677a4a10964105b4c6a4ff16b06fe4`, snippet "Peta Interaktif Data Utilitas", extent Batam (103.70–104.37 BT, 0.91–1.29 LU), Web Mercator (3857) |
| Tema | **TabTheme** — header kiri, sidebar controller vertikal, panel tab; warna latar `#0f2345` (navy), subjudul emas `#d29c2a` |
| Judul | "Geoportal BP Batam" / "Peta Interaktif Utilitas" |
| Basemap default | **Rupabumi Indonesia** (BIG, `geoservices.big.go.id/rbi/.../MapServer`) |
| Proxy | `/arcgis/sharing/proxy`, geometry service ArcGIS Online |

### 2. Layer operasional

Semua layer adalah *ArcGISMapServiceLayer* (hanya-baca, tidak ada FeatureServer → **tidak bisa ditambah/diedit dari web**), seluruhnya polyline, SRS asli UTM 48N (EPSG:32648), semua default **tidak tampil** saat aplikasi dibuka.

| Layer | Layanan | Jumlah fitur | Simbol | FCODE KUGI |
|---|---|---|---|---|
| AIRLIMBAH_LN_50K | `gis.fasling.AIRLIMBAH_LN_50K` | 1.935 | garis cokelat `#855000` | HE02050220 |
| KABELLISTRIK_LN_50K | `gis.dik.KABELLISTRIK_LN_50K` | 195 | garis hijau `#00a133` | HB02050040 |
| JALAN_LN_50K | `gis.dik.JALAN_LN_50K` | 61 | garis hijau tua `#00965f` | CA02050160 |
| SPAM_LN_50K | — | **layanan tidak ditemukan (error 500)** | — | — |
| JARINGANTELKOM_LN_50K | — | **layanan tidak ditemukan (error 500)** | — | — |

**Pengamatan kualitas data**

- *Air limbah*: field `namobj`, `fcode`, `jnslbh`, `jptyn` bernilai tunggal; `thnopr`, `thnpbn`, `koncou` kosong 100%. Informasi berguna ada di `nopipa` (mis. B22-01-001), `spekpipa` (mis. "D200, L=60m"), `ktgripipa` (5 kategori: *Mains, Secondary, Secondary_2, Secondary_3, Pressure*), `namajln`, dan `area` (85 kawasan perumahan).
- *Kabel listrik*: semua `klasifikas` = "SKTM 20 KV", `daya` & `remark` kosong; informasi utama `nm_jln` + `ruas`.
- *Jalan*: dari 33 field KUGI hanya `namobj`, `klsrjl` (6; 5,5; 9 …), `utkrjl` (semua "Jalan Provinsi"), dan `ruas` yang terisi; sisanya string spasi.
- Nilai kosong disimpan sebagai `' '` (spasi), bukan NULL; `srs_id` tidak konsisten antar layer ("EPSG 4326 - D WGS 1984" vs "EPSG:4326 - WGS 84", ada spasi di depan pada layer jalan; FCODE jalan juga diawali spasi).

### 3. Widget

| Widget asli | Posisi | Padanan di aplikasi Streamlit ini |
|---|---|---|
| Header, SidebarController, TabPanel | kiri | Header navy-emas + sidebar bertab (Layer · Tambah · Filter · Pilih · Unggah) |
| ZoomSlider, HomeButton, MyLocation | kiri-atas peta | Zoom Leaflet, tombol ⌂ extent Sabang, LocateControl |
| Search (Esri World Geocoder) | kanan-atas | Geocoder (Nominatim) |
| LayerList (legend, transparansi, zoom-to, tabel atribut) | kanan-atas | Panel **Layer**: centang tampil, slider transparansi, legenda |
| BasemapGallery | kanan-atas | Pilihan basemap (Esri Topo/Imagery, Rupabumi BIG, OSM, Carto) |
| Coordinate, Scalebar | kiri-bawah | MousePosition + skala |
| OverviewMap | kanan-bawah | MiniMap |
| AttributeTable | bawah peta | **Tabel Atribut** bertab per layer: pilih baris → zoom, edit sel, hapus, unduh CSV/GeoJSON |
| AddData | panel | Panel **Unggah**: GeoJSON sementara + impor permanen ke layer |
| Filter | panel | Panel **Filter** (=, ≠, mengandung, >, <) per layer, berlaku untuk peta & tabel |
| Legend | panel | Legenda di panel Layer |
| Select (warna seleksi `#00FFFF`) | panel | Panel **Pilih** desa (klik/daftar) disorot cyan + ringkasan utilitas dalam wilayah |
| Measurement (km, m²) | panel | MeasureControl (km/m, m²/ha) |
| Splash, ExtentNavigate | nonaktif | tidak direplikasi |

### 4. Apa yang berbeda / ditambahkan

1. **Data Sabang**: `sabang.geojson` — 19 poligon batas desa (KUGI BA03070040, sumber "Hasil Delineasi Batas Desa 2019", SRGI 2013). 18 desa di Kota Sabang (Kec. Sukajaya 7, Sukamakmue 6, Sukakarya 5) + 1 desa **Melingge (Kec. Pulo Aceh, Kab. Aceh Besar)** yang ikut terbawa — ditampilkan abu-abu dan dapat dikecualikan di dashboard. Field kode BPS (`KDBBPS`, `KDCBPS`, …) dan `WIADK*` kosong semua.
2. **Layer utilitas Sabang** memakai skema field yang sama persis dengan layanan BP Batam (nama field huruf kecil, urutan sama, nilai default FCODE/METADATA/SRS_ID/UTILITAS terisi otomatis). Untuk SPAM dan Telkom yang layanannya hilang, skema disusun ulang mengikuti pola KUGI dan ditandai di aplikasi.
3. **Pengguna dapat menambah data** (aslinya hanya-baca): gambar polyline → isi formulir atribut → tersimpan ke `data/layers/<LAYER>.geojson`. Panjang (`shape_leng`) dihitung geodesik dalam meter; dicatat juga `created_by`, `created_at`, `updated_at`. Edit atribut & hapus fitur dari tabel atribut.
4. **Dashboard analisis**: luas per desa/kecamatan, validasi LUASWH terhadap luas geodesik, panjang jaringan per desa (hasil *overlay* garis × poligon), kerapatan jaringan (m/ha), kelengkapan atribut per field, dan riwayat penambahan data.

### 5. Batasan

- Penyimpanan berbasis berkas GeoJSON (cocok untuk prototipe; untuk multi-pengguna serentak sebaiknya pindah ke PostGIS/GeoPackage dengan autentikasi).
- Basemap Rupabumi BIG bergantung pada ketersediaan server BIG.
- Data utilitas Batam **tidak** disalin — wilayahnya berbeda (Batam, bukan Sabang); yang direplikasi adalah struktur, simbologi, dan perilaku aplikasinya. Data Sabang berasal dari RBI 1:50.000 (lihat bagian berikut).

## Dataset RBI 1:50.000 Kota Sabang (folder `shp dataset`)

Sumber: Rupa Bumi Indonesia (BIG), format KUGI, WGS84 + elevasi EGM2008 (nilai Z dibuang saat konversi). Dikonversi oleh `convert_rbi.py` ke `data/layers/<LAYER>.geojson` dan katalog `data/catalog.json`; fitur tambahan pengguna dipertahankan bila konversi dijalankan ulang.

- **141 layer**: 32 berisi data, 109 kosong (hanya skema) — layer kosong dipakai sebagai tujuan *Tambah* data (titik/garis/area) dengan formulir yang dibangkitkan dari skemanya.
- Terbesar: Jalan 261 garis, Toponimi 226, Bangunan 221 titik, Sungai 214, Kontur 211 (19 MB; disederhanakan ±2 m hanya untuk tampilan peta), Jembatan 141, Pemerintahan 98, Permukiman 87, Sarana Ibadah 82, Pendidikan 51, Puskesmas 13.
- Layer utilitas RBI hampir seluruhnya kosong (hanya Kantor Air Minum 3, Stasiun TV 2, Stasiun Radio 1).
- Kualitas: atribut jalan hampir kosong (hanya `REMARK`: Jalan Lain 243, Jalan Setapak 13, Jalan Lokal 5); `ADMINISTRASIKECAMATAN_AR` hanya 6 poligon tanpa Kec. Sukamakmue (batas wilayah tetap memakai `sabang.geojson`); bangunan titik dan 207/214 sungai tanpa nama; FCODE kosong pada layer yang tidak berisi data.
- Simbol titik memakai ikon Font Awesome per jenis (sekolah, puskesmas, masjid, SPBU, menara BTS, dst.).
