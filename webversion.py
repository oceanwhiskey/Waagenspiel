"""Exportiert Raetsel fuer die Web-Version (web/) und ihre Datenbank.

    python webversion.py                   # beides: web/raetsel.json und build/raetsel.tsv.gz
    python webversion.py --je-stufe 1000   # Notvorrat je Stufe fuer web/raetsel.json

Jedes Raetsel bekommt als feste ``id`` seine Position in ``data/katalog.json.gz``.
Damit diese Nummern stabil bleiben, darf der Katalog nur hinten ergaenzt, aber
nicht umsortiert werden. Raetsel, deren Waagen sich kuerzen lassen (etwa
``2b < 2a``), kommen nicht ins Spiel.

In der kanonischen Form des Katalogs ist immer ``a`` der Schwerste; die
Web-Version benennt fuer jede Runde um. Loesungsschritte werden nicht mehr
exportiert: Menschen loesen anders, die Erklaerungen sind entfallen.

``web/raetsel.json`` ist der Notvorrat ohne Netz::

    {"levels": {"1": [{"id": 17, "s": ["b + c < a", ...]}, ...], ...}}

``build/raetsel.tsv.gz`` hat alle Raetsel fuer die Server-Datenbank, je Zeile::

    id <TAB> stufe <TAB> abkuerzung (0/1) <TAB> waagen ("b + c < a; ...")
"""

from __future__ import annotations

import argparse
import gzip
import json
import random
import sys
from math import gcd
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from waagenspiel.catalog import load_catalog  # noqa: E402
from waagenspiel.puzzle import Scale, free_heaviest  # noqa: E402

DEFAULT_JSON = ROOT / "web" / "raetsel.json"
DEFAULT_TSV = ROOT / "build" / "raetsel.tsv.gz"


def entries() -> Iterator[tuple[int, int, list[str]]]:
    """(id, stufe, waagen) aller spielbaren Raetsel in Katalog-Reihenfolge."""

    for index, entry in enumerate(load_catalog()["puzzles"]):  # type: ignore[union-attr]
        texts = list(entry[:-1])
        scales = [Scale.parse(t) for t in texts]
        if all(gcd(*s.left, *s.right) == 1 for s in scales):
            yield index, entry[-1], texts


def export_tsv(out: Path) -> dict[int, int]:
    counts: dict[int, int] = {}
    out.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(out, "wt", encoding="utf-8", newline="\n") as handle:
        for index, level, texts in entries():
            shortcut = free_heaviest([Scale.parse(t) for t in texts]) == 0
            handle.write(f"{index}\t{level}\t{int(shortcut)}\t{'; '.join(texts)}\n")
            counts[level] = counts.get(level, 0) + 1
    return dict(sorted(counts.items()))


def export_json(per_level: int, seed: int, out: Path) -> dict[str, int]:
    rng = random.Random(seed)
    by_level: dict[int, list[dict[str, object]]] = {}
    for index, level, texts in entries():
        by_level.setdefault(level, []).append({"id": index, "s": texts})
    levels = {
        str(level): sorted(items if len(items) <= per_level else rng.sample(items, per_level), key=lambda p: p["id"])
        for level, items in sorted(by_level.items())
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"levels": levels}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return {level: len(p) for level, p in levels.items()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--je-stufe", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--tsv", type=Path, default=DEFAULT_TSV)
    args = parser.parse_args(argv)
    counts = export_json(args.je_stufe, args.seed, args.json)
    print(f"{args.json}: {counts}, {args.json.stat().st_size // 1024} KB")
    counts = export_tsv(args.tsv)
    print(f"{args.tsv}: {counts}, {args.tsv.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
