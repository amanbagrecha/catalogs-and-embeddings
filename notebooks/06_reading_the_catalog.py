import marimo

__generated_with = "0.25.1"
app = marimo.App(app_title="6 · Reading the catalog", css_file="theme.css")


@app.cell(hide_code=True)
def _():
    import marimo as mo
    import pandas as pd

    from cngeo import charts, mycatalog
    from cngeo.config import LAKE

    return LAKE, charts, mo, mycatalog, pd


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    <div class="kicker">Lesson 6 · 15:25–15:45</div>

    # How do we get it all back?

    <div class="lead">During the day we saved seven things into <code>my_catalog/</code>: a picture,
    a night of rain, water bodies, watersheds, buildings, a change map and embeddings. Now we open
    them again, starting from nothing but <code>catalog.json</code>.</div>

    It is the same three steps every time: open the catalog, find the item, follow its link to the
    file.

    ## Open the catalog

    `pystac` reads `catalog.json` and follows its links to every item.
    """)
    return


@app.cell
def _(mo, mycatalog, pd):
    import pystac

    catalog_file = mycatalog.FOLDER / "catalog.json"     # lessons 1, 2, 3 and 5 fill it
    mo.stop(not catalog_file.exists(), "Run lessons 1, 2, 3 and 5 first.")

    catalog = pystac.Catalog.from_file(str(catalog_file))
    pd.DataFrame([{"id": item.id, "title": item.properties["title"],
                   "date": item.datetime.date(),
                   "format": item.assets["data"].media_type.split(";")[0]}
                  for item in catalog.get_items()])
    return (catalog,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    The `format` column (the media type) tells you which tool opens the file: `geopandas` for
    Parquet, `rasterio` for GeoTIFF, `xarray` for Zarr.

    ## The buildings, from GeoParquet

    Ask for an item by its id, then follow its `data` asset to the file.
    """)
    return


@app.cell
def _(catalog, charts):
    import geopandas as gpd

    buildings_item = catalog.get_item("buildings")
    buildings_file = buildings_item.assets["data"].get_absolute_href()
    buildings = gpd.read_parquet(buildings_file)
    title = f"{len(buildings):,} buildings, from the catalog"
    charts.buildings_map(buildings, title=title,
                         subtitle=buildings_item.properties["title"])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## The picture, from a COG
    """)
    return


@app.cell
def _(catalog, charts):
    import rasterio

    lake_item = catalog.get_item("lake_2025")
    with rasterio.open(lake_item.assets["data"].get_absolute_href()) as cog:
        lake = cog.read()                                # 3 colours x 500 x 700 pixels
    when = f"{lake_item.datetime:%d %B %Y}"
    charts.picture({when: lake.transpose(1, 2, 0)}, width=640)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## The rain, from Zarr
    """)
    return


@app.cell
def _(LAKE, catalog, charts):
    import xarray as xr

    rain_item = catalog.get_item("rain_flood_night")
    rain_file = rain_item.assets["data"].get_absolute_href()
    rain = xr.open_zarr(rain_file, consolidated=False)
    night = rain.rain_mm.sum("time").to_dataframe(name="mm").reset_index()
    charts.rain_map(night, LAKE, title="The flood night, back from the catalog",
                    subtitle=rain_item.properties["title"])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Searching a static catalog

    In lesson 1, Earth Search answered our questions because it runs a search service. A static
    catalog is only files, so we search it ourselves: read every item and keep the ones we want.
    Here, everything that covers the lake and is from 2025:
    """)
    return


@app.cell
def _(LAKE, catalog):
    from shapely.geometry import Point, shape

    lake_point = Point(LAKE)
    [item.id for item in catalog.get_items()
     if shape(item.geometry).contains(lake_point) and item.datetime.year == 2025]
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    That is quick for seven items or a few thousand. For millions, a catalog is kept as one table
    instead ([stac-geoparquet](https://github.com/stac-utils/stac-geoparquet)) and queried with
    DuckDB, the way we found Overture's buildings in lesson 3.

    ## Share it

    Everything above opened files on this laptop. Copy `my_catalog/` to any web server, an S3
    bucket, GitHub Pages or [Source Cooperative](https://source.coop) and the same code works with
    an address in place of the path: `pystac.Catalog.from_file("https://…/catalog.json")`.
    `geopandas`, `rasterio` and `xarray` then read the files over the internet, only the parts
    they need. Paste the address into [STAC Browser](https://radiantearth.github.io/stac-browser)
    and anyone can look through it in a web page.

    ## Try it

    1. **Only part of the buildings.** Add `bbox=(77.68, 12.92, 77.69, 12.93)` to
       `gpd.read_parquet` in the buildings cell. How many come back?
    2. **Older things.** Change the search to keep items from before 2023. Which lesson saved it?
    3. **The embeddings.** Find the item that has an `emb:dimensions` property and open its file
       with `rasterio`. Does the number of bands match the property?

    ## Where to go from here

    - [Satellite Embedding course](https://courses.spatialthoughts.com/gee-satellite-embedding.html)
      by Spatial Thoughts: more exercises, from crop mapping to finding brick kilns.
    - [A primer on Earth data embeddings](https://developmentseed.org/blog/2026-10-02-earth-embeddings/)
      by Development Seed, and the conventions at [geoembeddings.org](https://geoembeddings.org).
    - [The Cloud-Native Geospatial guide](https://guide.cloudnativegeo.org): every format we used
      today, explained in depth.
    - [STAC Index](https://stacindex.org): catalogs to explore, and tools for making your own.

    Thank you for spending the day with the lake. Everything here is open: try for a different location
    """)
    return


if __name__ == "__main__":
    app.run()
