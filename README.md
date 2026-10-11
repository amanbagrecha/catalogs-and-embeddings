# The lake and the city: cloud-native data and Earth embeddings

[![Fresh install](https://github.com/amanbagrecha/catalogs-and-embeddings/actions/workflows/fresh-install.yml/badge.svg)](https://github.com/amanbagrecha/catalogs-and-embeddings/actions/workflows/fresh-install.yml)

A hands-on workshop (11:00–16:00, lunch 13:00–14:00) for people who know Python and machine learning
but are new to geospatial data. The whole day follows one place, Bellandur lake in east Bengaluru, and one
question: what happened to it, and how would you find out from open data?

- **Morning: where the data lives and how it is stored.** Satellite pictures (STAC catalogs and
  Cloud-Optimized GeoTIFFs), rain (Zarr), watersheds and buildings (GeoParquet), and the catalogs
  that make them findable, including India's CoRE Stack.
- **Afternoon: what a foundation model makes of it.** AlphaEarth and TESSERA pixel embeddings:
  similarity search, clustering, few-label classification, change detection, and a global search
  for places that look like east Bengaluru.

Every lesson saves what it found into `my_catalog/`, a small STAC catalog that participants build
during the day and could publish as is; the last lesson opens it all again from `catalog.json`.
Open data and open-source Python only; no Earth Engine.

| Time | Notebook | The question |
|---|---|---|
| 11:00 | `00_intro_to_remote_sensing.py` | Welcome: about me, what a satellite measures, the plan, setup |
| 11:25 | `00_start_here.py` | the story of the lake, and a setup check |
| 11:35 | `01_satellite_images.py` | What did the lake look like in 2017, and now? |
| 12:10 | `02_weather_grids.py` | How much rain fell the night the lake overflowed? |
| 12:35 | `03_watersheds_and_buildings.py` | What drains into the lake, and what was built around it? |
| 13:00 | lunch | |
| 14:00 | `04_pixels_as_vectors.py` | Can a model read the pixels for us? |
| 14:45 | `05_using_embeddings.py` | What changed around the lake since 2017? |
| 15:25 | `06_reading_the_catalog.py` | How do we get it all back? |
| 15:45 | questions, close at 16:00 | |

## Setup

You need [uv](https://docs.astral.sh/uv/), which also installs the right Python (3.12).

```bash
git clone https://github.com/amanbagrecha/catalogs-and-embeddings && cd catalogs-and-embeddings
uv sync                               # Python 3.12 + dependencies
uv run cngeo check                    # everything should say True
uv run marimo edit notebooks/
```

The badge above is a weekly check that these steps work on a machine with nothing installed
(Linux, macOS and Windows), all the way to running every notebook.

There is no data to download first: the lessons read live from the cloud, and the few prepared
files download themselves the first time a notebook needs them. On weak Wi-Fi, fetch them all at
once with `uv run cngeo datapack download` (~130 MB).

The first DuckDB query downloads its `spatial` and `httpfs` extensions (~75 MB). Run
`uv run python -c "import duckdb; duckdb.sql('INSTALL spatial; INSTALL httpfs')"` once before the day.

## The course website

```bash
uv run cngeo site --repo-url https://github.com/<you>/catalogs-and-embeddings
```

This runs every notebook and writes a static site to `site/`: one page per lesson with the prose,
the code cells participants see, and the same interactive charts (vega-embed, no Python in the
browser). Colours and fonts are the tokens at the top of `src/cngeo/site.css` (site) and
`notebooks/theme.css` (notebooks).

## Data

Each lesson reads its data live from the cloud. A few charts use small files prepared in advance
(27 years of rain at the lake, nine years of AlphaEarth, a global sample of chip embeddings, a
ten-band Sentinel-2 average for the intro). `datapack.fetch` downloads each one, once, when a
notebook first needs it.

| What | Source | Stored as | Licence |
|---|---|---|---|
| Satellite pictures | Sentinel-2 L2A on AWS, via [Earth Search](https://earth-search.aws.element84.com/v1) | COG + STAC | Copernicus |
| Rain | [NASA IMERG](https://gpm.nasa.gov/data/imerg), via [dynamical.org](https://dynamical.org) | Zarr (Icechunk) | CC BY 4.0 |
| Temperature (chunking demo) | [NASA POWER](https://power.larc.nasa.gov) analysis-ready stores | Zarr | CC BY 4.0 |
| Water bodies, micro-watersheds | [CoRE Stack](https://core-stack.org), Bengaluru South tehsil | STAC + GeoJSON (WFS) | CC BY 4.0 |
| Buildings | [Overture Maps](https://overturemaps.org), latest release | GeoParquet + STAC | ODbL |
| Pixel embeddings | [AlphaEarth Foundations](https://source.coop/tge-labs/aef) (Google DeepMind), 2017–2025 | COG + GeoParquet index | CC BY 4.0 |
| Pixel embeddings | [TESSERA v1.1](https://source.coop/tessera/tessera) (Cambridge), via `geotessera` | Zarr | CC0 (cite arXiv:2506.20380) |
| Chip embeddings | [Clay v1.5 on Major TOM](https://huggingface.co/datasets/Major-TOM/Core-S2L2A-249k-Clay-v1_5) | GeoParquet | CC BY-SA 4.0 |
| Labels | [ESA WorldCover 2021](https://esa-worldcover.org) | COG | CC BY 4.0 |

### Prepared files, and what it takes to make them yourself

Each of these charts shows a folded "How this file was made" box with the code. The chart reads
your local copy if you have one, and otherwise downloads the small prepared file once.

| Chart (lesson) | Prepared file | Made from | Making it downloads |
|---|---|---|---|
| World search (4) | `clay_chips.parquet`, 21 MB | all 249,000 Clay v1.5 chip embeddings (Hugging Face) | **1.1 GB** |
| Year by year change (5) | `alphaearth_change.parquet`, 0.1 MB | AlphaEarth, nine years of the study area | ~460 MB, ~3 min |
| Wettest days (2) | `lake_daily.parquet`, 0.1 MB | NASA IMERG, 28 years of half-hours at the lake | ~0.3 GB, ~15 min |
| How many labels (5) | `label_curve.parquet`, 3 kB | AlphaEarth, TESSERA and a Sentinel-2 median for 2021, then 240 models | ~280 MB |
| Spectrum, false colour (intro) | `sentinel2_bands_2025.tif`, 3.6 MB | median of the clear Sentinel-2 scenes, Jan–Apr 2025 | ~135 MB, <1 min |

Remake any of them with `uv run cngeo datapack build --step NAME --force` (the box shows the exact
command).

Attribution for AlphaEarth: "The AlphaEarth Foundations Satellite Embedding dataset is produced by
Google and Google DeepMind."

To rebuild or publish the pack:

```bash
uv run cngeo datapack build                  # all steps, ~10 min and ~1.5 GB of downloads
uv run cngeo datapack build --step rain      # one step
uv run cngeo datapack zip                    # -> dist/cngeo-datapack.zip and dist/files/
```

Attach the zip and every file in `dist/files/` to a GitHub release tagged `data-v1` of this repo.
To host them elsewhere, set `CNGEO_DATA_URL` to the folder that holds them.

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
