"""Environment check used by ``cngeo check`` and the first notebook."""

from __future__ import annotations

import importlib
import time

PACKAGES = ["marimo", "numpy", "pandas", "geopandas", "rasterio", "xarray", "zarr", "pystac", "pystac_client",
            "odc.stac", "duckdb", "sklearn", "altair"]

ENDPOINTS = {  # one per lesson
    "Earth Search (Sentinel-2)": "https://earth-search.aws.element84.com/v1",
    "dynamical.org (rain)": "https://stac.dynamical.org/catalog.json",
    "CoRE Stack": "https://spatio-temporal-asset-catalog.s3.ap-south-1.amazonaws.com/"
                  "CorestackCatalogs_merged_collection/catalog.json",
    "Overture Maps": "https://stac.overturemaps.org/catalog.json",
    "Source Cooperative (AlphaEarth)": "https://data.source.coop/tge-labs/aef/v1/annual/aef_index.parquet",
    "Workshop files (GitHub)": None,  # filled in below: one small prepared file
}


def check_packages() -> list[dict]:
    rows = []
    for name in PACKAGES:
        try:
            m = importlib.import_module(name)
            rows.append({"check": name, "ok": True, "detail": getattr(m, "__version__", "installed")})
        except Exception as e:  # noqa: BLE001
            rows.append({"check": name, "ok": False, "detail": str(e)[:80]})
    return rows


def check_network(timeout: float = 10) -> list[dict]:
    import requests

    rows = []
    from .datapack import DATA_URL

    for name, url in ENDPOINTS.items():
        url = url or DATA_URL + "label_curve.parquet"
        t0 = time.time()
        try:
            r = requests.head(url, timeout=timeout, allow_redirects=True)
            rows.append({"check": name, "ok": r.ok, "detail": f"HTTP {r.status_code} in {time.time()-t0:.1f}s"})
        except Exception as e:  # noqa: BLE001
            rows.append({"check": name, "ok": False, "detail": type(e).__name__})
    return rows


def checks(network: bool = True):
    """One row per check: packages, then the internet services the lessons read from."""
    import pandas as pd

    return pd.DataFrame(check_packages() + (check_network() if network else []))
