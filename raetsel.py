"""Waagenspiel-Raetsel erzeugen oder im Terminal spielen.

Beispiele:

    python raetsel.py erzeugen --anzahl 20 --stufe mittel --ausgabe data/raetsel.json
    python raetsel.py erzeugen --anzahl 5 --stufe experte --mit-loesung
    python raetsel.py spielen --stufe leicht
    python raetsel.py spielen --stufe schwer --quelle baukasten

Quellen: ``katalog`` zieht gleichverteilt aus allen Raetseln (data/katalog.json.gz,
erzeugt mit katalog.py), ``baukasten`` baut Raetsel gezielt nach Loesungsplan
(Stufen 1-3), ``zufall`` zieht Waagen blind und prueft.

Grundlage ist docs/03_einfache_herleitung.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

SRC = Path(__file__).resolve().parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from waagenspiel.puzzle import LEVELS, NAMES, Puzzle, PuzzleGenerator, Settings  # noqa: E402

SOURCES = ("katalog", "baukasten", "zufall")


def make_source(name: str, settings: Settings, seed: int | None):
    """Raetselquelle mit ``generate(anzahl)`` und ``shuffled(raetsel)``."""

    if name == "katalog":
        from waagenspiel.catalog import DEFAULT_PATH, CatalogSource

        if not DEFAULT_PATH.exists():
            raise RuntimeError(f"{DEFAULT_PATH} fehlt; erst 'python katalog.py' ausfuehren")
        return CatalogSource(settings, seed)
    if name == "baukasten":
        from waagenspiel.construct import ConstructiveGenerator

        return ConstructiveGenerator(settings, seed)
    return PuzzleGenerator(settings, seed)


def settings_from(args: argparse.Namespace) -> Settings:
    settings = LEVELS[args.stufe]
    changes = {}
    if args.waagen:
        changes["scale_counts"] = tuple(args.waagen)
    if args.max_seite:
        changes["max_side"] = args.max_seite
    if args.min_schwierigkeit:
        changes["min_difficulty"] = args.min_schwierigkeit
    if args.max_schwierigkeit:
        changes["max_difficulty"] = args.max_schwierigkeit
    return replace(settings, **changes)


def print_puzzle(number: int, puzzle: Puzzle, *, solution: bool) -> None:
    print(f"Raetsel {number} (Stufe {puzzle.difficulty}: {puzzle.solution.level_name})")
    for index, scale in enumerate(puzzle.scales, start=1):
        print(f"  Waage {index}:  {scale}")
    if solution:
        print(f"  Am schwersten: {NAMES[puzzle.heaviest]}")
        for step in puzzle.solution.steps:
            print(f"  Schritt: {step.fact}")
            for line in step.lines():
                print(f"    {line}")
    print()


def command_generate(args: argparse.Namespace) -> int:
    settings = settings_from(args)
    generator = make_source(args.quelle, settings, args.seed)
    puzzles = list(generator.generate(args.anzahl))
    if args.ausgabe:
        data = {
            "metadata": {
                "schema_version": 1,
                "source": "docs/03_einfache_herleitung.md",
                "level": args.stufe,
                "puzzle_source": args.quelle,
                "settings": {
                    "scale_counts": list(settings.scale_counts),
                    "max_side": settings.max_side,
                    "max_weight": settings.max_weight,
                    "balance_share": settings.balance_share,
                    "allow_multiples": settings.allow_multiples,
                    "min_difficulty": settings.min_difficulty,
                    "max_difficulty": settings.max_difficulty,
                },
                "seed": args.seed,
                "count": len(puzzles),
            },
            "puzzles": [{"id": f"r{i:05d}", **p.to_json()} for i, p in enumerate(puzzles, start=1)],
        }
        path = Path(args.ausgabe)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{len(puzzles)} Raetsel nach {path} geschrieben.")
    else:
        for number, puzzle in enumerate(puzzles, start=1):
            print_puzzle(number, puzzle, solution=args.mit_loesung)
    return 0


def command_play(args: argparse.Namespace) -> int:
    generator = make_source(args.quelle, settings_from(args), args.seed)
    solved = played = 0
    print("Welcher Gegenstand ist am schwersten? Antworte mit a, b, c oder d.")
    print("h zeigt einen Hinweis, q beendet das Spiel.\n")
    while args.runden == 0 or played < args.runden:
        puzzle = generator.shuffled(next(generator.generate(1)))
        print_puzzle(played + 1, puzzle, solution=False)
        hints = list(puzzle.solution.steps)
        while True:
            try:
                answer = input("> ").strip().lower()
            except EOFError:
                answer = "q"
            if answer == "q":
                print(f"\n{solved} von {played} Raetseln richtig.")
                return 0
            if answer == "h":
                if hints:
                    step = hints.pop(0)
                    print(f"Hinweis: {step.fact}")
                    for line in step.lines():
                        print(f"  {line}")
                else:
                    print("Keine weiteren Hinweise.")
                continue
            if answer not in NAMES:
                print("Bitte a, b, c, d, h oder q eingeben.")
                continue
            played += 1
            if NAMES.index(answer) == puzzle.heaviest:
                solved += 1
                print("Richtig!\n")
            else:
                print(f"Leider nein, {NAMES[puzzle.heaviest]} ist am schwersten. Warum {answer} leichter ist:")
                for step in puzzle.solution.steps_for(NAMES.index(answer)):
                    print(f"  Schritt: {step.fact}")
                    for line in step.lines():
                        print(f"    {line}")
                print()
            break
    print(f"{solved} von {played} Raetseln richtig.")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--stufe", choices=sorted(LEVELS), default="mittel",
                        help="leicht: 1 Gegenstand pro Seite; mittel: bis 2, Stufe 1-2; "
                             "schwer: bis 3, Stufe 3; experte: Stufe 4")
    common.add_argument("--waagen", type=int, nargs="+", choices=(2, 3), help="erlaubte Anzahl Waagen")
    common.add_argument("--max-seite", type=int, choices=(1, 2, 3), help="Gegenstaende pro Seite hoechstens")
    common.add_argument("--min-schwierigkeit", type=int, choices=(1, 2, 3, 4),
                        help="mindestens diese Stufe (1 ablesen, 2 Kette, 3 kombinieren, 4 aufloesen)")
    common.add_argument("--max-schwierigkeit", type=int, choices=(1, 2, 3, 4), help="hoechstens diese Stufe")
    common.add_argument("--seed", type=int, help="Zufallsstartwert fuer reproduzierbare Raetsel")
    common.add_argument("--quelle", choices=SOURCES, default="katalog",
                        help="katalog (Standard), baukasten (Stufen 1-3) oder zufall")

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    generate = commands.add_parser("erzeugen", parents=[common], help="Raetsel erzeugen")
    generate.add_argument("--anzahl", type=int, default=10)
    generate.add_argument("--ausgabe", help="JSON-Datei; ohne Angabe Ausgabe als Text")
    generate.add_argument("--mit-loesung", action="store_true", help="Loesungswege in der Textausgabe zeigen")
    generate.set_defaults(run=command_generate)
    play = commands.add_parser("spielen", parents=[common], help="im Terminal spielen")
    play.add_argument("--runden", type=int, default=0, help="Anzahl Raetsel, 0 = bis q")
    play.set_defaults(run=command_play)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args(argv)
    try:
        return args.run(args)
    except (ValueError, RuntimeError) as error:
        print(f"Fehler: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
