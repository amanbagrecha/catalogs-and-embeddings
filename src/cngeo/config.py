"""Where things are: the data pack folder and the places we look at."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Bengaluru, as a lon/lat box: (west, south, east, north)
CITY = (77.45, 12.85, 77.80, 13.15)

# The study area: 7 km x 5 km around Bellandur lake and the offices east of it.
# Kept in UTM zone 43N metres so it sits exactly on the 10 m grid that Sentinel-2,
# AlphaEarth and TESSERA all share; no resampling needed anywhere.
CRS = "EPSG:32643"
STUDY = (787500, 1428500, 794500, 1433500)      # (west, south, east, north) in metres
STUDY_LONLAT = (77.6494, 12.9085, 77.7143, 12.9530)
LAKE = (77.6718, 12.9363)                         # open water in the east basin of Bellandur lake
RES = 10                                          # metres


def data_dir() -> Path:
    """The data pack folder: ``$CNGEO_DATA_DIR`` or ``data/`` in the repository."""
    return Path(os.environ.get("CNGEO_DATA_DIR", ROOT / "data"))
