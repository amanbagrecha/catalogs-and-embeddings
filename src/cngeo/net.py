"""Count how many bytes a block of code really fetched over the network, so we can see what "read only
the part you need" means.

    with count_bytes() as fetched:
        ...                                   # rasterio / GDAL reads
    fetched.mb                                # megabytes downloaded
"""

from __future__ import annotations

import logging
import re
from contextlib import contextmanager


class _Fetched:
    def __init__(self):
        self.ranges: list[tuple[int, int]] = []

    @property
    def requests(self) -> int:
        return len(self.ranges)

    @property
    def mb(self) -> float:
        return sum(b - a + 1 for a, b in self.ranges) / 1e6


class _Ranges(logging.Handler):
    def __init__(self, sink: _Fetched):
        super().__init__(logging.DEBUG)
        self.sink = sink

    def emit(self, record):
        self.sink.ranges += [(int(a), int(b)) for a, b in re.findall(r"Downloading (\d+)-(\d+)", record.getMessage())]


@contextmanager
def count_bytes():
    """GDAL logs every HTTP range request it makes; we listen to that log while the block runs."""
    import rasterio

    sink = _Fetched()
    log = logging.getLogger("rasterio")
    handler, level = _Ranges(sink), log.level
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)
    try:
        with rasterio.Env(CPL_DEBUG=True, GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"):
            yield sink
    finally:
        log.removeHandler(handler)
        log.setLevel(level)


def size_mb(href: str) -> float:
    """Size of a file on the web, from a HEAD request."""
    import requests

    return int(requests.head(href, timeout=30, allow_redirects=True).headers.get("Content-Length", 0)) / 1e6


def store(url: str):
    """A read-only Zarr store over HTTPS that retries dropped connections (venue Wi-Fi drops a lot)."""
    import zarr
    from obstore.store import HTTPStore

    return zarr.storage.ObjectStore(HTTPStore.from_url(url), read_only=True)
