"""Turn the lesson notebooks into a small static website: ``cngeo site``.

Each notebook is run top to bottom and its outputs are written into a plain
HTML page: prose, the code cells that are shown in the notebook, tables, and
the Altair charts (rendered in the browser by vega-embed, so every slider,
toggle and brush keeps working). The pages share one stylesheet and a sidebar,
and drop into any static host or website.

    uv run cngeo site                      # -> site/
    uv run cngeo site --repo-url https://github.com/you/catalogs-and-embeddings
"""

from __future__ import annotations

import base64
import html
import importlib.util
import io
import json
import re
import shutil
from pathlib import Path

import altair as alt
import pandas as pd

from . import mycatalog

ROOT = Path(__file__).resolve().parents[2]
NOTEBOOKS = ROOT / "notebooks"
COURSE = "The lake and the city"
TAGLINE = "Cloud-native data and Earth embeddings · a workshop, Bengaluru, 11:00–16:00"

PAGES = [  # notebook, page file, short title, time
    ("00_intro_to_remote_sensing.py", "index.html", "Welcome", "11:00"),
    ("00_start_here.py", "start-here.html", "Start here", "11:25"),
    ("01_satellite_images.py", "satellite-images.html", "Satellite images", "11:35"),
    ("02_weather_grids.py", "weather-grids.html", "Weather grids", "12:10"),
    ("03_watersheds_and_buildings.py", "watersheds-and-buildings.html", "Watersheds and buildings", "12:35"),
    ("04_pixels_as_vectors.py", "pixels-as-vectors.html", "Pixels as vectors", "14:00"),
    ("05_using_embeddings.py", "using-embeddings.html", "Using embeddings", "14:45"),
    ("06_reading_the_catalog.py", "reading-the-catalog.html", "Reading the catalog", "15:25"),
]

VEGA = [
    f"https://cdn.jsdelivr.net/npm/vega@{alt.VEGA_VERSION}",
    f"https://cdn.jsdelivr.net/npm/vega-lite@{alt.VEGALITE_VERSION}",
    f"https://cdn.jsdelivr.net/npm/vega-embed@{alt.VEGAEMBED_VERSION}",
]
FONTS = (
    "https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,700"
    "&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;1,400&display=swap"
)


# ---------------------------------------------------------------------------
# Running a notebook
# ---------------------------------------------------------------------------
def run_notebook(path: Path) -> list[tuple[str, bool, object]]:
    """[(code, code_is_shown, output), ...] in cell order."""
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    outputs, _ = mod.app.run()
    cells = list(mod.app._cell_manager.cell_data())
    return [(c.code, not c.config.hide_code, o) for c, o in zip(cells, outputs)]


# ---------------------------------------------------------------------------
# Output -> HTML
# ---------------------------------------------------------------------------
def _code_html(code: str) -> str:
    from pygments import highlight
    from pygments.formatters import HtmlFormatter
    from pygments.lexers import PythonLexer

    return highlight(code.strip(), PythonLexer(), HtmlFormatter(nowrap=True))


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", re.sub(r"<[^>]+>", "", text).lower()).strip("-")


def _prose(raw: str, toc: list) -> str:
    def h2(m):
        inner = m.group(2)
        sid = _slug(inner)
        toc.append((sid, re.sub(r"<[^>]+>", "", inner)))
        return f'<h2 id="{sid}">{inner}</h2>'

    raw = re.sub(r"<h2([^>]*)>(.*?)</h2>", h2, raw, flags=re.S)
    return f'<div class="prose">{raw}</div>'


def _folder_html() -> str:
    """The participants' catalog as a folder tree: catalog.json, each item's JSON and the file it points to.

    The JSON files link to the copy shipped with the site; data files are listed with their size.
    """
    files = [mycatalog.FOLDER / "catalog.json"]
    for item in mycatalog.open_catalog().get_items():
        files.append(Path(item.get_self_href()))
        files += [Path(a.get_absolute_href()) for a in item.assets.values()]
    tree: dict = {}
    for f in files:
        *dirs, name = f.relative_to(mycatalog.FOLDER).parts
        node = tree
        for d in dirs:
            node = node.setdefault(d + "/", {})
        node[name] = f

    lines = []

    def walk(node: dict, depth: int):
        for name in sorted(node, key=lambda n: (n != "catalog.json", n)):
            f, pad = node[name], "  " * depth
            if isinstance(f, dict):
                lines.append(pad + name)
                walk(f, depth + 1)
            elif f.suffix == ".json":
                lines.append(f'{pad}<a href="my_catalog/{f.relative_to(mycatalog.FOLDER).as_posix()}">{name}</a>')
            else:
                size = sum(x.stat().st_size for x in f.rglob("*")) if f.is_dir() else f.stat().st_size
                size = f"{size / 1e6:.1f} MB" if size > 1e5 else f"{size / 1e3:.0f} kB"
                lines.append(f"{pad}{name}{'/' if f.is_dir() else ''}  <span>{size}</span>")

    walk(tree, 1)
    return '<pre class="tree">my_catalog/\n' + "\n".join(lines) + "</pre>"


def _output_html(obj, n: int, toc: list, charts: dict) -> str:
    if obj is None:
        return ""
    if isinstance(obj, str):  # a one-line result, e.g. f"Read 5.3 MB ..."
        return f'<p class="out">{html.escape(obj)}</p>'
    if type(obj).__name__ == "altair_chart" and hasattr(obj, "_chart"):  # mo.ui.altair_chart
        obj = obj._chart
    if isinstance(obj, alt.TopLevelMixin):
        cid = f"chart-{n}"
        charts[cid] = obj.to_dict()
        return f'<figure class="chart"><div id="{cid}"></div></figure>'
    if isinstance(obj, pd.DataFrame):
        index = not isinstance(obj.index, pd.RangeIndex)
        return f'<div class="table">{obj.to_html(index=index, border=0, classes="data", na_rep="", float_format=lambda v: f"{v:,.1f}")}</div>'
    if hasattr(obj, "savefig"):  # matplotlib figure
        buf = io.BytesIO()
        obj.savefig(buf, format="webp", dpi=110, bbox_inches="tight", facecolor="none", pil_kwargs={"quality": 88, "method": 6})
        b64 = base64.b64encode(buf.getvalue()).decode()
        return f'<figure class="image"><img alt="" src="data:image/webp;base64,{b64}"></figure>'
    if type(obj).__name__ == "file_browser":  # mo.ui.file_browser over my_catalog/
        return _folder_html()
    text = getattr(obj, "text", None)  # mo.md, mo.Html
    if isinstance(text, str):
        return _prose(text, toc)
    return f"<pre class='repr'>{html.escape(repr(obj))}</pre>"


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
def _sidebar(current: str, repo_url: str | None) -> str:
    links = []
    for nb, page, title, time in PAGES:
        cls = ' class="current"' if page == current else ""
        num = "·" if nb.startswith("00") else str(int(nb[:2]))
        links.append(f'<a href="{page}"{cls}><span class="num">{num}</span><span class="t">{title}</span><span class="time">{time}</span></a>')
    repo = f'<a class="repo" href="{html.escape(repo_url)}">Notebooks &amp; code ↗</a>' if repo_url else ""
    return f"""<aside class="sidebar">
  <a class="course" href="index.html"><span class="course-title">{COURSE.replace(" and ", "<br>and ")}</span><span class="course-sub">{TAGLINE}</span></a>
  <nav class="lessons">{''.join(links)}</nav>
  {repo}
</aside>"""


def _page(i: int, body: str, toc: list, charts: dict, repo_url: str | None) -> str:
    _, page, title, _ = PAGES[i]
    prev_ = PAGES[i - 1] if i > 0 else None
    next_ = PAGES[i + 1] if i + 1 < len(PAGES) else None
    pager = '<nav class="pager">'
    pager += f'<a class="prev" href="{prev_[1]}"><span>Previous</span>{prev_[2]}</a>' if prev_ else "<span></span>"
    pager += f'<a class="next" href="{next_[1]}"><span>Next</span>{next_[2]}</a>' if next_ else "<span></span>"
    pager += "</nav>"
    toc_html = "".join(f'<li><a href="#{sid}">{html.escape(t)}</a></li>' for sid, t in toc)
    scripts = "\n".join(f'<script src="{u}"></script>' for u in VEGA)
    specs = json.dumps(charts, separators=(",", ":")).replace("</", "<\\/")
    head_title = COURSE if page == "index.html" else f"{title} · {COURSE}"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(head_title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTS}">
<link rel="stylesheet" href="assets/site.css">
{scripts}
</head>
<body>
<div class="layout">
{_sidebar(page, repo_url)}
<main class="content">
{body}
{pager}
<footer>Made with open data and open-source Python · <a href="https://marimo.io">marimo</a> · <a href="https://altair-viz.github.io">Altair</a></footer>
</main>
<aside class="toc">{'<p>On this page</p><ul>' + toc_html + '</ul>' if toc else ''}</aside>
</div>
<script>
const SPECS = {specs};
for (const [id, spec] of Object.entries(SPECS)) {{
  vegaEmbed("#" + id, spec, {{actions: false, renderer: "canvas"}}).catch(console.error);
}}
</script>
</body>
</html>
"""


def build(out: str | Path = "site", repo_url: str | None = None, only: list[str] | None = None) -> Path:
    """Run every lesson notebook and write the website into ``out``."""
    out = Path(out)
    (out / "assets").mkdir(parents=True, exist_ok=True)
    shutil.copy(Path(__file__).with_name("site.css"), out / "assets" / "site.css")
    for i, (nb, page, title, _) in enumerate(PAGES):
        if only and nb not in only and page not in only:
            continue
        cells = run_notebook(NOTEBOOKS / nb)
        toc: list = []
        charts: dict = {}
        blocks = []
        for n, (code, shown, obj) in enumerate(cells):
            if shown:
                blocks.append(f'<pre class="code"><code>{_code_html(code)}</code></pre>')
            blocks.append(_output_html(obj, n, toc, charts))
        (out / page).write_text(_page(i, "\n".join(b for b in blocks if b), toc, charts, repo_url), encoding="utf-8")
        print(f"{page}: {len(charts)} charts, {(out / page).stat().st_size / 1e6:.1f} MB")
    if mycatalog.FOLDER.exists():  # the catalog the lessons build; the pages link to its JSON files
        shutil.copytree(mycatalog.FOLDER, out / "my_catalog", dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("*.tif", "*.parquet", "*.zarr"))
    return out
