"""Endliches, kanonisches Datenmodell fuer Relationen und Systeme.

Eine Seite einer Relation ist ein Multiset der vier Namen ``a,b,c,d``.  Wir
speichern es als Koeffizientenvektor.  Damit sind Vergleiche, Hashing,
Umbenennungen und JSON-Ausgabe eindeutig und ohne String-Parsen moeglich.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations, product
from math import gcd
from typing import Iterable, Iterator, Literal, Mapping, Sequence

NAMES: tuple[str, ...] = ("a", "b", "c", "d")
NAME_TO_INDEX = {name: index for index, name in enumerate(NAMES)}
Operator = Literal["<", "="]
Vector = tuple[int, int, int, int]
Permutation = tuple[int, int, int, int]

ALL_PERMUTATIONS: tuple[Permutation, ...] = tuple(permutations(range(4)))
A_FIXED_PERMUTATIONS: tuple[Permutation, ...] = tuple(
    permutation for permutation in ALL_PERMUTATIONS if permutation[0] == 0
)


def _vector(values: Sequence[int]) -> Vector:
    if len(values) != 4:
        raise ValueError("Ein Koeffizientenvektor muss genau vier Eintraege haben")
    vector = tuple(values)
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in vector):
        raise ValueError("Koeffizienten muessen nichtnegative ganze Zahlen sein")
    return vector  # type: ignore[return-value]


def _renamed(vector: Vector, permutation: Permutation) -> Vector:
    """Benennt Variable i in Variable permutation[i] um."""

    result = [0, 0, 0, 0]
    for old_index, new_index in enumerate(permutation):
        result[new_index] = vector[old_index]
    return tuple(result)  # type: ignore[return-value]


@dataclass(frozen=True, order=True)
class Relation:
    """Eine gekuerzte Gleichung oder strikte Ungleichung."""

    left: Vector
    operator: Operator
    right: Vector

    def __post_init__(self) -> None:
        left = _vector(self.left)
        right = _vector(self.right)
        if self.operator not in ("<", "="):
            raise ValueError("operator muss '<' oder '=' sein")
        if not 1 <= sum(left) <= 3 or not 1 <= sum(right) <= 3:
            raise ValueError("Auf jeder Seite muessen ein bis drei Elemente stehen")
        if any(lvalue and rvalue for lvalue, rvalue in zip(left, right)):
            raise ValueError("Eine Relation muss gekuerzt sein (disjunkte Traeger)")
        common_divisor = 0
        for value in (*left, *right):
            common_divisor = gcd(common_divisor, value)
        if common_divisor > 1:
            left = tuple(value // common_divisor for value in left)  # type: ignore[assignment]
            right = tuple(value // common_divisor for value in right)  # type: ignore[assignment]
        if self.operator == "=":
            difference = tuple(lvalue - rvalue for lvalue, rvalue in zip(left, right))
            first_nonzero = next(value for value in difference if value)
            if first_nonzero < 0:
                left, right = right, left
        object.__setattr__(self, "left", left)
        object.__setattr__(self, "right", right)

    @classmethod
    def from_mapping(
        cls,
        left: Mapping[str, int],
        operator: Operator,
        right: Mapping[str, int],
    ) -> "Relation":
        unknown = (set(left) | set(right)) - set(NAMES)
        if unknown:
            raise ValueError(f"Unbekannte Namen: {sorted(unknown)}")
        return cls(
            tuple(left.get(name, 0) for name in NAMES),  # type: ignore[arg-type]
            operator,
            tuple(right.get(name, 0) for name in NAMES),  # type: ignore[arg-type]
        )

    @property
    def key(self) -> tuple[int, Vector, Vector]:
        return (0 if self.operator == "=" else 1, self.left, self.right)

    def renamed(self, permutation: Permutation) -> "Relation":
        if tuple(sorted(permutation)) != (0, 1, 2, 3):
            raise ValueError("Keine Permutation von (0,1,2,3)")
        return Relation(_renamed(self.left, permutation), self.operator, _renamed(self.right, permutation))

    @staticmethod
    def _side_text(vector: Vector) -> str:
        terms: list[str] = []
        for coefficient, name in zip(vector, NAMES):
            if coefficient == 1:
                terms.append(name)
            elif coefficient > 1:
                terms.append(f"{coefficient}{name}")
        return " + ".join(terms)

    def __str__(self) -> str:
        return f"{self._side_text(self.left)} {self.operator} {self._side_text(self.right)}"

    def to_dict(self) -> dict[str, object]:
        return {
            "left": {name: value for name, value in zip(NAMES, self.left) if value},
            "operator": self.operator,
            "right": {name: value for name, value in zip(NAMES, self.right) if value},
            "display": str(self),
        }


SystemKey = tuple[tuple[int, Vector, Vector], ...]


@dataclass(frozen=True)
class System:
    """Eine ungeordnete Menge aus zwei oder drei verschiedenen Relationen."""

    relations: tuple[Relation, ...]

    def __init__(self, relations: Iterable[Relation]) -> None:
        normalized = tuple(sorted(set(relations), key=lambda relation: relation.key))
        if len(normalized) not in (2, 3):
            raise ValueError("Ein System muss genau zwei oder drei verschiedene Relationen enthalten")
        object.__setattr__(self, "relations", normalized)

    @property
    def key(self) -> SystemKey:
        return tuple(relation.key for relation in self.relations)

    def renamed(self, permutation: Permutation) -> "System":
        return System(relation.renamed(permutation) for relation in self.relations)

    def canonical_key(self, *, fix_a: bool = False) -> SystemKey:
        permutations_to_use = A_FIXED_PERMUTATIONS if fix_a else ALL_PERMUTATIONS
        return min(self.renamed(permutation).key for permutation in permutations_to_use)

    def canonical(self, *, fix_a: bool = False) -> "System":
        permutations_to_use = A_FIXED_PERMUTATIONS if fix_a else ALL_PERMUTATIONS
        return min(
            (self.renamed(permutation) for permutation in permutations_to_use),
            key=lambda system: system.key,
        )

    def is_canonical(self, *, fix_a: bool = False) -> bool:
        return self.key == self.canonical_key(fix_a=fix_a)

    def to_dict(self) -> dict[str, object]:
        return {"relations": [relation.to_dict() for relation in self.relations]}


def generate_relations() -> Iterator[Relation]:
    """Erzeugt jede nach den Punkten 2--4 und 7--8 zulaessige Relation einmal.

    Bei Gleichungen wird die Vertauschung beider Seiten kanonisiert. Bei einer
    strikten Ungleichung sind die beiden Richtungen dagegen verschieden.
    """

    seen: set[Relation] = set()
    for left in product(range(4), repeat=4):
        if not 1 <= sum(left) <= 3:
            continue
        for right in product(range(4), repeat=4):
            if not 1 <= sum(right) <= 3:
                continue
            if any(lvalue and rvalue for lvalue, rvalue in zip(left, right)):
                continue
            for operator in ("=", "<"):
                relation = Relation(left, operator, right)  # type: ignore[arg-type]
                if relation not in seen:
                    seen.add(relation)
                    yield relation
