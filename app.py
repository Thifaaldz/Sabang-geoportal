"""Geoportal Sabang — Peta Interaktif Utilitas (Streamlit).

Replika fungsional aplikasi Web AppBuilder "Geoportal BP Batam - Peta Interaktif Utilitas"
dengan data RBI 1:50.000 Kawasan Sabang (Kota Sabang + pulau-pulau Pulo Aceh, Kab. Aceh Besar; 141 layer KUGI)
+ batas desa, dapat difilter/diwarnai per wilayah & pulau, dan pengguna dapat
menambah/mengedit fitur titik, garis, maupun area.

Persiapan data (sekali, atau setelah shapefile diperbarui):  python convert_rbi.py
Jalankan:  streamlit run app.py
"""

import json
import math
from pathlib import Path

import folium
import pandas as pd
import plotly.express as px
import streamlit as st
from branca.element import MacroElement
from folium import plugins
from jinja2 import Template
from shapely.geometry import mapping, shape
from streamlit_folium import st_folium

import config
import store
from config import (
    APP_SUBTITLE, APP_TITLE, BASEMAPS, CATALOG_PATH, DEFAULT_VISIBLE, DESA_FIELDS, FIELD_ALIASES, GEOM_LABEL,
    HOME_BOUNDS, HOME_CENTER, HOME_ZOOM, KECAMATAN_COLORS, OTHER_COLOR, PULAU_KAWASAN, RBI_SOURCE, SELECTION_COLOR,
    THEME_ACCENT, THEME_BG, WILAYAH_COLORS, WILAYAH_PULO_ACEH, WILAYAH_SABANG, pulau_color,
)

st.set_page_config(page_title=f"{APP_TITLE} — {APP_SUBTITLE}", page_icon="🗺️", layout="wide")

DESA_ID = "BATAS_DESA_AR"
UPLOAD_COLOR = "#6250d6"
OPERATORS = ["=", "≠", "mengandung", ">", "<"]
GEOM_ICON = {"Point": "●", "LineString": "━", "Polygon": "■"}
DISPLAY_TOLERANCE = 0.00002  # ±2 m; hanya untuk tampilan peta, data asli tidak diubah
PULAU_ID = "PULAU_KAWASAN"
ALL_PULAU = list(PULAU_KAWASAN)
WILAYAH_OPTIONS = {  # pilihan cepat wilayah → daftar pulau
    "Seluruh Kawasan Sabang": ALL_PULAU,
    WILAYAH_SABANG: [p for p, (w, _) in PULAU_KAWASAN.items() if w == WILAYAH_SABANG],
    WILAYAH_PULO_ACEH: [p for p, (w, _) in PULAU_KAWASAN.items() if w == WILAYAH_PULO_ACEH],
    **{(p if p.startswith("Pulau") else f"Pulau {p}") + f" · {w}": [p] for p, (w, _) in PULAU_KAWASAN.items()},
    "Pilih beberapa pulau…": None,
}
COLOR_MODES = ["Per layer", "Per wilayah", "Per pulau"]

# Kategori fasilitas untuk dashboard (urutan & warna tervalidasi; warna = simbol di peta)
FACILITY_GROUPS = {
    "Pendidikan": (["PENDIDIKAN_PT_50K"], "#2a78d6"),
    "Kesehatan": (["PUSKESMAS_PT_50K", "LAYANANKESEHATAN_PT_50K", "RUMAHSAKIT_PT_50K", "KESEHATAN_PT_50K"], "#e34948"),
    "Pemerintahan": (["PEMERINTAHAN_PT_50K"], "#6250d6"),
    "Ibadah": (["SARANAIBADAH_PT_50K"], "#1baf7a"),
    "Niaga": (["NIAGA_PT_50K"], "#eda100"),
}
ROAD_COLORS = {"Jalan Lokal": "#2a78d6", "Jalan Lain": "#eb6834", "Jalan Setapak": "#1baf7a"}

# ------------------------------------------------------------------ styling
st.markdown(
    f"""
    <style>
      .block-container {{ padding-top: 3.2rem; padding-bottom: 1rem; }}
      .gp-header {{ background: {THEME_BG}; color: #fff; padding: 10px 18px; border-radius: 6px;
                   display: flex; align-items: center; gap: 14px; margin-bottom: 10px; }}
      .gp-header .logo {{ font-size: 30px; line-height: 1; }}
      .gp-header .t {{ font-size: 20px; font-weight: 700; }}
      .gp-header .s {{ font-size: 15px; font-weight: 700; color: {THEME_ACCENT}; }}
      [data-testid="stSidebar"] {{ background: #f3f5f9; }}
      .legend-row {{ display: flex; align-items: center; gap: 8px; font-size: 13px; margin: 2px 0; }}
      .legend-line {{ width: 22px; height: 0; border-top-style: solid; flex: none; }}
      .legend-box {{ width: 16px; height: 11px; border: 1.5px solid; flex: none; }}
      .legend-dot {{ width: 10px; height: 10px; border-radius: 50%; border: 1.5px solid #fff;
                    box-shadow: 0 0 0 1px #8a8a85; margin: 0 6px 0 5px; flex: none; }}
      .legend-icon {{ width: 20px; height: 20px; border-radius: 50%; color: #fff; font-size: 10px; flex: none;
                     display: inline-flex; align-items: center; justify-content: center; border: 1.5px solid #fff;
                     box-shadow: 0 0 0 1px #c3c2b7; }}
      .kpi {{ border: 1px solid #d9dde5; border-radius: 6px; padding: 10px 14px; }}
      .kpi .v {{ font-size: 24px; font-weight: 700; color: #0b0b0b; }}
      .kpi .l {{ font-size: 13px; color: #52514e; }}
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown('<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@6.2.0/css/all.min.css">',
            unsafe_allow_html=True)


# --------------------------------------------------------------------- data
@st.cache_resource
def _catalog(mtime):
    return store.get_catalog()


@st.cache_resource
def _desa():
    return store.load_desa()


@st.cache_resource
def _pulau(mtime):
    return store.load_pulau()


@st.cache_resource(max_entries=400)
def _layer(layer_id, mtime):
    return store.load_layer(layer_id)


@st.cache_resource(max_entries=400)
def _display(layer_id, mtime):
    """Fitur untuk peta: geometri disederhanakan agar ringan."""
    feats = []
    for f in _layer(layer_id, mtime)["features"]:
        g = shape(f["geometry"])
        if g.geom_type != "Point" and g.geom_type != "MultiPoint":
            g = g.simplify(DISPLAY_TOLERANCE, preserve_topology=True)
        feats.append({"type": "Feature", "id": f.get("id"), "geometry": mapping(g), "properties": f["properties"]})
    return feats


@st.cache_resource(max_entries=400)
def _overlay(layer_id, mtime, only_sabang):
    desa = _desa()
    sub = {"features": [f for f in desa["features"] if not only_sabang or f["properties"]["WADMKK"] == "Kota Sabang"]}
    return store.overlay_by_desa(sub, CAT[layer_id], _layer(layer_id, mtime)["features"])


if not CATALOG_PATH.exists():
    st.error("Katalog RBI belum dibuat. Jalankan dulu: `python convert_rbi.py`")
    st.stop()

CAT = _catalog(CATALOG_PATH.stat().st_mtime)
desa_fc = _desa()
pulau_fc = _pulau(store.PULAU_PATH.stat().st_mtime if store.PULAU_PATH.exists() else 0.0)


def feats(lid):
    return _layer(lid, store.layer_mtime(lid))["features"]


def display_feats(lid):
    return _display(lid, store.layer_mtime(lid))


def overlay(lid, only_sabang=True):
    return _overlay(lid, store.layer_mtime(lid), only_sabang)


COUNTS = {lid: len(feats(lid)) for lid in CAT}


# ------------------------------------------------------------------- state
def init_state():
    ss = st.session_state
    ss.setdefault("map_ver", 0)
    # base_view: posisi awal saat komponen peta dibuat; nav: perintah zoom terprogram (satu-satunya
    # yang dikirim sebagai center/zoom ke st_folium, sehingga tidak ada loop maju-mundur)
    ss.setdefault("base_view", {"center": HOME_CENTER, "zoom": HOME_ZOOM})
    ss.setdefault("nav", None)
    ss.setdefault("nav_n", 0)
    ss.setdefault("filters", [])
    ss.setdefault("uploads", [])
    ss.setdefault("pulau", ALL_PULAU)  # filter Kawasan Sabang: pulau yang ditampilkan
    ss.setdefault("color_mode", COLOR_MODES[0])
    ss.setdefault("visible", {DESA_ID: True, "LABEL": True, PULAU_ID: True, **{lid: lid in DEFAULT_VISIBLE for lid in CAT}})
    ss.setdefault("opacity", {DESA_ID: 0.2, "AREA": 0.45})
    ss.setdefault("selected_desa", [])
    ss.setdefault("highlight", None)  # (layer_id, objectid)


init_state()
ss = st.session_state


def bounds_to_view(bounds):
    (s, w), (n, e) = bounds
    span = max(e - w, n - s, 0.0005)
    zoom = int(max(3, min(18, math.floor(math.log2(800 * 360 / (256 * span * 1.3))))))
    return [(s + n) / 2, (w + e) / 2], zoom


def zoom_to(bounds):
    if not bounds:
        return
    center, zoom = bounds_to_view(bounds)
    ss.nav_n += 1  # geser sangat kecil agar zoom ke target yang sama tetap terdeteksi
    ss.nav = {"center": [center[0] + ss.nav_n * 1e-9, center[1]], "zoom": zoom}


def reset_map(focus_bounds=None):
    """Buat ulang komponen peta (menghapus gambar sementara), lalu fokus ke bounds bila ada."""
    if focus_bounds:
        center, zoom = bounds_to_view(focus_bounds)
        ss.base_view = {"center": center, "zoom": min(zoom, 17)}
    ss.nav = None
    ss.map_ver += 1


def in_kawasan(features):
    """Fitur pada pulau yang dipilih di filter Kawasan Sabang."""
    if len(ss.pulau) == len(ALL_PULAU):
        return features
    keep = set(ss.pulau)
    return [f for f in features if f["properties"].get("PULAU") in keep]


def feature_color(props, default):
    if ss.color_mode == "Per wilayah":
        return WILAYAH_COLORS.get(props.get("WILAYAH"), OTHER_COLOR)
    if ss.color_mode == "Per pulau":
        return pulau_color(props["PULAU"]) if props.get("PULAU") else OTHER_COLOR
    return default


def apply_filters(layer_id, features):
    features = in_kawasan(features)
    for flt in ss.filters:
        if flt["layer"] != layer_id:
            continue
        out = []
        for f in features:
            v = f["properties"].get(flt["field"])
            target = flt["value"]
            try:
                if flt["op"] == "=":
                    ok = str(v).lower() == target.lower()
                elif flt["op"] == "≠":
                    ok = str(v).lower() != target.lower()
                elif flt["op"] == "mengandung":
                    ok = target.lower() in str(v).lower()
                elif flt["op"] == ">":
                    ok = v is not None and float(v) > float(target.replace(",", "."))
                else:
                    ok = v is not None and float(v) < float(target.replace(",", "."))
            except ValueError:
                ok = False
            if ok:
                out.append(f)
        features = out
    return features


def layer_title(lid):
    return "Batas Desa/Kelurahan" if lid == DESA_ID else CAT[lid]["title"]


def layer_label(lid):
    if lid == DESA_ID:
        return f"■ Batas Desa/Kelurahan ({len(desa_fc['features'])})"
    c = CAT[lid]
    return f"{GEOM_ICON[c['geom']]} {c['title']} ({COUNTS[lid]})"


def layer_fields(lid):
    if lid == DESA_ID:
        return list(DESA_FIELDS)
    return store.table_columns(CAT[lid])


def current_drawings():
    val = ss.get(f"map_{ss.map_ver}") or {}
    return [d["geometry"] for d in (val.get("all_drawings") or []) if d and d.get("geometry")]


# Ikon titik: lingkaran berwarna (warna layer) berisi glyph Font Awesome putih
SMALL_ICON_LAYERS = {"TOPONIMI", "BANGUNAN", "SPOTHEIGHT", "TITIKDEM", "TONGGAKKM"}  # layer padat → ikon lebih kecil


def icon_html(icon, color, size=22):
    # gaya inline: peta dirender di iframe sehingga CSS halaman tidak berlaku di dalamnya
    return (f'<div style="width:{size}px;height:{size}px;background:{color};font-size:{round(size * 0.5)}px;color:#fff;'
            'display:flex;align-items:center;justify-content:center;border-radius:50%;border:2px solid #fff;'
            f'box-sizing:border-box;box-shadow:0 1px 4px rgba(0,0,0,.45)"><i class="fa-solid fa-{icon}"></i></div>')


def legend_symbol(geom, color, width=2, icon=None):
    if geom == "Point":
        if icon:
            return f'<span class="legend-icon" style="background:{color}"><i class="fa-solid fa-{icon}"></i></span>'
        return f'<span class="legend-dot" style="background:{color}"></span>'
    if geom == "LineString":
        return f'<span class="legend-line" style="border-color:{color};border-top-width:{width + 1}px"></span>'
    return f'<span class="legend-box" style="border-color:{color};background:{color}66"></span>'


def fmt_measure(layer, value):
    if layer["geom"] == "Point":
        return f"{int(value)} titik"
    if layer["geom"] == "LineString":
        return f"{value / 1000:,.2f} km"
    return f"{value:,.1f} ha"


THEMES = {}
for lid, c in CAT.items():
    THEMES.setdefault(c["theme"], []).append(lid)

# ------------------------------------------------------------------ header
st.markdown(
    f"""<div class="gp-header"><div class="logo">🗺️</div>
        <div><div class="t">{APP_TITLE}</div><div class="s">{APP_SUBTITLE}</div></div></div>""",
    unsafe_allow_html=True,
)

# ============================================================ SIDEBAR (panel widget)
with st.sidebar:
    st.markdown("#### Kawasan Sabang")
    cur = next((k for k, v in WILAYAH_OPTIONS.items() if v == ss.pulau), "Pilih beberapa pulau…")
    wil = st.selectbox("Wilayah / pulau", list(WILAYAH_OPTIONS), index=list(WILAYAH_OPTIONS).index(cur), key="wilayah",
                       help="PP 83/2010: Kota Sabang + pulau-pulau Pulo Aceh (Kab. Aceh Besar). Berlaku untuk peta, tabel, dan dashboard.")
    if wil == "Pilih beberapa pulau…":
        chosen = st.multiselect("Pulau", ALL_PULAU, default=ss.pulau, key="pilih_pulau",
                                format_func=lambda p: f"{p} — {PULAU_KAWASAN[p][0]}")
        chosen = [p for p in ALL_PULAU if p in chosen]
    else:
        chosen = WILAYAH_OPTIONS[wil]
    if chosen != ss.pulau:
        ss.pulau = chosen
        zoom_to(store.fc_bounds([f for f in pulau_fc["features"] if f["properties"]["PULAU"] in chosen]))
    ss.color_mode = st.radio("Warna fitur", COLOR_MODES, index=COLOR_MODES.index(ss.color_mode), horizontal=True, key="color_mode_r",
                             help="Per wilayah: Kota Sabang vs Pulo Aceh · Per pulau: tiap pulau besar berbeda warna")
    st.divider()
    st.markdown("#### Panel Widget")
    t_layer, t_add, t_filter, t_select, t_upload = st.tabs(["Layer", "Tambah", "Filter", "Pilih", "Unggah"])

    # ---- Layer List + Legend
    with t_layer:
        st.caption("Basemap: pilih lewat ikon layer di pojok kanan atas peta")
        show_empty = st.toggle("Tampilkan layer kosong", value=False,
                               help="109 layer RBI belum berisi data — tersedia sebagai tujuan 'Tambah' data baru")
        ss.visible[PULAU_ID] = st.checkbox(f"Pulau Kawasan Sabang ({len(pulau_fc['features'])})", value=ss.visible[PULAU_ID], key="vis_pulau")
        c1, c2 = st.columns(2)
        ss.visible[DESA_ID] = c1.checkbox("Batas desa", value=ss.visible[DESA_ID], key="vis_desa")
        ss.visible["LABEL"] = c2.checkbox("Label desa", value=ss.visible["LABEL"], key="vis_label")
        for theme, lids in THEMES.items():
            shown = [lid for lid in lids if show_empty or COUNTS[lid] > 0]
            if not shown:
                continue
            n_on = sum(ss.visible[lid] for lid in shown)
            with st.expander(f"{theme}  ·  {n_on}/{len(shown)}"):
                for lid in shown:
                    ss.visible[lid] = st.checkbox(layer_label(lid), value=ss.visible[lid], key=f"vis_{lid}",
                                                  help=f"{lid} · {CAT[lid]['source']}")
        with st.expander("Transparansi"):
            ss.opacity[DESA_ID] = st.slider("Isi batas desa", 0.0, 1.0, ss.opacity[DESA_ID], 0.05)
            ss.opacity["AREA"] = st.slider("Isi layer area", 0.0, 1.0, ss.opacity["AREA"], 0.05)

        st.caption("Legenda")
        rows = []
        if ss.color_mode == "Per wilayah" or (ss.visible[PULAU_ID] and ss.color_mode == "Per layer"):
            rows += [f'<div class="legend-row">{legend_symbol("Polygon", col)}{w}</div>' for w, col in WILAYAH_COLORS.items()]
        elif ss.color_mode == "Per pulau":
            small = {w: [p for p in ss.pulau if PULAU_KAWASAN[p][0] == w and p not in config.PULAU_COLORS] for w in WILAYAH_COLORS}
            rows += [f'<div class="legend-row">{legend_symbol("Polygon", pulau_color(p))}P. {p}</div>' for p in ss.pulau if p in config.PULAU_COLORS]
            rows += [f'<div class="legend-row">{legend_symbol("Polygon", config.PULAU_SMALL_COLORS[w])}Pulau kecil {w}</div>' for w, ps in small.items() if ps]
        if ss.visible[DESA_ID]:
            rows += [f'<div class="legend-row">{legend_symbol("Polygon", col)}Desa · Kec. {kec}</div>' for kec, col in KECAMATAN_COLORS.items()]
            rows.append(f'<div class="legend-row">{legend_symbol("Polygon", OTHER_COLOR)}Desa · Kec. Pulo Aceh</div>')
        for lid, c in CAT.items():
            if ss.visible[lid] and COUNTS[lid]:
                col = c["color"] if ss.color_mode == "Per layer" else "#52514e"
                rows.append(f'<div class="legend-row">{legend_symbol(c["geom"], col, c["width"], c.get("icon"))}{c["title"]}</div>')
        if ss.uploads:
            rows.append(f'<div class="legend-row">{legend_symbol("LineString", UPLOAD_COLOR)}Data unggahan (sementara)</div>')
        st.markdown("".join(rows), unsafe_allow_html=True)

    # ---- Tambah fitur baru
    with t_add:
        st.markdown("**Tambah fitur baru**")
        st.caption("1) Pilih layer · 2) Gambar di peta: 📍 titik, ✏️ garis (klik ganda untuk selesai), ⬟ area · 3) Isi atribut · 4) Simpan")
        user = st.text_input("Nama editor", key="editor_name", placeholder="mis. Dinas PUPR Sabang")
        theme = st.selectbox("Tema", list(THEMES), key="add_theme")
        target = st.selectbox("Layer tujuan", THEMES[theme], key="add_layer",
                              format_func=lambda k: f"{GEOM_ICON[CAT[k]['geom']]} {CAT[k]['title']} · {GEOM_LABEL[CAT[k]['geom']]} ({COUNTS[k]})")
        layer = CAT[target]
        st.caption(f"`{target}` · sumber skema: {layer['source']}")
        drawings = current_drawings()
        fits = [d for d in drawings if store.to_layer_geom(layer, d) is not None]
        if fits:
            msg = f"{len(fits)} geometri {GEOM_LABEL[layer['geom']]} siap disimpan"
            geoms = [store.to_layer_geom(layer, d) for d in fits]
            if layer["geom"] == "LineString":
                msg += f" · {sum(store.geodesic_length_m(g) for g in geoms):,.1f} m"
            elif layer["geom"] == "Polygon":
                msg += f" · {sum(store.geodesic_area_ha(g) for g in geoms):,.3f} ha"
            st.success(msg)
            loc = geoms[-1].representative_point()
            d = store.desa_for_point(desa_fc, loc.x, loc.y)
            if d:
                st.caption(f"Lokasi: Desa {d['NAMOBJ']}, Kec. {d['WADMKC']}")
        else:
            st.warning(f"Gambar {GEOM_LABEL[layer['geom']]} di peta terlebih dahulu.")
        if len(drawings) > len(fits):
            st.caption(f"⚠️ {len(drawings) - len(fits)} geometri lain tidak sesuai tipe layer ini dan tidak akan disimpan.")

        with st.form("form_tambah", clear_on_submit=True):
            values = {}
            existing = feats(target)

            def field_input(fld):
                key = f"in_{target}_{fld['name']}"
                default = layer["defaults"].get(fld["name"])
                choices = fld.get("choices") or store.field_choices(existing, fld["name"])
                label = fld["alias"] if fld["alias"] == fld["name"] else f"{fld['alias']}"
                if choices:
                    opts = [""] + choices
                    idx = opts.index(str(default)) if default is not None and str(default) in opts else 0
                    return st.selectbox(label, opts, index=idx, key=key, help=fld.get("help"), accept_new_options=True)
                return st.text_input(label, value="" if default is None else str(default), key=key, help=fld.get("help"))

            main = [f for f in layer["fields"] if f["main"]]
            other = [f for f in layer["fields"] if not f["main"]]
            for fld in main[:8]:
                values[fld["name"]] = field_input(fld)
            if main[8:] or other:
                with st.expander(f"Atribut lainnya ({len(main[8:]) + len(other)})"):
                    for fld in main[8:] + other:
                        values[fld["name"]] = field_input(fld)
            submitted = st.form_submit_button("💾 Simpan ke layer", type="primary", width="stretch")
        if submitted:
            if not fits:
                st.error(f"Tidak ada geometri {GEOM_LABEL[layer['geom']]} untuk disimpan.")
            else:
                n = store.add_features(layer, fits, values, user=user)
                ss.visible[target] = True
                st.toast(f"{n} fitur ditambahkan ke {layer['title']}", icon="✅")
                reset_map(store.fc_bounds([{"geometry": d} for d in fits]))
                st.rerun()

    # ---- Filter
    with t_filter:
        st.markdown("**Filter atribut**")
        st.caption("Filter wilayah/pulau ada di bagian **Kawasan Sabang** di atas; filter di sini menambah syarat atribut.")
        options = [DESA_ID] + [lid for lid in CAT if COUNTS[lid]]
        f_layer = st.selectbox("Layer", options, format_func=layer_title, key="f_layer")
        f_field = st.selectbox("Field", layer_fields(f_layer), key="f_field",
                               format_func=lambda c: DESA_FIELDS.get(c) or FIELD_ALIASES.get(c, c))
        src = desa_fc["features"] if f_layer == DESA_ID else feats(f_layer)
        vals = sorted({str(f["properties"].get(f_field)) for f in src})[:500]
        c1, c2 = st.columns([1, 2])
        f_op = c1.selectbox("Operator", OPERATORS, key="f_op")
        f_val = c2.selectbox("Nilai", vals, key="f_val", accept_new_options=True)
        if st.button("Tambah filter", width="stretch") and f_val not in (None, ""):
            ss.filters.append({"layer": f_layer, "field": f_field, "op": f_op, "value": str(f_val)})
            if f_layer != DESA_ID:
                ss.visible[f_layer] = True
            st.rerun()
        for i, flt in enumerate(ss.filters):
            c1, c2 = st.columns([5, 1])
            c1.caption(f"**{layer_title(flt['layer'])}**: {flt['field']} {flt['op']} `{flt['value']}`")
            if c2.button("✕", key=f"rmf_{i}"):
                ss.filters.pop(i)
                st.rerun()
        if ss.filters and st.button("Hapus semua filter"):
            ss.filters = []
            st.rerun()

    # ---- Select (pilih desa → sorot + ringkasan isi wilayah)
    with t_select:
        st.markdown("**Pilih wilayah**")
        names = [f["properties"]["NAMOBJ"] for f in desa_fc["features"]]
        sel = st.multiselect("Desa/Kelurahan", names, default=ss.selected_desa, key="sel_desa")
        if sel != ss.selected_desa:
            ss.selected_desa = sel
            zoom_to(store.fc_bounds([f for f in desa_fc["features"] if f["properties"]["NAMOBJ"] in sel]))
            st.rerun()
        clicked = (ss.get(f"map_{ss.map_ver}") or {}).get("last_clicked")
        if clicked:
            d = store.desa_for_point(desa_fc, clicked["lng"], clicked["lat"])
            st.caption(f"Klik terakhir: {clicked['lat']:.5f}, {clicked['lng']:.5f}" + (f" — Desa **{d['NAMOBJ']}**" if d else " — di luar batas desa"))
            if d and d["NAMOBJ"] not in ss.selected_desa and st.button(f"Tambahkan {d['NAMOBJ']} ke pilihan"):
                ss.selected_desa = ss.selected_desa + [d["NAMOBJ"]]
                st.rerun()
        if ss.selected_desa:
            sel_feats = [f for f in desa_fc["features"] if f["properties"]["NAMOBJ"] in ss.selected_desa]
            st.metric("Luas terpilih", f"{sum(f['properties']['LUASWH'] for f in sel_feats):,.1f} ha")
            rows = []
            for lid, c in CAT.items():
                if not COUNTS[lid] or c["base"] in ("KONTUR", "TOPONIMI"):
                    continue
                ov = overlay(lid, only_sabang=False)
                v = ov[ov["desa"].isin(ss.selected_desa)]["nilai"].sum()
                if v > 0:
                    rows.append({"Tema": c["theme"], "Layer": c["title"], "Jumlah": fmt_measure(c, v)})
            if rows:
                st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", height=300)
            if st.button("Bersihkan pilihan"):
                ss.selected_desa = []
                st.rerun()

    # ---- Add Data (unggah)
    with t_upload:
        st.markdown("**Tambah data dari berkas**")
        up = st.file_uploader("GeoJSON (EPSG:4326)", type=["geojson", "json"])
        if up is not None and st.button("Tampilkan di peta"):
            try:
                fc = json.loads(up.getvalue().decode("utf-8"))
                if fc.get("type") == "Feature":
                    fc = {"type": "FeatureCollection", "features": [fc]}
                if fc.get("type") != "FeatureCollection":
                    raise ValueError("bukan FeatureCollection")
                ss.uploads.append({"name": up.name, "fc": fc})
                zoom_to(store.fc_bounds([f for f in fc["features"] if f.get("geometry")]))
                st.rerun()
            except (ValueError, KeyError, UnicodeDecodeError) as e:
                st.error(f"Berkas tidak valid: {e}")
        for i, u in enumerate(ss.uploads):
            with st.expander(f"{u['name']} ({len(u['fc']['features'])} fitur)"):
                imp = st.selectbox("Impor permanen ke layer", list(CAT), key=f"imp_{i}",
                                   format_func=lambda k: f"{GEOM_ICON[CAT[k]['geom']]} {CAT[k]['theme']} › {CAT[k]['title']}")
                st.caption("Atribut dengan nama field sama (tanpa membedakan huruf besar/kecil) ikut terbawa. Geometri yang tipenya tidak cocok dilewati.")
                c1, c2 = st.columns(2)
                if c1.button("Impor", key=f"impb_{i}"):
                    n = 0
                    for f in u["fc"]["features"]:
                        if f.get("geometry"):
                            n += store.add_features(CAT[imp], [f["geometry"]], f.get("properties") or {}, user=ss.get("editor_name") or "impor")
                    st.toast(f"{n} fitur diimpor ke {CAT[imp]['title']}", icon="✅")
                    ss.visible[imp] = True
                    ss.uploads.pop(i)
                    st.rerun()
                if c2.button("Hapus", key=f"rmu_{i}"):
                    ss.uploads.pop(i)
                    st.rerun()


# ================================================================== MAP
class HomeButton(MacroElement):
    """Widget HomeButton: kembali ke extent awal Kawasan Sabang."""

    _template = Template("""
        {% macro script(this, kwargs) %}
        (function () {
            var map = {{ this._parent.get_name() }};
            var Home = L.Control.extend({
                options: {position: 'topleft'},
                onAdd: function () {
                    var div = L.DomUtil.create('div', 'leaflet-bar leaflet-control');
                    var a = L.DomUtil.create('a', '', div);
                    a.href = '#'; a.title = 'Extent awal'; a.innerHTML = '&#8962;';
                    a.style.fontSize = '18px';
                    L.DomEvent.on(a, 'click', function (e) {
                        L.DomEvent.stop(e); map.fitBounds({{ this.bounds }});
                    });
                    return div;
                }
            });
            map.addControl(new Home());
        })();
        {% endmacro %}
    """)

    def __init__(self, bounds):
        super().__init__()
        self._name = "HomeButton"
        self.bounds = json.dumps(bounds)


def desa_style(selected):
    def style(feat):
        p = feat["properties"]
        col = KECAMATAN_COLORS.get(p["WADMKC"], OTHER_COLOR) if p["WADMKK"] == "Kota Sabang" else OTHER_COLOR
        if p["NAMOBJ"] in selected:
            return {"color": SELECTION_COLOR, "weight": 3.5, "fillColor": SELECTION_COLOR, "fillOpacity": 0.35}
        return {"color": col, "weight": 1.5, "fillColor": col, "fillOpacity": ss.opacity[DESA_ID]}
    return style


def build_base_map():
    """Peta dasar: basemap + widget. Isinya harus tetap sama antar-rerun — perubahan JS di sini
    membuat st_folium memuat ulang peta dari awal (posisi & gambar hilang)."""
    v = ss.base_view
    m = folium.Map(location=v["center"], zoom_start=v["zoom"], tiles=None, control_scale=True, max_zoom=20)
    for i, (name, bm) in enumerate(BASEMAPS.items()):
        folium.TileLayer(bm["tiles"], attr=bm["attr"], name=name, max_zoom=20, max_native_zoom=16 if "Gray" in name else 19,
                         show=i == 0).add_to(m)
    HomeButton(HOME_BOUNDS).add_to(m)
    plugins.LocateControl(position="topleft", strings={"title": "Lokasi saya"}).add_to(m)
    plugins.Fullscreen(position="topleft").add_to(m)
    plugins.Geocoder(position="topright", collapsed=True, add_marker=True).add_to(m)
    plugins.MeasureControl(position="topright", primary_length_unit="kilometers", secondary_length_unit="meters",
                           primary_area_unit="sqmeters", secondary_area_unit="hectares").add_to(m)
    plugins.MousePosition(position="bottomleft", separator=" | ", prefix="Lat | Lon:", num_digits=6).add_to(m)
    plugins.MiniMap(position="bottomright", toggle_display=True, zoom_level_offset=-5).add_to(m)
    plugins.Draw(
        position="topleft",
        draw_options={"polyline": {"shapeOptions": {"color": THEME_ACCENT, "weight": 4}},
                      "polygon": {"shapeOptions": {"color": THEME_ACCENT}},
                      "marker": True, "rectangle": False, "circle": False, "circlemarker": False},
        edit_options={"edit": True, "remove": True},
    ).add_to(m)
    return m


def layer_group(lid, features):
    c = CAT[lid]
    hl = ss.highlight
    popup_fields = store.informative_fields(c, features) + (["shape_leng"] if c["geom"] == "LineString" else []) \
        + (["luas_ha"] if c["geom"] == "Polygon" else []) + ["created_by"]
    label = store.label_field(c)

    def style(feat, c=c, lid=lid):
        on = hl and hl[0] == lid and feat["properties"].get("objectid") == hl[1]
        col = SELECTION_COLOR if on else feature_color(feat["properties"], c["color"])
        if c["geom"] == "LineString":
            return {"color": col, "weight": c["width"] + (3 if on else 0)}
        return {"color": col, "weight": 3 if on else 1, "fillColor": col, "fillOpacity": ss.opacity["AREA"]}

    fg = folium.FeatureGroup(name=c["title"])
    is_point = c["geom"] == "Point"
    size = 16 if c["base"] in SMALL_ICON_LAYERS else 24
    # cincin sorotan untuk fitur yang dipilih dari tabel atribut
    if is_point and hl and hl[0] == lid:
        for f in features:
            if f["properties"].get("objectid") == hl[1]:
                lon, lat = shape(f["geometry"]).representative_point().coords[0]
                folium.CircleMarker([lat, lon], radius=18, color=SELECTION_COLOR, weight=4, fill=False).add_to(fg)
    # ikon titik tetap memakai glyph layer; warnanya per wilayah/pulau → satu GeoJson per warna
    by_color = {}
    for f in features:
        by_color.setdefault(feature_color(f["properties"], c["color"]) if is_point else None, []).append(f)
    for col, group in by_color.items():
        marker = folium.Marker(icon=folium.DivIcon(html=icon_html(c["icon"], col, size), class_name="sbg-icon",
                                                   icon_size=(size, size), icon_anchor=(size // 2, size // 2))) if is_point else None
        folium.GeoJson(
            {"type": "FeatureCollection", "features": group},
            style_function=style,
            highlight_function=None if is_point else (lambda f: {"weight": 5, "color": SELECTION_COLOR}),
            marker=marker,
            tooltip=folium.GeoJsonTooltip([label], aliases=[c["title"]]),
            popup=folium.GeoJsonPopup(popup_fields, aliases=[FIELD_ALIASES.get(f, f) for f in popup_fields], max_width=380),
        ).add_to(fg)
    return fg


def pulau_style(feat):
    col = feature_color(feat["properties"], WILAYAH_COLORS[feat["properties"]["WILAYAH"]])
    return {"color": col, "weight": 2, "dashArray": "5 4", "fillColor": col, "fillOpacity": 0.08}


def build_overlays():
    """Layer operasional sebagai FeatureGroup; st_folium memperbaruinya tanpa memuat ulang peta."""
    groups = []
    if ss.visible[PULAU_ID]:
        pfeats = in_kawasan(pulau_fc["features"])
        if pfeats:
            fg = folium.FeatureGroup(name="Pulau Kawasan Sabang")
            folium.GeoJson(
                {"type": "FeatureCollection", "features": pfeats},
                style_function=pulau_style,
                tooltip=folium.GeoJsonTooltip(["PULAU", "WILAYAH"], aliases=["Pulau", "Wilayah"]),
                popup=folium.GeoJsonPopup(["PULAU", "WILAYAH", "KABKOTA", "luas_ha", "CATATAN"],
                                          aliases=["Pulau", "Wilayah", "Kab/Kota", "Luas (ha)", "Catatan"], max_width=360),
            ).add_to(fg)
            groups.append(fg)
    if ss.visible[DESA_ID]:
        dfeats = apply_filters(DESA_ID, desa_fc["features"])
        if dfeats:
            fg = folium.FeatureGroup(name="Batas Desa/Kelurahan")
            folium.GeoJson(
                {"type": "FeatureCollection", "features": dfeats},
                style_function=desa_style(set(ss.selected_desa)),
                tooltip=folium.GeoJsonTooltip(["NAMOBJ", "WADMKC"], aliases=["Desa", "Kecamatan"]),
                popup=folium.GeoJsonPopup(list(DESA_FIELDS), aliases=list(DESA_FIELDS.values()), max_width=360),
            ).add_to(fg)
            groups.append(fg)
    # urutan gambar: area → garis → titik, agar titik selalu di atas
    for kind in ("Polygon", "LineString", "Point"):
        for lid, c in CAT.items():
            if c["geom"] == kind and ss.visible[lid] and COUNTS[lid]:
                fl = apply_filters(lid, display_feats(lid))
                if fl:
                    groups.append(layer_group(lid, fl))
    if ss.visible[DESA_ID] and ss.visible["LABEL"]:
        fg = folium.FeatureGroup(name="Label Desa")
        for f in in_kawasan(desa_fc["features"]):
            pt = shape(f["geometry"]).representative_point()
            folium.Marker(
                [pt.y, pt.x],
                icon=folium.DivIcon(
                    icon_size=(120, 16), icon_anchor=(60, 8),
                    html=f'<div style="font:600 11px sans-serif;color:#1a1a19;text-align:center;pointer-events:none;'
                         f'text-shadow:0 0 3px #fff,0 0 3px #fff,0 0 3px #fff">{f["properties"]["NAMOBJ"]}</div>'),
            ).add_to(fg)
        groups.append(fg)
    for u in ss.uploads:
        ufeats = [f for f in u["fc"]["features"] if f.get("geometry")]
        if ufeats:
            fg = folium.FeatureGroup(name=u["name"])
            folium.GeoJson(
                {"type": "FeatureCollection", "features": ufeats},
                style_function=lambda f: {"color": UPLOAD_COLOR, "weight": 3, "dashArray": "6 4", "fillOpacity": 0.15},
                marker=folium.CircleMarker(radius=6, color=UPLOAD_COLOR, fill=True),
            ).add_to(fg)
            groups.append(fg)
    return groups


tab_map, tab_analysis, tab_about = st.tabs(["🗺️ Peta Interaktif", "📊 Dashboard Analisis", "ℹ️ Analisis Sistem & Data"])

with tab_map:
    if ss.filters:
        st.caption("🔎 Filter aktif: " + " · ".join(f"{layer_title(f['layer'])} [{f['field']} {f['op']} {f['value']}]" for f in ss.filters))
    nav = ss.nav or {}
    st_folium(
        build_base_map(),
        key=f"map_{ss.map_ver}",
        height=620,
        use_container_width=True,
        feature_group_to_add=build_overlays(),
        layer_control=folium.LayerControl(position="topright", collapsed=True),
        center=nav.get("center"),
        zoom=nav.get("zoom"),
        returned_objects=["all_drawings", "last_clicked"],
    )

    # ---------------------------------------------- Attribute Table
    with st.expander("📋 Tabel Atribut", expanded=True):
        visible_layers = [lid for lid in CAT if ss.visible[lid] and COUNTS[lid]]
        options = [DESA_ID] + visible_layers + [lid for lid in CAT if COUNTS[lid] and lid not in visible_layers]
        tl = st.selectbox("Layer", options, format_func=lambda k: layer_label(k) if k == DESA_ID else f"{CAT[k]['theme']} › {layer_label(k)}",
                          key="tbl_layer", index=1 if visible_layers else 0)

        if tl == DESA_ID:
            dfeats = apply_filters(DESA_ID, desa_fc["features"])
            df = pd.DataFrame([{a: f["properties"][k] for k, a in DESA_FIELDS.items()} for f in dfeats])
            st.caption(f"{len(df)} dari {len(desa_fc['features'])} fitur · pilih baris untuk memperbesar ke desa")
            ev = st.dataframe(df, hide_index=True, width="stretch", on_select="rerun", selection_mode="single-row", key="tbl_desa", height=300)
            rows = ev.selection.rows if ev else []
            if rows:
                name = df.iloc[rows[0]]["Nama Desa"]
                if ss.selected_desa != [name]:
                    ss.selected_desa = [name]
                    zoom_to(store.fc_bounds([f for f in dfeats if f["properties"]["NAMOBJ"] == name]))
                    st.rerun()
            c1, c2 = st.columns(2)
            c1.download_button("⬇️ CSV", df.to_csv(index=False).encode(), "batas_desa_sabang.csv", "text/csv")
            c2.download_button("⬇️ GeoJSON", json.dumps({"type": "FeatureCollection", "features": dfeats}, ensure_ascii=False),
                               "batas_desa_sabang.geojson", "application/geo+json")
        else:
            c = CAT[tl]
            all_f = feats(tl)
            tfeats = apply_filters(tl, all_f)
            cols = store.table_columns(c)
            df = store.layer_frame(tfeats, cols)
            df.insert(0, "_hapus", False)
            col_cfg = {name: st.column_config.Column(FIELD_ALIASES.get(name) or next((f["alias"] for f in c["fields"] if f["name"] == name), name))
                       for name in cols}
            col_cfg["_hapus"] = st.column_config.CheckboxColumn("Hapus?")
            if "shape_leng" in cols:
                col_cfg["shape_leng"] = st.column_config.NumberColumn("Panjang (m)", format="%.1f")
            for fld in c["fields"]:
                if fld.get("choices"):
                    col_cfg[fld["name"]] = st.column_config.SelectboxColumn(fld["alias"], options=fld["choices"])
            n_user = sum(1 for f in all_f if f["properties"].get("created_by") != RBI_SOURCE)
            info = f"{len(tfeats)} dari {len(all_f)} fitur ({n_user} tambahan pengguna)"
            if "shape_leng" in cols:
                info += f" · total {df['shape_leng'].sum() / 1000:,.2f} km"
            if "luas_ha" in cols:
                info += f" · total {df['luas_ha'].sum():,.1f} ha"
            st.caption(info + " · sel dapat diedit langsung")
            edited = st.data_editor(df, hide_index=True, width="stretch", column_config=col_cfg, height=320,
                                    disabled=[x for x in cols if x in ("objectid", "PULAU", "WILAYAH", "shape_leng", "luas_ha", "created_by", "created_at", "updated_at")],
                                    key=f"ed_{tl}_{store.layer_mtime(tl)}")
            c1, c2, c3, c4 = st.columns([1.2, 1.4, 1, 1])
            if c1.button("💾 Simpan perubahan", key=f"save_{tl}", type="primary"):
                changed, deleted = store.update_attributes(c, edited.to_dict("records"))
                st.toast(f"{changed} fitur diperbarui, {deleted} dihapus", icon="✅")
                st.rerun()
            oid = c2.selectbox("Zoom ke OBJECTID", [None] + df["objectid"].tolist(), key=f"z_{tl}", label_visibility="collapsed",
                               format_func=lambda v: "Zoom ke fitur…" if v is None else f"OBJECTID {v}")
            if oid is not None and ss.highlight != (tl, oid):
                ss.highlight = (tl, oid)
                ss.visible[tl] = True
                zoom_to(store.fc_bounds([f for f in tfeats if f["properties"]["objectid"] == oid]))
                st.rerun()
            c3.download_button("⬇️ CSV", df.drop(columns="_hapus").to_csv(index=False).encode(), f"{tl}.csv", "text/csv", key=f"csv_{tl}")
            c4.download_button("⬇️ GeoJSON", json.dumps({"type": "FeatureCollection", "name": tl, "features": tfeats}, ensure_ascii=False),
                               f"{tl}.geojson", "application/geo+json", key=f"gj_{tl}")


# ================================================================ ANALISIS
def kpi(col, value, label):
    col.markdown(f'<div class="kpi"><div class="v">{value}</div><div class="l">{label}</div></div>', unsafe_allow_html=True)


def bar_layout(fig, height, legend=True):
    fig.update_layout(height=height, margin=dict(l=0, r=10, t=10, b=0), bargap=0.25, plot_bgcolor="rgba(0,0,0,0)",
                      xaxis=dict(gridcolor="#e6e6e3"), yaxis=dict(categoryorder="total ascending"),
                      legend=dict(orientation="h", y=-0.12, title=None) if legend else None, showlegend=legend)
    fig.update_traces(marker_line_color="#ffffff", marker_line_width=1)
    return fig


with tab_analysis:
    only_sabang = st.toggle("Analisis per desa: hanya Kota Sabang (kecualikan Desa Melingge, Kec. Pulo Aceh, Kab. Aceh Besar)", value=True)
    dfeats = [f for f in desa_fc["features"] if not only_sabang or f["properties"]["WADMKK"] == "Kota Sabang"]
    ddf = pd.DataFrame([f["properties"] for f in dfeats])
    ddf["Luas geodesik (ha)"] = [round(store.geodesic_area_ha(shape(f["geometry"])), 2) for f in dfeats]
    n_filled = sum(1 for lid in CAT if COUNTS[lid])
    n_user = sum(1 for lid in CAT for f in feats(lid) if f["properties"].get("created_by") != RBI_SOURCE)

    c = st.columns(5)
    kpi(c[0], f"{len(ddf)}", f"Desa/Kelurahan · {ddf['WADMKC'].nunique()} kecamatan")
    kpi(c[1], f"{ddf['LUASWH'].sum():,.0f} ha", "Luas wilayah (LUASWH)")
    kpi(c[2], f"{n_filled} / {len(CAT)}", "Layer berisi data")
    kpi(c[3], f"{sum(COUNTS.values()):,}", "Total fitur")
    kpi(c[4], f"{n_user}", "Fitur tambahan pengguna")
    st.write("")

    # ---- Kawasan Sabang per pulau (mengikuti filter Kawasan Sabang di sidebar)
    st.markdown("#### Kawasan Sabang per pulau")
    st.caption(f"Filter wilayah: **{ss.get('wilayah', 'Seluruh Kawasan Sabang')}** ({len(ss.pulau)} pulau). "
               "Data Aceh Besar hanya diambil pada pulau-pulau Pulo Aceh yang termasuk Kawasan Sabang (PP 83/2010).")
    prow = {f["properties"]["PULAU"]: {"Pulau": f["properties"]["PULAU"], "Wilayah": f["properties"]["WILAYAH"],
                                       "Luas (ha)": f["properties"]["luas_ha"]} for f in in_kawasan(pulau_fc["features"])}
    pfac = []
    for group, (lids, _) in FACILITY_GROUPS.items():
        for lid in lids:
            for f in in_kawasan(feats(lid)) if lid in CAT else []:
                pfac.append({"Pulau": f["properties"].get("PULAU"), "Kategori": group})
    for r in prow.values():
        r["Fasilitas umum"] = sum(1 for x in pfac if x["Pulau"] == r["Pulau"])
        r["Jalan (km)"] = round(sum(f["properties"].get("shape_leng") or 0 for f in feats("JALAN_LN_50K")
                                    if f["properties"].get("PULAU") == r["Pulau"]) / 1000, 2) if "JALAN_LN_50K" in CAT else None
        r["Permukiman (ha)"] = round(sum(f["properties"].get("luas_ha") or 0 for f in feats("PEMUKIMAN_AR_50K")
                                         if f["properties"].get("PULAU") == r["Pulau"]), 1) if "PEMUKIMAN_AR_50K" in CAT else None
        r["Catatan"] = PULAU_KAWASAN[r["Pulau"]][1]
    pdf = pd.DataFrame(list(prow.values()))
    if pdf.empty:
        st.caption("Tidak ada pulau dipilih.")
    else:
        a, b = st.columns([2, 3])
        with a:
            wsum = pdf.groupby("Wilayah", as_index=False)[["Luas (ha)", "Fasilitas umum", "Jalan (km)", "Permukiman (ha)"]].sum()
            fig = px.bar(wsum, x="Luas (ha)", y="Wilayah", orientation="h", color="Wilayah", color_discrete_map=WILAYAH_COLORS,
                         text="Luas (ha)", labels={"Wilayah": ""})
            fig.update_traces(texttemplate="%{text:,.0f} ha", textposition="outside", cliponaxis=False)
            st.plotly_chart(bar_layout(fig, 160, legend=False), width="stretch")
            st.dataframe(wsum.round(1), hide_index=True, width="stretch")
        with b:
            fdf = pd.DataFrame(pfac, columns=["Pulau", "Kategori"]).value_counts().rename("jumlah").reset_index()
            if fdf.empty:
                st.caption("Tidak ada fasilitas umum tercatat pada pulau terpilih.")
            else:
                fig = px.bar(fdf, x="jumlah", y="Pulau", color="Kategori", orientation="h",
                             color_discrete_map={k: v[1] for k, v in FACILITY_GROUPS.items()},
                             category_orders={"Kategori": list(FACILITY_GROUPS)}, labels={"jumlah": "Jumlah fasilitas", "Pulau": ""})
                st.plotly_chart(bar_layout(fig, 260), width="stretch")
        st.dataframe(pdf, hide_index=True, width="stretch",
                     column_config={"Luas (ha)": st.column_config.NumberColumn(format="%.1f")})

    st.divider()
    st.markdown("#### Analisis per desa")
    st.caption("Batas desa hanya tersedia untuk Kota Sabang (18 desa) + Desa Melingge (Pulo Aceh); "
               "pulau-pulau Pulo Aceh lainnya belum memiliki poligon batas desa.")

    # ---- wilayah
    kec_colors = {**KECAMATAN_COLORS, "Pulo Aceh": OTHER_COLOR}
    left, right = st.columns([3, 2])
    with left:
        st.markdown("##### Luas desa/kelurahan (ha)")
        fig = px.bar(ddf, x="LUASWH", y="NAMOBJ", color="WADMKC", orientation="h", color_discrete_map=kec_colors,
                     labels={"LUASWH": "Luas (ha)", "NAMOBJ": "", "WADMKC": "Kecamatan"}, hover_data={"KDEPUM": True, "LUASWH": ":,.1f"})
        st.plotly_chart(bar_layout(fig, 480), width="stretch")
    with right:
        st.markdown("##### Ringkasan per kecamatan")
        kec = ddf.groupby("WADMKC").agg(jumlah_desa=("NAMOBJ", "count"), luas_ha=("LUASWH", "sum")).reset_index()
        kec["porsi"] = (kec["luas_ha"] / kec["luas_ha"].sum() * 100).round(1)
        kec["luas_ha"] = kec["luas_ha"].round(1)
        st.dataframe(kec.rename(columns={"WADMKC": "Kecamatan", "jumlah_desa": "Jumlah desa", "luas_ha": "Luas (ha)", "porsi": "Porsi luas (%)"})
                     .sort_values("Luas (ha)", ascending=False), hide_index=True, width="stretch")
        st.markdown("##### Validasi luas")
        st.caption("LUASWH (atribut) dibandingkan luas geodesik dihitung ulang dari geometri (WGS84).")
        ddf["Selisih (%)"] = ((ddf["Luas geodesik (ha)"] - ddf["LUASWH"]) / ddf["LUASWH"] * 100).round(2)
        st.dataframe(ddf[["NAMOBJ", "LUASWH", "Luas geodesik (ha)", "Selisih (%)"]].rename(columns={"NAMOBJ": "Desa", "LUASWH": "LUASWH (ha)"}),
                     hide_index=True, width="stretch", height=230)

    # ---- fasilitas umum
    st.divider()
    st.markdown("#### Fasilitas umum per desa")
    fac_rows = []
    for group, (lids, _) in FACILITY_GROUPS.items():
        for lid in lids:
            if lid in CAT and COUNTS[lid]:
                ov = overlay(lid, only_sabang)
                for desa, n in ov.groupby("desa")["nilai"].sum().items():
                    fac_rows.append({"desa": desa, "Kategori": group, "jumlah": int(n)})
    fac = pd.DataFrame(fac_rows, columns=["desa", "Kategori", "jumlah"])
    if fac.empty:
        st.caption("Belum ada data fasilitas.")
    else:
        fac = fac.groupby(["desa", "Kategori"], as_index=False)["jumlah"].sum()
        a, b = st.columns([3, 2])
        with a:
            fig = px.bar(fac, x="jumlah", y="desa", color="Kategori", orientation="h",
                         color_discrete_map={k: v[1] for k, v in FACILITY_GROUPS.items()},
                         category_orders={"Kategori": list(FACILITY_GROUPS)}, labels={"jumlah": "Jumlah fasilitas", "desa": ""})
            st.plotly_chart(bar_layout(fig, 460), width="stretch")
        with b:
            piv = fac.pivot_table(index="desa", columns="Kategori", values="jumlah", aggfunc="sum", fill_value=0)
            piv = piv.reindex(columns=[k for k in FACILITY_GROUPS if k in piv.columns])
            piv["Total"] = piv.sum(axis=1)
            luas = ddf.set_index("NAMOBJ")["LUASWH"]
            piv["per 100 ha"] = (piv["Total"] / luas.reindex(piv.index) * 100).round(2)
            st.dataframe(piv.sort_values("Total", ascending=False), width="stretch", height=420)
            missing = sorted(set(ddf["NAMOBJ"]) - set(piv.index))
            if missing:
                st.caption("Desa tanpa fasilitas tercatat: " + ", ".join(missing))

    # ---- jaringan jalan & tutupan lahan
    st.divider()
    a, b = st.columns(2)
    with a:
        st.markdown("#### Panjang jalan per desa (km)")
        if "JALAN_LN_50K" in CAT and COUNTS["JALAN_LN_50K"]:
            jl = overlay("JALAN_LN_50K", only_sabang).copy()
            jl["Kelas"] = jl["kelas"].fillna("Tanpa keterangan")
            jl = jl.groupby(["desa", "Kelas"], as_index=False)["nilai"].sum()
            jl["km"] = (jl["nilai"] / 1000).round(2)
            fig = px.bar(jl, x="km", y="desa", color="Kelas", orientation="h", color_discrete_map=ROAD_COLORS,
                         category_orders={"Kelas": list(ROAD_COLORS)}, labels={"km": "Panjang (km)", "desa": ""})
            st.plotly_chart(bar_layout(fig, 460), width="stretch")
            tot = jl.groupby("desa")["km"].sum()
            dens = (tot / ddf.set_index("NAMOBJ")["LUASWH"].reindex(tot.index) * 100).round(2)
            st.caption(f"Total {tot.sum():,.1f} km · kerapatan tertinggi: {dens.idxmax()} ({dens.max():.2f} km/100 ha), "
                       f"terendah: {dens.idxmin()} ({dens.min():.2f} km/100 ha)")
    with b:
        st.markdown("#### Tutupan lahan (ha)")
        lc = [{"Kelas": CAT[lid]["title"], "luas": overlay(lid, only_sabang)["nilai"].sum(), "color": CAT[lid]["color"]}
              for lid in THEMES.get("Tutupan Lahan", []) + [x for x in THEMES.get("Bangunan & Permukiman", []) if CAT[x]["geom"] == "Polygon"]
              if COUNTS[lid]]
        lc = pd.DataFrame(lc)
        if not lc.empty:
            lc["luas"] = lc["luas"].round(1)
            lc["porsi"] = (lc["luas"] / ddf["LUASWH"].sum() * 100).round(1)
            fig = px.bar(lc, x="luas", y="Kelas", orientation="h", color="Kelas",
                         color_discrete_map=dict(zip(lc["Kelas"], lc["color"])), text="porsi",
                         labels={"luas": "Luas (ha)", "Kelas": ""})
            fig.update_traces(texttemplate="%{text}%", textposition="outside", cliponaxis=False)
            st.plotly_chart(bar_layout(fig, 360, legend=False), width="stretch")
            st.caption(f"Tutupan lahan RBI hanya mencakup {lc['luas'].sum():,.0f} ha ({lc['luas'].sum() / ddf['LUASWH'].sum() * 100:.0f}% wilayah) "
                       "— sisanya tidak terpetakan pada layer tutupan lahan RBI ini.")

    # ---- utilitas: inventaris & kesenjangan data
    st.divider()
    st.markdown("#### Inventaris data utilitas")
    util = []
    for theme, lids in THEMES.items():
        if not theme.startswith("Utilitas"):
            continue
        for lid in lids:
            cc = CAT[lid]
            all_f = feats(lid)
            total = 0.0
            if cc["geom"] == "LineString":
                total = sum(f["properties"].get("shape_leng") or 0 for f in all_f) / 1000
            util.append({"Tema": theme.replace("Utilitas – ", ""), "Layer": cc["title"], "Tipe": GEOM_LABEL[cc["geom"]],
                         "Fitur": len(all_f), "Panjang (km)": round(total, 2) if cc["geom"] == "LineString" else None,
                         "Status": "✅ ada data" if all_f else "⬜ belum ada data"})
    udf = pd.DataFrame(util)
    a, b = st.columns([3, 1])
    a.dataframe(udf, hide_index=True, width="stretch", height=360)
    b.metric("Layer utilitas berisi data", f"{(udf['Fitur'] > 0).sum()} / {len(udf)}")
    b.caption("Layer utilitas RBI Sabang hampir seluruhnya kosong (hanya Kantor Air Minum, Stasiun TV, Stasiun Radio). "
              "Layer-layer ini adalah sasaran utama pengumpulan data lewat panel **Tambah**.")

    # ---- kelengkapan atribut
    st.divider()
    st.markdown("#### Kelengkapan atribut")
    q_layer = st.selectbox("Layer", [lid for lid in CAT if COUNTS[lid]], format_func=lambda k: f"{CAT[k]['theme']} › {CAT[k]['title']}",
                           key="q_layer", index=[lid for lid in CAT if COUNTS[lid]].index("JALAN_LN_50K") if COUNTS.get("JALAN_LN_50K") else 0)
    qf = feats(q_layer)
    comp = []
    for fld in CAT[q_layer]["fields"]:
        filled = sum(1 for f in qf if f["properties"].get(fld["name"]) not in (None, "", 0, 0.0))
        comp.append({"Field": f"{fld['name']} — {fld['alias']}", "Terisi (%)": round(filled / len(qf) * 100, 1)})
    cdf = pd.DataFrame(comp)
    fig = px.bar(cdf, x="Terisi (%)", y="Field", orientation="h", range_x=[0, 100], color_discrete_sequence=["#2a78d6"])
    fig.update_layout(yaxis=dict(categoryorder="total ascending"))
    st.plotly_chart(bar_layout(fig, max(220, 22 * len(cdf)), legend=False), width="stretch")
    st.caption("Nilai kosong, '0', dan spasi dihitung sebagai tidak terisi (KUGI memakai 0 untuk 'tidak diketahui').")

    with st.expander("Inventaris semua layer"):
        inv = pd.DataFrame([{"Tema": cc["theme"], "Layer": cc["title"], "ID": lid, "Tipe": GEOM_LABEL[cc["geom"]],
                             "Fitur RBI": cc["rbi_count"], "Fitur pengguna": COUNTS[lid] - cc["rbi_count"], "Sumber skema": cc["source"]}
                            for lid, cc in CAT.items()])
        st.dataframe(inv, hide_index=True, width="stretch", height=400)

    with st.expander("Riwayat penambahan data pengguna"):
        hist = [{"Layer": CAT[lid]["title"], **{k: f["properties"].get(k) for k in ("objectid", "created_by", "created_at", "updated_at")},
                 "Nama": f["properties"].get(store.label_field(CAT[lid]))}
                for lid in CAT for f in feats(lid) if f["properties"].get("created_by") != RBI_SOURCE]
        if hist:
            st.dataframe(pd.DataFrame(hist).sort_values("created_at", ascending=False), hide_index=True, width="stretch")
        else:
            st.caption("Belum ada.")

with tab_about:
    st.markdown(Path(__file__).with_name("ANALISIS.md").read_text(encoding="utf-8"))
