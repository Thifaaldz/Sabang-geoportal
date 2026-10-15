"""Katalog layer, penyimpanan (GeoJSON per layer) dan perhitungan geometri."""

import json
import os
import re
import tempfile
from datetime import datetime

import pandas as pd
from pyproj import Geod
from shapely.geometry import MultiPolygon, Point, mapping, shape
from shapely.prepared import prep
from shapely.validation import make_valid

from config import (
    AUTO_FIELDS, CATALOG_PATH, CUSTOM_LAYERS, DESA_PATH, FIELD_ALIASES, GEOM_LABEL, LAYER_COLORS, LAYER_DIR,
    LAYER_ICONS, RBI_SOURCE, SYSTEM_FIELDS, THEME_COLORS, THEME_ICONS, THEMES, TITLES,
)

GEOD = Geod(ellps="WGS84")
THEME_OF = {base: theme for theme, bases in THEMES.items() for base in bases}
THEME_ORDER = list(THEMES) + ["Lainnya"]


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def geodesic_length_m(geom):
    return abs(GEOD.geometry_length(geom))


def geodesic_area_ha(geom):
    return abs(GEOD.geometry_area_perimeter(geom)[0]) / 10_000


def base_name(layer_id):
    return re.sub(r"_(PT|LN|AR)_50K$", "", layer_id)


# ------------------------------------------------------------------- katalog
def get_catalog():
    """Definisi semua layer: {id: {title, theme, geom, fields, defaults, color, width, source}} terurut per tema."""
    rbi = {}
    if CATALOG_PATH.exists():
        with open(CATALOG_PATH, encoding="utf-8") as f:
            rbi = json.load(f)
    bases = {}
    for lid in rbi:
        bases.setdefault(base_name(lid), []).append(lid)

    cat = {}
    for lid, info in rbi.items():
        base = base_name(lid)
        title = TITLES.get(base, base.title())
        if len(bases[base]) > 1:
            title += f" ({GEOM_LABEL[info['geom']]})"
        theme = THEME_OF.get(base, "Lainnya")
        fields = [{"name": f["name"], "alias": FIELD_ALIASES.get(f["name"], f["name"]), "type": f["type"],
                   "choices": None, "main": f["name"] not in AUTO_FIELDS, "help": f["name"]}
                  for f in info["fields"]]
        cat[lid] = {"id": lid, "base": base, "title": title, "theme": theme, "geom": info["geom"], "fields": fields,
                    "defaults": info["defaults"], "color": LAYER_COLORS.get(base, THEME_COLORS.get(theme, "#52514e")),
                    "width": 2 if base == "JALAN" else (0.8 if base == "KONTUR" else 1.5),
                    "icon": LAYER_ICONS.get(base) or THEME_ICONS.get(theme, "circle-dot"),
                    "source": RBI_SOURCE, "rbi_count": info["rbi_count"]}

    for lid, cfg in CUSTOM_LAYERS.items():
        base = base_name(lid)
        cat[lid] = {**cfg, "id": lid, "base": base, "color": LAYER_COLORS.get(base, cfg["color"]), "rbi_count": 0}

    return dict(sorted(cat.items(), key=lambda kv: (THEME_ORDER.index(kv[1]["theme"]), kv[1]["title"])))


def field_names(layer):
    return [f["name"] for f in layer["fields"]]


def label_field(layer):
    names = field_names(layer)
    for c in ("NAMOBJ", "namobj", "NAMRJL", "REMARK", "remark"):
        if c in names:
            return c
    return "objectid"


# ---------------------------------------------------------------- batas desa
def load_desa():
    with open(DESA_PATH, encoding="utf-8") as f:
        fc = json.load(f)
    for i, feat in enumerate(fc["features"], start=1):
        feat["id"] = i
        feat["properties"]["LUASWH"] = round(feat["properties"]["LUASWH"], 2)
    return fc


# ------------------------------------------------------------------- layer
def layer_path(layer_id):
    return LAYER_DIR / f"{layer_id}.geojson"


def layer_mtime(layer_id):
    p = layer_path(layer_id)
    return p.stat().st_mtime if p.exists() else 0.0


def load_layer(layer_id):
    path = layer_path(layer_id)
    if not path.exists():
        return {"type": "FeatureCollection", "name": layer_id, "features": []}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_layer(layer_id, fc):
    LAYER_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=LAYER_DIR, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, layer_path(layer_id))


def coerce(value, ftype):
    if value is None or (isinstance(value, float) and pd.isna(value)) or (isinstance(value, str) and not value.strip()):
        return None
    try:
        if ftype == "int":
            return int(float(str(value).replace(",", ".")))
        if ftype == "float":
            return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None
    return str(value).strip()


def normalize_properties(layer, props):
    """Properti lengkap sesuai skema layer (semua field ada, tipe sesuai, default terisi)."""
    lower = {k.lower(): v for k, v in (props or {}).items()}
    out = {}
    for fld in layer["fields"]:
        val = lower.get(fld["name"].lower())
        if coerce(val, "str") is None and fld["name"] in layer["defaults"]:
            val = layer["defaults"][fld["name"]]
        out[fld["name"]] = coerce(val, fld["type"])
    return out


def to_layer_geom(layer, geom_json):
    """Sesuaikan geometri masukan dengan tipe layer; None bila tidak cocok."""
    geom = shape(geom_json)
    if not geom.is_valid:
        geom = make_valid(geom)
    kind = layer["geom"]
    gt = geom.geom_type
    if kind == "Point":
        return geom if gt in ("Point", "MultiPoint") else None
    if kind == "LineString":
        if gt in ("Polygon", "MultiPolygon"):
            geom = geom.boundary
        return geom if geom.geom_type in ("LineString", "MultiLineString") else None
    if gt == "GeometryCollection":
        polys = [g for g in geom.geoms if g.geom_type == "Polygon"]
        geom = MultiPolygon(polys) if polys else geom
    return geom if geom.geom_type in ("Polygon", "MultiPolygon") else None


def measure(layer, geom):
    if layer["geom"] == "LineString":
        return {"shape_leng": round(geodesic_length_m(geom), 2)}
    if layer["geom"] == "Polygon":
        return {"luas_ha": round(geodesic_area_ha(geom), 4)}
    return {}


def add_features(layer, geometries, props, user="anonim"):
    """Tambah geometri dengan atribut yang sama. Mengembalikan jumlah fitur tersimpan."""
    fc = load_layer(layer["id"])
    next_id = max((f["properties"].get("objectid") or 0 for f in fc["features"]), default=0) + 1
    added = 0
    for geom_json in geometries:
        geom = to_layer_geom(layer, geom_json)
        if geom is None or geom.is_empty:
            continue
        p = normalize_properties(layer, props)
        p.update(objectid=next_id, **measure(layer, geom), created_by=user or "anonim", created_at=now_iso(), updated_at=now_iso())
        fc["features"].append({"type": "Feature", "id": next_id, "geometry": mapping(geom), "properties": p})
        next_id += 1
        added += 1
    if added:
        save_layer(layer["id"], fc)
    return added


def update_attributes(layer, edited_rows):
    """edited_rows: list dict berisi objectid + field. Fitur dengan '_hapus' True dihapus."""
    fc = load_layer(layer["id"])
    by_id = {r["objectid"]: r for r in edited_rows}
    kept, changed, deleted = [], 0, 0
    for feat in fc["features"]:
        row = by_id.get(feat["properties"]["objectid"])
        if row is None:
            kept.append(feat)
            continue
        if row.get("_hapus"):
            deleted += 1
            continue
        dirty = False
        for fld in layer["fields"]:
            if fld["name"] in row:
                val = coerce(row[fld["name"]], fld["type"])
                if val != feat["properties"].get(fld["name"]):
                    feat["properties"][fld["name"]] = val
                    dirty = True
        if dirty:
            feat["properties"]["updated_at"] = now_iso()
            changed += 1
        kept.append(feat)
    fc["features"] = kept
    save_layer(layer["id"], fc)
    return changed, deleted


def table_columns(layer):
    sys_cols = [c for c in SYSTEM_FIELDS if c != "objectid"]
    if layer["geom"] != "LineString":
        sys_cols.remove("shape_leng")
    if layer["geom"] != "Polygon":
        sys_cols.remove("luas_ha")
    return ["objectid"] + field_names(layer) + sys_cols


def layer_frame(features, columns):
    df = pd.DataFrame([f["properties"] for f in features])
    for c in columns:
        if c not in df.columns:
            df[c] = None
    return df[columns]


def field_choices(features, name, limit=40):
    """Nilai unik yang sudah ada (untuk dropdown) bila jumlahnya wajar."""
    vals = {str(f["properties"].get(name)) for f in features if f["properties"].get(name) not in (None, "")}
    return sorted(vals) if 0 < len(vals) <= limit else None


def informative_fields(layer, features, limit=10):
    """Field yang benar-benar terisi (bukan kosong/0) untuk popup."""
    out = []
    for fld in layer["fields"]:
        if fld["name"] in AUTO_FIELDS:
            continue
        if any(f["properties"].get(fld["name"]) not in (None, "", 0, 0.0) for f in features):
            out.append(fld["name"])
    lf = label_field(layer)
    if lf in out:
        out.remove(lf)
    return [lf] + out[: limit - 1]


def fc_bounds(features):
    """Bounds [[south, west], [north, east]]."""
    xs, ys = [], []
    for f in features:
        minx, miny, maxx, maxy = shape(f["geometry"]).bounds
        xs += [minx, maxx]
        ys += [miny, maxy]
    if not xs:
        return None
    return [[min(ys), min(xs)], [max(ys), max(xs)]]


# ------------------------------------------------------------------ analisis
def _desa_geoms(desa_fc):
    return [(f["properties"]["NAMOBJ"], f["properties"]["WADMKC"], shape(f["geometry"])) for f in desa_fc["features"]]


def overlay_by_desa(desa_fc, layer, features):
    """Ukuran tiap layer per desa: jumlah (titik), panjang m (garis) atau luas ha (area)."""
    rows = []
    desa = [(n, k, g, prep(g)) for n, k, g in _desa_geoms(desa_fc)]
    for feat in features:
        geom = shape(feat["geometry"])
        for nama, kec, poly, pp in desa:
            if not pp.intersects(geom):
                continue
            if layer["geom"] == "Point":
                pts = list(geom.geoms) if geom.geom_type == "MultiPoint" else [geom]
                val = sum(1 for p in pts if pp.contains(p))
            elif layer["geom"] == "LineString":
                val = geodesic_length_m(geom.intersection(poly))
            else:
                val = geodesic_area_ha(make_valid(geom).intersection(poly))
            if val > 0:
                rows.append({"layer": layer["id"], "desa": nama, "kecamatan": kec, "nilai": val,
                             "kelas": feat["properties"].get("REMARK") or feat["properties"].get("remark")})
    return pd.DataFrame(rows, columns=["layer", "desa", "kecamatan", "nilai", "kelas"])


def desa_for_point(desa_fc, lon, lat):
    pt = Point(lon, lat)
    for f in desa_fc["features"]:
        if shape(f["geometry"]).contains(pt):
            return f["properties"]
    return None
