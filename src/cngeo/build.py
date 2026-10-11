"""Build the data pack from the original open sources: ``cngeo datapack build [--step NAME]``.

Every step reads only what the lessons need (the study area around Bellandur lake, one rain
series, a few thousand buildings, a global sample of embeddings) and writes it in a
cloud-native format: COG or GeoParquet.
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd

from . import datapack
from .config import CRS, RES, STUDY, STUDY_LONLAT, data_dir

EARTH_SEARCH = "https://earth-search.aws.element84.com/v1"
WORLDCOVER = "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_N12E075_Map.tif"
ENV = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", AWS_NO_SIGN_REQUEST="YES")


def _shape():
    return int((STUDY[3] - STUDY[1]) / RES), int((STUDY[2] - STUDY[0]) / RES)


def _transform():
    from rasterio.transform import from_origin

    return from_origin(STUDY[0], STUDY[3], RES, RES)


def write_cog(path: Path, arr: np.ndarray, nodata=None, **tags) -> Path:
    """(bands, H, W) array on the study grid -> Cloud-Optimized GeoTIFF."""
    import rasterio

    path.parent.mkdir(parents=True, exist_ok=True)
    arr = arr if arr.ndim == 3 else arr[None]
    with rasterio.open(path, "w", driver="COG", width=arr.shape[2], height=arr.shape[1], count=arr.shape[0],
                       dtype=arr.dtype, crs=CRS, transform=_transform(), nodata=nodata, compress="zstd",
                       blocksize=256, overviews="none" if arr.shape[0] > 3 else "auto") as dst:
        dst.write(arr)
        if tags:
            dst.update_tags(**{k: str(v) for k, v in tags.items()})
    return path


def _cache(name: str) -> Path:
    p = data_dir() / "cache" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------
def sentinel2(force: bool = False):
    """True-colour pictures of the study area: the clearest February scene of 2017 and of 2025.

    The older ``sentinel-2-l2a`` collection on Earth Search goes back to 2017 here; we only need its
    ready-made true-colour ``visual`` asset, so its pixel offsets don't matter.
    """
    import rasterio
    from pystac_client import Client
    from rasterio.enums import Resampling
    from rasterio.windows import from_bounds

    cat = Client.open(EARTH_SEARCH)
    H, W = _shape()
    for year in datapack.YEARS["sentinel2"]:
        out = datapack.path("sentinel2", year)
        if out.exists() and not force:
            continue
        items = cat.search(collections=["sentinel-2-l2a"], bbox=STUDY_LONLAT, datetime=f"{year}-02-01/{year}-02-28",
                           query={"eo:cloud_cover": {"lt": 3}}).item_collection()
        item = min((i for i in items if "43PGQ" in i.id), key=lambda i: (i.properties["eo:cloud_cover"], -i.datetime.day))
        with rasterio.Env(**ENV), rasterio.open(item.assets["visual"].href) as src:
            rgb = src.read(window=from_bounds(*STUDY, src.transform), out_shape=(3, H, W), resampling=Resampling.nearest)
        write_cog(out, rgb, source=item.id, date=item.datetime.date())
        print(f"sentinel2 {year}: {item.id}")


def worldcover(force: bool = False):
    """ESA WorldCover 2021 land cover, warped onto the study grid (nearest)."""
    import rasterio
    from rasterio.warp import Resampling, reproject
    from rasterio.windows import from_bounds

    out = datapack.path("worldcover")
    if out.exists() and not force:
        return
    w, s, e, n = STUDY_LONLAT
    with rasterio.Env(**ENV), rasterio.open("/vsicurl/" + WORLDCOVER) as src:
        win = from_bounds(w - 0.01, s - 0.01, e + 0.01, n + 0.01, src.transform).round_offsets().round_lengths()
        wc, wtr = src.read(1, window=win), src.window_transform(win)
    dst = np.zeros(_shape(), np.uint8)
    reproject(wc, dst, src_transform=wtr, src_crs="EPSG:4326", dst_transform=_transform(), dst_crs=CRS,
              resampling=Resampling.nearest)
    write_cog(out, dst, nodata=0)


def aef(force: bool = False):
    """AlphaEarth for every year 2017-2025 (cached); the pack keeps three of them."""
    from .embeddings import aef_tiles, alphaearth_int8

    for year in range(2017, 2026):
        out = _cache(f"alphaearth_{year}.tif")
        if not out.exists() or force:
            t0 = time.time()
            q = alphaearth_int8(year, STUDY, tiles=aef_tiles(year))
            write_cog(out, q, nodata=-128)
            print(f"alphaearth {year}: {q.shape} in {time.time() - t0:.0f}s")
        if year in datapack.YEARS["aef"]:
            datapack.path("aef", year).parent.mkdir(parents=True, exist_ok=True)
            datapack.path("aef", year).write_bytes(out.read_bytes())


def tessera(force: bool = False):
    """TESSERA for 2021 (for the label experiment, cached) and the pack's year."""
    from .embeddings import tessera_int8

    for year in sorted({2021, *datapack.YEARS["tessera"]}):
        out = _cache(f"tessera_{year}.tif")
        if not out.exists() or force:
            t0 = time.time()
            q, s = tessera_int8(year, STUDY)
            write_cog(out, q)
            write_cog(_cache(f"tessera_{year}_scales.tif"), s.astype("float32"), nodata=np.nan)
            print(f"tessera {year}: {q.shape} in {time.time() - t0:.0f}s")
        if year in datapack.YEARS["tessera"]:
            for src, key in ((out, "tessera"), (_cache(f"tessera_{year}_scales.tif"), "tessera_scales")):
                datapack.path(key, year).write_bytes(src.read_bytes())


def aef_change(force: bool = False):
    """How far each 50 m square's AlphaEarth vector moved from 2017, for every later year."""
    from .embeddings import coarsen, dequantise

    out = datapack.path("aef_change")
    if out.exists() and not force:
        return
    first = coarsen(dequantise(_read(_cache("alphaearth_2017.tif"))), 5)
    d, h, w = first.shape
    r, c = np.divmod(np.arange(h * w), w)
    df = pd.DataFrame({"c": c, "r": r})
    for year in range(2018, 2026):
        e = coarsen(dequantise(_read(_cache(f"alphaearth_{year}.tif"))), 5)
        df[f"s{year}"] = np.clip(np.round((e * first).sum(0).ravel() * 100), -100, 100).astype("int16")
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)


def label_curve(force: bool = False, seeds: int = 10):
    """Agreement with WorldCover for a classifier trained on n labels per class, for each kind of input."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    from .embeddings import dequantise, table, unit

    out = datapack.path("label_curve")
    if out.exists() and not force:
        return
    y = classes(_read(datapack.path("worldcover"))[0]).ravel()
    inputs = {
        "AlphaEarth": table(dequantise(_read(_cache("alphaearth_2021.tif")))),
        "TESSERA": table(unit(_read(_cache("tessera_2021.tif")).astype("float32") * _read(_cache("tessera_2021_scales.tif")))),
        "Sentinel-2 bands": table(sentinel2_bands(2021)),
    }
    keep = (y >= 0) & np.all([np.isfinite(x).all(1) for x in inputs.values()], axis=0)
    rows = []
    for n in (1, 2, 5, 10, 20, 50, 100, 200):
        for seed in range(seeds):
            rng = np.random.default_rng(seed)
            train = np.concatenate([rng.choice(np.flatnonzero(keep & (y == k)), n, replace=False) for k in np.unique(y[keep])])
            test = np.setdiff1d(np.flatnonzero(keep), train)
            test = rng.choice(test, min(50_000, len(test)), replace=False)
            for name, x in inputs.items():
                model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)).fit(x[train], y[train])
                rows.append({"input": name, "labels": n, "seed": seed, "accuracy": float((model.predict(x[test]) == y[test]).mean())})
        print(f"labels {n}: done")
    df = pd.DataFrame(rows).groupby(["input", "labels"], as_index=False)["accuracy"].mean()
    df.to_parquet(out, index=False)


S2_BANDS = ["blue", "green", "red", "rededge1", "rededge2", "rededge3", "nir", "nir08", "swir16", "swir22"]


def bands(force: bool = False):
    """Ten Sentinel-2 bands for the remote-sensing intro: the Jan-Apr 2025 median, reflectance x 10 000."""
    out = datapack.path("sentinel2_bands")
    if out.exists() and not force:
        return
    med = sentinel2_bands(2025)
    write_cog(out, (np.nan_to_num(med, nan=0) * 10000).clip(1, 65535).round().astype("uint16") * np.isfinite(med),
              nodata=0, bands=",".join(S2_BANDS))


def sentinel2_bands(year: int) -> np.ndarray:
    """Median of the clear Jan-Apr Sentinel-2 scenes (10 bands, reflectance), the no-model baseline."""
    import odc.stac
    from pystac_client import Client

    cache = _cache(f"sentinel2_bands_{year}.tif")
    if cache.exists():
        return _read(cache)
    items = Client.open(EARTH_SEARCH).search(collections=["sentinel-2-c1-l2a"], bbox=STUDY_LONLAT,
                                             datetime=f"{year}-01-01/{year}-04-30",
                                             query={"eo:cloud_cover": {"lt": 5}}).item_collection()
    items = [i for i in items if "43PGQ" in i.id]
    bands = S2_BANDS
    odc.stac.configure_rio(cloud_defaults=True)
    ds = odc.stac.load(items, bands=bands + ["scl"], crs=CRS, resolution=RES, x=(STUDY[0], STUDY[2]),
                       y=(STUDY[1], STUDY[3]), groupby="solar_day", chunks={}).compute()
    clear = ~ds.scl.isin([0, 1, 3, 8, 9, 10])
    med = np.stack([(ds[b].where(clear & (ds[b] > 0)) * 0.0001 - 0.1).median("time").values for b in bands]).astype("float32")
    med = med[:, ::-1] if ds.y[0] < ds.y[-1] else med
    write_cog(cache, med, nodata=np.nan)
    return med


IMERG = "https://dynamical-nasa-imerg.s3.us-west-2.amazonaws.com/nasa-imerg-analysis-late/v0.1.0.icechunk"
CORESTACK = ("https://spatio-temporal-asset-catalog.s3.ap-south-1.amazonaws.com/CorestackCatalogs_merged_collection/"
             "tehsil_wise/karnataka/bengaluru_urban/bengaluru_south/collection.json")
BUILDINGS_BOX = (77.675, 12.915, 77.705, 12.945)   # ~3 x 3 km east of the lake: Ecospace, Kadubeesanahalli


def imerg():
    """NASA IMERG half-hourly rain (0.1 degree), as an xarray Dataset over a cloud Icechunk store."""
    import os

    import icechunk
    import xarray as xr

    os.environ.setdefault("ICECHUNK_LOG", "error")
    repo = icechunk.Repository.open(icechunk.http_storage(IMERG))
    return xr.open_zarr(repo.readonly_session("main").store, chunks=None)


def rain(force: bool = False):
    """Rain over the lake: every day since 1998, the half-hours around the 2022 flood, and a map of that night."""
    from .config import LAKE

    out = datapack.path("rain")
    if out.exists() and not force:
        return
    p = imerg()["precipitation_surface"]  # mm per second, averaged over each half hour
    lon, lat = LAKE
    series = p.sel(latitude=lat, longitude=lon, method="nearest").sel(time=slice("1998-01-01", "2025-12-31")).load()
    s = series.to_series() * 1800  # mm in each half hour
    s.index = s.index.tz_localize("UTC").tz_convert("Asia/Kolkata").tz_localize(None)
    daily = s.resample("1D").sum().rename("mm").to_frame()
    out.parent.mkdir(parents=True, exist_ok=True)
    daily.round(1).to_parquet(out)
    s.loc["2022-08-20":"2022-09-15"].rename("mm").round(2).to_frame().to_parquet(datapack.path("rain_flood"))
    night = p.sel(time=slice("2022-09-04T13:30", "2022-09-05T03:30"), latitude=slice(13.45, 12.45), longitude=slice(77.15, 78.15))
    m = (night.sum("time") * 1800).to_dataframe(name="mm").reset_index()[["latitude", "longitude", "mm"]]
    m.round(2).to_parquet(datapack.path("rain_map"), index=False)


def buildings(force: bool = False):
    """Overture building footprints for a 3 x 3 km box, found through Overture's own STAC index."""
    import json
    import urllib.request

    import duckdb
    import geopandas as gpd
    import pyarrow.parquet as pq

    out = datapack.path("buildings")
    if out.exists() and not force:
        return
    con = duckdb.connect()
    con.sql("INSTALL spatial; LOAD spatial; INSTALL httpfs; LOAD httpfs;")
    release = json.load(urllib.request.urlopen("https://stac.overturemaps.org/catalog.json"))["latest"]
    w, s, e, n = BUILDINGS_BOX
    box = f"bbox.xmin <= {e} AND bbox.xmax >= {w} AND bbox.ymin <= {n} AND bbox.ymax >= {s}"
    files = [r[0] for r in con.sql(f"""SELECT assets.aws.href FROM 'https://stac.overturemaps.org/{release}/collections.parquet'
                                       WHERE collection = 'building' AND {box}""").fetchall()]
    rel = con.sql(f"SELECT id, height, num_floors, geometry FROM read_parquet({files}) WHERE {box}")
    gdf = gpd.GeoDataFrame.from_arrow(rel.arrow())
    gdf = gdf.iloc[gdf.hilbert_distance().argsort()]
    out.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_parquet(out, schema_version="1.1.0", write_covering_bbox=True, row_group_size=2000, compression="zstd")
    # the row groups of the file we just queried, with their bounding boxes (read from the footer only)
    import fsspec

    href = files[0].replace("s3://overturemaps-us-west-2/", "https://overturemaps-us-west-2.s3.us-west-2.amazonaws.com/")
    with fsspec.open(href, "rb", block_size=2**20) as f:
        meta = pq.ParquetFile(f).metadata
    cols = {meta.row_group(0).column(i).path_in_schema: i for i in range(meta.num_columns)}
    rows = []
    for g in range(meta.num_row_groups):
        rg = meta.row_group(g)
        st = {k: rg.column(cols[f"bbox.{k}"]).statistics for k in ("xmin", "ymin", "xmax", "ymax")}
        rows.append({"group": g, "rows": rg.num_rows, "MB": rg.total_byte_size / 1e6, "xmin": st["xmin"].min,
                     "ymin": st["ymin"].min, "xmax": st["xmax"].max, "ymax": st["ymax"].max})
    rg = pd.DataFrame(rows)
    rg.attrs["release"] = release
    rg.to_parquet(datapack.path("row_groups"), index=False)
    print(f"buildings: {len(gdf)} from {release}, {len(rg)} row groups in {href.rsplit('/', 1)[-1]}")


def corestack(force: bool = False):
    """CoRE Stack micro-watersheds and water bodies around the lake, converted from GeoJSON to GeoParquet."""
    import geopandas as gpd
    import pystac
    from shapely.geometry import box

    out = datapack.path("waterbodies")
    if out.exists() and not force:
        return
    col = pystac.Collection.from_file(CORESTACK)
    item = lambda name: col.get_item(f"karnataka_bengaluru_urban_bengaluru_south_{name}")
    study = box(*STUDY_LONLAT)
    wb = gpd.read_file(item("surface_water_bodies_vector").assets["data"].href)
    years = [c[5:] for c in wb.columns if c.startswith("area_") and c[5:7].isdigit()]
    wb = wb[wb.intersects(study)][["UID", "MWS_UID", "waterbody_type", "max_catchment_area", *[f"area_{y}" for y in years], "geometry"]]
    wb = wb.rename(columns={f"area_{y}": f"water_{y}" for y in years})
    mws = gpd.read_file(item("water_balance_fortnightly_vector").assets["data"].href)
    mws = mws[mws.intersects(study)][["uid", "area_in_ha", "geometry"]]
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.to_parquet(out, schema_version="1.1.0", write_covering_bbox=True)
    mws.to_parquet(datapack.path("watersheds"), schema_version="1.1.0", write_covering_bbox=True)
    print(f"corestack: {len(wb)} water bodies, {len(mws)} micro-watersheds")


# ---------------------------------------------------------------------------
# Small helpers shared with the lessons
# ---------------------------------------------------------------------------
WORLDCOVER_CLASSES = {10: "trees", 20: "grass & crops", 30: "grass & crops", 40: "grass & crops", 50: "built-up",
                      60: "bare", 80: "water", 90: "water"}
CLASS_NAMES = ["trees", "grass & crops", "built-up", "bare", "water"]


def classes(wc: np.ndarray) -> np.ndarray:
    """WorldCover codes -> 0..4 (the five classes we use), -1 for anything else."""
    out = np.full(wc.shape, -1, np.int8)
    for code, name in WORLDCOVER_CLASSES.items():
        out[wc == code] = CLASS_NAMES.index(name)
    return out


def _read(path: Path) -> np.ndarray:
    import rasterio

    with rasterio.open(path) as src:
        return src.read()


# ---------------------------------------------------------------------------
# Recipes: how each prepared file the charts read is made, shown folded under the chart
# ---------------------------------------------------------------------------
RECIPES = {  # prepared file -> (the code that makes it, build steps to run, what making it downloads)
    "sentinel2_bands": ([sentinel2_bands, bands], ["bands"], "about 135 MB of Sentinel-2 from Earth Search, under a minute"),
    "rain": ([imerg, rain], ["rain"], "about 0.3 GB of NASA IMERG (28 years at one point), about 15 minutes"),
    "aef_change": ([aef, aef_change], ["aef", "aef_change"], "about 460 MB of AlphaEarth (nine years of the study area), about 3 minutes"),
    "label_curve": ([label_curve], ["aef", "tessera", "label_curve"], "about 280 MB (AlphaEarth, TESSERA and Sentinel-2 for 2021), then 240 small models"),
}


def recipe(name: str):
    """A folded "How this file was made" box: the code behind a prepared file, and what it downloads."""
    import inspect

    import marimo as mo
    from pygments import highlight
    from pygments.formatters import HtmlFormatter
    from pygments.lexers import PythonLexer

    funcs, steps, cost = RECIPES[name]
    code = highlight("\n\n".join(inspect.getsource(f) for f in funcs), PythonLexer(), HtmlFormatter(nowrap=True))
    size = datapack.fetch(name).stat().st_size
    size = f"{size / 1e6:.1f} MB" if size > 1e5 else f"{size / 1e3:.0f} kB"
    cmd = "uv run cngeo datapack build " + " ".join(f"--step {s}" for s in steps) + " --force"
    return mo.Html(
        f'<details class="recipe"><summary>How this file was made <span>· making it reads {cost}</span></summary>'
        f"<p>The chart reads a small prepared file ({size}): your copy in <code>data/</code> if you have one, "
        f"otherwise it downloads once. To make it yourself from the original data, run <code>{cmd}</code>. "
        f"This is the code that runs:</p><pre class=\"code\">{code}</pre></details>")


STEPS = {"sentinel2": sentinel2, "bands": bands, "worldcover": worldcover, "aef": aef, "tessera": tessera,
         "aef_change": aef_change, "label_curve": label_curve, "rain": rain, "buildings": buildings,
         "corestack": corestack}


def run(steps: list[str] | None = None, force: bool = False):
    for name in steps or STEPS:
        t0 = time.time()
        STEPS[name](force=force)
        print(f"[{name}] {time.time() - t0:.0f}s")
