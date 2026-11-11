"""Das Waagen-Spiel mit Fenster starten.

    python spiel.py                    # Menue, 60 Sekunden, Schwierigkeit "Steigend"
    python spiel.py --zeit 45          # eigene Spielzeit in Sekunden
    python spiel.py --zeit 0           # Ueben ohne Uhr, mit Tipps
    python spiel.py --stufe Profi      # Steigend, Leicht, Mittel, Schwer, Profi

Die Raetsel kommen aus data/katalog.json.gz (erzeugt mit katalog.py); jedes hat
nachweislich genau eine schwerste Figur. Grundlage: docs/03_einfache_herleitung.md.
"""

from __future__ import annotations

import argparse
import sys
import tkinter as tk
from pathlib import Path

SRC = Path(__file__).resolve().parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from waagenspiel.catalog import DEFAULT_PATH  # noqa: E402
from waagenspiel.game import DEFAULT_HIGHSCORES, DIFFICULTIES, CatalogRounds, GameSession, Highscores  # noqa: E402
from waagenspiel.gui import GameWindow  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--zeit", type=float, default=60, help="Spielzeit in Sekunden, 0 = ueben")
    parser.add_argument("--stufe", choices=list(DIFFICULTIES), default="Steigend")
    parser.add_argument("--bestenliste", type=Path, default=DEFAULT_HIGHSCORES)
    args = parser.parse_args(argv)
    if not DEFAULT_PATH.exists():
        print(f"{DEFAULT_PATH} fehlt; bitte zuerst 'python katalog.py' ausfuehren.", file=sys.stderr)
        return 1

    source = CatalogRounds()

    def make_session(difficulty: str, time_limit: float | None, characters) -> GameSession:
        return GameSession(source, DIFFICULTIES[difficulty](), time_limit, characters=characters)

    root = tk.Tk()
    GameWindow(root, make_session, Highscores(args.bestenliste), args.zeit or None, args.stufe)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
