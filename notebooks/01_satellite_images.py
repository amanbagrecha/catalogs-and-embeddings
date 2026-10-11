import marimo

__generated_with = "0.25.1"
app = marimo.App(app_title="1 · Satellite images", css_file="theme.css")


@app.cell(hide_code=True)
def _():
    import warnings

    import marimo as mo
    import pandas as pd

    from cngeo import charts, cog, mycatalog, net
    from cngeo.config import CRS, STUDY, STUDY_LONLAT

    warnings.filterwarnings("ignore", message="Could not parse bucket")
    return CRS, STUDY, STUDY_LONLAT, charts, cog, mo, mycatalog, net, pd


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    <div class="kicker">Lesson 1 · 11:35–12:10</div>

    # What did the lake look like in 2017, and now?

    <div class="lead">The Sentinel-2 satellites photograph every patch of land on Earth about every
    five days, in 10 m pixels, and have done so since 2015. The archive is free and enormous. To
    compare two pictures of one lake we need to find them in it, and then read only the lake.</div>

    Two inventions make that easy, and they are the whole of this lesson: a **catalog** you can
    search, and **files you can read a piece of**.

    ## Find the pictures: a STAC catalog

    STAC (SpatioTemporal Asset Catalog) describes every picture as a small record called an
    **item**: where it was taken, when, how cloudy it was, and links to the actual files, called
    **assets**. Items are grouped into **collections** (here, "Sentinel-2, with the atmosphere
    removed"), and collections into a **catalog**. Element 84 runs a free one, Earth Search, over
    the Sentinel-2 archive on Amazon's cloud. Let's ask it for every picture of our study area, the
    7 × 5 km around the lake, since 2017.
    """)
    return


@app.cell
def _(STUDY_LONLAT, pd):
    from pystac_client import Client

    earth_search = Client.open("https://earth-search.aws.element84.com/v1")
    search = earth_search.search(
        collections=["sentinel-2-l2a"],     # Sentinel-2, atmosphere removed
        bbox=STUDY_LONLAT,                  # west, south, east, north, in degrees
        datetime="2017-01-01/2025-12-31",
    )
    items = [i for i in search.items() if "43PGQ" in i.id]   # the tile with the lake

    scenes = pd.DataFrame({
        "date": [i.datetime.replace(tzinfo=None) for i in items],
        "cloud": [i.properties["eo:cloud_cover"] for i in items],
    })
    f"{len(items)} pictures found"
    return earth_search, items, scenes


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Here is one of them, picked at random. A Sentinel-2 picture covers 110 × 110 km; the white box
    is our study area. To be quick we read only a small zoomed-out copy that is stored inside the
    file (more on that below). Run the cell again for another picture.
    """)
    return


@app.cell
def _(STUDY, charts, items):
    import random

    import rasterio

    one = random.choice(items)
    with rasterio.open(one.assets["visual"].href, overview_level=3) as tile:
        whole = tile.read()                        # 3 colours x 686 x 686 pixels
        edges = tile.bounds

    cloud = one.properties["eo:cloud_cover"]
    charts.tile_preview(whole.transpose(1, 2, 0), edges, STUDY,
                        title=f"{one.datetime:%d %B %Y}, {cloud:.0f}% cloud")
    return (rasterio,)


@app.cell(hide_code=True)
def _(charts, scenes):
    charts.scene_calendar(scenes, title="When can the satellite see the lake?",
                          subtitle="Nearly cloud-free pictures in each month. Hover a square.")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    From June to September the monsoon hides Bengaluru: a picture almost every week, and almost none
    of them clear. February is reliably clear, so we compare one February with another.

    ## Inside one item

    Here is the clearest picture from February 2017 and the files it links to. Each band of light the
    satellite measures is its own file, plus a ready-made true-colour picture called `visual`.
    """)
    return


@app.cell
def _(items, pd):
    def clearest(year, month=2):
        """The least cloudy picture of one month."""
        same_month = [i for i in items
                      if i.datetime.year == year and i.datetime.month == month]
        return min(same_month, key=lambda i: i.properties["eo:cloud_cover"])

    feb_2017 = clearest(2017)
    pd.DataFrame([{"asset": key, "what it is": a.title, "file": a.href.split("/")[-1]}
                  for key, a in feb_2017.assets.items() if a.href.endswith(".tif")])
    return clearest, feb_2017


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Read only the lake: a Cloud-Optimized GeoTIFF

    The `visual` file covers a 110 × 110 km square. We want 7 × 5 km of it. A **Cloud-Optimized
    GeoTIFF** (COG) is an ordinary image file laid out so that a program can ask the server for one
    byte range at a time: first the header, which says where everything is, then only the tiles it
    needs. Your laptop never downloads the rest.
    """)
    return


@app.cell
def _(STUDY, feb_2017, net, rasterio):
    from rasterio.windows import from_bounds

    href = feb_2017.assets["visual"].href
    with net.count_bytes() as fetched, rasterio.open(href) as image:
        window = from_bounds(*STUDY, image.transform)   # our box, in the file's metres
        lake_2017 = image.read(window=window)           # 3 colours x 500 x 700 pixels

    file_mb = net.size_mb(href)
    f"Read {fetched.mb:.1f} MB in {fetched.requests} requests from a {file_mb:.0f} MB file"
    return from_bounds, href, lake_2017


@app.cell(hide_code=True)
def _(STUDY, charts, cog, href):
    charts.cog_tiles(cog.tile_layout(href, STUDY), title="Inside the file",
                     subtitle="Each square is one tile. Dark ones hold part of our box. Slide to the zoomed-out copies.")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    At full detail our box touches two of the file's 121 tiles. The file also keeps zoomed-out copies
    of itself, called **overviews**, each a quarter the size of the last; a web map showing the
    whole tile reads one small overview tile instead of hundreds of megabytes. Hover a square to see
    how many bytes it holds.

    ## 2017 and now

    The same two steps for February 2025, then the two pictures side by side.
    """)
    return


@app.cell
def _(STUDY, clearest, from_bounds, rasterio):
    feb_2025 = clearest(2025)
    with rasterio.open(feb_2025.assets["visual"].href) as _image:
        lake_2025 = _image.read(window=from_bounds(*STUDY, _image.transform))
    return feb_2025, lake_2025


@app.cell(hide_code=True)
def _(charts, feb_2017, feb_2025, lake_2017, lake_2025):
    charts.picture({f"{feb_2017.datetime:%d %B %Y}": lake_2017.transpose(1, 2, 0),
                    f"{feb_2025.datetime:%d %B %Y}": lake_2025.transpose(1, 2, 0)}, width=640)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    The lake is the large shape left of centre. In 2017 a mat of water hyacinth and weeds covers
    almost all of it, fed by the sewage that flows in. By 2025 the western half has been drained
    and dug out, and open water fills the eastern basin. Around it, the grey blocks of offices and
    apartments have spread east and south. The straight grey line at the top is the HAL airport
    runway; the diagonal is the Outer Ring Road.

    ## Where catalogs live

    Earth Search is one of many. [STAC Index](https://stacindex.org) lists about 150 public
    catalogs. A few you will meet again:

    - [Microsoft Planetary Computer](https://planetarycomputer.microsoft.com/catalog): 130+
      collections; reading files needs a free, automatic signature (`planetary_computer.sign`).
    - [NASA CMR-STAC](https://cmr.earthdata.nasa.gov/stac): all of NASA's archive; searching is open,
      downloading needs a free Earthdata login.
    - [Source Cooperative](https://source.coop): a shared space where anyone can publish open data
      in cloud-native formats. The embeddings of lesson 4 live there.
    - From India: [CoRE Stack](https://core-stack.org), which we open in lesson 3, and ISRO's
      Bhoonidhi, which speaks STAC but needs a login.

    Because they all speak STAC, the code above works on any of them: change the URL and the
    collection name.

    ## Start your own catalog

    Now we turn the 2025 picture into our own cloud-native data: write it as a COG, describe it with
    a STAC item, and put the item in a catalog. `rio-stac` reads the file and fills in its footprint,
    size and projection for us.
    """)
    return


@app.cell
def _(CRS, STUDY, feb_2025, lake_2025, mycatalog, rasterio):
    import pystac
    from rasterio.transform import from_origin
    from rio_stac import create_stac_item

    # 1. the picture, as a Cloud-Optimized GeoTIFF on our 10 m grid
    path = mycatalog.DATA / "lake_2025.tif"
    grid = dict(crs=CRS, transform=from_origin(STUDY[0], STUDY[3], 10, 10),
                width=700, height=500, count=3, dtype="uint8")
    with rasterio.open(path, "w", driver="COG", compress="deflate", **grid) as out:
        out.write(lake_2025)

    # 2. a STAC item describing it; rio-stac reads the footprint, size and projection
    item = create_stac_item(str(path), id="lake_2025", input_datetime=feb_2025.datetime,
                            asset_name="data", asset_media_type=pystac.MediaType.COG,
                            with_proj=True)
    item.properties["title"] = "Bellandur lake, February 2025 (Sentinel-2)"

    # 3. a catalog holding the item, saved as a folder of JSON files. The first time we
    #    make a new one; after that we open it, so items from later lessons are kept
    catalog_file = mycatalog.FOLDER / "catalog.json"
    if catalog_file.exists():
        catalog = pystac.Catalog.from_file(str(catalog_file))
        catalog.remove_item("lake_2025")
    else:
        catalog = pystac.Catalog(id="bellandur",
                                 description="What we found out about Bellandur lake")
    catalog.add_item(item)
    catalog.normalize_hrefs(str(mycatalog.FOLDER))
    catalog.make_all_asset_hrefs_relative()       # links that still work when copied
    catalog.save(pystac.CatalogType.SELF_CONTAINED)
    mycatalog.items()
    return (catalog,)


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    Your catalog is the folder `my_catalog/`. Click through it below: `catalog.json` links to the
    item, `lake_2025/lake_2025.json`, and the item links to the picture in `data/`. That is all a
    static catalog is.
    """)
    return


@app.cell
def _(catalog, mo, mycatalog):
    # click a folder to go inside it, click a file to see it below
    folder = mo.ui.file_browser(mycatalog.FOLDER, value=catalog.get_self_href(),
                                multiple=False)
    folder
    return (folder,)


@app.cell(hide_code=True)
def _(folder, mycatalog):
    mycatalog.show(folder.path())
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Try it

    Each of the three cells below is ready to run. Change the values at the top and run it again.

    1. **A place you know.** Which months are clear there?
    2. **Near-infrared instead of true colour.** Plants reflect near-infrared light strongly: where
       is the picture brightest?
    3. **The whole tile from a zoomed-out copy.** How many megabytes does the whole 110 km tile take?
    """)
    return


@app.cell
def _(charts, earth_search, pd):
    # Try 1: change the box and the year
    my_box = (77.58, 12.96, 77.61, 12.99)     # west, south, east, north: around Cubbon Park
    my_year = "2024"

    found = list(earth_search.search(collections=["sentinel-2-l2a"], bbox=my_box,
                                     datetime=my_year).items())
    by_month = pd.DataFrame({"month": [i.datetime.month for i in found],
                             "cloud": [i.properties["eo:cloud_cover"] for i in found]})
    (by_month.groupby("month").cloud
     .agg(pictures="size", nearly_clear=lambda c: int((c < 10).sum()))
     .rename(index=dict(enumerate(charts.MONTHS, start=1))))
    return


@app.cell
def _(STUDY, charts, feb_2025, from_bounds, rasterio):
    # Try 2: change the band ("nir", "red", "swir16", ...) or the picture (feb_2017)
    band = "nir"
    picture = feb_2025

    with rasterio.open(picture.assets[band].href) as _image:
        values = _image.read(1, window=from_bounds(*STUDY, _image.transform))
    charts.image(values, cmap="Greens", label=f"{band}, {picture.datetime:%d %b %Y}")
    return


@app.cell
def _(charts, href, net, rasterio):
    # Try 3: change the zoom level (0 = half size ... 3 = one sixteenth)
    zoom_level = 3

    with net.count_bytes() as _fetched, rasterio.open(href, overview_level=zoom_level) as _small:
        whole_tile = _small.read()
    charts.picture({"tile": whole_tile.transpose(1, 2, 0)}, width=420,
                   title=f"The whole tile at {whole_tile.shape[2]:,} x {whole_tile.shape[1]:,} pixels",
                   subtitle=f"read {_fetched.mb:.1f} MB in {_fetched.requests} requests")
    return

if __name__ == "__main__":
    app.run()
