# Where the data lives: a cheat sheet for the talk

Everything below was tested from Bengaluru on 10 Oct 2026. Timings are for one laptop on good Wi-Fi.

## The formats, by kind of data

| Kind of data | The old way | Cloud-native | Read it with | Make it with |
|---|---|---|---|---|
| Satellite images (raster) | GeoTIFF, JP2, HDF | **COG** (tiles + overviews, HTTP range reads) | `rasterio`, `odc-stac`, `rioxarray` | `rasterio` (`driver="COG"`), `rio-cogeo` |
| Weather and climate grids | NetCDF, GRIB, IMD `.grd` | **Zarr** (chunks as objects), Icechunk (versions), virtual Zarr over old files | `xarray` + `zarr`, `icechunk` | `xarray.to_zarr`, `virtualizarr` |
| Shapes (vector) | Shapefile, GeoJSON | **GeoParquet** (row groups with bbox stats), FlatGeobuf, PMTiles (maps) | `duckdb`, `geopandas.read_parquet(bbox=…)` | `geopandas.to_parquet(write_covering_bbox=True)` after a Hilbert sort |
| Catalogs | portals, FTP folders | **STAC** (static JSON or an API), **stac-geoparquet** (a catalog as one table) | `pystac-client`, `pystac`, `rustac`, DuckDB | `pystac`, `rio-stac` |
| Embeddings | — | COG / Zarr / GeoParquet + STAC with the draft `emb:` fields ([geoembeddings.org](https://geoembeddings.org)) | as above | as above |

The Cloud-Native Geospatial guide covers all of these: <https://guide.cloudnativegeo.org>.

## Where catalogs live

| Catalog | Address | Notes |
|---|---|---|
| STAC Index | <https://stacindex.org> (JSON at `/api/catalogs`) | ~150 public catalogs; two from India (CoRE Stack, one dataset on Source Cooperative) |
| Earth Search (Element 84) | `https://earth-search.aws.element84.com/v1` | Sentinel-2, Landsat, Copernicus DEM on AWS; no auth. Use `sentinel-2-c1-l2a` for analysis (the older `sentinel-2-l2a` goes back to 2017 here but has an offset trap) |
| Microsoft Planetary Computer | `https://planetarycomputer.microsoft.com/api/stac/v1` | 130+ collections; files need `planetary_computer.sign` (free, automatic, ~45 min tokens) |
| NASA CMR-STAC | `https://cmr.earthdata.nasa.gov/stac/` | all of NASA; search is open, download needs an Earthdata login |
| Source Cooperative | <https://source.coop>, files at `https://data.source.coop/<account>/<repo>/…` | community data in cloud-native formats; listable over plain HTTPS |
| dynamical.org | `https://stac.dynamical.org/catalog.json` | NOAA GFS/GEFS/HRRR, ECMWF IFS/AIFS, NASA IMERG as Icechunk Zarr; CC BY 4.0 |
| Overture Maps | `https://stac.overturemaps.org/catalog.json` (`latest`) | its STAC index is a GeoParquet file per release; releases are deleted after 60 days |
| CoRE Stack (India) | `https://spatio-temporal-asset-catalog.s3.ap-south-1.amazonaws.com/CorestackCatalogs_merged_collection/catalog.json`, browser at <https://stac.core-stack.org> | static STAC per state → district → tehsil (620 tehsils, 44k items). Files come from GeoServer as GeoJSON (WFS) or uncompressed GeoTIFF (WCS; ask for a bbox and DEFLATE). Pan-India layers point at Earth Engine or Google Drive. CC BY 4.0 |
| ISRO Bhoonidhi | `https://bhoonidhi-api.nrsc.gov.in/data/…` | STAC-style API, login required |

## Browsers, for looking without code

| Browser | Address | Notes |
|---|---|---|
| Copernicus Browser | <https://browser.dataspace.copernicus.eu> | every Sentinel picture, band presets (true colour, false colour, NDVI); free login for downloads |
| Bhuvan (ISRO) | <https://bhuvan.nrsc.gov.in> | Indian satellite pictures and thematic maps; ISRO data downloads are on Bhoonidhi |
| EarthExplorer (USGS) | <https://earthexplorer.usgs.gov> | the Landsat archive back to 1972; free login |

## The datasets used in the lessons

| Lesson | Data | Address | Live cost |
|---|---|---|---|
| intro | Sentinel-2 C1 L2A, ten bands, Jan–Apr 2025 median | Earth Search, built into the data pack (`cngeo datapack build --step bands`) | ~1 min to build, 3.6 MB |
| 1 | Sentinel-2 via Earth Search | above | 9-year search ~14 s; study-area window 5 MB of a 363 MB COG |
| 2 | NASA IMERG half-hourly rain | `https://dynamical-nasa-imerg.s3.us-west-2.amazonaws.com/nasa-imerg-analysis-late/v0.1.0.icechunk` | 3 weeks at one point ~10 s (chunks 1440 × 100 × 100) |
| 2 | NASA POWER, same data in two layouts | `https://nasa-power.s3.us-west-2.amazonaws.com/merra2/{spatial,temporal}/power_merra2_daily_{…}_utc.zarr` | one year at a point: 15 s (maps) vs 3 s (time series) |
| 2 | ARCO-ERA5 (Google) | `gs://gcp-public-data-arco-era5/ar/full_37-1h-0p25deg-chunk-1.zarr-v3` | map-chunked: a year at one point ≈ 2.5 min, 850 MB. Good "slow" example, instructor only |
| 2 | IMD gridded rain/temperature | `imdlib` (web form → yearly `.grd`) | the status quo: 10–85 s per year-file |
| 3 | CoRE Stack water bodies, micro-watersheds | see above | GeoJSON for the whole tehsil, 2–3 s |
| 3 | Overture buildings | via the STAC GeoParquet index | 3 × 3 km: ~10 s, ~11 MB of a 500 MB file (3 of 128 row groups) |
| 3 | Google–Microsoft Open Buildings (VIDA) | `https://data.source.coop/vida/google-microsoft-open-buildings/geoparquet/by_country_s2/country_iso=IND/…` | similar; avoid the 64 GB `IND.parquet` |
| 4 | AlphaEarth Foundations (64-d, 2017–2025) | COGs + `aef_index.parquet` at `https://data.source.coop/tge-labs/aef/v1/annual/`; also `gs://alphaearth_foundations`; one global Zarr at `s3://us-west-2.opendata.source.coop/tge-labs/aef-mosaic/` | study area ~15 s with 16 threads. COGs are stored south-up; values `sign(q)·(|q|/127.5)²`, −128 = nodata. CC BY 4.0; model closed |
| 4 | TESSERA v1.1 (128-d, 2017–2025) | `geotessera.GeoTesseraZarr()` → `https://data.source.coop/tessera/tessera/zarr/v1.1-dclimate` | study area ~30 s. Not unit length: normalise. 2017 has gaps; use 2018+. Weights open |
| 5 | ESA WorldCover 2021 | `https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/…` | 4 s |

## Embeddings: further reading

- Development Seed, [A primer for Earth data embeddings](https://developmentseed.org/blog/2026-10-02-earth-embeddings/) (2 Oct 2026), and the conventions at [geoembeddings.org](https://geoembeddings.org).
- Spatial Thoughts, [Satellite Embedding course](https://courses.spatialthoughts.com/gee-satellite-embedding.html) (Earth Engine; its surface-water and open-plots exercises are set in Bengaluru).
- Brown et al. 2025, AlphaEarth Foundations, [arXiv:2507.22291](https://arxiv.org/abs/2507.22291).
- TESSERA (University of Cambridge), [arXiv:2506.20380](https://arxiv.org/abs/2506.20380).
- Other open embeddings: Earth Index (SoftCon, [Source Cooperative](https://source.coop/earthgenome/earthindexembeddings)), Clay v1.5 on [Source Cooperative](https://source.coop/clay/lgnd-clay-v1-5-sentinel-2-l2a), OlmoEarth and Prithvi weights on Hugging Face.
