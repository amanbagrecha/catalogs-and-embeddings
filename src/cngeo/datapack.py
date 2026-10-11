"""Prepared files: small cuts and summaries that would take minutes (or gigabytes) to make live.

The lessons read their data live from the cloud. A few charts use files prepared in advance,
for example 27 years of rain at the lake or nine years of AlphaEarth change. Each one is
downloaded the first time a notebook asks for it (``fetch``), a few megabytes at a time.

    uv run cngeo datapack status
    uv run cngeo datapack download     # everything at once (~130 MB), for a room with weak Wi-Fi
"""

from __future__ import annotations

import json
import os
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from .config import data_dir

DATA_URL = os.environ.get(  # one file per name below, plus the whole pack as a zip
    "CNGEO_DATA_URL", "https://github.com/amanbagrecha/catalogs-and-embeddings/releases/download/data-v1/")
DATAPACK_URL = DATA_URL + "cngeo-datapack.zip"

# name -> path inside the pack. ``cngeo datapack build`` writes all of them.
FILES = {
    "sentinel2": "bellandur/sentinel2_{year}.tif",          # true colour, clearest Jan-Mar scene (COG)
    "sentinel2_bands": "bellandur/sentinel2_bands_2025.tif",  # 10 bands, Jan-Apr 2025 median, reflectance x 10 000
    "aef": "bellandur/alphaearth_{year}.tif",               # 64 x int8 per 10 m pixel (COG)
    "tessera": "bellandur/tessera_{year}.tif",              # 128 x int8 per 10 m pixel (COG) ...
    "tessera_scales": "bellandur/tessera_{year}_scales.tif",  # ... times this per-pixel scale
    "worldcover": "bellandur/worldcover_2021.tif",          # ESA WorldCover land cover classes (COG)
    "aef_change": "bellandur/alphaearth_change.parquet",    # 50 m squares: similarity of each year to 2017
    "label_curve": "bellandur/label_curve.parquet",         # accuracy vs number of labels, per input
    "rain": "rain/lake_daily.parquet",                      # IMERG rain over the lake, every day since 1998
    "rain_flood": "rain/lake_flood_2022.parquet",           # ... every half hour around the September 2022 flood
    "rain_map": "rain/flood_night_map.parquet",             # ... and the night's total over Bengaluru
    "buildings": "bellandur/buildings.parquet",             # Overture footprints, 3 x 3 km (GeoParquet)
    "row_groups": "bellandur/overture_row_groups.parquet",  # the row groups of the Overture file we queried
    "waterbodies": "bellandur/waterbodies.parquet",         # CoRE Stack water bodies, water area per year
    "watersheds": "bellandur/watersheds.parquet",           # CoRE Stack micro-watersheds
    "chips": "world/clay_chips.parquet",                    # 249k global chips, 64 numbers each
}
YEARS = {"sentinel2": [2017, 2025], "aef": [2017, 2021, 2025], "tessera": [2025], "tessera_scales": [2025]}


def path(name: str, year: int | None = None) -> Path:
    rel = FILES[name].format(year=year) if year is not None else FILES[name]
    return data_dir() / rel


def _expected() -> list[str]:
    out = []
    for name, rel in FILES.items():
        out += [rel.format(year=y) for y in YEARS[name]] if "{year}" in rel else [rel]
    return out


def fetch(name: str, year: int | None = None) -> Path:
    """The local copy of one prepared file, downloaded the first time it is needed."""
    p = path(name, year)
    if not p.exists():
        import pooch

        pooch.get_logger().setLevel("WARNING")   # no hash advice in the notebook
        print(f"downloading {p.name} (once)")
        pooch.retrieve(DATA_URL + p.name, known_hash=None, fname=p.name, path=p.parent, progressbar=False)
    return p


def status() -> pd.DataFrame:
    rows = []
    for rel in _expected():
        p = data_dir() / rel
        rows.append({"file": rel, "present": p.exists(), "MB": round(p.stat().st_size / 1e6, 1) if p.exists() else None})
    return pd.DataFrame(rows)


def download(url: str | None = None, force: bool = False) -> Path:
    """Download and unzip the pack into the data folder (skipped if everything is there)."""
    import pooch

    root = data_dir()
    if not force and status().present.all():
        return root
    root.mkdir(parents=True, exist_ok=True)
    zpath = pooch.retrieve(url or DATAPACK_URL, known_hash=None, path=root / ".download", progressbar=True)
    with zipfile.ZipFile(zpath) as zf:
        zf.extractall(root)
    return root


def zip_pack(out: str | Path) -> Path:
    """The whole pack as one zip, and every file on its own in ``files/`` next to it.

    Attach all of them to a GitHub release tagged ``data-v1``: ``fetch`` downloads single files by
    name, ``download`` the zip.
    """
    import shutil

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    files = _expected()
    flat = out.parent / "files"
    flat.mkdir(exist_ok=True)
    assert len({Path(rel).name for rel in files}) == len(files), "file names must be unique"
    for rel in files:
        shutil.copy2(data_dir() / rel, flat / Path(rel).name)
    manifest = {rel: (data_dir() / rel).stat().st_size for rel in files}
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_STORED) as zf:
        for rel in files:
            zf.write(data_dir() / rel, rel)
        zf.writestr("manifest.json", json.dumps(manifest, indent=1))
    print(f"wrote {out} ({out.stat().st_size / 1e6:.0f} MB, {len(files)} files)")
    return out


# ---------------------------------------------------------------------------
# Reading the pack
# ---------------------------------------------------------------------------
def raster(name: str, year: int | None = None):
    """A raster from the pack as a numpy array (bands, rows, columns)."""
    import rasterio

    with rasterio.open(fetch(name, year)) as src:
        return src.read()


def sentinel2(year: int):
    """True-colour picture of the study area, (rows, columns, 3) uint8."""
    return raster("sentinel2", year).transpose(1, 2, 0)


def sentinel2_bands():
    """Ten Sentinel-2 bands of the study area (``build.S2_BANDS``), reflectance 0-1, (10, rows, columns)."""
    a = raster("sentinel2_bands").astype("float32")
    a[a == 0] = np.nan
    return a / 10000


def alphaearth(year: int):
    """AlphaEarth embeddings of the study area, (64, rows, columns) float32 unit vectors."""
    from .embeddings import dequantise

    return dequantise(raster("aef", year))


def tessera(year: int):
    """TESSERA embeddings of the study area, (128, rows, columns) float32 (int8 x per-pixel scale)."""
    return raster("tessera", year).astype("float32") * raster("tessera_scales", year)


def table(name: str):
    """A table from the pack: a GeoDataFrame if it has shapes, else a DataFrame."""
    import pyarrow.parquet as pq

    p = fetch(name)
    if b"geo" in (pq.read_schema(p).metadata or {}):
        import geopandas as gpd

        return gpd.read_parquet(p)
    return pd.read_parquet(p)
