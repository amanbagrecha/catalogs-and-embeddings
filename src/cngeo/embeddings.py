"""Reading and handling pixel embeddings: AlphaEarth (Google DeepMind) and TESSERA (Cambridge).

Both are published as open, cloud-native data, so we read only the study area:

- AlphaEarth Foundations Satellite Embedding V1: 64 numbers per 10 m pixel per year (2017-2025),
  as Cloud-Optimized GeoTIFFs with a GeoParquet index, mirrored on Source Cooperative.
  CC BY 4.0, "The AlphaEarth Foundations Satellite Embedding dataset is produced by Google and Google DeepMind."
- TESSERA v1.1: 128 numbers per 10 m pixel per year (2017-2025), a Zarr store on Source Cooperative,
  read with the ``geotessera`` package. CC0; please cite arXiv:2506.20380.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import numpy as np

from .config import CRS, RES, STUDY, STUDY_LONLAT

AEF_INDEX = "https://data.source.coop/tge-labs/aef/v1/annual/aef_index.parquet"
AEF_FILES = "https://data.source.coop/tge-labs/aef/"
GDAL_ENV = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_MAX_RETRY="5", GDAL_HTTP_RETRY_DELAY="1",
                CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tiff")


# ---------------------------------------------------------------------------
# AlphaEarth
# ---------------------------------------------------------------------------
def aef_tiles(year: int, bbox=STUDY_LONLAT):
    """The rows of the AlphaEarth tile index (a GeoParquet file) that cover a lon/lat box in one year."""
    import duckdb

    w, s, e, n = bbox
    return duckdb.sql(f"""
        SELECT year, utm_zone, crs, path, utm_west, utm_south, utm_east, utm_north
        FROM read_parquet('{AEF_INDEX}')
        WHERE year = {int(year)} AND wgs84_west < {e} AND wgs84_east > {w}
          AND wgs84_south < {n} AND wgs84_north > {s}
    """).df()


def dequantise(q: np.ndarray) -> np.ndarray:
    """AlphaEarth int8 -> float32 on the unit sphere; -128 (no data) -> NaN."""
    f = q.astype("float32")
    f = np.sign(f) * (np.abs(f) / 127.5) ** 2
    f[:, q[0] == -128] = np.nan
    return f


def alphaearth_int8(year: int, bounds=STUDY, tiles=None, workers: int = 16) -> np.ndarray:
    """Raw int8 AlphaEarth embeddings (64, H, W) for a box in UTM metres, north-up.

    The files are stored south-up (row 0 is the southern edge), so we count window rows from the
    south and flip the result. Each of the 64 bands is a separate set of tiles in the file, so we
    read them in parallel threads.
    """
    import rasterio
    from rasterio.windows import Window

    tiles = aef_tiles(year) if tiles is None else tiles
    tiles = tiles[tiles["crs"] == CRS]
    x0, y0, x1, y1 = bounds
    W, H = int((x1 - x0) / RES), int((y1 - y0) / RES)
    q = np.full((64, H, W), -128, np.int8)
    for t in tiles.itertuples():
        ox0, ox1 = max(x0, t.utm_west), min(x1, t.utm_east)
        oy0, oy1 = max(y0, t.utm_south), min(y1, t.utm_north)
        if ox0 >= ox1 or oy0 >= oy1:
            continue
        url = "/vsicurl/" + AEF_FILES + t.path.split("/tge-labs/aef/", 1)[1]
        win = Window(int((ox0 - t.utm_west) / RES), int((oy0 - t.utm_south) / RES),
                     int((ox1 - ox0) / RES), int((oy1 - oy0) / RES))

        def read(bands):
            with rasterio.Env(**GDAL_ENV), rasterio.open(url) as src:
                return src.read(bands.tolist(), window=win)

        with ThreadPoolExecutor(workers) as ex:
            block = np.concatenate(list(ex.map(read, np.array_split(np.arange(1, 65), workers))))
        block = block[:, ::-1, :]  # south-up -> north-up
        r, c = int((y1 - oy1) / RES), int((ox0 - x0) / RES)
        q[:, r:r + block.shape[1], c:c + block.shape[2]] = block
    return q


def alphaearth(year: int, bounds=STUDY) -> np.ndarray:
    """AlphaEarth embeddings (64, H, W) as float32 unit vectors, read live from Source Cooperative."""
    return dequantise(alphaearth_int8(year, bounds))


# ---------------------------------------------------------------------------
# TESSERA
# ---------------------------------------------------------------------------
def tessera_int8(year: int, bounds=STUDY):
    """Raw TESSERA int8 (128, H, W) and per-pixel scales (H, W), cropped to a box in UTM metres."""
    from geotessera import GeoTesseraZarr
    from pyproj import Transformer

    tr = Transformer.from_crs(CRS, "EPSG:4326", always_xy=True)
    lon, lat = tr.transform([bounds[0], bounds[2]], [bounds[1], bounds[3]])
    q, s, t, crs = GeoTesseraZarr().read_region_quantized((lon[0] - 0.001, lat[0] - 0.001, lon[1] + 0.001, lat[1] + 0.001), year)
    assert str(crs).endswith(CRS.split(":")[1]), crs
    c0, r0 = int(round((bounds[0] - t.c) / RES)), int(round((t.f - bounds[3]) / RES))
    W, H = int((bounds[2] - bounds[0]) / RES), int((bounds[3] - bounds[1]) / RES)
    return np.ascontiguousarray(q[r0:r0 + H, c0:c0 + W].transpose(2, 0, 1)), s[r0:r0 + H, c0:c0 + W]


def tessera(year: int, bounds=STUDY) -> np.ndarray:
    """TESSERA embeddings (128, H, W) as float32, read live. Not unit length: use ``unit()`` before comparing."""
    q, s = tessera_int8(year, bounds)
    return q.astype("float32") * s[None]


# ---------------------------------------------------------------------------
# Working with embeddings
# ---------------------------------------------------------------------------
def unit(e: np.ndarray) -> np.ndarray:
    """Scale every pixel's vector (axis 0) to length 1, so a dot product is the cosine similarity."""
    return e / np.linalg.norm(e, axis=0, keepdims=True)


def coarsen(e: np.ndarray, f: int) -> np.ndarray:
    """Average f x f blocks of pixels and scale back to length 1 (how AlphaEarth makes its overviews)."""
    d, h, w = e.shape
    m = np.nanmean(e[:, : h // f * f, : w // f * f].reshape(d, h // f, f, w // f, f), axis=(2, 4))
    return unit(m)


def table(e: np.ndarray) -> np.ndarray:
    """(D, H, W) -> (H*W, D): one row per pixel, the shape scikit-learn expects."""
    return e.reshape(e.shape[0], -1).T


def pixel(lonlat, bounds=STUDY) -> tuple[int, int]:
    """(row, column) of a lon/lat point in the study grid."""
    from pyproj import Transformer

    x, y = Transformer.from_crs("EPSG:4326", CRS, always_xy=True).transform(*lonlat)
    return int((bounds[3] - y) // RES), int((x - bounds[0]) // RES)


def squeeze(vectors: np.ndarray, dims: int) -> np.ndarray:
    """Project unit vectors (rows) onto their ``dims`` main directions, keeping dot products close to the
    originals (a truncated SVD, no centring). Lets a web page compare pixels with fewer numbers."""
    _, _, vt = np.linalg.svd(vectors[np.random.default_rng(0).choice(len(vectors), min(20_000, len(vectors)), replace=False)],
                             full_matrices=False)
    return vectors @ vt[:dims].T


def pixel_table(picture: np.ndarray, models: dict[str, np.ndarray], f: int, dims: int | None = None):
    """A chart table of f x f pixel squares: ``id, c, r, rgb`` and each model's vector as integers x100.

    ``picture`` is (rows, cols, 3) uint8; ``models`` maps a short prefix to a (D, rows, cols) array.
    """
    import pandas as pd

    h, w = picture.shape[0] // f, picture.shape[1] // f
    rgb = picture[: h * f, : w * f].reshape(h, f, w, f, 3).mean(axis=(1, 3)).astype(int).reshape(-1, 3)
    r, c = np.divmod(np.arange(h * w), w)
    df = pd.DataFrame({"id": np.arange(h * w), "c": c, "r": r,
                       "rgb": [f"#{a:02x}{b:02x}{d:02x}" for a, b, d in rgb]})
    for prefix, e in models.items():
        v = table(coarsen(unit(e), f))
        v = np.nan_to_num(v)
        if dims:
            v = squeeze(v, dims)
        cols = {f"{prefix}{i}": np.round(v[:, i] * 100).astype("int16") for i in range(v.shape[1])}
        df = pd.concat([df, pd.DataFrame(cols)], axis=1)
    return df


def pca_picture(e: np.ndarray) -> np.ndarray:
    """The three main directions of an embedding (D, rows, cols) painted as red, green and blue."""
    d, h, w = e.shape
    x = np.nan_to_num(table(e))
    x = x - x.mean(0)
    _, _, vt = np.linalg.svd(x[np.random.default_rng(0).choice(len(x), min(20_000, len(x)), replace=False)], full_matrices=False)
    z = x @ vt[:3].T
    lo, hi = np.percentile(z, [2, 98], axis=0)
    return np.clip((z - lo) / (hi - lo), 0, 1).reshape(h, w, 3)


def chip_picture(parquet_url: str, row_group: int, size: int = 256) -> np.ndarray:
    """The Sentinel-2 thumbnail of one Major TOM chip, read from a single row group of a big Parquet file."""
    import io

    import fsspec
    import pyarrow.parquet as pq
    from PIL import Image

    with fsspec.open(parquet_url, "rb", block_size=256 * 1024) as f:
        png = pq.ParquetFile(f).read_row_group(int(row_group), columns=["thumbnail"])["thumbnail"][0].as_py()
    return np.asarray(Image.open(io.BytesIO(png)).convert("RGB").resize((size, size)))
