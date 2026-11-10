"""Raetsel fuer das Waagenspiel: pruefen, erklaeren und zufaellig erzeugen.

Umsetzung von ``docs/03_einfache_herleitung.md``:

- Eine Waage wird nur gekuerzt und fest ausgerichtet, nicht durch den ggT
  geteilt (Abschnitt 4.1).
- Zwei Raetsel sind gleich, wenn sie bis auf Umbenennung aus denselben Waagen
  bestehen (Abschnitt 4.1).
- Eine Waage ist ueberfluessig, wenn der Schwerste auch ohne sie eindeutig ist
  (Abschnitt 4.2).
- Gleich schwere Gegenstaende sind erlaubt, nur der Schwerste muss echt am
  schwersten sein (Abschnitt 1).
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from functools import lru_cache
from fractions import Fraction
from itertools import combinations, permutations, product
from math import gcd, lcm
from typing import Iterable, Iterator, Literal, Mapping, Sequence

import z3

NAMES: tuple[str, ...] = ("a", "b", "c", "d")
MAX_SIDE = 3

Side = tuple[int, int, int, int]
Operator = Literal["<", "="]
Permutation = tuple[int, int, int, int]

# Umbenennungen, die a festhalten: a ist nach der Kanonisierung immer der Schwerste.
LOWER_PERMUTATIONS: tuple[Permutation, ...] = tuple(
    p for p in permutations(range(4)) if p[0] == 0  # type: ignore[misc]
)


# --------------------------------------------------------------------------
# Darstellung
# --------------------------------------------------------------------------


def side_text(side: Sequence[int]) -> str:
    """``(2, 0, 1, 0)`` wird zu ``"2a + c"``."""

    parts = [f"{count}{name}" if count > 1 else name for name, count in zip(NAMES, side) if count]
    return " + ".join(parts)


def _parse_side(text: str) -> Side:
    counts = [0, 0, 0, 0]
    for term in text.split("+"):
        term = term.strip()
        if not term:
            raise ValueError(f"Leerer Summand in {text!r}")
        name = term[-1]
        if name not in NAMES:
            raise ValueError(f"Unbekannter Gegenstand {name!r} in {text!r}")
        factor = term[:-1].strip().rstrip("*·").strip()
        counts[NAMES.index(name)] += int(factor) if factor else 1
    return tuple(counts)  # type: ignore[return-value]


# --------------------------------------------------------------------------
# Waagen
# --------------------------------------------------------------------------


@dataclass(frozen=True, order=True)
class Scale:
    """Eine Waage in Normalform.

    Bei ``"<"`` steht die leichte Seite links. Gemeinsame Gegenstaende werden
    gekuerzt. Bei ``"="`` steht die lexikographisch groessere Seite links.
    """

    left: Side
    operator: Operator
    right: Side

    def __post_init__(self) -> None:
        if self.operator not in ("<", "="):
            raise ValueError("operator muss '<' oder '=' sein")
        left, right = tuple(self.left), tuple(self.right)
        for side in (left, right):
            if len(side) != 4 or any(not isinstance(v, int) or isinstance(v, bool) or v < 0 for v in side):
                raise ValueError("Eine Seite braucht vier nichtnegative ganze Zahlen")
            if not 1 <= sum(side) <= MAX_SIDE:
                raise ValueError(f"Auf jeder Seite muessen 1 bis {MAX_SIDE} Gegenstaende liegen")
        common = tuple(min(l, r) for l, r in zip(left, right))
        left = tuple(l - c for l, c in zip(left, common))
        right = tuple(r - c for r, c in zip(right, common))
        if not any(left) or not any(right):
            raise ValueError("Nach dem Kuerzen waere eine Seite leer")
        if self.operator == "=" and left < right:
            left, right = right, left
        object.__setattr__(self, "left", left)
        object.__setattr__(self, "right", right)

    @classmethod
    def parse(cls, text: str) -> "Scale":
        """Liest ``"b + c < a"``, ``"3d > 2a"`` oder ``"a = b + c"``."""

        for symbol in ("<", ">", "="):
            if symbol in text:
                left_text, right_text = text.split(symbol, 1)
                left, right = _parse_side(left_text), _parse_side(right_text)
                if symbol == ">":
                    return cls(right, "<", left)
                return cls(left, symbol, right)  # type: ignore[arg-type]
        raise ValueError(f"Keine Waage erkannt: {text!r}")

    @classmethod
    def from_mapping(cls, data: Mapping[str, object]) -> "Scale":
        """Liest das JSON-Format ``{"left": {...}, "operator": "<", "right": {...}}``."""

        def side(mapping: object) -> Side:
            assert isinstance(mapping, Mapping)
            return tuple(int(mapping.get(name, 0)) for name in NAMES)  # type: ignore[return-value]

        return cls(side(data["left"]), data["operator"], side(data["right"]))  # type: ignore[arg-type]

    @property
    def vector(self) -> tuple[int, int, int, int]:
        """z = L - R; die Waage sagt z·w < 0 bzw. z·w = 0."""

        return tuple(l - r for l, r in zip(self.left, self.right))  # type: ignore[return-value]

    def renamed(self, permutation: Permutation) -> "Scale":
        """Benennt Gegenstand i in Gegenstand ``permutation[i]`` um."""

        def move(side: Side) -> Side:
            result = [0, 0, 0, 0]
            for old, new in enumerate(permutation):
                result[new] = side[old]
            return tuple(result)  # type: ignore[return-value]

        return Scale(move(self.left), self.operator, move(self.right))

    def holds(self, weights: Sequence[int | Fraction]) -> bool:
        left = sum(k * w for k, w in zip(self.left, weights))
        right = sum(k * w for k, w in zip(self.right, weights))
        return left < right if self.operator == "<" else left == right

    def to_json(self) -> dict[str, object]:
        return {
            "left": {n: k for n, k in zip(NAMES, self.left) if k},
            "operator": self.operator,
            "right": {n: k for n, k in zip(NAMES, self.right) if k},
            "display": str(self),
        }

    def __str__(self) -> str:
        return f"{side_text(self.left)} {self.operator} {side_text(self.right)}"


# --------------------------------------------------------------------------
# Satz 1: Wer ist eindeutig der Schwerste?
# --------------------------------------------------------------------------

_W = z3.Reals("a b c d")
_POSITIVE = [w > 0 for w in _W]


def _expression(scale: Scale) -> z3.BoolRef:
    left = sum((k * _W[i] for i, k in enumerate(scale.left) if k), z3.RealVal(0))
    right = sum((k * _W[i] for i, k in enumerate(scale.right) if k), z3.RealVal(0))
    return left < right if scale.operator == "<" else left == right


def _solver(scales: Iterable[Scale], extra: Iterable[z3.BoolRef] = ()) -> z3.Solver:
    solver = z3.Solver()
    solver.add(*_POSITIVE, *(_expression(s) for s in scales), *extra)
    return solver


def satisfiable(scales: Iterable[Scale]) -> bool:
    return _solver(scales).check() == z3.sat


def forces_lighter(scales: Iterable[Scale], lighter: int, heavier: int) -> bool:
    """Folgt w_lighter < w_heavier fuer alle positiven Gewichte?

    Gibt es keine Loesung mit w_lighter >= w_heavier, folgt die Aussage
    (Satz 1). Ein unerfuellbares System liefert ebenfalls ``True``; deshalb
    prueft :func:`heaviest` die Erfuellbarkeit vorher.
    """

    return _solver(scales, [_W[lighter] >= _W[heavier]]).check() == z3.unsat


def heaviest(scales: Sequence[Scale]) -> int | None:
    """Index des eindeutig schwersten Gegenstands oder ``None``."""

    solver = _solver(scales)
    if solver.check() != z3.sat:
        return None
    model = solver.model()
    values = [model.eval(w, model_completion=True).as_fraction() for w in _W]
    top = max(values)
    if values.count(top) > 1:
        return None  # dieses Modell ist selbst ein Gegenbeispiel
    candidate = values.index(top)
    return candidate if forces_heaviest(scales, candidate) else None


def _sample_weights(count: int = 600, seed: int = 20261110) -> list[tuple[int, ...]]:
    rng = random.Random(seed)
    samples = [tuple(rng.randint(1, 12) for _ in range(4)) for _ in range(count // 2)]
    samples += [tuple(rng.randint(1, 60) for _ in range(4)) for _ in range(count - len(samples))]
    return samples


_SAMPLES = _sample_weights()


def refuted_by_sample(scales: Sequence[Scale], top: int) -> bool:
    """Schneller, aber nur einseitiger Test: ``True`` heisst sicher, dass
    ``top`` nicht eindeutig am schwersten ist (ein Gegenbeispiel wurde
    gefunden). ``False`` beweist nichts."""

    for weights in _SAMPLES:
        if all(s.holds(weights) for s in scales) and any(
            weights[x] >= weights[top] for x in range(4) if x != top
        ):
            return True
    return False


def forces_heaviest(scales: Sequence[Scale], top: int) -> bool:
    """Exakt: Jede Loesung hat ``top`` echt am schwersten (Satz 1).

    Setzt voraus, dass die Waagen erfuellbar sind."""

    if refuted_by_sample(scales, top):
        return False
    return all(forces_lighter(scales, x, top) for x in range(4) if x != top)


def is_minimal(scales: Sequence[Scale], top: int | None = None) -> bool:
    """Der Schwerste ist eindeutig, aber ohne jede einzelne Waage nicht mehr.

    Ohne eine Waage gibt es mehr Loesungen, darunter alle alten. Erzwingen die
    uebrigen Waagen ueberhaupt einen Schwersten, ist es also derselbe. Deshalb
    genuegt es, fuer den bisherigen Schwersten zu pruefen. Ist ``top`` schon
    als eindeutig Schwerster bekannt, kann er uebergeben werden.
    """

    if top is None:
        top = heaviest(scales)
    if len(set(scales)) != len(scales) or top is None:
        return False
    return not any(forces_heaviest(scales[:i] + scales[i + 1 :], top) for i in range(len(scales)))


# --------------------------------------------------------------------------
# Gleichheit von Raetseln
# --------------------------------------------------------------------------


def _rename_weights(weights: Sequence[int], permutation: Permutation) -> tuple[int, ...]:
    result = [0, 0, 0, 0]
    for old, new in enumerate(permutation):
        result[new] = weights[old]
    return tuple(result)


def _key_under(scales: Iterable[Scale], permutation: Permutation) -> tuple[Scale, ...]:
    return tuple(sorted(s.renamed(permutation) for s in scales))


def canonical_form(scales: Sequence[Scale]) -> tuple[Permutation, tuple[Scale, ...]]:
    """Benennt den Schwersten in ``a`` um und waehlt unter den sechs
    Umbenennungen von b, c, d die kleinste sortierte Waagenliste.

    Zwei Raetsel sind genau dann gleich, wenn ihre kanonischen Formen gleich
    sind. Liefert zusaetzlich die verwendete Umbenennung.
    """

    top = heaviest(scales)
    if top is None:
        raise ValueError("Ohne eindeutig Schwersten gibt es keine kanonische Form")
    to_a = list(range(4))
    to_a[top], to_a[0] = 0, top  # vertauscht den Schwersten mit a
    best: tuple[Permutation, tuple[Scale, ...]] | None = None
    for lower in LOWER_PERMUTATIONS:
        permutation = tuple(lower[to_a[i]] for i in range(4))
        key = _key_under(scales, permutation)  # type: ignore[arg-type]
        if best is None or key < best[1]:
            best = (permutation, key)  # type: ignore[assignment]
    assert best is not None
    return best


# --------------------------------------------------------------------------
# Satz 2: Loesungsweg ueber das Farkas-Zertifikat
# --------------------------------------------------------------------------


def _add(*sides: Sequence[int]) -> list[int]:
    return [sum(values) for values in zip(*sides)]


def _scaled(side: Sequence[int], factor: int) -> list[int]:
    return [factor * v for v in side]


def _term(count: int, index: int) -> str:
    return f"{count}{NAMES[index]}" if count > 1 else NAMES[index]


@dataclass(frozen=True)
class Use:
    """Eine Waage, wie sie im Loesungsweg benutzt wird (Gleichgewichte
    gegebenenfalls andersherum gelesen), ``count``-mal genommen."""

    number: int
    left: Side
    operator: Operator
    right: Side
    count: int

    def __str__(self) -> str:
        prefix = f"{self.count}-mal " if self.count > 1 else ""
        return f"{prefix}Waage {self.number}: {side_text(self.left)} {self.operator} {side_text(self.right)}"


@dataclass(frozen=True)
class Derivation:
    """Warum ``lighter`` leichter ist als ``heavier``.

    Mit den Vektoren z = L - R der benutzten Waagen gilt exakt

        factor·(e_lighter - e_heavier) = Σ count·z - dropped,   dropped >= 0.

    In Worten: Man addiert die Waagen, kuerzt gleiche Gegenstaende und laesst
    auf der leichten Seite etwas weg (Satz 2).
    """

    lighter: int
    heavier: int
    uses: tuple[Use, ...]
    factor: int

    @property
    def scale_copies(self) -> int:
        """Wie viele Waagen insgesamt addiert werden (Mass fuer die Schwierigkeit)."""

        return sum(use.count for use in self.uses)

    def steps(self) -> list[str]:
        x, h = NAMES[self.lighter], NAMES[self.heavier]
        k = self.factor
        lines = [str(use) for use in self.uses]
        left = _add(*(_scaled(u.left, u.count) for u in self.uses))
        right = _add(*(_scaled(u.right, u.count) for u in self.uses))
        operator = "<" if any(u.operator == "<" for u in self.uses) else "="
        if self.scale_copies > 1:
            lines.append(f"Zusammen: {side_text(left)} {operator} {side_text(right)}")
        common = [min(l, r) for l, r in zip(left, right)]
        if any(common):
            left = [l - c for l, c in zip(left, common)]
            right = [r - c for r, c in zip(right, common)]
            lines.append(
                f"Auf beiden Seiten {side_text(common)} wegnehmen: "
                f"{side_text(left)} {operator} {side_text(right)}"
            )
        dropped = list(left)
        dropped[self.lighter] -= k
        if any(dropped):
            operator = "<"
            left = [0, 0, 0, 0]
            left[self.lighter] = k
            lines.append(
                f"Links {side_text(dropped)} weglassen, das wiegt mehr als nichts: "
                f"{side_text(left)} < {side_text(right)}"
            )
        m = right[self.heavier]
        if k == m == 1:
            lines.append(f"Also ist {x} leichter als {h}.")
        elif k == m:
            lines.append(f"Durch {k} teilen: {x} < {h}. Also ist {x} leichter als {h}.")
        else:
            lines.append(
                f"{_term(m, self.heavier)} wiegt weniger als {_term(k, self.heavier)}, "
                f"also {_term(k, self.lighter)} < {_term(k, self.heavier)} "
                f"und {x} ist leichter als {h}."
            )
        return lines

    def to_json(self) -> dict[str, object]:
        return {"lighter": NAMES[self.lighter], "heavier": NAMES[self.heavier], "steps": self.steps()}


def derive(scales: Sequence[Scale], lighter: int, heavier: int) -> Derivation:
    """Einfachster Loesungsweg fuer ``lighter < heavier``.

    Zuerst wird die kleinste Teilmenge der Waagen gesucht, die die Aussage
    schon erzwingt. Auf ihr bestimmt ein lineares Programm Faktoren nach
    Satz 2 mit moeglichst kleiner Summe.
    """

    subset: tuple[int, ...] | None = None
    for size in range(1, len(scales) + 1):
        for candidate in combinations(range(len(scales)), size):
            chosen = [scales[i] for i in candidate]
            if satisfiable(chosen) and forces_lighter(chosen, lighter, heavier):
                subset = candidate
                break
        if subset is not None:
            break
    if subset is None:
        raise ValueError(f"{NAMES[lighter]} < {NAMES[heavier]} folgt nicht aus den Waagen")

    opt = z3.Optimize()
    forward, backward = [], []  # Vielfache von L-R bzw. R-L (nur bei Gleichgewicht)
    for i in subset:
        f = z3.Real(f"f{i}")
        opt.add(f >= 0)
        forward.append(f)
        if scales[i].operator == "=":
            b = z3.Real(f"b{i}")
            opt.add(b >= 0)
            backward.append(b)
        else:
            backward.append(z3.RealVal(0))
    drop = [z3.Real(f"drop_{name}") for name in NAMES]
    opt.add(*(d >= 0 for d in drop))
    target = [0, 0, 0, 0]
    target[lighter], target[heavier] = 1, -1
    for coord in range(4):
        combined = sum(
            ((f - b) * scales[i].vector[coord] for i, f, b in zip(subset, forward, backward)),
            z3.RealVal(0),
        )
        opt.add(combined - drop[coord] == target[coord])
    # Kleine Faktoren ergeben kurze Loesungswege. Weglassen beim Schwersten
    # wird stark bestraft, weil es den Text unnoetig verschachtelt.
    opt.minimize(sum(forward) + sum(backward) + sum(drop) + 100 * drop[heavier])
    if opt.check() != z3.sat:  # pragma: no cover - nach Satz 2 ausgeschlossen
        raise RuntimeError("Kein Farkas-Zertifikat gefunden")
    model = opt.model()

    def value(term: z3.ArithRef) -> Fraction:
        return model.eval(term, model_completion=True).as_fraction()

    coefficients = [(value(f), value(b)) for f, b in zip(forward, backward)]
    factor = lcm(*(c.denominator for pair in coefficients for c in pair), *(value(d).denominator for d in drop))
    uses = []
    for i, (f, b) in zip(subset, coefficients):
        net = (f - b) * factor
        scale = scales[i]
        if net > 0:
            uses.append(Use(i + 1, scale.left, scale.operator, scale.right, int(net)))
        elif net < 0:  # Gleichgewicht andersherum gelesen
            uses.append(Use(i + 1, scale.right, "=", scale.left, int(-net)))
    return Derivation(lighter, heavier, tuple(uses), factor)


def explain(scales: Sequence[Scale]) -> tuple[Derivation, ...]:
    """Loesungswege fuer alle drei Vergleiche mit dem Schwersten."""

    top = heaviest(scales)
    if top is None:
        raise ValueError("Der Schwerste ist nicht eindeutig")
    return tuple(derive(scales, x, top) for x in range(4) if x != top)


# --------------------------------------------------------------------------
# Raetsel und Generator
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Puzzle:
    """Ein kanonisches Raetsel: ``a`` ist der Schwerste."""

    scales: tuple[Scale, ...]
    weights: tuple[int, ...]
    derivations: tuple[Derivation, ...]

    @property
    def difficulty(self) -> int:
        """Groesste Zahl addierter Waagen in einem der drei Loesungswege.

        1: direkt ablesen oder weglassen, 2: zwei Waagen kombinieren,
        3 und mehr: Waagen mehrfach nehmen.

        Das ist eine Faustregel: :func:`derive` minimiert die Summe der
        Faktoren vor dem Ganzzahligmachen, nicht die Zahl der Kopien danach.
        """

        return max(d.scale_copies for d in self.derivations)

    def renamed(self, permutation: Permutation, order: Sequence[int] | None = None) -> "Puzzle":
        """Benennt die Gegenstaende um und ordnet die Waagen optional neu.

        Fuer das Spiel, damit die Antwort nicht immer ``a`` ist.
        """

        scales = [s.renamed(permutation) for s in self.scales]
        if order is not None:
            scales = [scales[i] for i in order]
        weights = _rename_weights(self.weights, permutation)
        return Puzzle(tuple(scales), weights, explain(scales))

    @property
    def heaviest(self) -> int:
        return self.derivations[0].heavier

    def to_json(self) -> dict[str, object]:
        return {
            "scales": [s.to_json() for s in self.scales],
            "heaviest": NAMES[self.heaviest],
            "example_weights": dict(zip(NAMES, self.weights)),
            "difficulty": self.difficulty,
            "hints": [d.to_json() for d in self.derivations],
        }


def _all_sides(max_side: int) -> list[Side]:
    return [s for s in product(range(max_side + 1), repeat=4) if 1 <= sum(s) <= max_side]  # type: ignore[misc]


def true_scales(
    weights: Sequence[int], max_side: int, allow_multiples: bool = False
) -> tuple[list[Scale], list[Scale]]:
    """Alle Waagen mit hoechstens ``max_side`` Gegenstaenden pro Seite, die bei
    diesen Gewichten wahr sind, getrennt nach Neigung und Gleichgewicht.

    Ohne ``allow_multiples`` fallen Waagen wie ``2c < 2a`` oder ``3c = 3d`` weg:
    Sie sind nur vervielfachte einfachere Waagen und taeuschen Schwierigkeit vor.
    """

    tilted: set[Scale] = set()
    balanced: set[Scale] = set()
    for left, right, as_tilted, as_balanced in _side_pairs(max_side, allow_multiples):
        lw = sum(k * w for k, w in zip(left, weights))
        rw = sum(k * w for k, w in zip(right, weights))
        if lw < rw:
            tilted.add(as_tilted)
        elif lw == rw:
            balanced.add(as_balanced)
    return sorted(tilted), sorted(balanced)


@lru_cache(maxsize=None)
def _side_pairs(max_side: int, allow_multiples: bool) -> tuple[tuple[Side, Side, Scale, Scale], ...]:
    """Alle Paare disjunkter Seiten, mit ihren beiden moeglichen Waagen."""

    sides = _all_sides(max_side)
    pairs = []
    for left, right in product(sides, sides):
        if any(l and r for l, r in zip(left, right)):
            continue
        if not allow_multiples and gcd(*left, *right) > 1:
            continue
        pairs.append((left, right, Scale(left, "<", right), Scale(left, "=", right)))
    return tuple(pairs)


@dataclass(frozen=True)
class Settings:
    scale_counts: tuple[int, ...] = (2, 3)
    max_side: int = 3
    max_weight: int = 8
    balance_share: float = 0.25
    allow_multiples: bool = False
    min_difficulty: int = 1
    max_difficulty: int = 99


LEVELS: dict[str, Settings] = {
    "leicht": Settings(scale_counts=(3,), max_side=1),
    "mittel": Settings(scale_counts=(2, 3), max_side=2, max_difficulty=2),
    "schwer": Settings(scale_counts=(2, 3), max_side=3, min_difficulty=3, max_difficulty=6),
}


class PuzzleGenerator:
    """Erzeugt zufaellige, zielminimale und paarweise verschiedene Raetsel.

    Vorgehen nach Abschnitt 6 der Herleitung: Gewichte ziehen, wahre Waagen
    ziehen (damit ist das System erfuellbar), Satz 1 und Minimalitaet pruefen,
    kanonisieren und Wiederholungen verwerfen.
    """

    def __init__(self, settings: Settings = Settings(), seed: int | None = None) -> None:
        if not 1 <= settings.max_side <= MAX_SIDE:
            raise ValueError(f"max_side muss zwischen 1 und {MAX_SIDE} liegen")
        if settings.max_side == 1 and min(settings.scale_counts) < 3:
            raise ValueError(
                "Mit nur einem Gegenstand pro Seite braucht man mindestens drei Waagen "
                "(Satz 3: von a aus muessen drei andere erreichbar sein)"
            )
        self.settings = settings
        self.random = random.Random(seed)
        self.seen: set[tuple[Scale, ...]] = set()

    def _weights(self) -> tuple[int, ...]:
        while True:
            weights = tuple(self.random.randint(1, self.settings.max_weight) for _ in range(4))
            if list(weights).count(max(weights)) == 1:
                return weights

    def _draw(self, tilted: list[Scale], balanced: list[Scale], count: int) -> list[Scale] | None:
        chosen: list[Scale] = []
        for _ in range(count * 4):
            pool = balanced if balanced and self.random.random() < self.settings.balance_share else tilted
            if not pool:
                return None
            scale = self.random.choice(pool)
            if scale not in chosen:
                chosen.append(scale)
            if len(chosen) == count:
                return chosen
        return None

    def attempt(self) -> Puzzle | None:
        """Ein Versuch; ``None``, wenn die gezogenen Waagen nicht passen."""

        settings = self.settings
        weights = self._weights()
        tilted, balanced = true_scales(weights, settings.max_side, settings.allow_multiples)
        scales = self._draw(tilted, balanced, self.random.choice(settings.scale_counts))
        if scales is None:
            return None
        # Billiger Vorfilter: Ein Gegenstand, der auf keiner Waage liegt, ist unbestimmt.
        if not all(any(s.left[i] or s.right[i] for s in scales) for i in range(4)):
            return None
        # Die gezogenen Gewichte sind eine Loesung, also ist nur ihr Schwerster moeglich.
        top = weights.index(max(weights))
        if not forces_heaviest(scales, top) or not is_minimal(scales, top):
            return None
        permutation, key = canonical_form(scales)
        if key in self.seen:
            return None
        puzzle = Puzzle(key, _rename_weights(weights, permutation), explain(key))
        if not settings.min_difficulty <= puzzle.difficulty <= settings.max_difficulty:
            return None
        self.seen.add(key)
        return puzzle

    def generate(self, count: int, max_attempts: int = 200_000) -> Iterator[Puzzle]:
        made = 0
        for _ in range(max_attempts):
            if made == count:
                return
            puzzle = self.attempt()
            if puzzle is not None:
                made += 1
                yield puzzle
        raise RuntimeError(f"Nach {max_attempts} Versuchen nur {made} von {count} Raetseln gefunden")

    def shuffled(self, puzzle: Puzzle) -> Puzzle:
        """Zufaellige Namen und Reihenfolge fuer das Spiel."""

        names = list(range(4))
        self.random.shuffle(names)
        order = list(range(len(puzzle.scales)))
        self.random.shuffle(order)
        return puzzle.renamed(tuple(names), order)  # type: ignore[arg-type]
