import marimo

__generated_with = "0.25.1"
app = marimo.App(
    width="compact",
    app_title="The lake and the city",
    css_file="theme.css",
)


@app.cell(hide_code=True)
def _():
    import marimo as mo

    from cngeo import charts, datapack

    return charts, datapack, mo


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    <div class="kicker">Start here · 11:25–11:35</div>

    # The lake and the city

    <div class="lead">Bellandur is Bengaluru's largest lake. In the last ten years it has foamed over
    onto the roads, caught fire, been drained and dug out, and watched the fields around it turn into
    offices and apartments. Today we follow it through open data: first by finding and reading that
    data the cloud-native way, then by letting a foundation model read the pixels for us.</div>

    Flip between the two pictures. Both were taken by the Sentinel-2 satellite in February, eight
    years apart. The green mat on the left is the lake in 2017, covered in weeds.
    """)
    return


@app.cell(hide_code=True)
def _(charts, datapack):
    charts.picture(
        {"February 2017": datapack.sentinel2(2017), "February 2025": datapack.sentinel2(2025)},
        width=640,
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Your own catalog

    As you go, you save what you find into your own folder, `my_catalog/`, in the same format the
    big archives use. By the end of the day it holds a satellite picture, the rain of
    the flood night, the watersheds and buildings around the lake, and a map of what changed: a small
    catalog of the lake that you could publish.

    ## How these notebooks work

    A marimo notebook reruns itself: change a number in a cell and every cell that depends on it
    updates. Read the code cells that are shown; the plotting code lives in `cngeo/charts.py`.

    The charts are meant to be played with. Hover them, click them, drag the sliders. Nothing you do
    there can break anything.

    ## Check your setup

    This checks the Python packages and the internet services we use. Everything should say `True`.
    """)
    return


@app.cell
def _():
    from cngeo.setup_check import checks

    checks()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## The data

    Every dataset is open, and each lesson reads it live from the cloud. A few charts use small
    files we prepared in advance (27 years of rain at the lake, nine years of embeddings); each one
    downloads the first time a notebook needs it.

    | What | Source | Stored as |
    |---|---|---|
    | Satellite pictures | [Sentinel-2](https://registry.opendata.aws/sentinel-2-l2a-cogs/), via Element 84 Earth Search | COG + STAC |
    | Rain | [NASA IMERG](https://gpm.nasa.gov/data/imerg) via [dynamical.org](https://dynamical.org) | Zarr (Icechunk) |
    | Temperature | [NASA POWER](https://power.larc.nasa.gov) analysis-ready store | Zarr |
    | Watersheds, water bodies | [CoRE Stack](https://core-stack.org) | STAC + GeoJSON |
    | Buildings | [Overture Maps](https://overturemaps.org) | GeoParquet + STAC |
    | Embeddings | [AlphaEarth Foundations](https://source.coop/tge-labs/aef) (Google DeepMind), [TESSERA](https://source.coop/tessera/tessera) (Cambridge), [Clay v1.5 / Major TOM](https://huggingface.co/datasets/Major-TOM/Core-S2L2A-249k-Clay-v1_5) | COG, Zarr, GeoParquet |
    | Land cover labels | [ESA WorldCover 2021](https://esa-worldcover.org) | COG |
    """)
    return


if __name__ == "__main__":
    app.run()
