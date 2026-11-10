"""Semantische Gleichheit und kanonische Folgerungsabschluesse."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations
from hashlib import sha256
from math import gcd, lcm

import z3

from .model import A_FIXED_PERMUTATIONS, NAMES, Relation, System, SystemKey, generate_relations
from .solver import WeightSolver

RationalRow = tuple[Fraction, Fraction, Fraction, Fraction]
TheoryKey = tuple[tuple[tuple[int, int], ...], tuple[tuple[int, ...], ...]]


def _rref(rows: list[list[Fraction]], column_count: int = 4) -> tuple[list[list[Fraction]], list[int]]:
    matrix = [row[:] for row in rows if any(row)]
    pivot_columns: list[int] = []
    pivot_row = 0
    for column in range(column_count):
        found = next((row for row in range(pivot_row, len(matrix)) if matrix[row][column]), None)
        if found is None:
            continue
        matrix[pivot_row], matrix[found] = matrix[found], matrix[pivot_row]
        divisor = matrix[pivot_row][column]
        matrix[pivot_row] = [value / divisor for value in matrix[pivot_row]]
        for row in range(len(matrix)):
            if row == pivot_row or not matrix[row][column]:
                continue
            factor = matrix[row][column]
            matrix[row] = [
                value - factor * pivot_value
                for value, pivot_value in zip(matrix[row], matrix[pivot_row])
            ]
        pivot_columns.append(column)
        pivot_row += 1
        if pivot_row == len(matrix):
            break
    return matrix, pivot_columns


def _kernel_basis(rref: list[list[Fraction]], pivots: list[int]) -> list[list[Fraction]]:
    free_columns = [column for column in range(4) if column not in pivots]
    basis: list[list[Fraction]] = []
    for free in free_columns:
        vector = [Fraction(0) for _ in range(4)]
        vector[free] = Fraction(1)
        for row, pivot in enumerate(pivots):
            vector[pivot] = -rref[row][free]
        basis.append(vector)
    return basis


def _primitive_ray(values: list[Fraction]) -> tuple[int, ...]:
    denominator = 1
    for value in values:
        denominator = lcm(denominator, value.denominator)
    integers = [value.numerator * (denominator // value.denominator) for value in values]
    divisor = 0
    for value in integers:
        divisor = gcd(divisor, abs(value))
    if divisor == 0:
        raise ValueError("Nullfunktional in einer erfuellbaren strikten Theorie")
    return tuple(value // divisor for value in integers)


def _nonnegative_span_contains(target: tuple[int, ...], generators: list[tuple[int, ...]]) -> bool:
    """Exakter Caratheodory-Test in Dimension hoechstens vier."""

    dimension = len(target)
    for size in range(1, min(dimension, len(generators)) + 1):
        for subset in combinations(generators, size):
            augmented = [
                [Fraction(vector[row]) for vector in subset] + [Fraction(target[row])]
                for row in range(dimension)
            ]
            reduced, pivots = _rref(augmented, column_count=size)
            if len(pivots) != size:
                continue
            if any(all(not row[column] for column in range(size)) and row[size] for row in reduced):
                continue
            solution = [Fraction(0) for _ in range(size)]
            for row_index, pivot in enumerate(pivots):
                solution[pivot] = reduced[row_index][size]
            if all(value >= 0 for value in solution):
                return True
    return False


class TheoryCanonicalizer:
    """Schneller exakter Semantikschluessel fuer die homogenen Systeme.

    Er besteht aus dem rationalen Gleichungszeilenraum und den Extremstrahlen
    des dualen Ungleichungskegels (einschliesslich Positivitaet). Fuer jede
    erfuellbare Theorie ist dies aequivalent zur Modellmenge; ``Distinct``
    aendert den Schluessel nicht, weil die zulaessigen verschiedenen Punkte
    in jeder hier betrachteten, erfuellbaren Theorie dicht liegen.
    """

    @staticmethod
    def _representation(system: System) -> tuple[list[list[Fraction]], list[list[Fraction]]]:
        equality_rows = [
            [Fraction(lvalue - rvalue) for lvalue, rvalue in zip(relation.left, relation.right)]
            for relation in system.relations
            if relation.operator == "="
        ]
        equality_rref, pivots = _rref(equality_rows)
        basis = _kernel_basis(equality_rref, pivots)

        inequality_rows = [
            tuple(-1 if row == column else 0 for column in range(4))
            for row in range(4)
        ]
        inequality_rows.extend(
            tuple(lvalue - rvalue for lvalue, rvalue in zip(relation.left, relation.right))
            for relation in system.relations
            if relation.operator == "<"
        )
        projected_to_full: dict[tuple[int, ...], list[Fraction]] = {}
        free_columns = [column for column in range(4) if column not in pivots]
        for row in inequality_rows:
            projected = _primitive_ray(
                [sum(Fraction(row[index]) * vector[index] for index in range(4)) for vector in basis]
            )
            reduced_full = [Fraction(0) for _ in range(4)]
            for column, value in zip(free_columns, projected):
                reduced_full[column] = Fraction(value)
            projected_to_full.setdefault(projected, reduced_full)
        extreme = [
            ray
            for ray in projected_to_full
            if not _nonnegative_span_contains(
                ray, [other for other in projected_to_full if other != ray]
            )
        ]
        return equality_rref, [projected_to_full[ray] for ray in extreme]

    @staticmethod
    def _key_from_representation(
        equality_rows: list[list[Fraction]],
        facet_rows: list[list[Fraction]],
    ) -> TheoryKey:
        equality_rref, pivots = _rref(equality_rows)
        basis = _kernel_basis(equality_rref, pivots)
        extreme_rays = tuple(
            sorted(
                {
                    _primitive_ray(
                        [sum(row[index] * vector[index] for index in range(4)) for vector in basis]
                    )
                    for row in facet_rows
                }
            )
        )
        serialized_rref = tuple(
            tuple((value.numerator, value.denominator) for value in row)
            for row in equality_rref
        )
        return serialized_rref, extreme_rays

    @classmethod
    def key(cls, system: System) -> TheoryKey:
        return cls._key_from_representation(*cls._representation(system))

    @classmethod
    def _canonical_key_from_representation(
        cls,
        equality_rows: list[list[Fraction]],
        facet_rows: list[list[Fraction]],
    ) -> TheoryKey:
        def renamed(row: list[Fraction], permutation: tuple[int, int, int, int]) -> list[Fraction]:
            result = [Fraction(0) for _ in range(4)]
            for old_index, new_index in enumerate(permutation):
                result[new_index] = row[old_index]
            return result

        return min(
            cls._key_from_representation(
                [renamed(row, permutation) for row in equality_rows],
                [renamed(row, permutation) for row in facet_rows],
            )
            for permutation in A_FIXED_PERMUTATIONS
        )

    @classmethod
    def canonical_key(cls, system: System) -> TheoryKey:
        return cls._canonical_key_from_representation(*cls._representation(system))

    @classmethod
    def _implication_context(
        cls, system: System
    ) -> tuple[list[list[Fraction]], list[tuple[int, ...]]]:
        equality_rows, facet_rows = cls._representation(system)
        equality_rref, pivots = _rref(equality_rows)
        basis = _kernel_basis(equality_rref, pivots)
        generators = [
            _primitive_ray(
                [sum(facet[index] * vector[index] for index in range(4)) for vector in basis]
            )
            for facet in facet_rows
        ]
        return basis, generators

    @staticmethod
    def _entailed_in_context(
        relation: Relation,
        basis: list[list[Fraction]],
        generators: list[tuple[int, ...]],
    ) -> bool:
        row = [Fraction(lvalue - rvalue) for lvalue, rvalue in zip(relation.left, relation.right)]
        projected_values = [
            sum(row[index] * vector[index] for index in range(4)) for vector in basis
        ]
        if not any(projected_values):
            return relation.operator == "="
        if relation.operator == "=":
            return False
        target = _primitive_ray(projected_values)
        return target in generators or _nonnegative_span_contains(target, generators)

    @classmethod
    def entails(cls, system: System, relation: Relation) -> bool:
        return cls._entailed_in_context(relation, *cls._implication_context(system))

    @classmethod
    def output_representative(cls, system: System) -> System:
        context = cls._implication_context(system)
        forced_lt: set[tuple[int, int]] = set()
        for left in range(1, 4):
            for right in range(1, 4):
                if left == right:
                    continue
                relation = Relation(
                    tuple(1 if index == left else 0 for index in range(4)),  # type: ignore[arg-type]
                    "<",
                    tuple(1 if index == right else 0 for index in range(4)),  # type: ignore[arg-type]
                )
                if cls._entailed_in_context(relation, *context):
                    forced_lt.add((left, right))

        # Die verbotenen Aussagen lauten in (linke,rechte)-Form c<b, c<d, b<d.
        forbidden_new = ((2, 1), (2, 3), (1, 3))
        choices: list[System] = []
        for permutation in A_FIXED_PERMUTATIONS:
            inverse = {new: old for old, new in enumerate(permutation)}
            if any((inverse[left], inverse[right]) in forced_lt for left, right in forbidden_new):
                continue
            choices.append(system.renamed(permutation))
        if not choices:
            raise AssertionError("Keine mit der README-Reihenfolge vertraegliche Umbenennung gefunden")
        return min(choices, key=lambda candidate: candidate.key)


@dataclass(frozen=True)
class SemanticSignature:
    """Exakter kanonischer Abschluss plus kompakter stabiler Fingerabdruck."""

    closure: tuple[int, ...]

    @property
    def digest(self) -> str:
        bit_count = 567
        bits = 0
        for index in self.closure:
            bits |= 1 << index
        payload = bits.to_bytes((bit_count + 7) // 8, "little")
        return sha256(payload).hexdigest()


class SemanticCanonicalizer:
    """Berechnet Modellmengen-Gleichheit innerhalb des endlichen Atomraums.

    Fuer Systeme, die aus den 567 zulaessigen Relationsatomen bestehen, gilt:
    Zwei Systeme haben genau dann dieselbe Modellmenge, wenn sie denselben
    Abschluss aller aus ihnen folgenden Atome besitzen.
    """

    def __init__(self, solver: WeightSolver | None = None) -> None:
        self.solver = solver or WeightSolver(pairwise_distinct=True, arithmetic="real")
        self.universe = tuple(sorted(set(generate_relations()), key=lambda relation: relation.key))
        self.expressions = tuple(self.solver.expression(relation) for relation in self.universe)
        self.index = {relation: index for index, relation in enumerate(self.universe)}
        self.permutation_maps = tuple(
            tuple(self.index[relation.renamed(permutation)] for relation in self.universe)
            for permutation in A_FIXED_PERMUTATIONS
        )

    @staticmethod
    def _is_true(model: z3.ModelRef, expression: z3.BoolRef) -> bool:
        return z3.is_true(model.eval(expression, model_completion=True))

    def closure(self, system: System) -> tuple[int, ...]:
        """Berechnet den exakten Abschluss mit gebuendelten Gegenmodellen."""

        base = self.solver._solver(system.relations)
        if base.check() != z3.sat:
            raise ValueError("Der semantische Abschluss ist nur fuer erfuellbare Systeme definiert")
        model = base.model()
        known = {self.index[relation] for relation in system.relations}
        remaining = [
            index
            for index, expression in enumerate(self.expressions)
            if index not in known and self._is_true(model, expression)
        ]
        entailed = set(known)

        while remaining:
            candidate = remaining.pop()
            base.push()
            base.add(z3.Not(self.expressions[candidate]))
            result = base.check()
            if result == z3.unsat:
                entailed.add(candidate)
                base.pop()
                continue
            model = base.model()
            base.pop()
            remaining = [
                index
                for index in remaining
                if self._is_true(model, self.expressions[index])
            ]
        return tuple(sorted(entailed))

    def canonical_signature_from_closure(self, closure: tuple[int, ...]) -> SemanticSignature:
        canonical = min(
            tuple(sorted(mapping[index] for index in closure))
            for mapping in self.permutation_maps
        )
        return SemanticSignature(canonical)

    def canonical_signature(self, system: System) -> SemanticSignature:
        return self.canonical_signature_from_closure(self.closure(system))

    def equivalent(self, left: System, right: System) -> bool:
        return self.canonical_signature(left) == self.canonical_signature(right)

    def output_representative(self, system: System, closure: tuple[int, ...] | None = None) -> System:
        """Waehlt einen S3-Vertreter, der die README-Ordnungsverbote erfuellt."""

        closure = self.closure(system) if closure is None else closure
        forbidden = (
            self.index[Relation.from_mapping({"c": 1}, "<", {"b": 1})],  # b > c
            self.index[Relation.from_mapping({"c": 1}, "<", {"d": 1})],  # d > c
            self.index[Relation.from_mapping({"b": 1}, "<", {"d": 1})],  # d > b
        )
        choices: list[System] = []
        for permutation, mapping in zip(A_FIXED_PERMUTATIONS, self.permutation_maps):
            renamed_closure = {mapping[index] for index in closure}
            if any(index in renamed_closure for index in forbidden):
                continue
            choices.append(system.renamed(permutation))
        if not choices:
            raise AssertionError("Keine mit der README-Reihenfolge vertraegliche Umbenennung gefunden")
        return min(choices, key=lambda candidate: candidate.key)
