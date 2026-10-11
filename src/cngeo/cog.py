"""Look inside a Cloud-Optimized GeoTIFF: its tiles, its zoomed-out copies, and how many bytes each holds."""

from __future__ import annotations

import pandas as pd


def tile_layout(href: str, bounds: tuple) -> pd.DataFrame:
    """One row per internal tile, for the full image and each overview, marking the tiles a box touches.

    ``bounds`` is (west, south, east, north) in the file's own coordinates.
    """
    import rasterio
    from rasterio.windows import from_bounds

    rows = []
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"), rasterio.open(href) as full:
        levels = [None, *range(len(full.overviews(1)))]
    for level, ov in enumerate(levels):
        with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"), rasterio.open(href, overview_level=ov) as src:
            bh, bw = src.block_shapes[0]
            win = from_bounds(*bounds, src.transform)
            r0, r1 = int(win.row_off // bh), int((win.row_off + win.height - 1e-9) // bh)
            c0, c1 = int(win.col_off // bw), int((win.col_off + win.width - 1e-9) // bw)
            for (i, j), _ in src.block_windows(1):
                rows.append({"level": level, "row": i, "col": j, "mb": src.block_size(1, i, j) / 1e6,
                             "hit": r0 <= i <= r1 and c0 <= j <= c1, "size": f"{src.width:,} x {src.height:,}"})
    return pd.DataFrame(rows)
