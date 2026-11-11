"""Spiellogik fuer das grafische Waagenspiel (ohne jede Oberflaeche).

Die Oberflaeche (:mod:`waagenspiel.gui`) bekommt eine :class:`GameSession`
von aussen gereicht und fragt sie nur noch: Was ist zu zeigen? Was passiert
bei dieser Antwort? Wie viel Zeit bleibt? Uhr, Zufall und Raetselquelle sind
ebenfalls eingereicht, deshalb laesst sich alles ohne Fenster testen.

Die Raetsel kommen aus dem exakt gepruefen Katalog (docs/03, Abschnitt 9):
Jedes hat genau einen echt schwersten Gegenstand, und jede Waage wird dafuer
gebraucht. Fuer das Spiel werden die Gegenstaende zufaellig umbenannt, die
Waagen gemischt und zufaellig gespiegelt.
"""

from __future__ import annotations

import json
import random
import re
import time
from dataclasses import dataclass, field
from math import gcd
from pathlib import Path
from typing import Callable, Iterable, Protocol, Sequence

from .puzzle import NAMES, Scale, Solution, heaviest, solve

# --------------------------------------------------------------------------
# Figuren
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Character:
    """Eine Spielfigur: Farbe und Form unterscheiden sie doppelt."""

    name: str
    color: str
    shape: str


COLORS: tuple[tuple[str, str], ...] = (
    ("Rot", "#ef476f"),
    ("Blau", "#3a86ff"),
    ("Gelb", "#ffd23f"),
    ("Grün", "#06d6a0"),
    ("Lila", "#9b5de5"),
    ("Orange", "#ff8c42"),
)
SHAPES: tuple[str, ...] = ("kreis", "quadrat", "dreieck", "tropfen")


def pick_characters(rng: random.Random) -> tuple[Character, ...]:
    """Vier Figuren mit verschiedenen Farben und verschiedenen Formen."""

    colors = rng.sample(COLORS, 4)
    shapes = rng.sample(SHAPES, 4)
    return tuple(Character(name, color, shape) for (name, color), shape in zip(colors, shapes))


# --------------------------------------------------------------------------
# Was auf einer Waage zu sehen ist
# --------------------------------------------------------------------------


def pan_items(side: Sequence[int]) -> tuple[int, ...]:
    """Gegenstaende einer Waagschale, gleiche nebeneinander.

    Bei drei Gegenstaenden liegen die ersten beiden unten und der dritte
    obendrauf; ein Paar gleicher Gegenstaende kommt deshalb nach unten.
    """

    items = [i for i, count in enumerate(side) for _ in range(count)]
    if len(items) == 3 and items[1] == items[2] != items[0]:
        items = [items[1], items[2], items[0]]
    return tuple(items)


def pan_positions(count: int) -> tuple[tuple[float, int], ...]:
    """Platz jedes Gegenstands: (waagrechter Versatz in Breiten, Reihe).

    Hoechstens zwei liegen nebeneinander; ein dritter liegt mittig oben.
    """

    return {
        1: ((0.0, 0),),
        2: ((-0.5, 0), (0.5, 0)),
        3: ((-0.5, 0), (0.5, 0), (0.0, 1)),
    }[count]


@dataclass(frozen=True)
class ScaleView:
    """Eine Waage, wie sie gezeigt wird.

    ``tilt`` ist -1, wenn die linke Schale unten haengt (links schwerer),
    +1, wenn die rechte unten haengt, und 0 im Gleichgewicht.
    """

    number: int
    left: tuple[int, ...]
    right: tuple[int, ...]
    tilt: int

    @staticmethod
    def from_scale(scale: Scale, number: int, mirrored: bool) -> "ScaleView":
        light, heavy = pan_items(scale.left), pan_items(scale.right)
        tilt = 0 if scale.operator == "=" else 1
        if mirrored:
            light, heavy, tilt = heavy, light, -tilt
        return ScaleView(number, light, heavy, tilt)


# --------------------------------------------------------------------------
# Eine Runde
# --------------------------------------------------------------------------


@dataclass
class Round:
    """Ein Raetsel, so wie es gerade auf dem Bildschirm steht."""

    scales: tuple[Scale, ...]
    views: tuple[ScaleView, ...]
    answer: int
    level: int
    _solution: Solution | None = field(default=None, repr=False)

    def is_correct(self, choice: int) -> bool:
        return choice == self.answer

    @property
    def solution(self) -> Solution:
        """Loesungsweg (wird erst bei Bedarf berechnet, dauert ~50 ms)."""

        if self._solution is None:
            self._solution = solve(self.scales)
        return self._solution

    def why_lighter(self, choice: int) -> list[str]:
        """Begruendung, warum ``choice`` leichter ist als die Antwort."""

        lines: list[str] = []
        for step in self.solution.steps_for(choice):
            lines.extend(step.lines())
        return lines

    def hints(self) -> list[list[str]]:
        """Alle Loesungsschritte, jeder als Liste von Zeilen."""

        return [step.lines() for step in self.solution.steps]


def round_from_scales(
    scales: Sequence[Scale], level: int, rng: random.Random, mirror: bool = True
) -> Round:
    """Benennt zufaellig um, mischt die Waagen und spiegelt manche."""

    names = list(range(4))
    rng.shuffle(names)
    renamed = [s.renamed(tuple(names)) for s in scales]  # type: ignore[arg-type]
    rng.shuffle(renamed)
    top = heaviest(renamed)
    if top is None:
        raise ValueError("Das Raetsel hat keinen eindeutig Schwersten")
    views = tuple(
        ScaleView.from_scale(s, number, mirror and rng.random() < 0.5) for number, s in enumerate(renamed, 1)
    )
    return Round(tuple(renamed), views, top, level)


def explain_with_names(line: str, characters: Sequence[Character]) -> str:
    """Ersetzt a, b, c, d (auch ``2a``) durch die Namen der Figuren."""

    def replace(match: re.Match[str]) -> str:
        count, letter = match.group(1), match.group(2)
        name = characters[NAMES.index(letter)].name
        return f"{count}× {name}" if count else name

    return re.sub(r"\b(\d*)([abcd])\b", replace, line)


# --------------------------------------------------------------------------
# Raetselquelle
# --------------------------------------------------------------------------


class RoundSource(Protocol):
    def next_round(self, level: int) -> Round: ...


class CatalogRounds:
    """Zieht Raetsel einer Stufe aus dem Katalog, ohne Wiederholung.

    Sind alle Raetsel einer Stufe gespielt, beginnt sie neu gemischt von vorn
    (ausser mit ``repeat=False``).

    Der Katalog wird einmal geladen (~0,3 s) und nur nach Stufen sortiert;
    die einzelnen Waagen werden erst beim Ziehen gelesen. Raetsel mit
    Vielfachen wie ``2b < 2a`` werden uebersprungen.
    """

    def __init__(
        self,
        entries: Iterable[Sequence[object]] | None = None,
        rng: random.Random | None = None,
        repeat: bool = True,
    ) -> None:
        if entries is None:
            from .catalog import load_catalog

            entries = load_catalog()["puzzles"]  # type: ignore[assignment]
        self.rng = rng or random.Random()
        self.repeat = repeat
        self.all_by_level: dict[int, list[tuple[str, ...]]] = {}
        for entry in entries:  # type: ignore[union-attr]
            self.all_by_level.setdefault(int(entry[-1]), []).append(tuple(entry[:-1]))  # type: ignore[arg-type]
        self.by_level: dict[int, list[tuple[str, ...]]] = {}
        for level in self.all_by_level:
            self._refill(level)

    def _refill(self, level: int) -> None:
        pool = list(self.all_by_level[level])
        self.rng.shuffle(pool)
        self.by_level[level] = pool

    @property
    def levels(self) -> list[int]:
        return sorted(self.by_level)

    def next_round(self, level: int) -> Round:
        for attempt in range(2):
            pool = self.by_level[level]
            while pool:
                scales = [Scale.parse(text) for text in pool.pop()]
                if all(gcd(*s.left, *s.right) == 1 for s in scales):
                    return round_from_scales(scales, level, self.rng)
            if not self.repeat:
                break
            self._refill(level)  # alle gespielt: von vorn, neu gemischt
        raise RuntimeError(f"Keine Raetsel der Stufe {level} mehr uebrig")


# --------------------------------------------------------------------------
# Schwierigkeit
# --------------------------------------------------------------------------


LEVEL_TITLES = {1: "Leicht", 2: "Mittel", 3: "Schwer", 4: "Profi"}


class Difficulty(Protocol):
    @property
    def level(self) -> int: ...

    def record(self, correct: bool) -> None: ...


@dataclass
class FixedDifficulty:
    level: int

    def record(self, correct: bool) -> None:
        pass


@dataclass
class RisingDifficulty:
    """Startet leicht; drei Richtige in Folge heben die Stufe, ein Fehler senkt sie."""

    level: int = 1
    needed: int = 3
    highest: int = 4
    _run: int = 0

    def record(self, correct: bool) -> None:
        if correct:
            self._run += 1
            if self._run >= self.needed and self.level < self.highest:
                self.level += 1
                self._run = 0
        else:
            self._run = 0
            self.level = max(1, self.level - 1)


DIFFICULTIES: dict[str, Callable[[], Difficulty]] = {
    "Steigend": RisingDifficulty,
    "Leicht": lambda: FixedDifficulty(1),
    "Mittel": lambda: FixedDifficulty(2),
    "Schwer": lambda: FixedDifficulty(3),
    "Profi": lambda: FixedDifficulty(4),
}


# --------------------------------------------------------------------------
# Eine Partie
# --------------------------------------------------------------------------


Clock = Callable[[], float]


@dataclass(frozen=True)
class Feedback:
    correct: bool
    answer: int
    points: int
    streak: int
    level_before: int
    level_after: int


@dataclass(frozen=True)
class Result:
    rounds: int
    correct: int
    wrong: int
    points: int
    best_streak: int


def points_for(level: int, streak: int) -> int:
    """10 Punkte je Stufe, dazu 2 Punkte je Richtige in Folge (hoechstens 20)."""

    return 10 * level + min(2 * (streak - 1), 20)


class GameSession:
    """Eine Partie: auf Zeit (``time_limit`` Sekunden) oder zum Ueben (``None``)."""

    def __init__(
        self,
        source: RoundSource,
        difficulty: Difficulty,
        time_limit: float | None = 60,
        clock: Clock = time.monotonic,
        characters: Sequence[Character] | None = None,
    ) -> None:
        self.source = source
        self.difficulty = difficulty
        self.time_limit = time_limit
        self.clock = clock
        self.characters = tuple(characters or pick_characters(random.Random()))
        self.rounds = self.correct = self.wrong = self.points = 0
        self.streak = self.best_streak = 0
        self.current: Round | None = None
        self.started_at: float | None = None

    @property
    def is_practice(self) -> bool:
        return self.time_limit is None

    def start(self) -> Round:
        self.started_at = self.clock()
        return self.next_round()

    def next_round(self) -> Round:
        self.current = self.source.next_round(self.difficulty.level)
        return self.current

    def time_left(self) -> float | None:
        if self.time_limit is None or self.started_at is None:
            return self.time_limit
        return max(0.0, self.time_limit - (self.clock() - self.started_at))

    def is_over(self) -> bool:
        left = self.time_left()
        return left is not None and left <= 0

    def answer(self, choice: int) -> Feedback:
        """Wertet eine Antwort zur aktuellen Runde aus."""

        if self.current is None:
            raise RuntimeError("Es laeuft keine Runde")
        current, self.current = self.current, None
        correct = current.is_correct(choice)
        level_before = self.difficulty.level
        self.rounds += 1
        points = 0
        if correct:
            self.correct += 1
            self.streak += 1
            self.best_streak = max(self.best_streak, self.streak)
            points = points_for(current.level, self.streak)
            self.points += points
        else:
            self.wrong += 1
            self.streak = 0
        self.difficulty.record(correct)
        return Feedback(correct, current.answer, points, self.streak, level_before, self.difficulty.level)

    def result(self) -> Result:
        return Result(self.rounds, self.correct, self.wrong, self.points, self.best_streak)


# --------------------------------------------------------------------------
# Bestenliste
# --------------------------------------------------------------------------


class Highscores:
    """Bester Punktestand je Modus, gespeichert als kleine JSON-Datei."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        self.best: dict[str, int] = {}
        if path is not None and path.exists():
            try:
                self.best = {k: int(v) for k, v in json.loads(path.read_text(encoding="utf-8")).items()}
            except (ValueError, OSError, AttributeError):
                self.best = {}

    @staticmethod
    def key(difficulty: str, time_limit: float | None) -> str:
        return f"{difficulty}/{int(time_limit)}s" if time_limit else f"{difficulty}/ueben"

    def get(self, key: str) -> int:
        return self.best.get(key, 0)

    def submit(self, key: str, points: int) -> bool:
        """Traegt ein; ``True`` bei neuem Rekord."""

        if points <= self.best.get(key, 0):
            return False
        self.best[key] = points
        if self.path is not None:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self.path.write_text(json.dumps(self.best, indent=2, sort_keys=True), encoding="utf-8")
            except OSError:
                pass
        return True


DEFAULT_HIGHSCORES = Path.home() / ".waagenspiel" / "bestenliste.json"
