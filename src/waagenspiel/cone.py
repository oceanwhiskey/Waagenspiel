"""Exakter Strahlen-Loeser fuer das Waagenspiel (docs/03, Abschnitt 11).

Die Loesungen eines Systems bilden die Menge

    C = { w : w_v > 0,  z·w < 0 fuer jede geneigte Waage,  y·w = 0 fuer jedes Gleichgewicht }.

Ihr Abschluss K (alle ``<`` durch ``<=`` ersetzt) ist ein spitzer Kegel im
R^4, der von endlich vielen Kantenstrahlen aufgespannt wird. Ist C nicht leer,
dann ist C genau das relative Innere von K, also die Menge der Summen
``Σ λ_i r_i`` mit allen ``λ_i > 0``. Daraus folgt:

- C ist nicht leer  <=>  jede echte Ungleichung (Waagen ``<`` und ``w_v > 0``)
  ist auf mindestens einem Strahl echt erfuellt.
- Aus dem System folgt ``x < h``  <=>  auf allen Strahlen gilt
  ``r_x <= r_h`` und auf mindestens einem ``r_x < r_h``.

Die Strahlen werden mit der Double-Description-Methode berechnet: Man beginnt
mit dem Kegel ``w >= 0`` (Strahlen e_a, ..., e_d) und schneidet nacheinander
mit jeder Bedingung. Alles rechnet mit ganzen Zahlen und ist daher exakt.
"""

from __future__ import annotations

from functools import lru_cache
from math import gcd
from typing import Iterable, Sequence

Vector = tuple[int, int, int, int]
# Eine Bedingung (z, Art): Art "<" heisst z·w < 0, "<=" heisst z·w <= 0,
# "=" heisst z·w = 0. Die Waagen liefern nur "<" und "="; "<=" dient der
# Suche nach Gegenbeispielen.
Constraint = tuple[Vector, str]

UNIT: tuple[Vector, ...] = ((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1))
POSITIVITY: tuple[Vector, ...] = tuple(tuple(-v for v in e) for e in UNIT)  # type: ignore[misc]


def _dot(a: Sequence[int], b: Sequence[int]) -> int:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2] + a[3] * b[3]


def _primitive(v: Sequence[int]) -> Vector:
    g = 0
    for x in v:
        g = gcd(g, x)
    return tuple(x // g for x in v) if g > 1 else tuple(v)  # type: ignore[return-value]


def _rank(rows: list[Vector]) -> int:
    """Rang einer kleinen ganzzahligen Matrix (bruchfreie Elimination)."""

    matrix = [list(r) for r in rows]
    rank = 0
    for col in range(4):
        pivot = next((i for i in range(rank, len(matrix)) if matrix[i][col]), None)
        if pivot is None:
            continue
        matrix[rank], matrix[pivot] = matrix[pivot], matrix[rank]
        p = matrix[rank]
        for i in range(rank + 1, len(matrix)):
            f = matrix[i][col]
            if f:
                matrix[i] = [p[col] * matrix[i][k] - f * p[k] for k in range(4)]
        rank += 1
        if rank == 3:
            return 3  # mehr brauchen wir nie zu wissen
    return rank


class Cone:
    """Kantenstrahlen des abgeschlossenen Loesungskegels eines Systems."""

    __slots__ = ("constraints", "rays", "_satisfiable")

    def __init__(self, constraints: tuple[Constraint, ...], rays: tuple[Vector, ...]) -> None:
        self.constraints = constraints
        self.rays = rays
        self._satisfiable: bool | None = None

    @staticmethod
    def orthant() -> "Cone":
        return Cone((), UNIT)

    def _tight_rank(self, ray: Vector, extra: Vector) -> int:
        rows = [extra]
        rows += [e for e, p in zip(POSITIVITY, ray) if p == 0]
        rows += [z for z, _ in self.constraints if _dot(z, ray) == 0]
        return _rank(rows)

    def add(self, constraint: Constraint) -> "Cone":
        """Schneidet den Kegel mit ``z·w <= 0`` bzw. ``z·w = 0``."""

        z, kind = constraint
        values = [(_dot(z, r), r) for r in self.rays]
        positive = [(v, r) for v, r in values if v > 0]
        negative = [(v, r) for v, r in values if v < 0]
        kept = [r for v, r in values if v == 0 or (kind != "=" and v < 0)]
        new: set[Vector] = set()
        for vp, p in positive:
            for vn, n in negative:
                ray = _primitive([vp * n[k] - vn * p[k] for k in range(4)])
                # Nur Kantenstrahlen behalten: die dort scharfen Bedingungen
                # (mit der neuen) muessen Rang 3 haben.
                if ray not in new and self._tight_rank(ray, z) == 3:
                    new.add(ray)
        rays = tuple(dict.fromkeys(kept + sorted(new)))
        return Cone(self.constraints + (constraint,), rays)

    # --- Fragen ------------------------------------------------------------

    def satisfiable(self) -> bool:
        """Gibt es positive Gewichte, die alle Bedingungen echt erfuellen?"""

        if self._satisfiable is None:
            self._satisfiable = bool(self.rays) and all(
                any(r[v] > 0 for r in self.rays) for v in range(4)
            ) and all(
                any(_dot(z, r) < 0 for r in self.rays) for z, kind in self.constraints if kind == "<"
            )
        return self._satisfiable

    def forces_lighter(self, x: int, h: int) -> bool:
        """Folgt w_x < w_h? (Wie bei Z3: ein unerfuellbares System folgert alles.)

        Nur fuer Systeme ohne ``<=``-Bedingungen: Dann ist die Loesungsmenge
        das relative Innere des Kegels.
        """

        if not self.satisfiable():
            return True
        some = False
        for r in self.rays:
            d = r[x] - r[h]
            if d > 0:
                return False
            some = some or d < 0
        return some

    def interior_point(self) -> Vector:
        """Ganzzahlige Loesung im relativen Inneren (Summe aller Strahlen).

        Erfuellt alle Bedingungen, ``<`` echt; nur fuer erfuellbare Systeme.
        """

        return tuple(sum(r[k] for r in self.rays) for k in range(4))  # type: ignore[return-value]


@lru_cache(maxsize=400_000)
def cone_of(constraints: tuple[Constraint, ...]) -> Cone:
    """Kegel zu einer Folge von Bedingungen, mit Zwischenspeicher.

    Teilfolgen werden wiederverwendet: Der Kegel zu ``(c1, c2, c3)`` entsteht
    aus dem gespeicherten Kegel zu ``(c1, c2)``.
    """

    if not constraints:
        return Cone.orthant()
    return cone_of(constraints[:-1]).add(constraints[-1])


def constraints_of(scales: Iterable[object]) -> tuple[Constraint, ...]:
    """Bedingungen zu Waagen (Objekte mit ``vector`` und ``operator``).

    Die Reihenfolge bleibt erhalten: Wer nacheinander Bedingungen anhaengt
    (wie die Stufenberechnung mit neu gefolgerten Vergleichen), bekommt jeden
    Kegel aus dem vorigen und rechnet nur den letzten Schnitt neu.
    """

    return tuple((s.vector, s.operator) for s in scales)  # type: ignore[attr-defined]
