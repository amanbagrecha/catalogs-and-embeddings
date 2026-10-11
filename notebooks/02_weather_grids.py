import marimo

__generated_with = "0.25.1"
app = marimo.App(
    width="compact",
    app_title="2 · Weather grids",
    css_file="theme.css",
)


@app.cell(hide_code=True)
def _():
    import os

    import marimo as mo
    import pandas as pd
    import xarray as xr

    from cngeo import build, charts, datapack, mycatalog, net
    from cngeo.config import LAKE

    os.environ.setdefault("ICECHUNK_LOG", "error")
    return LAKE, build, charts, datapack, mo, mycatalog, net, pd, xr


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    <div class="kicker">Lesson 2 · 12:10–12:35</div>

    # How much rain fell the night the lake overflowed?

    <div class="lead">On the night of 4 September 2022 it poured on east Bengaluru. By morning the
    Outer Ring Road beside Bellandur was a river, lakes had spilled into apartment blocks, and
    people were rowing boats past the IT parks. Rain gauges recorded about 131 mm overnight. What
    does the satellite record say?</div>

    Weather and climate data come as **grids**: one number for every cell of a map, for every time
    step, often for decades. NASA's IMERG rain estimate covers the whole planet in 0.1° cells
    (about 11 km), every half hour since 1998. That is half a million maps.

    ## The usual way: one file per year

    The India Meteorological Department publishes its gridded rainfall as one file per year, which
    you download from a web form (the `imdlib` package automates the form). To get one place you
    download the whole country; for 25 years you download 25 files. That is fine for one dataset.
    For an archive of petabytes it is not.

    ## Zarr: a grid cut into chunks

    **Zarr** stores a big array as many small compressed pieces, called **chunks**, each its own
    file or cloud object, plus a little JSON that describes the whole. A reader opens the JSON,
    works out which chunks hold what you asked for, and fetches only those. dynamical.org keeps
    IMERG as a Zarr store on Amazon's cloud and lists it in its own STAC catalog.
    """)
    return


@app.cell
def _(pd, xr):
    import icechunk
    import pystac

    dynamical = pystac.Catalog.from_file("https://stac.dynamical.org/catalog.json")
    imerg = dynamical.get_child("nasa-imerg-analysis-late")
    storage = icechunk.http_storage(imerg.assets["icechunk-https"].href)
    session = icechunk.Repository.open(storage).readonly_session("main")
    rain = xr.open_zarr(session.store, chunks=None)["precipitation_surface"]

    pd.DataFrame({
        "": ["time steps", "latitudes", "longitudes", "size, if loaded", "one chunk"],
        "IMERG rain": [f"{rain.shape[0]:,}", rain.shape[1], rain.shape[2],
                       f"{rain.nbytes / 1e12:.0f} TB", str(rain.encoding["chunks"])],
    })
    return (rain,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Thirteen terabytes, and nothing has been downloaded yet: xarray has only read the description.
    Each chunk holds 1,440 half-hours (30 days) of a 100 × 100 cell square, so the store is built for
    exactly our question: a stretch of time at one place. Let's take the cell over the lake for the
    three weeks around the flood.
    """)
    return


@app.cell
def _(LAKE, pd, rain):
    at_lake = rain.sel(longitude=LAKE[0], latitude=LAKE[1], method="nearest")
    weeks = at_lake.sel(time=slice("2022-08-20", "2022-09-15")).load()  # bytes move now

    flood = (weeks.to_series() * 1800).rename("mm")   # mm per second over half an hour
    flood.index = flood.index + pd.Timedelta(hours=5, minutes=30)   # UTC -> India time
    f"{len(flood)} half-hours, {flood.sum():.0f} mm in total"
    return (flood,)


@app.cell(hide_code=True)
def _(charts, flood):
    charts.rain_night(flood.to_frame(), title="Rain over Bellandur lake, every half hour",
                      subtitle="Drag across some bars to add them up. The tall cluster is the night of 4 September.")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Drag across the night of the 4th: about 50 mm fell between seven in the evening and five in the
    morning, and the 5th ended with about 70 mm. The gauges caught 131 mm overnight. A satellite estimate averages over an 11 km square and
    smooths out the heaviest bursts, so it is useful for patterns and comparisons, not for the
    exact number at one street.

    Was it unusual? The data pack has the same cell for every day since 1998, and the night's total
    for the cells around the city.
    """)
    return


@app.cell(hide_code=True)
def _(LAKE, charts, datapack):
    _daily = datapack.table("rain")
    _rank = int((_daily.mm > _daily.loc["2022-09-05", "mm"]).sum()) + 1
    (charts.rain_map(datapack.table("rain_map"), LAKE, title="The night over Bengaluru",
                     subtitle="Rain from 7 pm on 4 September to 9 am on 5 September 2022")
     | charts.wettest_days(_daily, "2022-09-05", n=20, title=f"5 September 2022: the {_rank}th wettest day",
                           subtitle=f"over the lake, of {len(_daily):,} days since 1998"))
    return


@app.cell(hide_code=True)
def _(build):
    build.recipe("rain")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    The heaviest rain fell in a band from the north-west down through the centre of the city,
    close to 100 mm. The lake's own cell got about 50. But the centre of Bengaluru drains south-east
    through the Koramangala valley into Bellandur, so much of that band's water ran towards the
    lake. Which land drains where is the question of the next lesson.

    ## Chunks decide what is fast

    The shape of the chunks is a choice the data's publisher makes, and it decides which questions
    are quick. NASA's POWER project stores the same daily weather twice: once **chunked as maps**
    (one day of the whole globe per chunk) and once **chunked as time series** (40 years of a small
    square per chunk). Let's ask both the same two questions and time them.
    """)
    return


@app.cell
def _(LAKE, net, pd, xr):
    import time

    power = ("https://nasa-power.s3.us-west-2.amazonaws.com/merra2/"
             "{0}/power_merra2_daily_{0}_utc.zarr")
    place = dict(lon=LAKE[0], lat=LAKE[1], method="nearest")
    questions = {
        "one place, every day": lambda t: t.sel(**place).sel(time="2024"),
        "one day, every place": lambda t: t.sel(time="2024-05-01",
                                                lat=slice(6, 37), lon=slice(68, 98)),
    }
    rows = []
    for layout, name in [("spatial", "chunked as maps"),
                         ("temporal", "chunked as time series")]:
        t2m = xr.open_zarr(net.store(power.format(layout)))["T2M"]   # air temperature
        for question, ask in questions.items():
            start = time.perf_counter()
            ask(t2m).load()
            rows.append({"layout": name, "question": question,
                         "chunk shape": str(t2m.encoding["chunks"]),
                         "seconds": round(time.perf_counter() - start, 1)})
    timings = pd.DataFrame(rows)
    timings
    return (timings,)


@app.cell(hide_code=True)
def _(charts, timings):
    charts.chunk_explainer(timings, title="The same grid, stored two ways",
                           subtitle="Pick a question. Black: the cells you want. Blue: the chunks that must be fetched to get them.")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    A year at one place, from the map-shaped store, means fetching 366 global maps to keep one
    number from each; from the time-series store it is one chunk. A map of India for one day is the
    reverse. Neither layout is wrong; they serve different people. When you publish a grid, ask who
    will read it and how.

    Two more tools you will meet:

    - **Virtual Zarr** ([VirtualiZarr](https://virtualizarr.readthedocs.io), Kerchunk) writes a
      small index of where each chunk sits inside existing NetCDF or GRIB files, so an old archive
      of files can be read like Zarr without copying it.
    - **[Icechunk](https://icechunk.io)** adds versions to a Zarr store: every update is a commit
      you can go back to. The IMERG store above is an Icechunk repository; we read its `main` branch.

    ## Store your own

    We save the flood night over Bengaluru as our own Zarr store, chunked for maps (the whole area
    in one chunk per half hour), and add it to the catalog.
    """)
    return


@app.cell
def _(mycatalog, rain):
    night = rain.sel(time=slice("2022-09-04T13:30", "2022-09-05T03:30"),  # 7 pm-9 am
                     latitude=slice(13.45, 12.45), longitude=slice(77.15, 78.15))
    night_mm = (night.load() * 1800).rename("rain_mm").to_dataset().drop_encoding()

    zarr_path = mycatalog.DATA / "rain_flood_night.zarr"
    maps = night_mm.chunk({"time": 1, "latitude": -1, "longitude": -1})  # a map a chunk
    maps.to_zarr(zarr_path, mode="w", zarr_format=3, consolidated=False)
    mycatalog.add(zarr_path, title="Rain over Bengaluru, night of 4-5 Sep 2022 (IMERG)",
                  datetime="2022-09-04T13:30:00", bbox=[77.15, 12.45, 78.15, 13.45])

    files = sorted(p.relative_to(zarr_path) for p in zarr_path.rglob("*") if p.is_file())
    [f.as_posix() for f in files[:8]]
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Each file under `rain_mm/c/` is one chunk: one half-hour map. `zarr.json` is the description.

    ## Try it

    1. Change the place in `at_lake` to your own neighbourhood and the dates to this year's monsoon.
    2. In the timing cell, ask for ten years at one place instead of one. How long does each layout
       take now? (Start with the time-series store.)
    3. Rechunk `night_mm` with `{"time": -1, "latitude": 1, "longitude": 1}` and save it again. How
       many files do you get, and which question is that layout good for?
    """)
    return


if __name__ == "__main__":
    app.run()
