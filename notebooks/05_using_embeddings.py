import marimo

__generated_with = "0.25.1"
app = marimo.App(
    width="compact",
    app_title="5 · Using embeddings",
    css_file="theme.css",
)


@app.cell(hide_code=True)
def _():
    import marimo as mo
    import numpy as np
    import pandas as pd

    from cngeo import build, charts, datapack, mycatalog
    from cngeo import embeddings as em
    from cngeo.build import CLASS_NAMES, classes
    from cngeo.config import LAKE

    return CLASS_NAMES, LAKE, build, charts, classes, datapack, em, mo, mycatalog, np, pd


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    <div class="kicker">Lesson 5 · 14:45–15:25</div>

    # What changed around the lake since 2017?

    <div class="lead">Embeddings earn their keep when we ask questions with them. Three questions,
    each a few lines of scikit-learn or numpy: which places belong together, what each place is,
    and where things changed.</div>

    ## Groups without labels

    k-means sorts the pixels into k groups whose vectors are close. It learns from every 20th pixel
    and then labels them all.
    """)
    return


@app.cell
def _(datapack, em):
    from sklearn.cluster import KMeans

    aef = datapack.alphaearth(2025)
    pixels = em.table(aef)                     # one row per pixel: 350,000 x 64
    kmeans = KMeans(n_clusters=6, n_init="auto", random_state=0)
    kmeans.fit(pixels[::20])                   # learn from every 20th pixel
    groups = kmeans.predict(pixels).reshape(aef.shape[1:])
    f"{len(pixels):,} pixels in {kmeans.n_clusters} groups"
    return KMeans, aef


@app.cell(hide_code=True)
def _(KMeans, aef, charts, datapack, em, np):
    _px = em.pixel_table(datapack.sentinel2(2025), {}, f=5)
    _v = em.table(em.coarsen(aef, 5))
    for _k in range(2, 11):
        _px[f"k{_k}"] = KMeans(n_clusters=_k, n_init="auto", random_state=0).fit_predict(_v).astype(str)
    _colors = ["#1f5f74", "#c9a227", "#8c5a4a", "#4f7d4a", "#9b6b9e", "#d98b5f", "#6d98a3", "#e3c9a1", "#3b211b", "#b9b2a5"]
    charts.category_map(_px, {"groups": "k"}, _colors, slider=("number of groups ", list(range(2, 11))), cell=4.4,
                        title="Groups the model's numbers fall into", subtitle="Slide to change k", legend="group")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    With two groups you get roughly "city" and "not city". As you add groups they start to follow
    the lake, the airport's grass, different kinds of built-up land and the remaining fields.
    Nobody gave the model a single label. But a group has no name: you have to look and name it yourself.

    ## A few labels go a long way

    Now suppose we can afford to label only a handful of pixels. As labels we borrow ESA's
    WorldCover map of 2021 (trees, grass and crops, built-up, bare, water), take 20 pixels of each
    class, train a logistic regression on their 2021 embeddings, and let it map everything else.
    """)
    return


@app.cell
def _(CLASS_NAMES, classes, datapack, em, np):
    from sklearn.linear_model import LogisticRegression

    labels = classes(datapack.raster("worldcover")[0]).ravel()   # 0-4; -1 = other
    x = em.table(datapack.alphaearth(2021))

    rng = np.random.default_rng(0)
    train = np.concatenate([rng.choice(np.flatnonzero(labels == k), 20, replace=False)
                            for k in range(len(CLASS_NAMES))])     # 20 pixels a class
    model = LogisticRegression(max_iter=2000).fit(x[train], labels[train])
    predicted = model.predict(x)

    agree = (predicted == labels)[labels >= 0].mean()
    f"{len(train)} labelled pixels: a map that agrees with WorldCover on {agree:.0%}"
    return labels, predicted


@app.cell(hide_code=True)
def _(CLASS_NAMES, charts, datapack, labels, predicted):
    _shape = datapack.raster("worldcover").shape[1:]
    charts.pictures({"WorldCover 2021": charts.paint(labels.reshape(_shape), CLASS_NAMES),
                     "Our map, from 100 labels": charts.paint(predicted.reshape(_shape), CLASS_NAMES)})
    return


@app.cell(hide_code=True)
def _(charts, datapack):
    charts.label_curve(datapack.table("label_curve"), title="How many labels do you need?",
                       subtitle="Agreement with WorldCover, averaged over 10 random draws. Hover the legend.")
    return


@app.cell(hide_code=True)
def _(build):
    build.recipe("label_curve")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    In both maps brown is built-up, yellow grass and crops, green trees, blue water and beige bare
    ground. Ours is blotchier but gets the big picture right from 100 clicks' worth of labels.

    The curve repeats this for different numbers of labels. The grey line is the same classifier
    given the raw Sentinel-2 colours instead of embeddings.
    With embeddings, ten labels per class do about as well as 200 labels on raw colours. That is the
    point of a foundation model: it did the expensive learning once, so your map needs only a few
    labels. Take the exact numbers with salt: WorldCover has its own errors, and pixels picked at
    random from one small area flatter any method.

    ## What changed since 2017?

    If a square of ground stays the same, its vector stays put; if it changes, the vector swings
    away. One minus the dot product between two years is a change map, in one line.
    """)
    return


@app.cell
def _(charts, datapack):
    before, after = datapack.alphaearth(2017), datapack.alphaearth(2025)
    change = 1 - (before * after).sum(axis=0)   # 0: same as in 2017; higher: changed
    charts.image(change, cmap=charts.CHANGE, vmin=0, vmax=0.6,
                 label="change from 2017 to 2025")
    return (change,)


@app.cell(hide_code=True)
def _(LAKE, charts, datapack, em):
    _px = datapack.table("aef_change")
    _px = _px.assign(id=range(len(_px)))
    _r, _c = em.pixel(LAKE)
    _start = int(_px.id[(_px.r == _r // 5) & (_px.c == _c // 5)].iloc[0])
    charts.change_explorer(_px, list(range(2017, 2026)), start=_start, cell=3,
                           title="Year by year", subtitle="Slide through the years; hover a square to see its whole path")
    return


@app.cell(hide_code=True)
def _(build):
    build.recipe("aef_change")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    The lake dominates: its surface went from a mat of weeds to a dug-out bed and open water. The
    small bright patches around it are buildings that went up and plots that were cleared. Hover
    one and follow it through the years to see when it happened.

    Two cautions. First, slide to 2022 and 2023: almost every square moves a little, then comes back.
    The ground didn't change; most likely the model's inputs did (one of the two Sentinel-1 radar
    satellites failed at the end of 2021). Always compare a change with places you know stayed
    the same.
    Second, each vector summarises a whole year, so a flood that lasted a week barely registers.

    ## Put it in the catalog

    Last, our map of change and the embeddings themselves go into the catalog. For the embeddings
    we add the fields of the draft [embeddings convention for STAC](https://geoembeddings.org), so a
    reader knows what the 64 bands are and how to turn the integers back into numbers.
    """)
    return


@app.cell
def _(change, datapack, mycatalog):
    change_path = mycatalog.DATA / "change_2017_2025.tif"
    mycatalog.write_cog(change_path, change.astype("float32"))
    mycatalog.add(change_path, datetime="2025-01-01",
                  title="Change of each 10 m square, 2017 to 2025 (AlphaEarth)")

    embeddings_path = mycatalog.DATA / "alphaearth_2025.tif"
    embeddings_path.write_bytes(datapack.fetch("aef", 2025).read_bytes())
    embeddings_item = mycatalog.add(
        embeddings_path, datetime="2025-01-01",
        title="AlphaEarth Foundations embeddings, 2025 (Google DeepMind)",
        **{"emb:type": "pixel", "emb:dimensions": 64, "emb:temporal_resolution": "annual",
           "emb:quantization": {"method": "signed_square", "nodata": -128,
                                "quantized_dtype": "int8"}})
    mycatalog.items()
    return (embeddings_item,)


@app.cell
def _(embeddings_item, mo, mycatalog):
    # the whole folder again; the embeddings item is open, with its emb: fields
    folder = mo.ui.file_browser(mycatalog.FOLDER, value=embeddings_item.get_self_href(),
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
    That folder is a complete, small, cloud-native dataset about one lake. In the last lesson we
    open it all again, starting from `catalog.json`.

    ## What embeddings can't do

    - **One summary per year.** No dates within the year, and short events wash out.
    - **10 m squares.** A single rooftop or a narrow drain is below what they can see.
    - **Inputs change.** Satellites fail and are replaced, so the "no change" level drifts from
      year to year.
    - **Learned mostly elsewhere.** AlphaEarth's training labels were mostly from the United States.
      Check results against what you know on the ground.
    - **Read the licences.** AlphaEarth's embeddings are CC BY 4.0 but the model is closed;
      TESSERA's embeddings and model are open.

    ## Try it

    1. Change `n_clusters` and `pixels[::20]` in the k-means cell. Does learning from every 5th
       pixel change the groups?
    2. Give the classifier 5, then 100 labels per class. Does it match the curve above?
    3. Make the change map with TESSERA for 2018 and 2025 (`em.tessera(2018)`, normalised with
       `em.unit`). Does it agree with AlphaEarth about where things changed?
    """)
    return


if __name__ == "__main__":
    app.run()
