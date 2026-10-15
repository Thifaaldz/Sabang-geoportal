"""Konfigurasi Geoportal Sabang.

Data utama: Rupa Bumi Indonesia (RBI) 1:50.000 Kota Sabang dari BIG (141 layer KUGI, folder "shp dataset"),
dikonversi oleh convert_rbi.py. Tiga layer utilitas jaringan (air limbah, SPAM, telkom) skemanya direplikasi dari layanan ArcGIS BP Batam
(web-gis.bpbatam.go.id/arcgis/rest/services/Utilitas/*_LN_50K/MapServer/0),
yang dipakai oleh aplikasi Web AppBuilder "Peta Interaktif - Utilitas"
(item 1fbd4dcf7c074e0dbde881962c17992f, web map f5677a4a10964105b4c6a4ff16b06fe4).
"""

from pathlib import Path

BASE_DIR = Path(__file__).parent
DESA_PATH = BASE_DIR / "sabang.geojson"
LAYER_DIR = BASE_DIR / "data" / "layers"
RBI_DIR = BASE_DIR / "shp dataset" / "KAB_SABANG" / "KAB_SABANG"
RBI_DIR_ACEH_BESAR = BASE_DIR / "shp dataset" / "KAB_SABANG" / "KAB_ACEH_BESAR" / "KAB_ACEH_BESAR" / "KAB_ACEH_BESAR"
CATALOG_PATH = BASE_DIR / "data" / "catalog.json"
PULAU_PATH = BASE_DIR / "data" / "pulau.geojson"
RBI_SOURCE = "RBI 1:50.000 (BIG)"

APP_TITLE = "Geoportal Sabang"
APP_SUBTITLE = "Peta Interaktif Utilitas"

# Warna tema TabTheme pada aplikasi asli
THEME_BG = "#0f2345"
THEME_ACCENT = "#d29c2a"
SELECTION_COLOR = "#00FFFF"  # widget Select: selectionColor

# Extent awal mencakup seluruh Kawasan Sabang (Pulau Weh s.d. Pulau Rondo dan pulau-pulau Pulo Aceh)
HOME_BOUNDS = [[5.545, 94.96], [6.08, 95.38]]
HOME_CENTER = [5.81, 95.17]
HOME_ZOOM = 11

# ------------------------------------------------------------- Kawasan Sabang
# PP 83/2010: Kawasan Sabang = Kota Sabang + sebagian Kab. Aceh Besar (pulau-pulau Pulo Aceh).
# Data RBI Aceh Besar hanya diambil pada pulau-pulau di bawah ini (dipotong oleh convert_rbi.py).
WILAYAH_SABANG = "Kota Sabang"
WILAYAH_PULO_ACEH = "Pulo Aceh (Aceh Besar)"
WILAYAH_COLORS = {WILAYAH_SABANG: "#2a78d6", WILAYAH_PULO_ACEH: "#eb6834"}

# Pulau → (wilayah, catatan). Urutan = urutan tampil di filter/legenda.
PULAU_KAWASAN = {
    "Weh": (WILAYAH_SABANG, "Pulau utama, semua permukiman dan pelabuhan"),
    "Klah": (WILAYAH_SABANG, "Pulau kecil"),
    "Rubiah": (WILAYAH_SABANG, "Pulau kecil, lokasi wisata selam"),
    "Seulako": (WILAYAH_SABANG, "Pulau kecil"),
    "Rondo": (WILAYAH_SABANG, "±42 ha, pulau terluar, berbatasan dengan ZEE"),
    "Breuh": (WILAYAH_PULO_ACEH, "Berpenghuni, bergunung, puncak ±600 mdpl"),
    "Nasi": (WILAYAH_PULO_ACEH, "Berpenghuni, puncak ±300 mdpl"),
    "Teunom": (WILAYAH_PULO_ACEH, "RBI: 'Pulau Nasi Kecil' (gampong Teunom, Gle Keureuse)"),
    "Bunta": (WILAYAH_PULO_ACEH, "Tidak berpenghuni (RBI: Kec. Peukan Bada)"),
    "Tuan Diapit": (WILAYAH_PULO_ACEH, "Tidak berpenghuni (RBI: Kec. Peukan Bada)"),
    "U": (WILAYAH_PULO_ACEH, "Tidak berpenghuni"),
    "Geupon": (WILAYAH_PULO_ACEH, "Tidak berpenghuni"),
    "Sidom": (WILAYAH_PULO_ACEH, "Tidak berpenghuni"),
    "Jroeng": (WILAYAH_PULO_ACEH, "Tidak berpenghuni"),
    "Tangkora": (WILAYAH_PULO_ACEH, "Tidak berpenghuni"),
    "Pulau kecil lain (Pulo Aceh)": (WILAYAH_PULO_ACEH, "Benggala, Bole, Guasarang, Kelapa, dan pulau tak bernama"),
}

# Nama toponimi RBI → pulau (dipakai convert_rbi.py untuk memberi nama poligon pulau)
TOPONIM_PULAU = {
    "Pulau Weh": "Weh", "Pulau Klah": "Klah", "Pulau Rubiah": "Rubiah", "Pulau Seulako": "Seulako",
    "Pulau Rondo": "Rondo", "Pulau Breueh": "Breuh", "Pulau Brueh": "Breuh", "Pulau Nasi Besar": "Nasi",
    "Pulau Nasi Kecil": "Teunom", "Teunom": "Teunom", "Pulau Bunta": "Bunta", "Pulau Tuandipait": "Tuan Diapit",
    "Pulau Ue": "U", "Pulau Geupon": "Geupon", "Pualu Sidom Satu": "Sidom", "Pualu Sidom Dua": "Sidom",
    "Pulau Jroh": "Jroeng", "Pulau Tangkorak": "Tangkora",
}

# Warna pulau: pulau besar berbeda warna, pulau kecil memakai warna muda wilayahnya
PULAU_COLORS = {"Weh": "#2a78d6", "Breuh": "#eb6834", "Nasi": "#1baf7a", "Teunom": "#6250d6"}
PULAU_SMALL_COLORS = {WILAYAH_SABANG: "#7fb2ea", WILAYAH_PULO_ACEH: "#f2a882"}


def pulau_color(pulau):
    if pulau in PULAU_COLORS:
        return PULAU_COLORS[pulau]
    wil = PULAU_KAWASAN.get(pulau, (WILAYAH_PULO_ACEH, ""))[0]
    return PULAU_SMALL_COLORS[wil]

# Basemap gallery. Rupabumi Indonesia (BIG) adalah basemap default di web map asli.
BASEMAPS = {
    "Esri World Topographic": {
        "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
        "attr": "Esri, HERE, Garmin, USGS, NGA",
    },
    "Esri World Imagery": {
        "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        "attr": "Esri, Maxar, Earthstar Geographics",
    },
    "Rupabumi Indonesia (BIG)": {
        "tiles": "https://geoservices.big.go.id/rbi/rest/services/BASEMAP/Rupabumi_Indonesia/MapServer/tile/{z}/{y}/{x}",
        "attr": "Badan Informasi Geospasial",
    },
    "OpenStreetMap": {
        "tiles": "OpenStreetMap",
        "attr": "© OpenStreetMap contributors",
    },
    "Esri Light Gray Canvas": {
        "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}",
        "attr": "Esri, HERE, Garmin",
    },
}

# Warna kecamatan (palet kategorikal tervalidasi, 3 slot pertama + abu-abu untuk wilayah lain)
KECAMATAN_COLORS = {
    "Sukajaya": "#2a78d6",
    "Sukamakmue": "#eb6834",
    "Sukakarya": "#1baf7a",
}
OTHER_COLOR = "#8a8a85"

# Field batas desa (KUGI BA03070040) yang tampil di popup/tabel
DESA_FIELDS = {
    "NAMOBJ": "Nama Desa",
    "WADMKC": "Kecamatan",
    "WADMKK": "Kab/Kota",
    "WADMPR": "Provinsi",
    "KDEPUM": "Kode Desa (PUM)",
    "KDCPUM": "Kode Kecamatan (PUM)",
    "LUASWH": "Luas (ha)",
    "PULAU": "Pulau",
    "UUPP": "Sumber",
    "SRS_ID": "SRS",
}


def _f(name, alias, ftype="str", choices=None, main=False, help=None):
    return {"name": name, "alias": alias, "type": ftype, "choices": choices, "main": main, "help": help}


# Layer jaringan utilitas tambahan bergaya BP Batam (tidak ada di RBI)
CUSTOM_LAYERS = {
    "AIRLIMBAH_LN_50K": {
        "title": "Jaringan Air Limbah",
        "theme": "Utilitas – Air & Limbah",
        "geom": "LineString",
        "source": "Skema layanan BP Batam",
        "service": "gis.fasling.AIRLIMBAH_LN_50K",
        "color": "#855000",  # renderer layanan: [133, 80, 0]
        "width": 1.5,
        "defaults": {
            "fcode": "HE02050220",
            "metadata": "HE02050220_AIRLIMBAH_LN_50K",
            "namobj": "INSTALASI PENGELOLAAN AIR LIMBAH",
            "srs_id": "EPSG 4326 - D WGS 1984",
            "jnslbh": 0,
            "jptyn": 0,
        },
        "fields": [
            _f("fcode", "FCODE"),
            _f("jnslbh", "Jenis Limbah (JNSLBH)", "int"),
            _f("jptyn", "Jenis Pengolahan (JPTYN)", "int"),
            _f("koncou", "Kondisi (KONCOU)"),
            _f("metadata", "METADATA"),
            _f("namobj", "Nama Objek", main=True),
            _f("remark", "Keterangan", main=True),
            _f("srs_id", "SRS_ID"),
            _f("thnopr", "Tahun Operasi", main=True),
            _f("thnpbn", "Tahun Pembangunan", main=True),
            _f("namajln", "Nama Jalan", main=True),
            _f("nopipa", "No. Pipa", main=True, help="Contoh: B22-01-001"),
            _f("spekpipa", "Spesifikasi Pipa", main=True, help="Contoh: D200, L=60m"),
            _f("ktgripipa", "Kategori Pipa", main=True, choices=[
                "#. Sewer Pipeline_Mains",
                "#. Sewer Pipeline_Secondary",
                "#. Sewer Pipeline_Secondary_2",
                "#. Sewer Pipeline_Secondary_3",
                "#. Sewer Pipeline_Pressure",
            ]),
            _f("area", "Area / Kawasan", main=True),
        ],
    },
    "SPAM_LN_50K": {
        "title": "Jaringan Pipa Air Minum (SPAM)",
        "theme": "Utilitas – Air & Limbah",
        "geom": "LineString",
        "source": "Skema disusun ulang (layanan BP Batam hilang)",
        "service": "(layanan tidak tersedia di server asli — skema disusun ulang)",
        "color": "#0070ff",
        "width": 1.5,
        "inferred": True,
        "defaults": {
            "metadata": "SPAM_LN_50K",
            "namobj": "Jaringan Pipa Air Minum",
            "srs_id": "EPSG:4326 - WGS 84",
            "utilitas": "Jaringan Air Minum",
        },
        "fields": [
            _f("fcode", "FCODE"),
            _f("metadata", "METADATA"),
            _f("srs_id", "SRS_ID"),
            _f("namobj", "Nama Objek", main=True),
            _f("ruas", "No. Ruas", "float", main=True),
            _f("nm_jln", "Nama Jalan", main=True),
            _f("jnspipa", "Jenis Pipa", main=True, choices=["Transmisi", "Distribusi Utama", "Distribusi Sekunder", "Pipa Tersier"]),
            _f("diameter", "Diameter (mm)", "float", main=True),
            _f("material", "Material", main=True, choices=["HDPE", "PVC", "GIP", "DCIP", "Steel"]),
            _f("thnpbn", "Tahun Pembangunan", main=True),
            _f("remark", "Keterangan", main=True),
            _f("utilitas", "Utilitas"),
        ],
    },
    "JARINGANTELKOM_LN_50K": {
        "title": "Jaringan Kabel Telekomunikasi",
        "theme": "Utilitas – Telekomunikasi",
        "geom": "LineString",
        "source": "Skema disusun ulang (layanan BP Batam hilang)",
        "service": "(layanan tidak tersedia di server asli — skema disusun ulang)",
        "color": "#8400a8",
        "width": 1.5,
        "inferred": True,
        "defaults": {
            "metadata": "JARINGANTELKOM_LN_50K",
            "namobj": "Jaringan Kabel Telekomunikasi",
            "srs_id": "EPSG:4326 - WGS 84",
            "utilitas": "Jaringan Telekomunikasi",
        },
        "fields": [
            _f("fcode", "FCODE"),
            _f("metadata", "METADATA"),
            _f("srs_id", "SRS_ID"),
            _f("namobj", "Nama Objek", main=True),
            _f("ruas", "No. Ruas", "float", main=True),
            _f("nm_jln", "Nama Jalan", main=True),
            _f("jnskbl", "Jenis Kabel", main=True, choices=["Fiber Optik", "Tembaga", "Koaksial"]),
            _f("posisi", "Posisi", main=True, choices=["Udara (aerial)", "Tanam langsung", "Duct"]),
            _f("operator", "Operator", main=True),
            _f("remark", "Keterangan", main=True),
            _f("utilitas", "Utilitas"),
        ],
    },
}


# ------------------------------------------------------------------ katalog RBI
GEOM_LABEL = {"Point": "titik", "LineString": "garis", "Polygon": "area"}

# Judul layer per nama dasar KUGI (tanpa akhiran _PT/_LN/_AR_50K)
TITLES = {
    "ADMINISTRASI": "Garis Batas Administrasi", "ADMINISTRASIKECAMATAN": "Wilayah Kecamatan (RBI)", "ADMINLAUT": "Batas Administrasi Laut",
    "AGRIKEBUN": "Perkebunan", "AGRILADANG": "Ladang/Tegalan", "AGRISAWAH": "Sawah", "AGRITANAMCAMPUR": "Tanaman Campuran",
    "AIRPORT": "Bandar Udara", "AIRTERJUN": "Air Terjun", "ANTSTASIUNBUMIK": "Antena Stasiun Bumi", "ARENAOLAHRAGA": "Arena Olahraga",
    "BANGUNAN": "Bangunan", "BATUKARANG": "Batu Karang", "BENDUNG": "Bendung", "BENDUNGAN": "Bendungan", "BETING": "Beting",
    "CAGARBUDAYA": "Cagar Budaya", "DANAU": "Danau", "DEPOGAS": "Depo Gas", "DEPOKA": "Depo Kereta Api", "DEPOMINYAK": "Depo Minyak",
    "DERMAGA": "Dermaga", "EMPANG": "Empang", "GARAM": "Tambak Garam", "GARDULISTRIK": "Gardu Listrik", "GARDUTELPON": "Gardu Telepon",
    "GARISRPANTAI": "Garis Pantai", "GENLISTRIK": "Pembangkit Listrik", "GORONG": "Gorong-gorong", "HANKAM": "Pertahanan & Keamanan",
    "HELIPORT": "Helipad", "HIDRANUMUM": "Hidran Umum", "INDUSTRI": "Industri", "IRIGASI": "Saluran Irigasi", "JALAN": "Jalan",
    "JEMBATAN": "Jembatan", "KABELLISTRIK": "Jaringan Kabel Listrik", "KANAL": "Kanal", "KANTORAIRMINUM": "Kantor Air Minum (PDAM)",
    "KANTORGAS": "Kantor Gas", "KANTORKIRIMPAKET": "Kantor Jasa Kiriman", "KANTORPLN": "Kantor PLN", "KANTORPOS": "Kantor Pos",
    "KANTORSTASKOMBUMI": "Stasiun Komunikasi Bumi", "KANTORTELPON": "Kantor Telepon", "KELOLALIMBAH": "Pengelolaan Limbah",
    "KESEHATAN": "Fasilitas Kesehatan", "KOLAM": "Kolam", "KONTUR": "Kontur", "LAGUNA": "Laguna", "LAYANANKESEHATAN": "Layanan Kesehatan",
    "LIGHT": "Mercusuar / Rambu Suar", "MAKAM": "Makam", "MENARAAIRMINUM": "Menara Air", "MENARAEKSPLOITMINYAK": "Menara Eksploitasi Minyak",
    "MENARALISTRIK": "Menara Listrik (SUTT)", "MENARATELPON": "Menara Telekomunikasi (BTS)", "NIAGA": "Niaga / Perdagangan",
    "NONAGRIALANG": "Padang Alang-alang", "NONAGRIHUTANBASAH": "Hutan Lahan Basah", "NONAGRIHUTANKERING": "Hutan Lahan Kering",
    "NONAGRISEMAKBELUKAR": "Semak Belukar", "OLAHAIRMINUM": "Pengolahan Air Minum", "OLAHGAS": "Pengolahan Gas",
    "OLAHMINYAK": "Pengolahan Minyak", "PANCARRADIO": "Pemancar Radio", "PANCARTV": "Pemancar TV", "PELABUHAN": "Pelabuhan",
    "PEMERINTAHAN": "Kantor Pemerintahan", "PEMERINTAHASING": "Perwakilan Asing", "PEMUKIMAN": "Permukiman", "PENDIDIKAN": "Pendidikan",
    "PILARBATAS": "Pilar Batas", "PIPAHIDROKARBON": "Pipa Hidrokarbon", "PIPAMINYAK": "Pipa Minyak", "PUSKESMAS": "Puskesmas",
    "RAWA": "Rawa", "RELKA": "Rel Kereta Api", "RUMAHSAKIT": "Rumah Sakit", "RUNWAY": "Landasan Pacu", "SALURANAIR": "Saluran Air",
    "SARANAIBADAH": "Sarana Ibadah", "SARANATELKOM": "Sarana Telekomunikasi", "SOSIAL": "Fasilitas Sosial", "SPBU": "SPBU",
    "SPOTHEIGHT": "Titik Tinggi", "STASIUNKA": "Stasiun Kereta Api", "STASIUNPASUT": "Stasiun Pasang Surut", "STASIUNRADIO": "Stasiun Radio",
    "STASIUNTV": "Stasiun TV", "SUMBERAIRMINUM": "Sumber Air Minum", "SUMURGAS": "Sumur Gas", "SUMURMINYAK": "Sumur Minyak",
    "SUNGAI": "Sungai", "TAMBAK": "Tambak", "TAMBANGAN": "Tambang", "TANGGUL": "Tanggul", "TAXIWY": "Taxiway",
    "TEMPATSAMPAHAKHIR": "Tempat Pembuangan Akhir (TPA)", "TERMINALBUS": "Terminal Bus", "TEROWONG": "Terowongan",
    "TERUMBUKARANG": "Terumbu Karang", "TIANGLISTRIK": "Tiang Listrik", "TITIKDEM": "Titik DEM", "TONGGAKKM": "Tonggak Kilometer",
    "TOPONIMI": "Nama Tempat (Toponimi)", "WADUK": "Waduk",
}

# Tema Layer List (urutan = urutan tampil) dan anggotanya (nama dasar)
THEMES = {
    "Batas Wilayah": ["ADMINISTRASI", "ADMINISTRASIKECAMATAN", "ADMINLAUT", "PILARBATAS"],
    "Utilitas – Listrik": ["KABELLISTRIK", "TIANGLISTRIK", "GARDULISTRIK", "MENARALISTRIK", "GENLISTRIK", "KANTORPLN"],
    "Utilitas – Telekomunikasi": ["MENARATELPON", "SARANATELKOM", "KANTORTELPON", "GARDUTELPON", "ANTSTASIUNBUMIK",
                                  "KANTORSTASKOMBUMI", "PANCARRADIO", "PANCARTV", "STASIUNRADIO", "STASIUNTV", "JARINGANTELKOM"],
    "Utilitas – Air & Limbah": ["HIDRANUMUM", "OLAHAIRMINUM", "SUMBERAIRMINUM", "MENARAAIRMINUM", "KANTORAIRMINUM", "SALURANAIR",
                                "KELOLALIMBAH", "TEMPATSAMPAHAKHIR", "AIRLIMBAH", "SPAM"],
    "Utilitas – Energi & Migas": ["SPBU", "DEPOGAS", "DEPOMINYAK", "KANTORGAS", "OLAHGAS", "OLAHMINYAK", "SUMURGAS", "SUMURMINYAK",
                                  "MENARAEKSPLOITMINYAK", "PIPAHIDROKARBON", "PIPAMINYAK"],
    "Transportasi": ["JALAN", "JEMBATAN", "TONGGAKKM", "GORONG", "TEROWONG", "TERMINALBUS", "PELABUHAN", "DERMAGA", "LIGHT",
                     "AIRPORT", "RUNWAY", "TAXIWY", "HELIPORT", "RELKA", "STASIUNKA", "DEPOKA"],
    "Fasilitas Umum": ["PEMERINTAHAN", "PENDIDIKAN", "PUSKESMAS", "LAYANANKESEHATAN", "KESEHATAN", "RUMAHSAKIT", "SARANAIBADAH",
                       "NIAGA", "KANTORPOS", "KANTORKIRIMPAKET", "SOSIAL", "ARENAOLAHRAGA", "MAKAM", "CAGARBUDAYA", "HANKAM",
                       "PEMERINTAHASING", "INDUSTRI"],
    "Bangunan & Permukiman": ["BANGUNAN", "PEMUKIMAN"],
    "Hidrografi & Pesisir": ["GARISRPANTAI", "SUNGAI", "DANAU", "WADUK", "RAWA", "LAGUNA", "KOLAM", "EMPANG", "KANAL", "IRIGASI",
                             "BENDUNG", "BENDUNGAN", "TANGGUL", "AIRTERJUN", "BATUKARANG", "TERUMBUKARANG", "BETING", "STASIUNPASUT", "GARAM"],
    "Topografi": ["KONTUR", "SPOTHEIGHT", "TITIKDEM", "TAMBANGAN"],
    "Tutupan Lahan": ["AGRISAWAH", "AGRILADANG", "AGRIKEBUN", "AGRITANAMCAMPUR", "TAMBAK", "NONAGRISEMAKBELUKAR",
                      "NONAGRIHUTANKERING", "NONAGRIHUTANBASAH", "NONAGRIALANG"],
    "Nama Tempat": ["TOPONIMI"],
}

THEME_COLORS = {
    "Batas Wilayah": "#52514e", "Utilitas – Listrik": "#00a133", "Utilitas – Telekomunikasi": "#8400a8",
    "Utilitas – Air & Limbah": "#0070ff", "Utilitas – Energi & Migas": "#c98500", "Transportasi": "#e34948",
    "Fasilitas Umum": "#6250d6", "Bangunan & Permukiman": "#8a8a85", "Hidrografi & Pesisir": "#2a78d6",
    "Topografi": "#a0703c", "Tutupan Lahan": "#7cae3a", "Nama Tempat": "#0b0b0b",
}

# Warna khusus per nama dasar (mengalahkan warna tema)
LAYER_COLORS = {
    "JALAN": "#9b3b2a", "JEMBATAN": "#5c1f14", "SUNGAI": "#2a78d6", "GARISRPANTAI": "#1f4e8c", "DANAU": "#3987e5",
    "KONTUR": "#b08a5a", "SPOTHEIGHT": "#7a5230", "PEMUKIMAN": "#eb6834", "BANGUNAN": "#6b6a66",
    "PENDIDIKAN": "#2a78d6", "PUSKESMAS": "#e34948", "LAYANANKESEHATAN": "#e34948", "RUMAHSAKIT": "#e34948",
    "KESEHATAN": "#e34948", "SARANAIBADAH": "#1baf7a", "PEMERINTAHAN": "#6250d6", "NIAGA": "#eda100",
    "AGRISAWAH": "#d4e157", "AGRILADANG": "#e8c468", "AGRIKEBUN": "#5a9e3a", "TAMBAK": "#7fd1d8",
    "NONAGRISEMAKBELUKAR": "#9fbf6a", "NONAGRIHUTANKERING": "#2f7d32", "PELABUHAN": "#1f4e8c", "AIRPORT": "#52514e",
    "AIRLIMBAH": "#855000", "SPAM": "#0070ff", "JARINGANTELKOM": "#8400a8", "KABELLISTRIK": "#00a133",
}

# Layer yang tampil saat aplikasi dibuka (nama layer lengkap)
DEFAULT_VISIBLE = {
    "JALAN_LN_50K", "PENDIDIKAN_PT_50K", "PUSKESMAS_PT_50K", "LAYANANKESEHATAN_PT_50K", "PEMERINTAHAN_PT_50K",
    "SARANAIBADAH_PT_50K", "PELABUHAN_AR_50K", "AIRPORT_AR_50K", "KANTORAIRMINUM_PT_50K", "STASIUNTV_PT_50K",
    "STASIUNRADIO_PT_50K", "KANTORPOS_PT_50K", "NIAGA_PT_50K",
}

# Alias field KUGI yang umum
FIELD_ALIASES = {
    "NAMOBJ": "Nama Objek", "REMARK": "Keterangan", "FCODE": "Kode Unsur (FCODE)", "LCODE": "Kode Lokasi (LCODE)",
    "SRS_ID": "Sistem Referensi", "METADATA": "Metadata", "LUAS": "Luas", "ALAMAT": "Alamat", "DAYA": "Daya",
    "NAMRJL": "Nama Ruas Jalan", "KONRJL": "Kondisi Jalan", "MATRJL": "Material Perkerasan", "FGSRJL": "Fungsi Jalan",
    "UTKRJL": "Status Jalan", "TOLRJL": "Jalan Tol", "WLYRJL": "Wilayah Jalan", "AUTRJL": "Otoritas Jalan",
    "KLSRJL": "Kelas Jalan", "SPCRJL": "Spesifikasi Jalan", "JPARJL": "Jumlah Jalur", "ARHRJL": "Arah Jalan",
    "STARJL": "Status Ruas", "KLLRJL": "Kelas Lalu Lintas", "MEDRJL": "Median Jalan", "LOCRJL": "Lokasi Jalan",
    "JARRJL": "Jaringan Jalan", "LBRJLN": "Lebar Jalan (m)",
    "TIPJMB": "Tipe Jembatan", "FGSJMB": "Fungsi Jembatan", "TONJMB": "Tonase", "TGGJMB": "Tinggi", "LBRJMB": "Lebar",
    "MATJMB": "Material", "STRJMB": "Struktur", "DEKJMB": "Dek", "BTSJMB": "Bentang", "AYUJMB": "Ayunan", "JBTJMB": "Jumlah Bentang",
    "FGSGOV": "Fungsi Kantor", "KATPDK": "Kategori Pendidikan", "JLPDDK": "Jalur Pendidikan", "FGGPDK": "Fungsi Pendidikan",
    "JJGPDF": "Jenjang Formal", "JNSPDL": "Jenis Pendidikan", "FGSIBD": "Fungsi Ibadah",
    "TIPSNG": "Tipe Sungai", "KLSSNG": "Kelas Sungai", "NAMWS": "Wilayah Sungai", "NAMDAS": "Nama DAS",
    "VALKNT": "Nilai Kontur (m)", "TIPKNT": "Tipe Kontur", "IDXKNT": "Indeks Kontur", "JNSKNT": "Jenis Kontur", "ELEVAS": "Elevasi (m)",
    "KLSTPN": "Kelas Toponimi", "LOKTPN": "Lokasi Toponimi", "ALIAS": "Nama Lain",
    "JGLGRL": "Jenis Gardu", "JNSPLS": "Jenis Pembangkit", "JNSSTK": "Jenis Sarana Telkom", "KAPSTS": "Kapasitas", "DEBIT": "Debit",
    "JNSALR": "Jenis Saluran", "JPLTPL": "Jenis Pengolahan", "TIPRST": "Tipe Rumah Sakit", "JPLYRS": "Jenis Layanan",
    "WADMKC": "Kecamatan", "WADMKK": "Kab/Kota", "WADMPR": "Provinsi", "WADMKD": "Desa/Kelurahan", "LUASWH": "Luas Wilayah (ha)",
    "PULAU": "Pulau", "WILAYAH": "Wilayah Kawasan Sabang",
    "objectid": "OBJECTID", "shape_leng": "Panjang (m)", "luas_ha": "Luas (ha)", "created_by": "Sumber/Editor",
    "created_at": "Dibuat", "updated_at": "Diubah",
}

# Field yang diisi otomatis dan disembunyikan di bagian "lainnya" pada formulir
AUTO_FIELDS = {"FCODE", "LCODE", "METADATA", "SRS_ID", "AQDATE", "PUDATE", "KODLCO", "KLSLCO",
               "fcode", "metadata", "srs_id", "utilitas"}

# Field sistem yang ditambahkan aplikasi ini ke setiap fitur
SYSTEM_FIELDS = ["objectid", "PULAU", "WILAYAH", "shape_leng", "luas_ha", "created_by", "created_at", "updated_at"]

# Ikon titik (Font Awesome 6.2 Free, gaya solid) per nama dasar KUGI; lainnya memakai ikon tema
LAYER_ICONS = {
    # fasilitas umum
    "PENDIDIKAN": "school", "PUSKESMAS": "house-medical", "LAYANANKESEHATAN": "stethoscope", "RUMAHSAKIT": "hospital",
    "KESEHATAN": "kit-medical", "SARANAIBADAH": "mosque", "PEMERINTAHAN": "landmark", "NIAGA": "store",
    "KANTORPOS": "envelope", "KANTORKIRIMPAKET": "box-open", "SOSIAL": "hand-holding-heart", "ARENAOLAHRAGA": "futbol",
    "MAKAM": "monument", "CAGARBUDAYA": "landmark-dome", "HANKAM": "shield-halved", "PEMERINTAHASING": "flag",
    "INDUSTRI": "industry", "BANGUNAN": "building",
    # listrik
    "TIANGLISTRIK": "plug", "GARDULISTRIK": "bolt", "MENARALISTRIK": "tower-observation", "GENLISTRIK": "solar-panel",
    "KANTORPLN": "building-columns",
    # telekomunikasi
    "MENARATELPON": "tower-cell", "SARANATELKOM": "tower-broadcast", "KANTORTELPON": "phone", "GARDUTELPON": "phone",
    "ANTSTASIUNBUMIK": "satellite-dish", "KANTORSTASKOMBUMI": "satellite-dish", "PANCARRADIO": "tower-broadcast",
    "PANCARTV": "tower-broadcast", "STASIUNRADIO": "radio", "STASIUNTV": "tv",
    # air & limbah
    "HIDRANUMUM": "faucet-drip", "OLAHAIRMINUM": "arrow-up-from-water-pump", "SUMBERAIRMINUM": "droplet",
    "MENARAAIRMINUM": "water", "KANTORAIRMINUM": "faucet", "KELOLALIMBAH": "recycle", "TEMPATSAMPAHAKHIR": "trash-can",
    # energi & migas
    "SPBU": "gas-pump", "DEPOGAS": "fire-flame-simple", "KANTORGAS": "fire-flame-simple", "OLAHGAS": "fire-flame-simple",
    "SUMURGAS": "fire-flame-simple", "DEPOMINYAK": "oil-can", "OLAHMINYAK": "oil-can", "SUMURMINYAK": "oil-well",
    "MENARAEKSPLOITMINYAK": "oil-well",
    # transportasi
    "JEMBATAN": "bridge", "TONGGAKKM": "signs-post", "GORONG": "water-ladder", "TEROWONG": "road", "TERMINALBUS": "bus",
    "PELABUHAN": "ship", "DERMAGA": "anchor", "LIGHT": "tower-observation", "AIRPORT": "plane", "RUNWAY": "plane",
    "TAXIWY": "plane", "HELIPORT": "helicopter", "STASIUNKA": "train", "DEPOKA": "train",
    # hidrografi, topografi, lainnya
    "AIRTERJUN": "water", "BENDUNG": "water", "BENDUNGAN": "water", "TANGGUL": "water", "STASIUNPASUT": "ruler-vertical",
    "SPOTHEIGHT": "mountain", "TITIKDEM": "mountain", "TAMBANGAN": "hill-rockslide", "PILARBATAS": "map-pin",
    "TOPONIMI": "location-dot",
}
THEME_ICONS = {
    "Utilitas – Listrik": "bolt", "Utilitas – Telekomunikasi": "tower-broadcast", "Utilitas – Air & Limbah": "droplet",
    "Utilitas – Energi & Migas": "gas-pump", "Transportasi": "road", "Fasilitas Umum": "building",
    "Hidrografi & Pesisir": "water", "Topografi": "mountain",
}
