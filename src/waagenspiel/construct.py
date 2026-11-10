"""Baukasten-Generator: Raetsel gezielt nach einem Loesungsplan bauen
(docs/03, Abschnitt 10).

Statt Waagen blind zu ziehen, merkt sich der Generator, was ein Spieler aus den
bisher gewaehlten Waagen schon schliessen kann, und waehlt nur Waagen, die nach
der Bausteinregel etwas Neues zeigen:

    Links n Gegenstaende, die alle mindestens so schwer wie x sind (der Rest
    links faellt weg), rechts m Einheiten, die alle hoechstens so schwer wie h
    sind, und n >= m. Dann ist x leichter als h (bei Gleichgewicht braucht es
    zusaetzlich etwas Echtes: Weglassen, n > m oder einen echten Vergleich).

Eine Einheit ist ein einzelner Gegenstand oder - nur fuer Stufe 3 - ein
ganzer Block wie ``c + d``, von dem eine Waage zeigt, dass er hoechstens so
schwer ist wie ein Gegenstand (``c + d < a``).

Die Regel dient nur der Auswahl. Ob das Ergebnis gilt, minimal ist und die
gewuenschte Stufe hat, wird am Ende exakt geprueft.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations
from typing import Sequence

from .puzzle import (
    Puzzle,
    PuzzleGenerator,
    Scale,
    Settings,
    Side,
    _rename_weights,
    canonical_form,
    forces_heaviest,
    is_minimal,
    level_of,
    solve,
    true_scales,
)

Pair = tuple[int, int]


def _items(side: Side) -> list[int]:
    return [i for i, k in enumerate(side) for _ in range(k)]


def _orientations(scale: Scale) -> list[tuple[Side, Side, bool]]:
    """(leichte Seite, schwere Seite, echt kleiner) in allen Leserichtungen."""

    if scale.operator == "<":
        return [(scale.left, scale.right, True)]
    return [(scale.left, scale.right, False), (scale.right, scale.left, False)]


@dataclass(frozen=True)
class Block:
    """Eine Summe aus mindestens zwei Gegenstaenden, die hoechstens so schwer
    ist wie ``heavier`` (echt leichter, wenn ``strict``)."""

    items: Side
    heavier: int
    strict: bool


@dataclass
class Knowledge:
    """Was ein Spieler aus den gewaehlten Waagen nach der Bausteinregel weiss."""

    use_facts: bool = True
    use_blocks: bool = False
    lt: set[Pair] = field(default_factory=set)  # u < v
    le: set[Pair] = field(default_factory=set)  # u <= v (enthaelt lt)
    blocks: list[Block] = field(default_factory=list)

    def copy(self) -> "Knowledge":
        return Knowledge(self.use_facts, self.use_blocks, set(self.lt), set(self.le), list(self.blocks))

    def at_most(self, u: int, h: int) -> tuple[bool, bool]:
        """(u <= h bekannt, echt)."""

        if u == h:
            return True, False
        if not self.use_facts:
            return False, False
        return (u, h) in self.le, (u, h) in self.lt

    def _units(self, heavy: Side, h: int) -> tuple[int, bool] | None:
        """Kleinste Zahl von Einheiten <= h, die die schwere Seite abdeckt."""

        best: tuple[int, bool] | None = None
        options: list[tuple[Side | None, Block | None]] = [(heavy, None)]
        if self.use_blocks:
            for block in self.blocks:
                if all(b <= s for b, s in zip(block.items, heavy)):
                    rest = tuple(s - b for s, b in zip(heavy, block.items))
                    options.append((rest, block))  # type: ignore[arg-type]
        for rest, block in options:
            strict = False
            units = 0
            if block is not None:
                ok, block_strict = self.at_most(block.heavier, h)
                if not ok:
                    continue
                units, strict = 1, block.strict or block_strict
            ok = True
            for item in _items(rest):  # type: ignore[arg-type]
                known, item_strict = self.at_most(item, h)
                if not known:
                    ok = False
                    break
                units += 1
                strict = strict or item_strict
            if ok and (best is None or (units, not strict) < (best[0], not best[1])):
                best = (units, strict)
        return best

    def proves(self, scale: Scale, x: int, h: int) -> str | None:
        """``"lt"`` fuer x < h, ``"le"`` fuer x <= h, sonst ``None``."""

        result = None
        for light, heavy, strict in _orientations(scale):
            cover = self._units(heavy, h)
            if cover is None or cover[0] == 0:
                continue
            m, heavy_strict = cover
            n, dropped, light_strict = 0, 0, False
            for item in _items(light):
                known, item_strict = self.at_most(x, item)
                if known:
                    n += 1
                    light_strict = light_strict or item_strict
                else:
                    dropped += 1
            if n < m or n == 0:
                continue
            if strict or dropped or n > m or heavy_strict or light_strict:
                return "lt"
            result = "le"
        return result

    def learn(self, scales: Sequence[Scale]) -> None:
        """Wendet Bausteinregel und Transitivitaet an, bis nichts Neues folgt."""

        for scale in scales:
            for light, heavy, strict in _orientations(scale):
                if sum(light) >= 2 and sum(heavy) == 1:
                    block = Block(light, heavy.index(1), strict)
                    if block not in self.blocks:
                        self.blocks.append(block)
        changed = True
        while changed:
            changed = False
            for scale in scales:
                for x in range(4):
                    for h in range(4):
                        if x == h or (x, h) in self.lt:
                            continue
                        found = self.proves(scale, x, h)
                        if found == "lt":
                            self.lt.add((x, h))
                            self.le.add((x, h))
                            changed = True
                        elif found == "le" and (x, h) not in self.le:
                            self.le.add((x, h))
                            changed = True
            if self.use_facts:
                for (u, v) in list(self.le):
                    for (v2, w) in list(self.le):
                        if v == v2 and u != w:
                            if ((u, v) in self.lt or (v2, w) in self.lt) and (u, w) not in self.lt:
                                self.lt.add((u, w))
                                self.le.add((u, w))
                                changed = True
                            elif (u, w) not in self.le:
                                self.le.add((u, w))
                                changed = True


def _simpler(level: int) -> Knowledge:
    """Wissen nach der Regel der naechstniedrigeren Stufe."""

    return Knowledge(use_facts=level - 1 >= 2, use_blocks=False)


class ConstructiveGenerator(PuzzleGenerator):
    """Baut Raetsel der Stufen 1 bis 3 gezielt nach einem Loesungsplan.

    Stufe 1: nur Waagen, die fuer sich allein etwas ueber den Schwersten
    zeigen. Stufe 2: Bausteinregel mit bekannten Vergleichen. Stufe 3:
    zusaetzlich ganze Bloecke wie ``c + d``. Stufe 4 laesst sich so nicht
    gezielt bauen; dafuer gibt es den Katalog.
    """

    def __init__(self, settings: Settings = Settings(), seed: int | None = None) -> None:
        super().__init__(settings, seed)
        highest = 2 if settings.max_side == 1 else 3  # Satz 3: ein Gegenstand pro Seite reicht nur bis Stufe 2
        self.levels = [
            level for level in range(1, highest + 1)
            if settings.min_difficulty <= level <= settings.max_difficulty
        ]
        if not self.levels:
            raise ValueError("Der Baukasten baut nur die Stufen 1 bis 3; Stufe 4 gibt es im Katalog")

    def _weights_a_top(self) -> tuple[int, ...]:
        weights = list(self._weights())
        top = weights.index(max(weights))
        weights[0], weights[top] = weights[top], weights[0]
        return tuple(weights)

    def plan(self, weights: Sequence[int], level: int, count: int) -> list[Scale] | None:
        """Waehlt nacheinander Waagen, die nach dem Plan etwas Neues zeigen."""

        tilted, balanced = true_scales(weights, self.settings.max_side, self.settings.allow_multiples)
        pool = tilted + balanced
        knowledge = Knowledge(use_facts=level >= 2, use_blocks=level >= 3)
        goals = {(x, 0) for x in (1, 2, 3)}
        chosen: list[Scale] = []
        for _ in range(count):
            useful = []
            for scale in self.random.sample(pool, min(len(pool), 60)):
                if scale in chosen:
                    continue
                trial = knowledge.copy()
                trial.learn(chosen + [scale])
                gained = trial.lt - knowledge.lt
                if gained:
                    # Was die naechstniedrigere Stufe nicht schafft, ist fuer
                    # diesen Plan besonders wertvoll.
                    simpler = _simpler(level)
                    simpler.learn(chosen + [scale])
                    special = len(gained - simpler.lt)
                    useful.append((scale, trial, 1 + 2 * len(gained & goals) + 3 * special))
            if not useful:
                return None
            scale, knowledge, _ = self.random.choices(useful, weights=[u[2] for u in useful])[0]
            chosen.append(scale)
            if goals <= knowledge.lt:
                break
        if not goals <= knowledge.lt:
            return None
        if level > 1:
            simpler = _simpler(level)
            simpler.learn(chosen)
            if goals <= simpler.lt:
                return None  # das waere schon mit der leichteren Regel loesbar
        return chosen

    def attempt(self) -> Puzzle | None:
        level = self.random.choice(self.levels)
        count = self.random.choice(self.settings.scale_counts)
        weights = self._weights_a_top()
        scales = self.plan(weights, level, count)
        if scales is None or len(scales) not in self.settings.scale_counts:
            return None
        if not forces_heaviest(scales, 0) or not is_minimal(scales, 0):
            return None
        permutation, key = canonical_form(scales)
        if key in self.seen:
            return None
        actual = level_of(list(key), top=0)
        if not self.settings.min_difficulty <= actual <= self.settings.max_difficulty:
            return None
        self.seen.add(key)
        return Puzzle(key, _rename_weights(weights, permutation), solve(key))
