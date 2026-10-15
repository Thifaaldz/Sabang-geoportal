"""Konversi shapefile RBI 1:50.000 (BIG) Kawasan Sabang ke GeoJSON per layer + katalog.

Sumber: RBI Kota Sabang (seluruhnya) + RBI Kab. Aceh Besar yang dipotong hanya pada pulau-pulau Pulo Aceh
yang termasuk Kawasan Sabang (PP 83/2010). Setiap fitur diberi atribut PULAU dan WILAYAH; poligon pulau
disimpan di data/pulau.geojson.

Jalankan ulang kapan saja:  .venv/bin/python convert_rbi.py
Fitur yang ditambahkan pengguna (created_by bukan sumber RBI) dipertahankan.
"""

import collections
import json
import sys
from pathlib import Path

import shapefile
from shapely.geometry import MultiPolygon, Point, mapping, shape
from shapely.ops import unary_union
from shapely.prepared import prep

import store
from config import (
    CATALOG_PATH, LAYER_DIR, PULAU_KAWASAN, PULAU_PATH, RBI_DIR, RBI_DIR_ACEH_BESAR, RBI_SOURCE, TOPONIM_PULAU,
    WILAYAH_PULO_ACEH, WILAYAH_SABANG,
)
from store import geodesic_area_ha, geodesic_length_m, load_layer, save_layer

GEOM_TYPES = {
    "POINT": "Point", "POINTZ": "Point", "POINTM": "Point", "MULTIPOINT": "Point", "MULTIPOINTZ": "Point",
    "POLYLINE": "LineString", "POLYLINEZ": "LineString", "POLYLINEM": "LineString",
    "POLYGON": "Polygon", "POLYGONZ": "Polygon", "POLYGONM": "Polygon",
}
DROP_FIELDS = {"SHAPE_LENG", "SHAPE_AREA", "SHAPE_LE_1", "SHAPE_LEN"}
CONST_FIELDS = ("FCODE", "LCODE", "METADATA", "SRS_ID")
KAWASAN_BUFFER = 0.004  # ±450 m di sekitar pulau Pulo Aceh: dermaga, karang, rambu suar, dsb. ikut terbawa
# Pulau di Kec. Peukan Bada (versi RBI) yang termasuk Kawasan Sabang: gugus Bunta dan Tuan Diapit (barat 95,178° BT)
PEUKANBADA_MAX_LON = 95.178


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


def polygon_parts(path, keep=lambda rec, part: True):
    r = shapefile.Reader(str(path), encoding="latin1")
    parts = []
    for sr in r.iterShapeRecords():
        g = shape(to_2d(sr.shape.__geo_interface__))
        parts += [p for p in getattr(g, "geoms", [g]) if keep(sr.record, p)]
    u = unary_union(parts)
    return list(getattr(u, "geoms", [u]))


def build_pulau():
    """Poligon pulau Kawasan Sabang, satu fitur per pulau, dinamai dari toponimi RBI."""
    kec = "ADMINISTRASIKECAMATAN_AR_50K.shp"
    parts = [(p, WILAYAH_SABANG) for p in polygon_parts(RBI_DIR / kec)]
    parts += [(p, WILAYAH_PULO_ACEH) for p in polygon_parts(
        RBI_DIR_ACEH_BESAR / kec,
        lambda rec, p: rec["NAMOBJ"] == "PULO ACEH" or (rec["NAMOBJ"] == "PEUKANBADA" and p.bounds[2] < PEUKANBADA_MAX_LON))]

    votes = collections.defaultdict(collections.Counter)
    for d in (RBI_DIR, RBI_DIR_ACEH_BESAR):
        r = shapefile.Reader(str(d / "TOPONIMI_PT_50K.shp"), encoding="latin1")
        for sr in r.iterShapeRecords():
            name = TOPONIM_PULAU.get(clean(sr.record["NAMOBJ"], "str"))
            if not name:
                continue
            pt = Point(sr.shape.points[0][:2])
            i, dist = min(((i, p.distance(pt)) for i, (p, _) in enumerate(parts)), key=lambda x: x[1])
            if dist < 0.002:
                votes[i][name] += 1

    groups = collections.defaultdict(list)
    for i, (p, wil) in enumerate(parts):
        name = votes[i].most_common(1)[0][0] if votes[i] else "Pulau kecil lain (Pulo Aceh)"
        assert PULAU_KAWASAN[name][0] == wil, (name, wil)
        groups[name].append(p)

    feats = []
    for name in PULAU_KAWASAN:
        if name not in groups:
            print(f"⚠️  pulau {name} tidak ditemukan pada data RBI", file=sys.stderr)
            continue
        geom = MultiPolygon(groups[name]) if len(groups[name]) > 1 else groups[name][0]
        wil, note = PULAU_KAWASAN[name]
        feats.append({"type": "Feature", "id": len(feats) + 1, "geometry": mapping(geom), "properties": {
            "PULAU": name, "WILAYAH": wil, "KABKOTA": "Kota Sabang" if wil == WILAYAH_SABANG else "Kab. Aceh Besar",
            "CATATAN": note, "BAGIAN": len(groups[name]), "luas_ha": round(geodesic_area_ha(geom), 2)}})
    PULAU_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PULAU_PATH, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "name": "PULAU_KAWASAN_SABANG", "features": feats}, f, ensure_ascii=False)
    for f in feats:
        p = f["properties"]
        print(f"  {p['PULAU']:30s} {p['WILAYAH']:24s} {p['luas_ha']:10,.1f} ha  ({p['BAGIAN']} poligon)")
    aceh = unary_union([p for p, wil in parts if wil == WILAYAH_PULO_ACEH]).buffer(KAWASAN_BUFFER)
    return aceh


def clip(geom, mask, gtype):
    """Bagian geometri di dalam mask dengan tipe yang sama; None bila tidak ada."""
    if gtype == "Point":
        return geom if mask.contains(geom) else None
    if not mask.intersects(geom):
        return None
    if mask.contains(geom):
        return geom
    g = mask.intersection(geom if geom.is_valid else geom.buffer(0))
    want = ("LineString", "MultiLineString") if gtype == "LineString" else ("Polygon", "MultiPolygon")
    if g.geom_type == "GeometryCollection":
        g = unary_union([x for x in g.geoms if x.geom_type in want])
    return g if not g.is_empty and g.geom_type in want else None


def read_layer(path, mask=None):
    """(gtype, fields, [(geom, props)]) dari shapefile; dengan mask hanya fitur di dalam Kawasan Sabang."""
    r = shapefile.Reader(str(path), encoding="latin1")
    gtype = GEOM_TYPES.get(r.shapeTypeName)
    if gtype is None:
        return None
    fields = [{"name": f.name, "type": field_type(f), "size": f.size} for f in r.fields[1:] if f.name.upper() not in DROP_FIELDS]
    out = []
    if mask is not None:
        mx0, my0, mx1, my1 = mask.bounds
        pmask = prep(mask)
    for sr in r.iterShapeRecords():
        s = sr.shape
        if s.shapeTypeName == "NULL" or not s.points:
            continue
        if mask is not None:
            xs = [p[0] for p in s.points] if gtype == "Point" else (s.bbox[0], s.bbox[2])
            ys = [p[1] for p in s.points] if gtype == "Point" else (s.bbox[1], s.bbox[3])
            if max(xs) < mx0 or min(xs) > mx1 or max(ys) < my0 or min(ys) > my1:
                continue
        geom = shape(to_2d(s.__geo_interface__))
        if geom.is_empty:
            continue
        if mask is not None:
            if gtype == "Point" and not pmask.contains(geom):
                continue
            geom = clip(geom, mask, gtype) if gtype != "Point" else geom
            if geom is None:
                continue
        rec = sr.record.as_dict()
        out.append((geom, {f["name"]: clean(rec.get(f["name"]), f["type"]) for f in fields}))
    return gtype, fields, out


def merge_fields(a, b):
    names = {f["name"] for f in a}
    return a + [f for f in b if f["name"] not in names]


def convert(layer_id, sources):
    """sources: [(path, mask|None)] — semua bagian digabung menjadi satu layer."""
    gtype, fields, rows = None, [], []
    for path, mask in sources:
        res = read_layer(path, mask)
        if res is None:
            continue
        gtype = gtype or res[0]
        fields = merge_fields(fields, res[1])
        rows += res[2]
    if gtype is None:
        return None

    features = []
    for i, (geom, props) in enumerate(rows, start=1):
        props = {f["name"]: props.get(f["name"]) for f in fields}
        props["objectid"] = i
        props["PULAU"], props["WILAYAH"] = store.pulau_of(geom)
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
        f["properties"]["PULAU"], f["properties"]["WILAYAH"] = store.pulau_of(shape(f["geometry"]))
        next_id += 1
    fc = {"type": "FeatureCollection", "name": layer_id, "features": features + user_feats}
    save_layer(layer_id, fc)
    by_wil = collections.Counter(f["properties"]["WILAYAH"] for f in features)
    return {"id": layer_id, "geom": gtype, "fields": fields, "defaults": defaults,
            "rbi_count": len(features), "user_count": len(user_feats),
            "sabang_count": by_wil[WILAYAH_SABANG], "pulo_aceh_count": by_wil[WILAYAH_PULO_ACEH]}


def main():
    LAYER_DIR.mkdir(parents=True, exist_ok=True)
    print("Pulau Kawasan Sabang:")
    aceh_mask = build_pulau()
    sources = collections.defaultdict(list)
    for path in sorted(Path(RBI_DIR).glob("*_50K.shp")):
        sources[path.stem].append((path, None))
    for path in sorted(Path(RBI_DIR_ACEH_BESAR).glob("*_50K.shp")):
        sources[path.stem].append((path, aceh_mask))

    catalog = {}
    for layer_id in sorted(sources):
        info = convert(layer_id, sources[layer_id])
        if info:
            catalog[info["id"]] = info
            print(f"{info['id']:32s} {info['geom']:10s} {info['sabang_count']:5d} Sabang {info['pulo_aceh_count']:5d} Pulo Aceh"
                  f"  {info['user_count']:3d} pengguna")
    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=1)
    print(f"\n{len(catalog)} layer → {LAYER_DIR}", file=sys.stderr)


if __name__ == "__main__":
    main()
