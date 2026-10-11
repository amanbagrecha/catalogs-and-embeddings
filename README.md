# Cloud-native data and Earth embeddings

[![Fresh install](https://github.com/amanbagrecha/catalogs-and-embeddings/actions/workflows/fresh-install.yml/badge.svg)](https://github.com/amanbagrecha/catalogs-and-embeddings/actions/workflows/fresh-install.yml)

A hands-on workshop for people who know Python and machine learning but are new to geospatial
data. The whole day follows one place, Bellandur lake in east Bengaluru, and one question: what
happened to it, and how would you find out from open data?

- **Morning: where the data lives and how it is stored.** Satellite pictures (STAC catalogs and
  Cloud-Optimized GeoTIFFs), rain (Zarr), watersheds and buildings (GeoParquet), and the catalogs
  that make them findable, including India's CoRE Stack.
- **Afternoon: what a foundation model makes of it.** AlphaEarth and TESSERA pixel embeddings:
  similarity search, clustering, few-label classification, change detection, and a global search
  for places that look like east Bengaluru.

Every lesson saves what it found into `my_catalog/`, a small STAC catalog that participants build
during the day and could publish as is; the last lesson opens it all again from `catalog.json`.
Open data and open-source Python only; no Earth Engine.

## Setup

You need [uv](https://docs.astral.sh/uv/), which also installs the right Python (3.12).

**Windows** (PowerShell, no git needed):

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"   # then reopen PowerShell
irm https://github.com/amanbagrecha/catalogs-and-embeddings/archive/main.zip -OutFile workshop.zip
Expand-Archive workshop.zip -DestinationPath .
cd catalogs-and-embeddings-main
uv sync
uv run cngeo check                    # everything should say True
uv run marimo edit notebooks
```

**macOS and Linux:**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh     # then open a new terminal
git clone https://github.com/amanbagrecha/catalogs-and-embeddings && cd catalogs-and-embeddings
uv sync
uv run cngeo check                    # everything should say True
uv run marimo edit notebooks
```

The badge above is a weekly check that exactly these steps work on machines with nothing
installed: Windows (PowerShell, no git), macOS and Linux, all the way to running every notebook.

There is no data to download first: the lessons read live from the cloud, and the few prepared
files download themselves the first time a notebook needs them. On weak Wi-Fi, fetch them all at
once with `uv run cngeo datapack download` (~130 MB).

The first DuckDB query downloads its `spatial` and `httpfs` extensions (~75 MB). Run
`uv run python -c "import duckdb; duckdb.sql('INSTALL spatial; INSTALL httpfs')"` once before the day.

## Data

| Lesson | What | Source | Stored as | Licence |
|---|---|---|---|---|
| intro, 1 | Satellite pictures | Sentinel-2 L2A on AWS, via [Earth Search](https://earth-search.aws.element84.com/v1) | COG + STAC | Copernicus |
| 2 | Rain | [NASA IMERG](https://gpm.nasa.gov/data/imerg), via [dynamical.org](https://dynamical.org) | Zarr (Icechunk) | CC BY 4.0 |
| 2 | Temperature (chunking demo) | [NASA POWER](https://power.larc.nasa.gov) analysis-ready stores | Zarr | CC BY 4.0 |
| 3 | Water bodies, micro-watersheds | [CoRE Stack](https://core-stack.org), Bengaluru South tehsil | STAC + GeoJSON (WFS) | CC BY 4.0 |
| 3 | Buildings | [Overture Maps](https://overturemaps.org), latest release | GeoParquet + STAC | ODbL |
| 4, 5 | Pixel embeddings | [AlphaEarth Foundations](https://source.coop/tge-labs/aef) (Google DeepMind), 2017–2025 | COG + GeoParquet index | CC BY 4.0 |
| 4 | Pixel embeddings | [TESSERA v1.1](https://source.coop/tessera/tessera) (Cambridge), via `geotessera` | Zarr | CC0 (cite arXiv:2506.20380) |
| 4 | Chip embeddings | [Clay v1.5 on Major TOM](https://huggingface.co/datasets/Major-TOM/Core-S2L2A-249k-Clay-v1_5) | GeoParquet | CC BY-SA 4.0 |
| intro, 5 | Labels | [ESA WorldCover 2021](https://esa-worldcover.org) | COG | CC BY 4.0 |

Attribution for AlphaEarth: "The AlphaEarth Foundations Satellite Embedding dataset is produced by
Google and Google DeepMind."

## Repository

```
notebooks/        the lessons (marimo) + theme.css
src/cngeo/
  charts.py       every chart (Altair), interactivity included
  embeddings.py   reading AlphaEarth and TESSERA; similarity, squeezing, pictures
  mycatalog.py    the participants' own STAC catalog
  net.py cog.py   counting bytes over the network; looking inside a COG
  site.py         notebooks -> static website (site.css)
  datapack.py build.py cli.py config.py setup_check.py
tests/run_notebook.py
```

For another place, change `STUDY`, `STUDY_LONLAT` and `LAKE` in `config.py` (keep `STUDY` on a
10 m UTM grid) and run `cngeo datapack build`.

Code: MIT. Data: see each source's licence above.
