"""Konversi shapefile RBI 1:50.000 (BIG) Kota Sabang ke GeoJSON per layer + katalog.

Jalankan ulang kapan saja:  .venv/bin/python convert_rbi.py
Fitur yang ditambahkan pengguna (created_by bukan sumber RBI) dipertahankan.
"""

import collections
import json
import sys
from pathlib import Path

import shapefile
from shapely.geometry import mapping, shape

from config import CATALOG_PATH, LAYER_DIR, RBI_DIR, RBI_SOURCE
from store import geodesic_area_ha, geodesic_length_m, load_layer, save_layer

GEOM_TYPES = {
    "POINT": "Point", "POINTZ": "Point", "POINTM": "Point", "MULTIPOINT": "Point", "MULTIPOINTZ": "Point",
    "POLYLINE": "LineString", "POLYLINEZ": "LineString", "POLYLINEM": "LineString",
    "POLYGON": "Polygon", "POLYGONZ": "Polygon", "POLYGONM": "Polygon",
}
DROP_FIELDS = {"SHAPE_LENG", "SHAPE_AREA", "SHAPE_LE_1", "SHAPE_LEN"}
CONST_FIELDS = ("FCODE", "LCODE", "METADATA", "SRS_ID")


def field_type(f):
    if str(getattr(f.field_type, "name", f.field_type)) in ("N", "F"):
        return "float" if f.decimal else "int"
    return "str"


def clean(value, ftype):
    if isinstance(value, bytes):
        value = value.decode("latin1", "ignore")
    if isinstance(value, str):
        value = value.strip()
        return value or None
    if value is None:
        return None
    if ftype == "int":
        return int(value)
    if ftype == "float":
        return round(float(value), 6)
    return str(value)


def to_2d(geom_json):
    def strip(c):
        if isinstance(c, (list, tuple)) and c and isinstance(c[0], (int, float)):
            return [round(c[0], 7), round(c[1], 7)]
        return [strip(x) for x in c]
    return {"type": geom_json["type"], "coordinates": strip(geom_json["coordinates"])}


def convert(path):
    layer_id = path.stem
    r = shapefile.Reader(str(path), encoding="latin1")
    gtype = GEOM_TYPES.get(r.shapeTypeName)
    if gtype is None:
        return None
    fields = [{"name": f.name, "type": field_type(f), "size": f.size} for f in r.fields[1:] if f.name.upper() not in DROP_FIELDS]
    features = []
    for i, sr in enumerate(r.iterShapeRecords(), start=1):
        if sr.shape.shapeTypeName == "NULL":
            continue
        geom = shape(to_2d(sr.shape.__geo_interface__))
        if geom.is_empty:
            continue
        rec = sr.record.as_dict()
        props = {f["name"]: clean(rec.get(f["name"]), f["type"]) for f in fields}
        props["objectid"] = i
        if gtype == "LineString":
            props["shape_leng"] = round(geodesic_length_m(geom), 2)
        elif gtype == "Polygon":
            props["luas_ha"] = round(geodesic_area_ha(geom), 4)
        props.update(created_by=RBI_SOURCE, created_at=None, updated_at=None)
        features.append({"type": "Feature", "id": i, "geometry": mapping(geom), "properties": props})

    # nilai konstan (FCODE, METADATA, ...) dipakai sebagai default saat pengguna menambah fitur
    defaults = {}
    for c in CONST_FIELDS:
        if any(f["name"] == c for f in fields):
            vals = collections.Counter(f["properties"][c] for f in features if f["properties"].get(c))
            if vals:
                defaults[c] = vals.most_common(1)[0][0]
    if "METADATA" not in defaults and any(f["name"] == "METADATA" for f in fields):
        defaults["METADATA"] = layer_id
    if "SRS_ID" not in defaults and any(f["name"] == "SRS_ID" for f in fields):
        defaults["SRS_ID"] = "WGS 84"

    # simpan: fitur RBI baru + fitur buatan pengguna yang sudah ada
    old = load_layer(layer_id)
    user_feats = [f for f in old["features"] if f["properties"].get("created_by") != RBI_SOURCE]
    next_id = len(features) + 1
    for f in user_feats:
        f["properties"]["objectid"] = f["id"] = next_id
        next_id += 1
    fc = {"type": "FeatureCollection", "name": layer_id, "features": features + user_feats}
    save_layer(layer_id, fc)
    return {"id": layer_id, "geom": gtype, "fields": fields, "defaults": defaults,
            "rbi_count": len(features), "user_count": len(user_feats)}


def main():
    LAYER_DIR.mkdir(parents=True, exist_ok=True)
    catalog = {}
    for path in sorted(Path(RBI_DIR).glob("*_50K.shp")):
        info = convert(path)
        if info:
            catalog[info["id"]] = info
            print(f"{info['id']:32s} {info['geom']:10s} {info['rbi_count']:5d} RBI  {info['user_count']:3d} pengguna")
    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=1)
    print(f"\n{len(catalog)} layer → {LAYER_DIR}", file=sys.stderr)


if __name__ == "__main__":
    main()
