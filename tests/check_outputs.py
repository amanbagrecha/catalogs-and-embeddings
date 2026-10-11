"""After the notebooks have run: things that can pass silently on one system and break on another.

    uv run python tests/check_outputs.py

1. The catalog the participants made links with relative, forward-slash paths, so the folder
   still works when copied to a web server (Windows paths would put backslashes or C:\\ in it).
2. Lesson 1's byte counter sees GDAL's range requests (it reads GDAL's debug log).
"""

import json
import re
import sys
from pathlib import Path

from cngeo import mycatalog, net
from cngeo.build import WORLDCOVER

problems = []

files = [mycatalog.FOLDER / "catalog.json", *mycatalog.FOLDER.glob("*/*.json")]
for f in files:
    doc = json.loads(f.read_text(encoding="utf-8"))
    hrefs = [link["href"] for link in doc.get("links", [])] + [a["href"] for a in doc.get("assets", {}).values()]
    for href in hrefs:
        if "\\" in href or re.match(r"^([a-zA-Z]:|/)", href):
            problems.append(f"{f.relative_to(mycatalog.FOLDER).as_posix()}: {href}")
print(f"catalog: {len(files)} JSON files, {len(problems)} non-portable links")

import rasterio
from rasterio.windows import Window

with net.count_bytes() as fetched, rasterio.open("/vsicurl/" + WORLDCOVER) as src:
    src.read(1, window=Window(0, 0, 512, 512))
print(f"byte counter: {fetched.mb:.2f} MB in {fetched.requests} requests")
if fetched.requests == 0:
    problems.append("the byte counter saw no requests")

if problems:
    print("\n".join(problems))
    sys.exit(1)
