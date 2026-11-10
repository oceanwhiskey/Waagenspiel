"""Kommandozeilenprogramm zur Erzeugung von ``data/systems.json``."""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import sys
import time
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parent
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from waagenspiel.generator import GenerationStats, SystemGenerator  # noqa: E402
from waagenspiel.model import NAMES, System  # noqa: E402
from waagenspiel.semantic import TheoryCanonicalizer, TheoryKey  # noqa: E402

_WORKER_GENERATOR: SystemGenerator | None = None


def _worker_init() -> None:
    global _WORKER_GENERATOR
    _WORKER_GENERATOR = SystemGenerator()


def _better(left: System, right: System) -> System:
    """Kuerzeste, danach strukturell lexikographisch kleinste Basis."""

    return min((left, right), key=lambda system: (len(system.relations), system.key))


def _triple_chunk(
    task: tuple[int, tuple[tuple[int, int], ...]]
) -> tuple[int, dict[TheoryKey, System], GenerationStats]:
    if _WORKER_GENERATOR is None:  # auch direkt in Tests verwendbar
        _worker_init()
    assert _WORKER_GENERATOR is not None
    chunk_number, prefixes = task
    stats = GenerationStats(relation_count=len(_WORKER_GENERATOR.relations))
    fixed_classes: dict[TheoryKey, tuple[System, object]] = {}
    for system in _WORKER_GENERATOR.generate_triples(stats, pair_prefixes=prefixes):
        representation = TheoryCanonicalizer._representation(system)
        fixed_key = TheoryCanonicalizer._key_from_representation(*representation)
        previous = fixed_classes.get(fixed_key)
        if previous is None or _better(previous[0], system) is system:
            fixed_classes[fixed_key] = (system, representation)

    classes: dict[TheoryKey, System] = {}
    for system, representation_object in fixed_classes.values():
        representation = representation_object  # Typ bleibt lokal und wird nicht serialisiert.
        key = TheoryCanonicalizer._canonical_key_from_representation(*representation)  # type: ignore[arg-type]
        previous = classes.get(key)
        classes[key] = system if previous is None else _better(previous, system)
    return chunk_number, classes, stats


def _merge(target: dict[TheoryKey, System], source: Iterable[tuple[TheoryKey, System]]) -> None:
    for key, system in source:
        previous = target.get(key)
        target[key] = system if previous is None else _better(previous, system)


def _add_stats(target: GenerationStats, source: GenerationStats) -> None:
    target.relation_count = max(target.relation_count, source.relation_count)
    target.pair_prefixes += source.pair_prefixes
    target.candidates_checked += source.candidates_checked
    target.countermodels += source.countermodels
    target.systems_found += source.systems_found


def _theory_digest(key: TheoryKey) -> str:
    payload = json.dumps(key, ensure_ascii=True, separators=(",", ":")).encode("ascii")
    return sha256(payload).hexdigest()


def generate_classes(*, sizes: tuple[int, ...], workers: int, quiet: bool = False) -> tuple[dict[TheoryKey, System], GenerationStats]:
    generator = SystemGenerator()
    stats = GenerationStats(relation_count=len(generator.relations))
    classes: dict[TheoryKey, System] = {}

    if 2 in sizes:
        pair_stats = GenerationStats(relation_count=len(generator.relations))
        for system in generator.generate_pairs(pair_stats):
            key = TheoryCanonicalizer.canonical_key(system)
            previous = classes.get(key)
            classes[key] = system if previous is None else _better(previous, system)
        _add_stats(stats, pair_stats)
        if not quiet:
            print(
                f"Zweiersysteme: {pair_stats.systems_found} strukturell, "
                f"{len(classes)} semantische Klassen",
                flush=True,
            )

    if 3 in sizes:
        prefixes = [
            (first, second)
            for first in generator._orbit_minimum
            for second in range(first + 1, len(generator.relations) - 1)
        ]
        # Genuegend gross fuer lokale semantische Deduplizierung, aber klein
        # genug fuer gute Lastverteilung und regelmaessige Fortschrittswerte.
        chunk_size = 50
        tasks = [
            (chunk_number, tuple(prefixes[start : start + chunk_size]))
            for chunk_number, start in enumerate(range(0, len(prefixes), chunk_size), start=1)
        ]
        completed = 0
        started = time.monotonic()
        if workers == 1:
            _worker_init()
            iterator = map(_triple_chunk, tasks)
            pool = None
        else:
            context = mp.get_context("spawn")
            pool = context.Pool(processes=workers, initializer=_worker_init)
            iterator = pool.imap_unordered(_triple_chunk, tasks, chunksize=1)
        try:
            for _chunk_number, local_classes, local_stats in iterator:
                _merge(classes, local_classes.items())
                _add_stats(stats, local_stats)
                completed += 1
                if not quiet:
                    elapsed = time.monotonic() - started
                    print(
                        f"Dreier-Chunks: {completed}/{len(tasks)}; "
                        f"strukturell={stats.systems_found}; Klassen={len(classes)}; "
                        f"Zeit={elapsed:.1f}s",
                        flush=True,
                    )
        finally:
            if pool is not None:
                pool.close()
                pool.join()
    return classes, stats


def write_json(path: Path, classes: dict[TheoryKey, System], stats: GenerationStats) -> None:
    rows: list[tuple[TheoryKey, System]] = []
    for semantic_key, system in classes.items():
        rows.append((semantic_key, TheoryCanonicalizer.output_representative(system)))
    rows.sort(key=lambda item: (len(item[1].relations), item[0], item[1].key))

    systems = []
    for number, (semantic_key, system) in enumerate(rows, start=1):
        item = system.to_dict()
        item["id"] = f"s{number:06d}"
        item["semantic_key"] = _theory_digest(semantic_key)
        systems.append(item)

    document = {
        "metadata": {
            "schema_version": 1,
            "variables": list(NAMES),
            "domain": "pairwise_distinct_positive_integers",
            "relation_normalization": "primitive_coefficients",
            "equivalence": "same_solution_set_up_to_variable_permutation; winner_named_a",
            "redundancy": "logical_entailment_over_the_domain",
            "relation_universe_size": 567,
            "a_compatible_relation_count": stats.relation_count,
            "system_count": len(systems),
            "structural_systems_before_semantic_deduplication": stats.systems_found,
        },
        "systems": systems,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Erzeugt die Menge S des Waagenspiels exakt.")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data" / "systems.json")
    parser.add_argument("--size", type=int, choices=(2, 3), action="append", dest="sizes")
    parser.add_argument(
        "--workers",
        type=int,
        default=max(1, min(3, os.cpu_count() or 1)),
        help="Anzahl paralleler Prozesse fuer Dreiersysteme (Standard: max. 3)",
    )
    parser.add_argument("--quiet", action="store_true")
    return parser.parse_args()


def main() -> int:
    arguments = parse_args()
    sizes = tuple(sorted(set(arguments.sizes or (2, 3))))
    if arguments.workers < 1:
        raise SystemExit("--workers muss mindestens 1 sein")
    started = time.monotonic()
    classes, stats = generate_classes(sizes=sizes, workers=arguments.workers, quiet=arguments.quiet)
    write_json(arguments.output.resolve(), classes, stats)
    if not arguments.quiet:
        print(
            f"Fertig: {len(classes)} Systeme in {arguments.output.resolve()} "
            f"({time.monotonic() - started:.1f}s)",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    mp.freeze_support()
    raise SystemExit(main())
