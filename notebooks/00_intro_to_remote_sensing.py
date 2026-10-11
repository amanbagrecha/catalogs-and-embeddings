import marimo

__generated_with = "0.25.1"
app = marimo.App(
    width="compact",
    app_title="Intro · What a satellite sees",
    css_file="theme.css",
)


@app.cell(hide_code=True)
def _():
    import marimo as mo
    import numpy as np

    from cngeo import build, charts, datapack

    return build, charts, datapack, mo, np


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    <div class="kicker">Welcome · 11:00–11:25</div>

    # What does a satellite see?

    <div class="lead">Today we follow one lake in Bengaluru through open satellite, weather and map
    data, read the cloud-native way, and then let a foundation model read the pixels for us. We
    start with the basics: what a satellite measures, who takes the pictures, and where to look at
    them.</div>

    ## About me

    I'm Aman Bagrecha, a geospatial consultant working on remote sensing, computer vision and
    open-source tools. I write about maps, satellites and code at
    [amanbagrecha.com](https://amanbagrecha.com), and I've spoken about open-source geospatial tools
    at FOSS4G in Kosovo, Seoul and Hiroshima. In Bengaluru I co-run
    [Let's Talk Spatial](https://letstalkspatial.in), a community for anyone into GIS, remote sensing
    and maps: free meetups, talks and workshops, over chai. Come to the next one.

    <div style="display:flex; flex-wrap:wrap; gap:12px; margin:14px 0 6px">
      <figure style="flex:1 1 220px; margin:0">
        <img src="https://amanbagrecha.com/_astro/geonerds.rsHE1WLH_Z1p2iL2.webp" alt="Presenting at FOSS4G 2023" style="display:block; width:100%; height:170px; object-fit:cover; border-radius:4px">
        <figcaption style="font-size:12px; color:#6b665c; margin-top:4px">Presenting at FOSS4G 2023, Prizren, Kosovo</figcaption>
      </figure>
      <figure style="flex:1 1 220px; margin:0">
        <img src="https://letstalkspatial.in/images/2026/05/Event_22_Group.jpg" alt="Let's Talk Spatial meetup group photo" style="display:block; width:100%; height:170px; object-fit:cover; border-radius:4px">
        <figcaption style="font-size:12px; color:#6b665c; margin-top:4px">Let's Talk Spatial #22, Takshashila Institution, May 2026</figcaption>
      </figure>
    </div>

    ## The satellites we will meet

    An Earth-observation satellite is a camera that measures how much sunlight each patch of ground
    reflects, in a handful of colours called bands. Several of those colours are invisible to us.

    | Satellite | From | Pixel | Passes every | Since | Measures |
    |---|---|---|---|---|---|
    | **Sentinel-2** | ESA, Europe's Copernicus programme | 10 m | 5 days | 2015 | 13 bands, visible to shortwave infrared |
    | **Landsat 8 and 9** | NASA and USGS | 30 m | 8 days | 1972, for the series | 11 bands, including heat |
    | **Sentinel-1** | ESA | 10 m | 6–12 days | 2014 | radar, through clouds, day and night |
    | **Resourcesat-2 and 2A** (LISS-III) | ISRO | 23.5 m | 24 days each | 2011 | 4 bands, green to shortwave infrared |

    All four are free to use. ISRO's newest, NISAR, built with NASA and launched from Sriharikota
    in July 2025, adds free radar at two wavelengths. Today we use Sentinel-2: small pixels, a new
    picture every few days, and the whole archive free on the cloud.

    ## Light we can't see

    Each Sentinel-2 band measures one slice of the spectrum. Here are ten of them over the lake,
    a cloud-free average of January to April 2025.
    """)
    return


@app.cell
def _(datapack):
    bands = datapack.sentinel2_bands()    # 10 bands x 500 x 700 pixels; a prepared file
    wavelength = {                        # centre of each band, in nanometres
        "blue": 492, "green": 560, "red": 665,
        "red edge 1": 704, "red edge 2": 740, "red edge 3": 783,
        "near-infrared": 833, "narrow near-infrared": 865,
        "shortwave infrared 1": 1614, "shortwave infrared 2": 2202,
    }
    return bands, wavelength


@app.cell(hide_code=True)
def _(build):
    build.recipe("sentinel2_bands")
    return


@app.cell(hide_code=True)
def _(bands, charts, datapack, np, wavelength):
    _wc = datapack.raster("worldcover")[0]                    # ESA WorldCover land cover classes
    _water = (_wc == 80).reshape(50, 10, 70, 10).mean(axis=(1, 3))
    _r, _c = np.unravel_index(np.argmax(_water), _water.shape)    # start on the most open water
    charts.spectrum_explorer(bands, wavelength,
                             {"water": _wc == 80, "trees": _wc == 10, "buildings": _wc == 50},
                             start=(_r * 10, _c * 10))
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Water absorbs almost all light beyond green, so it stays dark. Leaves reflect near-infrared
    strongly, so plants are bright in a colour our eyes can't see. Roofs, roads and bare ground
    reflect a lot everywhere, and most in the shortwave infrared. Those differences are what lets a
    computer tell one surface from another. Point at the middle of the lake: in places it reflects
    like a plant, because floating weeds cover the water.

    ## False colour

    To see near-infrared, show it as red, show red as green and green as blue. In this false-colour
    picture plants turn red, water goes nearly black and buildings look grey-blue. Move the line to
    compare it with true colour.
    """)
    return


@app.cell
def _(bands, charts, np):
    blue, green, red, nir = bands[0], bands[1], bands[2], bands[6]

    true_colour = charts.stretch(np.dstack([red, green, blue]))
    false_colour = charts.stretch(np.dstack([nir, red, green]))   # near-infrared as red
    charts.swipe(false_colour, true_colour, title="Bellandur lake, early 2025",
                 subtitle="left of the line: false colour · right: true colour")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Where to look at pictures

    You don't need code to look:

    - [Copernicus Browser](https://browser.dataspace.copernicus.eu): every Sentinel picture, any
      band combination, in a web page. Search for Bellandur and pick the "False color" preset.
    - [Bhuvan](https://bhuvan.nrsc.gov.in): ISRO's map portal, with Indian satellite pictures and
      maps made from them. ISRO's data itself is downloaded from
      [Bhoonidhi](https://bhoonidhi.nrsc.gov.in).
    - [EarthExplorer](https://earthexplorer.usgs.gov): the Landsat archive, back to 1972.

    A browser shows one place on one date at a time. To use nine years of pictures in a few lines
    of code we need catalogs, and files we can read a piece of. That's the first lesson.

    ## Today

    We find out what happened to Bellandur lake, one question at a time.

    | Time | Lesson | The question | How we answer it |
    |---|---|---|---|
    | 11:00 | **Welcome** (this page) | What does a satellite see? | bands, false colour, where to look |
    | 11:25 | **Start here** | | the lake's story, and a check that your setup works |
    | 11:35 | **1 · Satellite images** | What did the lake look like in 2017, and now? | find Sentinel-2 pictures in a STAC catalog and read just the lake from Cloud-Optimized GeoTIFFs |
    | 12:10 | **2 · Weather grids** | How much rain fell the night the lake overflowed? | read NASA's rain record from Zarr stores |
    | 12:35 | **3 · Watersheds and buildings** | What drains into the lake, and what was built around it? | CoRE Stack watersheds and Overture buildings, from GeoParquet |
    | 13:00 | *lunch* | | |
    | 14:00 | **4 · Pixels as vectors** | Can a model tell lake from road from rooftop, and find places like this anywhere on Earth? | AlphaEarth and TESSERA embeddings |
    | 14:45 | **5 · Using embeddings** | What changed around the lake since 2017? | groups, a few labels, and change between years |
    | 15:25 | **6 · Reading the catalog** | How do we get it all back? | open our own catalog with pystac and read each file again |
    | 15:45 | questions | | |
    | 16:00 | close | | |

    By lunch you will know where satellite, weather and map data live, how they are stored, and how
    to read only the piece you need. After lunch you will use a foundation model's summary of every
    10 m square to search, classify and compare places, here and across the planet. The same code
    works for any place: change the box.

    ## Get set up

    You need [uv](https://docs.astral.sh/uv/), which installs Python and every package for you.

    **Windows.** Open PowerShell (Start menu, type "PowerShell") and run these one at a time:

    ```powershell
    # 1. install uv, once. Then close PowerShell and open it again.
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

    # 2. download the workshop and install its packages (no git needed)
    irm https://github.com/amanbagrecha/catalogs-and-embeddings/archive/main.zip -OutFile workshop.zip
    Expand-Archive workshop.zip -DestinationPath .
    cd catalogs-and-embeddings-main
    uv sync

    # 3. open the notebooks in your browser
    uv run marimo edit notebooks
    ```

    **macOS and Linux.** In a terminal:

    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh     # once; then open a new terminal
    git clone https://github.com/amanbagrecha/catalogs-and-embeddings
    cd catalogs-and-embeddings
    uv sync
    uv run marimo edit notebooks
    ```

    To come back later, open a terminal in the workshop folder and run `uv run marimo edit notebooks`
    again.

    There is no data to download first. The lessons read their data straight from the cloud, and
    the few small files we prepared in advance download themselves when a notebook needs them. In
    marimo, open **Start here** first: it checks that everything works.
    """)
    return


if __name__ == "__main__":
    app.run()
