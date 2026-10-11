"""Charts for the lessons: one quiet look, with the interactivity inside the chart.

Every chart is plain Altair (Vega-Lite). Sliders, toggles, hovering and clicking
run in the browser, so a chart behaves the same inside marimo and on the static
course website made by ``cngeo site``.
"""

from __future__ import annotations

import base64
import io
import json
import warnings

import altair as alt
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Look
# ---------------------------------------------------------------------------
INK, MUTED, RULE, PAPER = "#1d1b16", "#6b665c", "#e3ded2", "#faf8f3"
ACCENT = "#1f5f74"
FONT = "IBM Plex Sans, system-ui, sans-serif"

BLUES = ["#f6f3ea", "#d6e3e2", "#9fc2c6", "#5f97a5", "#2f6b80", "#163f4f"]
SIMILAR = ["#f6f3ea", "#efe2c4", "#d9b77d", "#b47a3c", "#7a3f1d"]
CHANGE = ["#f6f3ea", "#f1d9a8", "#e3a15a", "#c4562f", "#7d2a2a"]
CLASSES = {"trees": "#4f7d4a", "grass & crops": "#c9b45d", "built-up": "#8c5a4a", "bare": "#d8cbb3", "water": "#3d7ea6"}


def _theme():
    axis = dict(labelColor=MUTED, titleColor=MUTED, labelFontSize=11, titleFontSize=11, titleFontWeight=500,
                gridColor=RULE, domainColor="#cfc8b8", tickColor="#cfc8b8", labelFont=FONT, titleFont=FONT)
    return {"config": {
        "background": "transparent",
        "font": FONT,
        "view": {"stroke": None},
        "title": dict(font=FONT, fontSize=14, fontWeight=600, color=INK, anchor="start", offset=12,
                      subtitleFont=FONT, subtitleFontSize=12, subtitleColor=MUTED),
        "axis": axis,
        "axisY": {"domain": False, "ticks": False},
        "legend": dict(labelColor=MUTED, titleColor=INK, labelFontSize=11, titleFontSize=11, titleFontWeight=500,
                       labelFont=FONT, titleFont=FONT, orient="bottom", direction="horizontal", symbolType="square"),
        "text": {"font": FONT, "color": INK},
        "range": {"category": list(CLASSES.values())},
        "mark": {"color": ACCENT},
    }}


alt.theme.register("cngeo", enable=True)(_theme)
alt.data_transformers.disable_max_rows()  # pixel maps have ~10 000 squares; fine in a browser
warnings.filterwarnings("ignore", message="Automatically deduplicated selection parameter")


def _when(param: str, options: dict[str, str]) -> str:
    """Vega expression picking ``datum[column]`` for the option chosen in ``param``."""
    parts = [f"{param} == {json.dumps(label)} ? datum[{json.dumps(col)}]" for label, col in options.items()]
    return " : ".join(parts) + " : null"


def _switch(name: str, options: list, label: str = ""):
    return alt.param(name=name, value=options[0], bind=alt.binding_radio(options=options, name=label))


# ---------------------------------------------------------------------------
# Pictures
# ---------------------------------------------------------------------------
def img_uri(rgb: np.ndarray, quality: int = 85) -> str:
    """An (H, W, 3) array, floats 0-1 or uint8, as a WebP data URI (photos are ~10x smaller than PNG)."""
    from PIL import Image

    a = np.asarray(rgb)
    if a.dtype != np.uint8:
        a = (np.clip(np.nan_to_num(a), 0, 1) * 255).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(a).save(buf, format="WEBP", quality=quality, method=6)
    return "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()


def stretch(rgb: np.ndarray, lo: float = 2, hi: float = 98) -> np.ndarray:
    """Scale each band of an (H, W, 3) array between its lo and hi percentiles, for display."""
    out = np.empty(rgb.shape, dtype="float32")
    for i in range(rgb.shape[-1]):
        a, b = np.nanpercentile(rgb[..., i], [lo, hi])
        out[..., i] = (rgb[..., i] - a) / (b - a)
    return np.clip(out, 0, 1)


def picture(images: dict[str, np.ndarray], width: int = 520, title: str = "", subtitle: str = ""):
    """One or more same-sized RGB pictures; with several you get buttons to flip between them."""
    labels = list(images)
    h, w = next(iter(images.values())).shape[:2]
    height = round(width * h / w)
    data = pd.DataFrame({"label": labels, "url": [img_uri(images[k]) for k in labels]})
    chart = alt.Chart(data, title=alt.Title(title, subtitle=subtitle) if title else alt.Undefined)
    if len(labels) > 1:
        chart = chart.add_params(_switch("picture", labels)).transform_filter("datum.label == picture")
    return (
        chart.mark_image(width=width, height=height, align="left", baseline="top")
        .encode(x=alt.value(0), y=alt.value(0), url="url:N")
        .properties(width=width, height=height)
    )


def swipe(left: np.ndarray, right: np.ndarray, width: int = 640, title: str = "", subtitle: str = ""):
    """Two same-sized pictures split by a line; the slider moves the line.

    ``left`` is cut into thin vertical strips laid over ``right``; strips left of the line are shown.
    """
    h, w = left.shape[:2]
    height = round(width * h / w)
    edges = np.linspace(0, w, w // 10 + 1).round().astype(int)          # strips ~10 pixels wide
    strips = pd.DataFrame({"x": edges[:-1] / w * width,
                           "url": [img_uri(left[:, a:b]) for a, b in zip(edges[:-1], edges[1:])]})
    step = width / (len(edges) - 1)
    split = alt.param(name="split", value=50, bind=alt.binding_range(min=0, max=100, step=1, name="move the line "))
    under = alt.Chart(pd.DataFrame({"url": [img_uri(right)]})).mark_image(
        width=width, height=height, align="left", baseline="top").encode(x=alt.value(0), y=alt.value(0), url="url:N")
    over = alt.Chart(strips).transform_filter(f"datum.x < split * {width} / 100").mark_image(
        width=step + 1.5, height=height, align="left", baseline="top"          # overlap: no hairline seams
    ).encode(x=alt.X("x:Q", scale=None), y=alt.value(0), url="url:N")
    line = alt.Chart(pd.DataFrame({"k": [0]})).transform_calculate(at=f"split * {width} / 100").mark_rule(
        color="#ffffff", strokeWidth=2).encode(x=alt.X("at:Q", scale=None))
    chart = alt.layer(under, over, line).add_params(split).properties(width=width, height=height)
    return chart.properties(title=alt.Title(title, subtitle=subtitle)) if title else chart


def spectrum_explorer(refl: np.ndarray, nm: dict[str, int], kinds: dict[str, np.ndarray], start: tuple[int, int],
                      f: int = 10, cell: float = 4.5, rgb: tuple[int, int, int] = (2, 1, 0), title: str = "",
                      subtitle: str = ""):
    """Point at the picture (left): the line (right) shows how much sunlight that square reflects in each band.

    ``refl`` is (bands, rows, cols) reflectance 0-1, one band per entry of ``nm`` (name -> centre
    wavelength in nanometres). ``kinds`` maps a name ("water") to a (rows, cols) mask; the median
    spectrum of those pixels is drawn faintly for comparison. ``start`` is the (row, col) shown first.
    """
    n, h, w = refl.shape
    H, W = h // f, w // f
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        sq = np.nanmean(refl[:, : H * f, : W * f].reshape(n, H, f, W, f), axis=(2, 4))  # f x f squares
    colour = (stretch(np.dstack([sq[i] for i in rgb])) * 255).astype(int).reshape(-1, 3)
    r, c = np.divmod(np.arange(H * W), W)
    pct = np.round(np.nan_to_num(sq.reshape(n, -1).T) * 1000).astype(int)        # percent x 10
    px = pd.DataFrame({"id": np.arange(H * W), "c": c, "r": r,
                       "rgb": [f"#{a:02x}{b:02x}{d:02x}" for a, b, d in colour],
                       "s": [",".join(map(str, row)) for row in pct]})
    top = float(np.ceil(np.nanpercentile(sq, 99.5) * 10) * 10)
    names, waves = list(nm), list(nm.values())

    hov = alt.selection_point(name="hov", on="pointerover", fields=["id"], clear=False,
                              value=[{"id": int(start[0] // f * W + start[1] // f)}])
    enc, size = _grid(px, cell)
    photo = _squares(alt.Chart(px)).mark_rect().encode(
        **enc, color=alt.Color("rgb:N", scale=None),
        stroke=alt.when(hov).then(alt.value("#e3a15a")).otherwise(alt.value(None)),   # shows on water and roofs
        strokeWidth=alt.when(hov).then(alt.value(2)).otherwise(alt.value(0)),
    ).add_params(hov).properties(**size, title=alt.Title("Point at a square", subtitle=f"{f * 10} m squares"))

    x = alt.X("nm:Q", title="wavelength (nanometres)", scale=alt.Scale(domain=[400, 2300], nice=False),
              axis=alt.Axis(values=[400, 700, 1000, 1300, 1600, 1900, 2200], grid=False))
    y = alt.Y("pct:Q", title="% of sunlight reflected", scale=alt.Scale(domain=[0, top], clamp=True))
    regions = pd.DataFrame({"nm": [400, 700, 1300], "nm2": [700, 1300, 2300],
                            "label": ["visible", "near-infrared", "shortwave infrared"]})
    rainbow = alt.LinearGradient(gradient="linear", x1=0, x2=1, y1=0, y2=0, stops=[
        alt.GradientStop(offset=o, color=col) for o, col in
        [(0, "#7b4fc9"), (0.2, "#3f6fd8"), (0.4, "#3fa66b"), (0.6, "#e3d24a"), (0.8, "#e88a3a"), (1, "#d2413a")]])
    band_regions = alt.Chart(regions).encode(x=x, x2="nm2:Q")
    visible = band_regions.transform_filter("datum.label == 'visible'").mark_rect(color=rainbow, opacity=0.18)
    invisible = band_regions.transform_filter("datum.label != 'visible'").mark_rect(color=RULE, opacity=0.35)
    labels = alt.Chart(regions).transform_calculate(mid="(datum.nm + datum.nm2) / 2").mark_text(
        baseline="top", fontSize=11, color=MUTED, dy=4).encode(x="mid:Q", y=alt.value(0), text="label:N")
    typical = pd.DataFrame([{"kind": k, "nm": wl, "pct": float(np.nanmedian(refl[i][m])) * 100}
                            for k, m in kinds.items() for i, wl in enumerate(waves)])
    faint = alt.Chart(typical).mark_line(strokeWidth=1.5, strokeDash=[4, 3], opacity=0.8).encode(
        x=x, y=y, color=alt.Color("kind:N", title=None, scale=alt.Scale(domain=list(kinds), range=[
            {"water": CLASSES["water"], "trees": CLASSES["trees"], "buildings": CLASSES["built-up"]}.get(k, MUTED)
            for k in kinds])))
    picked = (
        alt.Chart(px).transform_filter(hov).transform_calculate(v="split(datum.s, ',')")
        .transform_flatten(["v"]).transform_window(i="row_number()")
        .transform_calculate(pct="datum.v / 10", nm=f"{json.dumps(waves)}[datum.i - 1]",
                             band=f"{json.dumps(names)}[datum.i - 1]")
    )
    line = picked.mark_line(color=INK, strokeWidth=2.2).encode(x=x, y=y)
    dots = picked.mark_point(color=INK, filled=True, size=40).encode(
        x=x, y=y, tooltip=[alt.Tooltip("band:N"), alt.Tooltip("nm:Q", title="nanometres"),
                           alt.Tooltip("pct:Q", format=".1f", title="% reflected")])
    spectrum = alt.layer(visible, invisible, labels, faint, line, dots).properties(
        width=290, height=size["height"],
        title=alt.Title("How much sunlight it reflects", subtitle="dark line: that square · dashed: typical"))
    chart = alt.hconcat(photo, spectrum, spacing=24)
    return chart.properties(title=alt.Title(title, subtitle=subtitle)) if title else chart


# ---------------------------------------------------------------------------
# Pixel maps: a raster as a grid of small squares (one row per pixel)
# ---------------------------------------------------------------------------
def _grid(px: pd.DataFrame, cell: float):
    """Encodings that place each pixel at its column/row (row 0 = north), and the chart size."""
    c1, r1 = int(px.c.max()) + 1, int(px.r.max()) + 1
    enc = dict(x=alt.X("c:Q", scale=alt.Scale(domain=[0, c1], nice=False, zero=False), axis=None), x2="c2:Q",
               y=alt.Y("r:Q", scale=alt.Scale(domain=[r1, 0], nice=False, zero=False), axis=None), y2="r2:Q")
    return enc, dict(width=float(c1 * cell), height=float(r1 * cell))


def _squares(chart: alt.Chart) -> alt.Chart:
    return chart.transform_calculate(c2="datum.c + 1.12", r2="datum.r + 1.12")  # overlap: no hairline seams


def _pack(df: pd.DataFrame, prefix: str, n: int) -> pd.DataFrame:
    """Replace columns prefix0 … prefix{n-1} (integers) by one comma-separated string column ``prefix``.

    A web page stores a table as JSON with every column name repeated on every row; one short string
    per row instead of 64 named numbers makes the pages several times lighter.
    """
    cols = [f"{prefix}{i}" for i in range(n)]
    out = df.drop(columns=cols)
    out[prefix] = [",".join(map(str, row)) for row in df[cols].to_numpy(int)]
    return out


def _unpack(chart: alt.Chart, *prefixes: str) -> alt.Chart:
    """Vega side of ``_pack``: ``datum.{prefix}v`` becomes the array of numbers (as strings)."""
    return chart.transform_calculate(**{f"{p}v": f"split(datum.{p}, ',')" for p in prefixes})


def _dot(prefix: str, dims: int, other: str = "datum.q") -> str:
    # strings times strings are numbers in JavaScript, so no conversion is needed
    return " + ".join(f"datum.{prefix}v[{i}] * {other}.{prefix}v[{i}]" for i in range(dims))


def similarity_explorer(px: pd.DataFrame, models: dict[str, str], start: int, cell: float = 3.6,
                        dims: int = 16, title: str = "", subtitle: str = ""):
    """Click a spot on the picture (left); every pixel on the right is coloured by how similar it is.

    ``px`` has one row per pixel: ``id, c, r, rgb`` (hex colour of the picture) and, for each model
    prefix in ``models`` (e.g. {"AlphaEarth": "a", "TESSERA": "t"}), unit-length vectors squeezed to
    ``dims`` numbers and stored as integers x100 (``a0 … a15``).
    """
    pick = alt.selection_point(name="pick", on="click", fields=["id"], value=[{"id": int(start)}], clear=False)
    data = px.assign(k=1)
    for p in models.values():
        data = _pack(data, p, dims)
    enc, size = _grid(px, cell)
    base = _unpack(_squares(alt.Chart(data)), *models.values()).encode(**enc)
    photo = base.mark_rect().encode(
        color=alt.Color("rgb:N", scale=None),
        stroke=alt.when(pick).then(alt.value(INK)).otherwise(alt.value(None)),
        strokeWidth=alt.when(pick).then(alt.value(2)).otherwise(alt.value(0)),
    ).add_params(pick).properties(**size, title=alt.Title("Click a spot", subtitle="Sentinel-2, true colour"))
    params, expr = [], {}
    for name, p in models.items():
        expr[name] = f"({_dot(p, dims)}) / 10000"
    if len(models) > 1:
        params.append(_switch("model", list(models), "model "))
        sim = " : ".join(f"model == {json.dumps(n)} ? {e}" for n, e in expr.items()) + " : 0"
    else:
        sim = next(iter(expr.values()))
    heat = (
        base.transform_lookup(lookup="k", from_=alt.LookupSelection(key="k", param="pick"), as_="q")
        .transform_calculate(sim=f"datum.q ? {sim} : 0")
        .mark_rect()
        .encode(color=alt.Color("sim:Q", scale=alt.Scale(range=SIMILAR, domain=[0.3, 1], clamp=True),
                                legend=alt.Legend(title="similarity to the clicked spot", gradientLength=200,
                                                  gradientThickness=8)),
                tooltip=[alt.Tooltip("sim:Q", format=".2f", title="similarity")])
        .add_params(*params)
        .properties(**size, title=alt.Title("Pixels that look alike", subtitle="cosine similarity of the embeddings"))
    )
    chart = alt.hconcat(photo, heat, spacing=18)
    if title:
        chart = chart.properties(title=alt.Title(title, subtitle=subtitle))
    return chart


def embedding_barcode(px: pd.DataFrame, prefix: str = "a", dims: int = 64, start: int = 0, cell: float = 3.6,
                      title: str = "", subtitle: str = ""):
    """Hover over the picture: the bars show the hovered pixel's embedding, number by number."""
    hov = alt.selection_point(name="hov", on="pointerover", fields=["id"], value=[{"id": int(start)}], clear=False)
    enc, size = _grid(px, cell)
    data = _pack(px, prefix, dims)
    photo = _squares(alt.Chart(data)).mark_rect().encode(
        **enc, color=alt.Color("rgb:N", scale=None),
        stroke=alt.when(hov).then(alt.value(INK)).otherwise(alt.value(None)),
        strokeWidth=alt.when(hov).then(alt.value(2)).otherwise(alt.value(0)),
    ).add_params(hov).properties(**size)
    bars = (
        alt.Chart(data).transform_filter(hov).transform_calculate(v=f"split(datum.{prefix}, ',')")
        .transform_flatten(["v"]).transform_window(n="row_number()")
        .transform_calculate(n="datum.n - 1", v="datum.v / 100")
        .mark_bar(width=4)
        .encode(x=alt.X("n:Q", title="number in the embedding", scale=alt.Scale(domain=[-0.5, dims - 0.5], nice=False),
                        axis=alt.Axis(values=[0, 16, 32, 48, 63], grid=False)),
                y=alt.Y("v:Q", title=None, scale=alt.Scale(domain=[-0.5, 0.5], clamp=True)),
                color=alt.condition("datum.v > 0", alt.value(ACCENT), alt.value("#c9a27a")),
                tooltip=[alt.Tooltip("n:Q", title="number"), alt.Tooltip("v:Q", format=".2f", title="value")])
        .properties(width=300, height=size["height"] * 0.6)
    )
    chart = alt.hconcat(photo, bars, spacing=24)
    if title:
        chart = chart.properties(title=alt.Title(title, subtitle=subtitle))
    return chart


def category_map(px: pd.DataFrame, show: dict[str, str], palette: dict[str, str] | list[str], cell: float = 3.6,
                 slider: tuple[str, list] | None = None, title: str = "", subtitle: str = "", legend: str = ""):
    """A map of categories. ``show`` maps a button label to a column; ``slider`` = (label, values) picks
    the column ``f"{show[button]}{value}"`` with a slider instead (e.g. clusters for k = 2 … 10)."""
    enc, size = _grid(px, cell)
    params = []
    if slider:
        label, values = slider
        prefix = next(iter(show.values()))
        cols = [f"{prefix}{v}" for v in values]
        data = px[["c", "r"]].copy()
        data[prefix] = [",".join(map(str, row)) for row in px[cols].to_numpy()]
        chart = _squares(alt.Chart(data, title=alt.Title(title, subtitle=subtitle) if title else alt.Undefined))
        p = alt.param(name="n", value=values[len(values) // 2],
                      bind=alt.binding_range(min=min(values), max=max(values), step=values[1] - values[0], name=label))
        params.append(p)
        chart = chart.transform_calculate(value=f"split(datum.{prefix}, ',')[indexof({json.dumps(list(values))}, n)]")
    elif len(show) > 1:
        chart = _squares(alt.Chart(px, title=alt.Title(title, subtitle=subtitle) if title else alt.Undefined))
        params.append(_switch("layer", list(show)))
        chart = chart.transform_calculate(value=_when("layer", show))
    else:
        chart = _squares(alt.Chart(px, title=alt.Title(title, subtitle=subtitle) if title else alt.Undefined))
        chart = chart.transform_calculate(value=f"datum[{json.dumps(next(iter(show.values())))}]")
    if isinstance(palette, dict):
        scale = alt.Scale(domain=list(palette), range=list(palette.values()))
    else:
        scale = alt.Scale(range=palette)
    return (
        chart.mark_rect()
        .encode(**enc, color=alt.Color("value:N", scale=scale, legend=alt.Legend(title=legend or None, columns=6)),
                tooltip=[alt.Tooltip("value:N", title=legend or "class")])
        .add_params(*params)
        .properties(**size)
    )


def change_explorer(px: pd.DataFrame, years: list[int], start: int, cell: float = 3.6, title: str = "", subtitle: str = ""):
    """Slide through the years: each pixel is coloured by how far its embedding moved from the first year.

    ``px`` has ``id, c, r`` and ``s<year>`` = similarity (x100) between that year's embedding and the
    first year's. Hover a pixel to see its whole path on the right.
    """
    first = years[0]
    later = years[1:]
    yr = alt.param(name="year", value=later[-1],
                   bind=alt.binding_range(min=later[0], max=later[-1], step=1, name=f"compare {first} with "))
    hov = alt.selection_point(name="hov", on="pointerover", fields=["id"], value=[{"id": int(start)}], clear=False)
    enc, size = _grid(px, cell)
    data = px[["id", "c", "r"]].copy()
    data["s"] = [",".join(map(str, row)) for row in px[[f"s{y}" for y in later]].to_numpy(int)]
    m = (
        _squares(alt.Chart(data)).transform_calculate(change=f"1 - split(datum.s, ',')[year - {later[0]}] / 100")
        .mark_rect()
        .encode(**enc,
                color=alt.Color("change:Q", scale=alt.Scale(range=CHANGE, domain=[0, 0.8], clamp=True),
                                legend=alt.Legend(title=f"how much it changed since {first}", gradientLength=200,
                                                  gradientThickness=8)),
                stroke=alt.when(hov).then(alt.value(INK)).otherwise(alt.value(None)),
                strokeWidth=alt.when(hov).then(alt.value(2)).otherwise(alt.value(0)),
                tooltip=[alt.Tooltip("change:Q", format=".2f")])
        .add_params(yr, hov)
        .properties(**size)
    )
    path = (
        alt.Chart(data).transform_filter(hov).transform_calculate(v="split(datum.s, ',')")
        .transform_flatten(["v"]).transform_window(n="row_number()")
        .transform_calculate(year=f"datum.n - 1 + {later[0]}", change="1 - datum.v / 100")
    )
    line = path.mark_line(point=True, color=ACCENT).encode(
        x=alt.X("year:Q", title=None, axis=alt.Axis(format="d", values=later),
                scale=alt.Scale(domain=[later[0] - 0.4, later[-1] + 0.4], nice=False)),
        y=alt.Y("change:Q", title=f"change since {first}", scale=alt.Scale(domain=[0, 1])),
        tooltip=[alt.Tooltip("year:Q", format="d"), alt.Tooltip("change:Q", format=".2f")],
    )
    now = path.transform_filter("datum.year == year").mark_point(size=90, filled=True, color=INK).encode(x="year:Q", y="change:Q")
    chart = alt.hconcat(m, alt.layer(line, now).properties(width=260, height=size["height"] * 0.55), spacing=24)
    if title:
        chart = chart.properties(title=alt.Title(title, subtitle=subtitle))
    return chart


def label_curve(curve: pd.DataFrame, title: str = "", subtitle: str = ""):
    """Accuracy against the number of labelled examples per class, one line per input."""
    hl = alt.selection_point(name="hl", fields=["input"], bind="legend", on="pointerover", clear="pointerout")
    return (
        alt.Chart(curve, title=alt.Title(title, subtitle=subtitle) if title else alt.Undefined)
        .mark_line(point=True, strokeWidth=2.2)
        .encode(
            x=alt.X("labels:Q", scale=alt.Scale(type="log"), title="labelled examples per class",
                    axis=alt.Axis(values=sorted(curve["labels"].unique().tolist()), format="d", grid=False)),
            y=alt.Y("accuracy:Q", title="agreement with the reference map", axis=alt.Axis(format=".0%"),
                    scale=alt.Scale(zero=False)),
            color=alt.Color("input:N", scale=alt.Scale(domain=["AlphaEarth", "TESSERA", "Sentinel-2 bands"],
                                                       range=[ACCENT, "#b47a3c", "#9a948a"]),
                            legend=alt.Legend(title=None, orient="bottom")),
            opacity=alt.when(hl).then(alt.value(1)).otherwise(alt.value(0.35)),
            tooltip=["input:N", alt.Tooltip("labels:Q", title="labels per class"), alt.Tooltip("accuracy:Q", format=".1%")],
        )
        .add_params(hl)
        .properties(width=480, height=260)
    )


def image(arr, cmap="magma", vmin=None, vmax=None, label: str = "", width: float = 6.4, marker=None):
    """A single-band array as a plain picture (matplotlib), with a thin colour bar underneath."""
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap

    if isinstance(cmap, list):
        cmap = LinearSegmentedColormap.from_list("c", cmap)
    lo, hi = np.nanpercentile(arr, [2, 98])
    h, w = arr.shape
    fig, ax = plt.subplots(figsize=(width, width * h / w + 0.5))
    im = ax.imshow(arr, cmap=cmap, vmin=lo if vmin is None else vmin, vmax=hi if vmax is None else vmax,
                   interpolation="nearest")
    if marker is not None:
        ax.plot(marker[1], marker[0], "o", ms=9, mfc="none", mec=INK, mew=2)
    ax.set_axis_off()
    cb = fig.colorbar(im, ax=ax, orientation="horizontal", fraction=0.04, pad=0.02, aspect=50)
    cb.set_label(label, color=MUTED, fontsize=9)
    cb.outline.set_visible(False)
    cb.ax.tick_params(labelsize=8, colors=MUTED, length=0)
    fig.patch.set_alpha(0)
    plt.close(fig)
    return fig


def pictures(images: dict[str, np.ndarray], width: float = 9.6):
    """Several RGB pictures side by side (matplotlib), each with a small caption."""
    import matplotlib.pyplot as plt

    n = len(images)
    h, w = next(iter(images.values())).shape[:2]
    fig, axes = plt.subplots(1, n, figsize=(width, width / n * h / w + 0.4))
    for ax, (label, img) in zip(np.atleast_1d(axes), images.items()):
        ax.imshow(img, interpolation="nearest")
        ax.set_title(label, fontsize=10, color=INK, loc="left", fontfamily="sans-serif")
        ax.set_axis_off()
    fig.patch.set_alpha(0)
    fig.tight_layout()
    plt.close(fig)
    return fig


# ---------------------------------------------------------------------------
# Lesson 1: satellite images
# ---------------------------------------------------------------------------
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def tile_preview(rgb: np.ndarray, tile_bounds, box, size: int = 420, title: str = "", subtitle: str = ""):
    """A whole satellite tile (``rgb``: rows, cols, 3) with a white frame around ``box``.

    ``tile_bounds`` and ``box`` are (west, south, east, north) in the same coordinates (metres).
    """
    w, s, e, n = tile_bounds
    fx = lambda x: (x - w) / (e - w) * size
    fy = lambda y: (n - y) / (n - s) * size
    image = alt.Chart(pd.DataFrame({"url": [img_uri(rgb)]})).mark_image(
        width=size, height=size, align="left", baseline="top").encode(x=alt.value(0), y=alt.value(0), url="url:N")
    frame = alt.Chart(pd.DataFrame({"k": [0]})).mark_rect(fill=None, stroke="#ffffff", strokeWidth=2).encode(
        x=alt.value(fx(box[0])), x2=alt.value(fx(box[2])), y=alt.value(fy(box[3])), y2=alt.value(fy(box[1])))
    chart = alt.layer(image, frame).properties(width=size, height=size)
    return chart.properties(title=alt.Title(title, subtitle=subtitle)) if title else chart


def scene_calendar(scenes: pd.DataFrame, title: str = "", subtitle: str = ""):
    """How many clear Sentinel-2 pictures each month of each year has (``scenes``: date, cloud)."""
    d = scenes.assign(year=scenes.date.dt.year, month=scenes.date.dt.month - 1)
    d = d.groupby(["year", "month"]).agg(scenes=("cloud", "size"), clear=("cloud", lambda c: int((c < 10).sum()))).reset_index()
    d["mon"] = d.month.map(dict(enumerate(MONTHS)))
    return (
        alt.Chart(d, title=alt.Title(title, subtitle=subtitle) if title else alt.Undefined)
        .mark_rect(stroke=PAPER, strokeWidth=1.5)
        .encode(
            x=alt.X("mon:O", sort=MONTHS, title=None, axis=alt.Axis(labelAngle=0, domain=False, ticks=False)),
            y=alt.Y("year:O", title=None),
            color=alt.Color("clear:Q", scale=alt.Scale(range=BLUES), legend=alt.Legend(title="pictures with < 10 % cloud")),
            tooltip=[alt.Tooltip("mon:N", title="month"), alt.Tooltip("year:O"), alt.Tooltip("scenes:Q", title="pictures"),
                     alt.Tooltip("clear:Q", title="nearly cloud-free")],
        )
        .properties(width=480, height=24 * d.year.nunique())
    )


def cog_tiles(tiles: pd.DataFrame, title: str = "", subtitle: str = ""):
    """The internal tiles of one COG, at full detail and each zoomed-out copy (overview).

    ``tiles``: level, col, row, mb, hit (True where the tile overlaps what we asked for), size (pixels).
    Move the slider: the darker squares are the only bytes GDAL has to fetch.
    """
    levels = sorted(tiles.level.unique())
    lv = alt.param(name="level", value=0, bind=alt.binding_range(min=levels[0], max=levels[-1], step=1, name="zoom out "))
    data = tiles.assign(mb_hit=np.where(tiles.hit, tiles.mb, 0.0), hitn=tiles.hit.astype(int))
    base = alt.Chart(data).transform_filter("datum.level == level")
    tile = base.transform_calculate(c2="datum.col + 0.94", r2="datum.row + 0.94").mark_rect().encode(
        x=alt.X("col:Q", axis=None, scale=alt.Scale(domain=[0, int(tiles.col.max()) + 1], nice=False)), x2="c2:Q",
        y=alt.Y("row:Q", axis=None, scale=alt.Scale(domain=[int(tiles.row.max()) + 1, 0], nice=False)), y2="r2:Q",
        color=alt.condition("datum.hit", alt.value(ACCENT), alt.value("#e6e0d2")),
        tooltip=[alt.Tooltip("mb:Q", format=".2f", title="MB in this tile"), alt.Tooltip("size:N", title="pixels")],
    )
    agg = base.transform_aggregate(read="sum(mb_hit)", total="sum(mb)", n="sum(hitn)", tiles="count()", groupby=["level", "size"]) \
        .transform_calculate(text="'read ' + datum.n + ' of ' + datum.tiles + ' tiles: ' + format(datum.read, '.1f') + ' MB of ' "
                                  "+ format(datum.total, '.0f') + ' MB at this zoom (' + datum.size + ' pixels)'")
    label = agg.mark_text(align="left", baseline="top", dx=0, dy=6, fontSize=12, color=INK).encode(
        x=alt.value(0), y=alt.value(330), text="text:N")
    chart = alt.layer(tile, label).add_params(lv).properties(width=330, height=330)
    return chart.properties(title=alt.Title(title, subtitle=subtitle)) if title else chart


# ---------------------------------------------------------------------------
# Lesson 2: weather grids
# ---------------------------------------------------------------------------
def rain_night(s: pd.DataFrame, title: str = "", subtitle: str = ""):
    """Rain over the lake every half hour (``s``: time, mm). Drag across the bars to add up a stretch."""
    d = s.reset_index().rename(columns={s.index.name or "index": "time"})
    brush = alt.selection_interval(name="span", encodings=["x"])
    bars = (
        alt.Chart(d).mark_bar(color=ACCENT, width=2.2)
        .encode(x=alt.X("time:T", title=None, axis=alt.Axis(format="%d %b", tickCount=10)),
                y=alt.Y("mm:Q", title="mm in each half hour"),
                opacity=alt.when(brush).then(alt.value(1)).otherwise(alt.value(0.55)),
                tooltip=[alt.Tooltip("time:T", format="%d %b %H:%M"), alt.Tooltip("mm:Q", format=".1f")])
        .add_params(brush)
        .properties(width=620, height=200)
    )
    total = (
        alt.Chart(d).transform_filter(brush).transform_aggregate(mm="sum(mm)")
        .transform_calculate(text="'dark bars add up to ' + format(datum.mm, '.0f') + ' mm'")
        .mark_text(align="left", fontSize=13, fontWeight=600, color=INK).encode(x=alt.value(4), y=alt.value(8), text="text:N")
    )
    return alt.layer(bars, total).properties(title=alt.Title(title, subtitle=subtitle) if title else alt.Undefined)


def rain_map(m: pd.DataFrame, lake: tuple[float, float], title: str = "", subtitle: str = ""):
    """The night's rain on the 0.1 degree grid (``m``: latitude, longitude, mm), with the lake marked."""
    # IMERG coordinates are cell centres; each cell spans 0.05 degrees either side
    d = m.assign(lon=m.longitude - 0.05, lon2=m.longitude + 0.05, lat=m.latitude - 0.05, lat2=m.latitude + 0.05)
    cells = alt.Chart(d).mark_rect(stroke=PAPER, strokeWidth=0.5).encode(
        x=alt.X("lon:Q", scale=alt.Scale(zero=False, nice=False), title=None, axis=alt.Axis(format=".1f")),
        x2="lon2:Q",
        y=alt.Y("lat:Q", scale=alt.Scale(zero=False, nice=False), title=None, axis=alt.Axis(format=".1f")),
        y2="lat2:Q",
        color=alt.Color("mm:Q", scale=alt.Scale(range=BLUES), legend=alt.Legend(title="mm of rain that night")),
        tooltip=[alt.Tooltip("mm:Q", format=".0f")],
    )
    here = alt.Chart(pd.DataFrame({"lon": [lake[0]], "lat": [lake[1]], "t": ["Bellandur lake"]}))
    pt = here.mark_point(shape="circle", size=120, color=INK, strokeWidth=2).encode(x="lon:Q", y="lat:Q")
    tx = here.mark_text(dx=8, dy=-10, align="left", fontSize=12, color=INK).encode(x="lon:Q", y="lat:Q", text="t:N")
    return alt.layer(cells, pt, tx).properties(width=340, height=340, title=alt.Title(title, subtitle=subtitle) if title else alt.Undefined)


def wettest_days(daily: pd.DataFrame, mark: str, n: int = 25, title: str = "", subtitle: str = ""):
    """The ``n`` wettest days at the lake since records began (``daily``: index date, mm)."""
    d = daily["mm"].sort_values(ascending=False).head(n).reset_index()
    d.columns = ["date", "mm"]
    d["label"] = d.date.dt.strftime("%d %b %Y")
    d["it"] = d.date.dt.strftime("%Y-%m-%d") == mark
    return (
        alt.Chart(d, title=alt.Title(title, subtitle=subtitle) if title else alt.Undefined)
        .mark_bar(height=11)
        .encode(y=alt.Y("label:N", sort=alt.SortField("mm", order="descending"), title=None),
                x=alt.X("mm:Q", title="mm of rain in the day"),
                color=alt.condition("datum.it", alt.value(ACCENT), alt.value("#cfc6b3")),
                tooltip=[alt.Tooltip("label:N", title="day"), alt.Tooltip("mm:Q", format=".0f")])
        .properties(width=420, height=14 * n)
    )


def chunk_explainer(times: pd.DataFrame, title: str = "", subtitle: str = ""):
    """The same grid stored two ways. Pick a question; the squares show which chunks must be fetched.

    ``times``: layout (chunked as maps / as time series), question, seconds: measured on the real NASA POWER stores.
    """
    T, S = 24, 12   # a toy grid: 24 time steps x 12 places
    cells = pd.DataFrame([(t, s) for t in range(T) for s in range(S)], columns=["t", "s"])
    layouts = {"chunked as maps": lambda t, s: f"t{t}", "chunked as time series": lambda t, s: f"s{s // 3}"}
    rows = []
    for name, chunk in layouts.items():
        for t, s in cells.itertuples(index=False):
            rows.append({"layout": name, "t": t, "s": s, "chunk": chunk(t, s)})
    d = pd.DataFrame(rows)
    q = alt.param(name="question", value="one place, every day",
                  bind=alt.binding_radio(options=["one place, every day", "one day, every place"], name=""))
    need = "(question == 'one place, every day' ? datum.s == 5 : datum.t == 9)"
    grid = (
        alt.Chart(d)
        .transform_calculate(want=need)
        .transform_calculate(want_n="datum.want ? 1 : 0")
        .transform_joinaggregate(touch="max(want_n)", groupby=["layout", "chunk"])
        .transform_calculate(cell="datum.want ? 'what you asked for' : datum.touch > 0 ? 'fetched with it' : 'not fetched'")
        .mark_rect(stroke=PAPER, strokeWidth=0.6)
        .encode(x=alt.X("t:O", axis=alt.Axis(title="time →", labels=False, ticks=False, domain=False)),
                y=alt.Y("s:O", axis=alt.Axis(title="place →", labels=False, ticks=False, domain=False)),
                color=alt.Color("cell:N", scale=alt.Scale(domain=["what you asked for", "fetched with it", "not fetched"],
                                                          range=[INK, ACCENT, "#e6e0d2"]),
                                legend=alt.Legend(title=None)))
        .properties(width=300, height=150)
    )
    tm = times.assign(text=times.apply(lambda r: f"{r.seconds:.1f} seconds", axis=1))
    label = (
        alt.Chart(tm).transform_filter("datum.question == question")
        .mark_text(align="left", fontSize=13, fontWeight=600, color=INK, dy=-6)
        .encode(text="text:N", x=alt.value(0), y=alt.value(0))
    )
    panels = [
        alt.layer(grid.transform_filter(alt.datum.layout == name),
                  label.transform_filter(alt.datum.layout == name))
        .properties(title=alt.Title(name, fontSize=12, offset=22))
        for name in layouts
    ]
    chart = alt.hconcat(*panels, spacing=36).add_params(q)
    if title:
        chart = chart.properties(title=alt.Title(title, subtitle=subtitle))
    return chart


# ---------------------------------------------------------------------------
# Lesson 3: watersheds and buildings
# ---------------------------------------------------------------------------
def _lean(g, keep: list[str], tol: float = 0.00005, grid: float = 1e-6):
    """Shapes in lon/lat with simplified outlines and only the columns a chart needs (keeps pages light)."""
    g = g.to_crs(4326)[[*keep, "geometry"]].copy()
    g["geometry"] = g.geometry.simplify(tol, preserve_topology=True).set_precision(grid)
    return g[~g.geometry.is_empty]


def waterbody_explorer(water, sheds, start_uid: str, title: str = "", subtitle: str = ""):
    """CoRE Stack water bodies on their micro-watersheds. Click a water body: the bars show how much of it
    held water in each year (hectares)."""
    years = [c[6:] for c in water.columns if c.startswith("water_")]
    w = _lean(water, ["UID", *[f"water_{y}" for y in years]])
    pick = alt.selection_point(name="wb", fields=["UID"], on="click", value=[{"UID": start_uid}], clear=False)
    shed = alt.Chart(_lean(sheds, ["uid"], 0.0002)).mark_geoshape(fill="#f1ede3", stroke="#b9b09c", strokeWidth=0.8)
    lakes = (
        alt.Chart(w).mark_geoshape(strokeWidth=0.6)
        .encode(color=alt.when(pick).then(alt.value(ACCENT)).otherwise(alt.value("#8fb3bd")),
                stroke=alt.when(pick).then(alt.value(INK)).otherwise(alt.value("#6d98a3")),
                tooltip=[alt.Tooltip("UID:N", title="CoRE Stack id")])
        .add_params(pick)
    )
    m = alt.layer(shed, lakes).project("mercator").properties(width=420, height=330)
    bars = (
        alt.Chart(w).transform_filter(pick).transform_fold([f"water_{y}" for y in years], as_=["key", "ha"])
        .transform_calculate(year="'20' + slice(datum.key, 6, 8) + '–' + slice(datum.key, 9, 11)")
        .mark_bar(color=ACCENT, width=16)
        .encode(x=alt.X("year:N", title=None, axis=alt.Axis(labelAngle=-40)),
                y=alt.Y("ha:Q", title="hectares with water"),
                tooltip=["year:N", alt.Tooltip("ha:Q", format=".1f")])
        .properties(width=230, height=230)
    )
    chart = alt.hconcat(m, bars, spacing=24)
    if title:
        chart = chart.properties(title=alt.Title(title, subtitle=subtitle))
    return chart


def buildings_map(b, title: str = "", subtitle: str = ""):
    """Building footprints, coloured by size; hover for the area."""
    g = b.assign(m2=b.to_crs(32643).area.round(-1).astype(int).values)
    g = _lean(g, ["m2"], 0.00002, grid=1e-5)          # ~1 m: plenty for a 3 km map
    return (
        alt.Chart(g, title=alt.Title(title, subtitle=subtitle) if title else alt.Undefined)
        .mark_geoshape(strokeWidth=0)
        .encode(color=alt.Color("m2:Q", scale=alt.Scale(type="log", range=["#d8cfbd", "#8c5a4a", "#3b211b"]),
                                legend=alt.Legend(title="footprint (m², log scale)", gradientLength=200, gradientThickness=8)),
                tooltip=[alt.Tooltip("m2:Q", title="m²", format=",.0f")])
        .project("mercator")
        .properties(width=480, height=480)
    )


def row_groups(rg: pd.DataFrame, box: tuple, title: str = "", subtitle: str = ""):
    """Every row group of one Overture file, drawn as its bounding box. The query only reads the dark ones."""
    w, s, e, n = box
    d = rg.assign(hit=(rg.xmin <= e) & (rg.xmax >= w) & (rg.ymin <= n) & (rg.ymax >= s))
    boxes = (
        alt.Chart(d).mark_rect(strokeWidth=0.8, fillOpacity=0.25)
        .encode(x=alt.X("xmin:Q", scale=alt.Scale(zero=False), title="longitude"), x2="xmax:Q",
                y=alt.Y("ymin:Q", scale=alt.Scale(zero=False), title="latitude"), y2="ymax:Q",
                color=alt.condition("datum.hit", alt.value(ACCENT), alt.value("#cfc6b3")),
                stroke=alt.condition("datum.hit", alt.value(ACCENT), alt.value("#a79f8c")),
                order=alt.Order("hit:N"),
                tooltip=[alt.Tooltip("group:Q", title="row group"), alt.Tooltip("rows:Q", format=","),
                         alt.Tooltip("MB:Q", format=".1f")])
    )
    q = alt.Chart(pd.DataFrame({"w": [w], "s": [s], "e": [e], "n": [n]})).mark_rect(
        fill=None, stroke=INK, strokeWidth=2).encode(x="w:Q", x2="e:Q", y="s:Q", y2="n:Q")
    return alt.layer(boxes, q).properties(width=480, height=420, title=alt.Title(title, subtitle=subtitle) if title else alt.Undefined)


def paint(classes: np.ndarray, names: list[str]) -> np.ndarray:
    """A class map (0..n-1, -1 = none) as an RGB picture in the CLASSES colours."""
    rgb = np.full((*classes.shape, 3), 235, np.uint8)
    for i, name in enumerate(names):
        h = CLASSES[name].lstrip("#")
        rgb[classes == i] = [int(h[j:j + 2], 16) for j in (0, 2, 4)]
    return rgb
