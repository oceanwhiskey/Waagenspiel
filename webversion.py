"""Exportiert Raetsel samt Loesungsschritten fuer die Web-Version (web/).

    python webversion.py                 # 400 Raetsel je Stufe, etwa 2 Minuten
    python webversion.py --je-stufe 800

Im Browser laeuft kein Loeser. Deshalb werden die Loesungsschritte (docs/03,
Abschnitt 8) hier vorberechnet. In der kanonischen Form des Katalogs ist
immer ``a`` der Schwerste; die Web-Version benennt fuer jede Runde um.

Format von web/raetsel.json::

    {"levels": {"1": [puzzle, ...], ...}}
    puzzle = {"s": ["b + c < a", ...],
              "steps": [{"f": [x, h], "r": [[u, v], ...], "t": ["Zeile", ...]}, ...]}

``f`` ist der gezeigte Vergleich (x leichter als h, Indizes 0-3 fuer a-d),
``r`` die dafuer benutzten, vorher gezeigten Vergleiche, ``t`` der Text.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from math import gcd
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from waagenspiel.catalog import load_catalog  # noqa: E402
from waagenspiel.puzzle import Scale, solve  # noqa: E402

DEFAULT_OUT = ROOT / "web" / "raetsel.json"


def export(per_level: int, seed: int, out: Path) -> dict[str, int]:
    rng = random.Random(seed)
    by_level: dict[int, list[list[str]]] = {}
    for entry in load_catalog()["puzzles"]:  # type: ignore[union-attr]
        scales = [Scale.parse(t) for t in entry[:-1]]
        if all(gcd(*s.left, *s.right) == 1 for s in scales):
            by_level.setdefault(entry[-1], []).append(entry[:-1])
    levels: dict[str, list[dict[str, object]]] = {}
    for level, entries in sorted(by_level.items()):
        chosen = entries if len(entries) <= per_level else rng.sample(entries, per_level)
        puzzles = []
        for i, texts in enumerate(chosen):
            solution = solve([Scale.parse(t) for t in texts])
            assert solution.top == 0 and solution.level == level
            puzzles.append({
                "s": list(texts),
                "steps": [
                    {"f": [step.lighter, step.heavier], "r": [list(p) for p in step.requires], "t": step.lines()}
                    for step in solution.steps
                ],
            })
            if (i + 1) % 100 == 0:
                print(f"Stufe {level}: {i + 1}/{len(chosen)}", flush=True)
        levels[str(level)] = puzzles
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"levels": levels}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return {level: len(p) for level, p in levels.items()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--je-stufe", type=int, default=400)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--ausgabe", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    counts = export(args.je_stufe, args.seed, args.ausgabe)
    print(f"{args.ausgabe}: {counts}, {args.ausgabe.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
