"""Command line: ``cngeo check``, ``cngeo datapack {status,download,build,zip}`` and ``cngeo site``."""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="cngeo", description="The lake and the city: workshop toolkit")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("check", help="check packages, internet access and the data pack")

    dp = sub.add_parser("datapack", help="the pre-built data pack (for weak Wi-Fi)")
    dsub = dp.add_subparsers(dest="action", required=True)
    dsub.add_parser("status", help="list which files are present")
    d = dsub.add_parser("download", help="download the pre-built pack")
    d.add_argument("--url", default=None)
    d.add_argument("--force", action="store_true")
    b = dsub.add_parser("build", help="build the pack from the original sources")
    b.add_argument("--step", action="append", help="run only this step (repeatable)")
    b.add_argument("--force", action="store_true")
    z = dsub.add_parser("zip", help="zip the pack for publishing as a release asset")
    z.add_argument("--out", default="dist/cngeo-datapack.zip")

    st = sub.add_parser("site", help="build the static course website from the notebooks")
    st.add_argument("--out", default="site")
    st.add_argument("--repo-url", default=None, help="link to the notebooks repository, shown in the sidebar")
    st.add_argument("--only", action="append", help="build only this notebook or page (repeatable)")

    args = ap.parse_args(argv)
    if args.cmd == "check":
        from .setup_check import checks

        df = checks()
        print(df.to_string(index=False))
        return 0 if df.ok.all() else 1
    if args.cmd == "datapack":
        from . import datapack

        if args.action == "status":
            print(datapack.status().to_string(index=False))
        elif args.action == "download":
            print(datapack.download(url=args.url, force=args.force))
        elif args.action == "build":
            from . import build

            build.run(args.step, force=args.force)
        elif args.action == "zip":
            print(datapack.zip_pack(args.out))
    elif args.cmd == "site":
        from .site import build

        build(args.out, repo_url=args.repo_url, only=args.only)
    return 0


if __name__ == "__main__":
    sys.exit(main())
