import marimo

__generated_with = "0.25.1"
app = marimo.App(
    width="compact",
    app_title="4 · Pixels as vectors",
    css_file="theme.css",
)


@app.cell(hide_code=True)
def _():
    import marimo as mo
    import numpy as np

    from cngeo import charts, datapack
    from cngeo import embeddings as em
    from cngeo.config import LAKE, STUDY

    return LAKE, STUDY, charts, datapack, em, mo, np


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    <div class="kicker">Lesson 4 · 14:00–14:45</div>

    # Can a model read the pixels for us?

    <div class="lead">This morning we learned to find and fetch data. This afternoon we let a model
    look at it. A geospatial foundation model has studied years of satellite pictures of the whole
    planet, without anyone labelling them, and written down a short list of numbers for every 10 m
    square of land, every year. Similar places get similar numbers.</div>

    If you know word2vec, you know the idea: words used in similar sentences get nearby vectors.
    Here, squares of ground that look and behave alike through the year (their colour in every
    season, their radar echo, their texture, their neighbours) get nearby vectors. These vectors are
    called **embeddings**.

    Two open sets cover Bengaluru:

    - **AlphaEarth Foundations** from Google DeepMind: 64 numbers per 10 m square per year,
      2017–2025, for all land. The embeddings are open (CC BY 4.0); the model is not.
    - **TESSERA** from the University of Cambridge: 128 numbers per square per year, learned from
      Sentinel-1 radar and Sentinel-2 time series. Both the embeddings and the model are open.

    ## Find and read the embeddings

    Everything from the morning applies. AlphaEarth's embeddings are Cloud-Optimized GeoTIFFs, one
    per 82 km square per year with 64 bands, and a GeoParquet index lists every file. Source
    Cooperative mirrors them. First the index:
    """)
    return


@app.cell
def _(em):
    our_box = (77.6494, 12.9085, 77.7143, 12.9530)  # west, south, east, north: 7 × 5 km around Bellandur lake
    tiles = em.aef_tiles(2025, bbox=our_box)        # DuckDB on the GeoParquet index: which file has it?
    tiles[["year", "utm_zone", "path"]]
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    That file is 3 GB. We read only our 7 × 5 km box from it: 64 bands, each in its own tiles, so
    the helper fetches them in parallel. (The files happen to be stored upside down, south at the
    top; the helper flips them back.)
    """)
    return


@app.cell
def _(STUDY, em):
    aef = em.alphaearth(2025, bounds=STUDY)   # the same box in UTM metres (config.py); offline? datapack.alphaearth(2025)
    f"{aef.shape[0]} numbers for each of {aef[0].size:,} pixels"
    return (aef,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## A pixel is 64 numbers

    Hover over the picture. The bars are the 64 numbers of the 100 m square under your mouse
    (averaged from the 10 m pixels). Water, roofs, trees and bare ground each have their own pattern,
    but no single number means "water": the meaning is in the whole pattern.
    """)
    return


@app.cell(hide_code=True)
def _(LAKE, aef, charts, datapack, em):
    _px = em.pixel_table(datapack.sentinel2(2025), {"a": aef}, f=10)
    _r, _c = em.pixel(LAKE)
    charts.embedding_barcode(_px, "a", 64, start=int(_px.id[(_px.r == _r // 10) & (_px.c == _c // 10)].iloc[0]), cell=5)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Every pixel's vector has length 1, so all of them sit on the surface of a sphere in 64
    dimensions. Two pixels are alike when their vectors point the same way, and the **dot product**
    measures exactly that: 1 for the same direction, 0 for unrelated. Here is every pixel compared
    with one pixel of open water in the lake.
    """)
    return


@app.cell
def _(LAKE, aef, charts, em, np):
    row, col = em.pixel(LAKE)                          # the lake's pixel in our grid
    lake = aef[:, row, col]                            # its 64 numbers
    similarity = np.einsum("dhw,d->hw", aef, lake)     # dot product with every pixel

    charts.image(similarity, cmap=charts.SIMILAR, vmin=0.3, vmax=1,
                 label="similarity to one lake pixel", marker=(row, col))
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    The lake lights up, and so do the small ponds to the south, although nobody told the model what
    water is. Try it yourself: click anywhere on the picture below and the map on the right shows how
    similar every 70 m square is to the one you clicked. Switch between the two models.
    """)
    return


@app.cell(hide_code=True)
def _(LAKE, aef, charts, datapack, em):
    _tessera = datapack.tessera(2025)
    _px = em.pixel_table(datapack.sentinel2(2025), {"a": aef, "t": _tessera}, f=7, dims=16)
    _r, _c = em.pixel(LAKE)
    _start = int(_px.id[(_px.r == _r // 7) & (_px.c == _c // 7)].iloc[0])
    charts.similarity_explorer(_px, {"AlphaEarth": "a", "TESSERA": "t"}, start=_start, cell=3.5)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Click a block of offices, a road, a patch of trees. In the browser each square is compared using
    16 numbers squeezed from the full vector so the page stays fast; the code above uses all 64.

    ## Two models, one place

    TESSERA is read through its own package, `geotessera`, from a Zarr store on Source Cooperative.
    Its vectors are not length 1, so we scale them before comparing.
    """)
    return


@app.cell
def _(em):
    tessera = em.unit(em.tessera(2025))   # offline? em.unit(datapack.tessera(2025))
    f"{tessera.shape[0]} numbers for each of {tessera[0].size:,} pixels"
    return (tessera,)


@app.cell(hide_code=True)
def _(aef, charts, em, tessera):
    charts.pictures({"AlphaEarth: its three main directions as colour": em.pca_picture(aef),
                     "TESSERA: the same": em.pca_picture(tessera)})
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Each picture paints a model's three most important directions as red, green and blue, so
    colours mean nothing in themselves; what matters is which places share a colour. Both separate
    the lake, the airport, the office parks and the fields. AlphaEarth is smoother; TESSERA keeps
    sharper 10 m detail of roads and buildings. They are different spaces: never compare a vector
    from one model with a vector from the other.

    ## Try it

    1. Change `LAKE` in the similarity cell to the coordinates of a park (try 77.682, 12.925) and see
       what else the model thinks is park.
    2. Compute the similarity map with TESSERA (`tessera` instead of `aef`). Where do the two models
       disagree?
    """)
    return


if __name__ == "__main__":
    app.run()
