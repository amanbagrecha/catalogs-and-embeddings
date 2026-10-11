"""Our own STAC catalog of the lake, which grows lesson by lesson.

A static STAC catalog is just a folder of JSON files that link to each other and to the data files.
Put the folder on any web server or bucket and other people can find and read what you made.

    from cngeo import mycatalog
    mycatalog.add(mycatalog.DATA / "lake_2025.tif", title="Bellandur, February 2025", datetime="2025-02-21")
    mycatalog.items()
"""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

import pandas as pd

from .config import ROOT

FOLDER = ROOT / "my_catalog"
DATA = FOLDER / "data"
DATA.mkdir(parents=True, exist_ok=True)

MEDIA = {".tif": "image/tiff; application=geotiff; profile=cloud-optimized",
         ".parquet": "application/vnd.apache.parquet",
         ".zarr": "application/vnd.zarr"}


def open_catalog():
    """The catalog, created on first use."""
    import pystac

    path = FOLDER / "catalog.json"
    if path.exists():
        return pystac.Catalog.from_file(str(path))
    DATA.mkdir(parents=True, exist_ok=True)
    return pystac.Catalog(id="bellandur", title="Bellandur lake and the city around it",
                          description="What we found out about Bellandur lake, Bengaluru, in one day of open data.")


def _when(value) -> dt.datetime:
    if isinstance(value, dt.datetime):
        return value if value.tzinfo else value.replace(tzinfo=dt.timezone.utc)
    return dt.datetime.fromisoformat(str(value)).replace(tzinfo=dt.timezone.utc)


def add(path, title: str, datetime=None, bbox=None, **properties):
    """Describe one file as a STAC item and add it to the catalog (replacing an item with the same id)."""
    import pystac

    path = Path(path).resolve()
    item_id = path.stem.replace(".", "-")
    when = _when(datetime or dt.date.today().isoformat())
    if path.suffix == ".tif":
        from rio_stac import create_stac_item

        item = create_stac_item(str(path), id=item_id, input_datetime=when, asset_name="data",
                                asset_media_type=MEDIA[".tif"], with_proj=True)
    else:
        if bbox is None and path.suffix == ".parquet":
            import geopandas as gpd

            bbox = list(gpd.read_parquet(path).to_crs(4326).total_bounds)
        w, s, e, n = (float(v) for v in bbox)
        geom = {"type": "Polygon", "coordinates": [[[w, s], [e, s], [e, n], [w, n], [w, s]]]}
        item = pystac.Item(id=item_id, geometry=geom, bbox=[w, s, e, n], datetime=when, properties={})
        item.add_asset("data", pystac.Asset(href=str(path), media_type=MEDIA.get(path.suffix), roles=["data"]))
    item.properties.update(title=title, **properties)
    catalog = open_catalog()
    if catalog.get_item(item_id) is not None:
        catalog.remove_item(item_id)
    catalog.add_item(item)
    catalog.normalize_hrefs(str(FOLDER))
    catalog.make_all_asset_hrefs_relative()
    catalog.save(catalog_type=pystac.CatalogType.SELF_CONTAINED)
    return item


def items() -> pd.DataFrame:
    """One row per item in the catalog."""
    catalog = open_catalog()
    rows = []
    for item in catalog.get_items():
        asset = item.assets["data"]
        rows.append({"item": item.id, "title": item.properties.get("title", ""), "date": item.datetime.date() if item.datetime else None,
                     "file": Path(asset.get_absolute_href()).name, "type": (asset.media_type or "").split(";")[0]})
    return pd.DataFrame(rows)


def write_cog(path, array, nodata=None):
    """Save an array on the study grid (rows, cols) or (bands, rows, cols) as a Cloud-Optimized GeoTIFF."""
    import numpy as np

    from .build import write_cog as _write

    DATA.mkdir(parents=True, exist_ok=True)
    return _write(Path(path), np.asarray(array), nodata=nodata)


def show(path) -> object:
    """What is inside one file of the catalog: JSON as text, any other file as its size."""
    import marimo as mo

    if path is None:
        return "Click a file above to see what is inside."
    path = Path(path)
    if path.suffix == ".json":
        text = path.read_text().strip()
        text = re.sub(r"\[[^\[\]{}]*\]", lambda m: re.sub(r"\s+", " ", m.group()).replace("[ ", "[").replace(" ]", "]"), text)
        return mo.md(f"`{path.relative_to(FOLDER)}`\n\n```json\n{text}\n```")
    size = path.stat().st_size
    size = f"{size / 1e6:.1f} MB" if size > 1e5 else f"{size / 1e3:.1f} kB"
    return f"{path.relative_to(FOLDER)}: {size} of data, the file an item's JSON points to"
