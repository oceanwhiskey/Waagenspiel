"""Erzeugt den vollstaendigen Raetselkatalog ``data/katalog.json.gz``.

    python katalog.py              # etwa 3 Minuten auf 4 Kernen
    python katalog.py --workers 8

Grundlage ist docs/03_einfache_herleitung.md, Abschnitt 9.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

SRC = Path(__file__).resolve().parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from waagenspiel.catalog import DEFAULT_PATH, build_catalog, write_catalog  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--ausgabe", type=Path, default=DEFAULT_PATH)
    args = parser.parse_args(argv)
    start = time.time()

    def log(message: str) -> None:
        print(f"[{time.time() - start:7.1f}s] {message}", flush=True)

    catalog = build_catalog(workers=args.workers, log=log)
    write_catalog(catalog, args.ausgabe)
    log(f"{catalog['metadata']['count']} Raetsel nach {args.ausgabe} geschrieben")
    for name, count in catalog["metadata"]["counts"].items():
        log(f"  {name}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
