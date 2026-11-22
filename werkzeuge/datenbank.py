"""Server-Datenbank der Web-Version: Raetsel einspielen, sichern, zurueckspielen.

    python werkzeuge/datenbank.py sichern                 # Bestenliste + Statistik holen
    python werkzeuge/datenbank.py einspielen              # build/raetsel.tsv.gz hochladen
    python werkzeuge/datenbank.py zurueckspielen DATEI    # Sicherung wieder einspielen

Die Einstellungen stehen ausserhalb des Repos in ~/.waagenspiel/datenbank.ini::

    [verwaltung]
    url = https://imazeki.de
    schluessel = <Inhalt von waagenspiel-config/verwaltung.txt auf dem Server>
    sicherungen = C:/Pfad/zum/Ordner/fuer/Sicherungen

Sicherungen sind gepackte JSON-Dateien ``waagenspiel-JJJJ-MM-TT-HHMMSS.json.gz`` mit
Bestenliste (Namen!) und Statistik. Sie gehoeren deshalb nicht ins Repo. Die
Raetsel selbst sind nicht dabei: Sie lassen sich jederzeit aus
``data/katalog.json.gz`` mit ``webversion.py`` neu erzeugen und einspielen.
"""

from __future__ import annotations

import argparse
import configparser
import gzip
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INI = Path.home() / ".waagenspiel" / "datenbank.ini"
TSV = ROOT / "build" / "raetsel.tsv.gz"
PORTION = 4000


def settings(url: str | None) -> dict[str, str]:
    parser = configparser.ConfigParser(interpolation=None)
    if not parser.read(INI, encoding="utf-8") or "verwaltung" not in parser:
        raise SystemExit(f"Einstellungen fehlen: {INI}")
    values = dict(parser["verwaltung"])
    if url:
        values["url"] = url
    return values


def call(conf: dict[str, str], data: dict[str, object]) -> dict:
    body = urllib.parse.urlencode({k: str(v) for k, v in data.items()}).encode()
    req = urllib.request.Request(conf["url"].rstrip("/") + "/verwaltung.php", data=body)
    req.add_header("X-Waagenspiel-Verwaltung", conf["schluessel"])
    req.add_header("User-Agent", "waagenspiel-werkzeug")
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            answer = json.loads(response.read())
    except urllib.error.HTTPError as error:
        try:
            answer = json.loads(error.read())
        except ValueError:
            raise SystemExit(f"Server-Fehler {error.code}") from None
    if not answer.get("ok"):
        raise SystemExit(f"Server meldet: {answer.get('fehler')}")
    return answer


def import_lines(path: Path) -> list[str]:
    """TSV-Zeilen mit laufender Nummer je Stufe: id, stufe, nr, abkuerzung, waagen."""

    numbers: dict[str, int] = {}
    lines = []
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            index, level, shortcut, scales = line.rstrip("\n").split("\t")
            numbers[level] = numbers.get(level, 0) + 1
            lines.append(f"{index}\t{level}\t{numbers[level]}\t{shortcut}\t{scales}")
    return lines


def cmd_import(conf: dict[str, str], path: Path) -> None:
    lines = import_lines(path)
    call(conf, {"aktion": "import_beginnen"})
    for start in range(0, len(lines), PORTION):
        call(conf, {"aktion": "import_teil", "zeilen": "\n".join(lines[start:start + PORTION])})
        print(f"\r{min(start + PORTION, len(lines))}/{len(lines)}", end="", flush=True)
    print()
    done = call(conf, {"aktion": "import_abschliessen", "anzahl": len(lines)})
    print(f"Eingespielt: {done['anzahl']} Raetsel")


def cmd_backup(conf: dict[str, str], folder: Path | None) -> Path:
    data = call(conf, {"aktion": "sicherung"})
    data.pop("ok", None)
    folder = folder or Path(conf.get("sicherungen") or Path.home() / ".waagenspiel" / "sicherungen")
    folder.mkdir(parents=True, exist_ok=True)
    out = folder / f"waagenspiel-{time.strftime('%Y-%m-%d-%H%M%S')}.json.gz"
    with gzip.open(out, "wt", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False)
    print(f"{out}: {len(data['rekord'])} Bestenlisten-Eintraege, {len(data['statistik'])} Statistik-Zeilen, "
          f"{data['raetsel']} Raetsel auf dem Server")
    return out


def cmd_restore(conf: dict[str, str], path: Path) -> None:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        data = json.load(handle)
    for table in ("rekord", "statistik"):
        rows = data[table]
        if data[f"{table}_spalten"] != {"rekord": ["id", "kategorie", "name", "punkte", "erreicht"],
                                        "statistik": ["raetsel_id", "modus", "gespielt", "richtig", "zeit_ms"]}[table]:
            raise SystemExit(f"Unerwartete Spalten in {table}")
        for start in range(0, max(len(rows), 1), PORTION):
            call(conf, {"aktion": "wiederherstellen", "tabelle": table, "leeren": int(start == 0),
                        "zeilen": json.dumps(rows[start:start + PORTION], ensure_ascii=False)})
        print(f"{table}: {len(rows)} Zeilen zurueckgespielt")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", help="anderer Server, z. B. ein Testordner")
    sub = parser.add_subparsers(dest="befehl", required=True)
    backup = sub.add_parser("sichern")
    backup.add_argument("--ordner", type=Path)
    importing = sub.add_parser("einspielen")
    importing.add_argument("datei", type=Path, nargs="?", default=TSV)
    restore = sub.add_parser("zurueckspielen")
    restore.add_argument("datei", type=Path)
    args = parser.parse_args(argv)
    conf = settings(args.url)
    if args.befehl == "sichern":
        cmd_backup(conf, args.ordner)
    elif args.befehl == "einspielen":
        cmd_import(conf, args.datei)
    else:
        cmd_restore(conf, args.datei)
    return 0


if __name__ == "__main__":
    sys.exit(main())
