"""Execute a marimo notebook headlessly; any cell error raises and exits non-zero.

    uv run python tests/run_notebook.py notebooks/01_satellite_images.py
    uv run python tests/run_notebook.py notebooks/*.py
"""

import importlib.util
import sys
import time


def run(path: str) -> None:
    spec = importlib.util.spec_from_file_location("nb", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    t0 = time.time()
    _, defs = mod.app.run()
    print(f"ok  {path}  ({len(defs)} definitions, {time.time() - t0:.1f}s)")


if __name__ == "__main__":
    for p in sys.argv[1:]:
        run(p)
