# Instructor notes

## Before the day

- [ ] Publish the repo at github.com/amanbagrecha/catalogs-and-embeddings (the setup block on the
      Welcome page clones it), and the prepared files: `uv run cngeo datapack zip`, then attach
      `dist/cngeo-datapack.zip` and everything in `dist/files/` to a release tagged `data-v1`.
- [ ] Send participants the setup block (end of the Welcome page) beforehand, so `uv sync` is not
      run by forty laptops on the venue Wi-Fi at once.
- [ ] Run every notebook headless the day before: `uv run python tests/run_notebook.py notebooks/*.py`.
      Overture deletes releases after 60 days; the notebooks always ask for the latest, so this
      also checks that nothing moved.
- [ ] Keep the data-pack zip on a USB stick, for laptops that can't download.

## On the day

- The Welcome page (11:00) is shown from the website: about me, the remote-sensing basics, the
  plan, and the setup block at the end. People who haven't installed yet do it then; the Start
  here check (11:25) catches the rest. The morning is tight (two hours for the Welcome and three
  lessons): if it runs long, shorten lesson 2's NASA POWER timing to the projector only.
- Tell the story first, then the format. Each lesson opens with a question about the lake; the
  storage format is how we answer it.
- Live reads, roughly (from Bengaluru, good Wi-Fi):

  | Lesson | Live step | Time | Per laptop |
  |---|---|---|---|
  | 1 | search 9 years of Sentinel-2, one whole-tile overview, two windows, three Try-it cells | ~100 s | ~20 MB |
  | 2 | IMERG three weeks at the lake; NASA POWER timing | ~10 s + ~40 s | ~150 MB (the slow map-chunked read) |
  | 3 | CoRE Stack GeoJSON; Overture buildings | ~5 s, ~15 s | ~15 MB |
  | 4 | AlphaEarth box; TESSERA box; 9 thumbnails | ~15 s, ~30 s, ~10 s | ~90 MB |

  If the room is large or the Wi-Fi weak, run lesson 2's timing cell on the projector only. Lessons 5 and 6 run entirely from the data pack and `my_catalog/`.
- Each lesson ends with three "Try it" prompts. In lesson 1 each prompt has a ready-made cell below
  it: change the values at the top (the box, the band, the zoom level) and run it. Cut these before
  cutting the charts.
- Lessons 1 and 5 show `my_catalog/` as a folder to click through (`mo.ui.file_browser`); clicking
  a JSON file shows its text underneath. Walk the room through catalog → item → data file once.
- Lesson 6 reads back what lessons 1, 2, 3 and 5 saved, so it needs those run first. Rerunning
  lesson 1 later opens the existing catalog instead of replacing it.

## Points that land

- **5 MB out of 363 MB** (lesson 1). Reading only the lake from a COG is the morning's thesis.
- **The same data, stored twice** (lesson 2). Ask the room to guess which layout wins before
  running the timing cell.
- **CoRE Stack's lake history** (lesson 3): Bellandur's open water went from about 120 ha to 7 ha
  in 2020–21 when it was drained, and back. A good catalog with old-fashioned files behind it.
- **Ten labels with embeddings beat 200 without** (lesson 5).
- **2022–23 drift** (lesson 5). Every pixel moves a little and comes back. Change needs a control.

## Say out loud

- Satellite rain is an estimate: IMERG says ~50 mm over the lake that night (~70 mm for the whole of 5 Sep), the gauges said 131 mm.
- Embeddings summarise a whole year in 10 m squares; nothing within the year, nothing smaller.
- AlphaEarth's model is closed and its future years depend on Google; TESSERA is fully open.
- TESSERA's licence is listed as CC0 in its README and CC BY-SA on AWS Open Data. Attribute it either way.
