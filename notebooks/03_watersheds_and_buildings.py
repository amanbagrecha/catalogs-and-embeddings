import marimo

__generated_with = "0.25.1"
app = marimo.App(
    width="compact",
    app_title="3 · Watersheds and buildings",
    css_file="theme.css",
)


@app.cell(hide_code=True)
def _():
    import marimo as mo

    from cngeo import charts, datapack, mycatalog
    from cngeo.config import STUDY_LONLAT

    return STUDY_LONLAT, charts, datapack, mo, mycatalog


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    <div class="kicker">Lesson 3 · 12:35–13:00</div>

    # What drains into the lake, and what was built around it?

    <div class="lead">The rain of that night did not fall only on the lake. It fell on every street,
    roof and field that drains into it, and ran downhill. To see that we need shapes: the outline of
    each watershed and water body, and the footprint of each building.</div>

    Maps made of shapes are called **vector** data: points, lines and polygons, each with a row of
    attributes. We take them from two catalogs, one built in India for India and one built for the
    whole world.

    ## An Indian catalog: CoRE Stack

    [CoRE Stack](https://core-stack.org) (Commoning for Resilience and Equality) is an open platform
    built with IIT Delhi and community organisations to help villages plan their land and water. It
    publishes its layers for each tehsil (block) as a STAC catalog, hosted in Mumbai. Here is the
    collection for Bengaluru South, which covers the lake.
    """)
    return


@app.cell
def _():
    import pystac

    CORE = ("https://spatio-temporal-asset-catalog.s3.ap-south-1.amazonaws.com/"
            "CorestackCatalogs_merged_collection/tehsil_wise/")
    tehsil = pystac.Collection.from_file(
        CORE + "karnataka/bengaluru_urban/bengaluru_south/collection.json")
    prefix = "karnataka_bengaluru_urban_bengaluru_south_"
    links = {link.href.split("/")[-1][len(prefix):-5]: link
             for link in tehsil.get_item_links()}

    def layer(name):
        """The download link of one CoRE Stack layer."""
        item = pystac.Item.from_file(links[name].get_absolute_href())
        return item.assets["data"].href

    f"{len(links)} layers, for example: " + ", ".join(list(links)[40:52])
    return (layer,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    We want two of them: the **micro-watersheds** (the small basins that drain to one point) and the
    **surface water bodies**, which records how much of each lake held water in every year since
    2017.
    """)
    return


@app.cell
def _(STUDY_LONLAT, layer):
    import geopandas as gpd
    from shapely.geometry import box

    study = box(*STUDY_LONLAT)
    water = gpd.read_file(layer("surface_water_bodies_vector"))       # lakes and ponds
    sheds = gpd.read_file(layer("water_balance_fortnightly_vector"))  # micro-watersheds
    water, sheds = water[water.intersects(study)], sheds[sheds.intersects(study)]
    f"{len(water)} water bodies and {len(sheds)} micro-watersheds in our study area"
    return gpd, sheds, water


@app.cell(hide_code=True)
def _(STUDY_LONLAT, charts, datapack):
    from shapely.geometry import box as _box

    _water = datapack.table("waterbodies").clip(_box(*STUDY_LONLAT))
    _lake = _water.loc[_water.to_crs(32643).area.idxmax(), "UID"]
    charts.waterbody_explorer(
        _water, datapack.table("watersheds").clip(_box(*STUDY_LONLAT)), _lake,
        title="Water bodies on their watersheds",
        subtitle="Click a lake or pond: the bars show how much of it held water each year (CoRE Stack)")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Bellandur is selected. By CoRE Stack's count about 120 hectares held water in 2017–18; in 2020–21
    only 7, when the lake was drained to dig out decades of sludge; by 2022–23 it was back above 80.
    The same layer says the lake's catchment covers about 144 km²: most of south-east Bengaluru.

    Notice how the data arrived, though. The catalog is proper STAC, which made it easy to find. But
    the files behind it come from a map server as GeoJSON, a text format with no index, so we
    downloaded every water body in the tehsil (about 2,000) to keep 115. At the scale of one tehsil
    that is fine. For a whole country we need a format we can query.

    ## Buildings: GeoParquet

    [Overture Maps](https://overturemaps.org) publishes 2.5 billion building footprints for the
    whole world as **GeoParquet**. Parquet stores a table column by column and splits it into
    **row groups** of a few thousand rows, writing the smallest and largest value of every column in
    each group into the file's footer. GeoParquet adds a bounding box column, so the footer knows
    roughly where each row group lies. Overture also publishes a STAC index of its files, which is
    itself a GeoParquet table. DuckDB can query both straight from the cloud.
    """)
    return


@app.cell
def _(gpd):
    import json
    import urllib.request

    import duckdb

    db = duckdb.connect()
    db.sql("INSTALL spatial; LOAD spatial; INSTALL httpfs; LOAD httpfs;")
    overture = "https://stac.overturemaps.org"
    release = json.load(urllib.request.urlopen(f"{overture}/catalog.json"))["latest"]

    BOX = (77.675, 12.915, 77.705, 12.945)              # 3 x 3 km east of the lake
    w, s, e, n = BOX
    in_box = (f"bbox.xmin < {e} AND bbox.xmax > {w} "
              f"AND bbox.ymin < {n} AND bbox.ymax > {s}")

    # 1. the catalog (one row per file) says which files can hold our box
    index = f"{overture}/{release}/collections.parquet"
    files = db.sql(f"SELECT assets.aws.href FROM '{index}' "
                   f"WHERE collection = 'building' AND {in_box}").fetchall()
    files = [row[0] for row in files]

    # 2. inside those files, DuckDB reads the footers and skips row groups outside it
    query = f"SELECT id, height, geometry FROM read_parquet({files}) WHERE {in_box}"
    buildings = gpd.GeoDataFrame.from_arrow(db.sql(query).arrow())
    f"{len(buildings):,} buildings from Overture release {release}"
    return BOX, buildings


@app.cell(hide_code=True)
def _(BOX, buildings, charts, datapack):
    (charts.buildings_map(buildings, title="Every building in the box", subtitle="Overture Maps footprints; hover one")
     & charts.row_groups(datapack.table("row_groups"), BOX, title="What DuckDB actually read",
                         subtitle="The file's 128 row groups as rectangles. Black: our box. Blue: the row groups it overlaps."))
    return


@app.cell(hide_code=True)
def _(BOX, datapack, mo):
    _rg = datapack.table("row_groups")
    _hit = (_rg.xmin <= BOX[2]) & (_rg.xmax >= BOX[0]) & (_rg.ymin <= BOX[3]) & (_rg.ymax >= BOX[1])
    mo.md(f"""
    The file holds {_rg.rows.sum() / 1e6:.0f} million buildings of this part of India in
    {len(_rg)} row groups, about {_rg.MB.sum():.0f} MB. DuckDB read its footer, saw that only
    {int(_hit.sum())} row groups overlap our box, and fetched just those, about
    {_rg.MB[_hit].sum():.0f} MB. The rows are sorted along a space-filling curve, so buildings that
    are near each other on the ground sit near each other in the file; that is what keeps the
    row groups' rectangles small.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Store your own

    We save the watersheds, water bodies and buildings as GeoParquet: sorted along a space-filling
    curve, with a bounding box column and small row groups, the same recipe that made the Overture
    query fast. Then they go into the catalog.
    """)
    return


@app.cell
def _(buildings, mycatalog, sheds, water):
    def save(frame, name, title):
        frame = frame.iloc[frame.hilbert_distance().argsort()]  # neighbours stay together
        path = mycatalog.DATA / f"{name}.parquet"
        frame.to_parquet(path, write_covering_bbox=True, row_group_size=2000)
        mycatalog.add(path, title=title, datetime="2025-01-01")

    save(water, "waterbodies", "Water bodies and their water area per year (CoRE Stack)")
    save(sheds, "watersheds", "Micro-watersheds around the lake (CoRE Stack)")
    save(buildings, "buildings", "Building footprints east of the lake (Overture Maps)")
    mycatalog.items()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Try it

    1. Ask the Overture index for `collection = 'place'` instead of `'building'`: shops, schools and
       temples. Which categories are most common in the box?
    2. Pick another CoRE Stack layer from the list (try `drainage_lines_vector` or
       `land_use_land_cover_vector`) and draw it with `.plot()`.
    3. Change `BOX` to a 1 × 1 km square around a place you know. How many buildings does it hold,
       and how long does the query take?
    """)
    return


if __name__ == "__main__":
    app.run()
