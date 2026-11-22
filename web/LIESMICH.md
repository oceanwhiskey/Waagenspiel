# Waagen-Spiel im Browser

Reine statische Seite (HTML, CSS, JavaScript, SVG), ohne Server-Code und ohne
fremde Dienste. Läuft auf dem Handy und am Rechner, lässt sich auf den
Startbildschirm legen und funktioniert danach auch offline.

## Online stellen

1. Den **Inhalt** dieses Ordners `web/` auf den Webspace hochladen, z. B. per
   SFTP nach `imazeki.de/` oder in einen Unterordner wie `imazeki.de/waagen/`.
   Alle Pfade sind relativ, beides funktioniert.
   `LIESMICH.md` und `tests.html` braucht es online nicht.
2. Die Seite muss über **https** erreichbar sein. Nur dann bietet das Handy
   „Zum Startbildschirm hinzufügen“ als App an und speichert sie für offline.
3. `.htaccess` ist für Apache-Webspace gedacht: Sie setzt die richtigen
   Dateitypen, packt die Rätseldatei (1,1 MB → etwa 75 KB) und sperrt die
   Testseite. Bei anderen Servern einfach weglassen.

Auf dem Handy: Seite öffnen, dann im Browser-Menü „Zum Startbildschirm“
(Android: Chrome-Menü ⋮, iPhone: Teilen-Knopf).

## Aktualisieren

Geänderte Dateien einfach erneut hochladen. Die `.htaccess` sorgt dafür, dass
Browser jedes Mal kurz nachfragen (`Cache-Control: no-cache`), und der Service
Worker holt immer zuerst die neue Fassung. Wenn sich `index.html` und
`oberflaeche.js` gemeinsam ändern, die Versionsnummer in beiden erhöhen
(`<meta name="waagenspiel-version">` und `VERSION`). Erwischt ein Browser
dann noch die alte Seite, lädt das Spiel sie von selbst neu.

## Lokal ausprobieren

```bash
python -m http.server 8000 --directory web
```

Dann <http://localhost:8000> öffnen. Direkt als Datei (`file://`) geht es
nicht, weil die Seite Module und `raetsel.json` nachlädt. Die Tests der
Spiellogik laufen unter <http://localhost:8000/tests.html>.

## Aufbau

| Datei | Inhalt |
|---|---|
| `spiel.js` | Spiellogik ohne Oberfläche: Runden, Partie, Punkte, Stufen, Bestenliste |
| `figuren.js` | SVG-Zeichnungen der Figuren und Waagen |
| `oberflaeche.js` | Bildschirme, Eingaben, Animationen; bekommt die Partie von außen |
| `raetsel.php` | Rätsel aus der Datenbank (alle 115 775) und anonyme Zähler je Rätsel |
| `raetsel.json` | Notvorrat ohne Netz: 4 000 Rätsel (1 000 je Stufe), erzeugt mit `python webversion.py` |
| `verwaltung.php` | Rätsel einspielen, Sicherung holen und zurückspielen (nur mit Verwaltungsschlüssel) |
| `spiel.css` | Aussehen |
| `bestenliste.js`, `bestenliste.php` | Globale Bestenliste (Browser und Server) |
| `sw.js`, `manifest.webmanifest`, `icon*` | Installierbar und offline spielbar; der Service Worker speichert nur die Spieldateien |

Die Rätsel stammen aus dem exakt geprüften Katalog: Jedes hat genau eine
schwerste Figur, und jede Waage wird gebraucht. Ihre feste `id` ist die
Position in `data/katalog.json.gz`; der Katalog darf deshalb nur hinten
ergänzt, nicht umsortiert werden. Das Spiel holt sie vom Server und hält je
Stufe einen kleinen Vorrat bereit; ohne Netz nimmt es den Notvorrat aus
`raetsel.json`. Tipps und Erklärungen gibt es nicht mehr (Menschen lösen
anders als die Herleitung).

## Rätsel-Datenbank, Statistik und Sicherung

- `python webversion.py` schreibt `web/raetsel.json` und `build/raetsel.tsv.gz`
  (alle Rätsel für die Datenbank).
- `python werkzeuge/datenbank.py einspielen` lädt sie in Portionen hoch und
  tauscht die Tabelle erst am Ende aus; das Spiel läuft dabei weiter.
- Je Rätsel und Modus (`zeit`, `ueben`) zählt der Server nur `gespielt`,
  `richtig` und die Summe der Bedenkzeit (`zeit_ms`, je Antwort höchstens
  10 Minuten). Nichts davon lässt sich einer Person zuordnen.
- `python werkzeuge/datenbank.py sichern` holt Bestenliste und Statistik als
  `waagenspiel-JJJJ-MM-TT-HHMMSS.json.gz`; `zurueckspielen DATEI` spielt eine
  Sicherung zurück. Die Rätsel selbst sind nicht in der Sicherung, sie lassen
  sich jederzeit neu einspielen.
- Einstellungen in `~/.waagenspiel/datenbank.ini` (Abschnitt `[verwaltung]`
  mit `url`, `schluessel`, `sicherungen`). Derselbe Schlüssel liegt auf dem
  Server in `waagenspiel-config/verwaltung.txt` neben `db.ini`.

## Bestenliste

Eigene Rekorde und Einstellungen liegen nur im Browser des Geräts
(`localStorage`). Dazu kommt eine **Bestenliste** je Schwierigkeit und Zeit
(`bestenliste.php`, `inc/gemeinsam.php`, `bestenliste.js`): Nach jeder vollen
Partie auf Zeit kann sich jeder mit einem frei gewählten Namen eintragen
(einmal je Partie). Alle Einträge bleiben stehen; angezeigt werden die besten
100 je Kategorie. Es gibt keine Anmeldung und keine Spielerkonten.

- Braucht PHP (ab 7.4) und eine MySQL-Datenbank. Die Zugangsdaten liegen in
  `waagenspiel-config/db.ini` **außerhalb** der Webseiten (die PHP-Dateien
  suchen sie in den Ordnern darüber). Format:
  `[datenbank]` mit `host`, `port`, `name`, `benutzer`, `passwort` (in
  Anführungszeichen). Die Tabellen (`ws_…`) entstehen beim ersten Aufruf.
- `inc/` ist per `.htaccess` gesperrt.
- Schutz gegen einfaches Schummeln: Beim Spielstart gibt es eine signierte
  Spielmarke. Der Server nimmt sie erst nach Ablauf der Spielzeit an, nur
  einmal und nur mit glaubwürdigen Punkten (höchstens 150 je Sekunde). Wer es
  darauf anlegt, kann im Browser trotzdem schummeln.
- Die Einträge stehen in der Tabelle `ws_rekord` (der Name stammt aus der
  Zeit, als nur Rekorde zählten). Zurücksetzen: Tabelle leeren. Einen
  unpassenden Eintrag entfernen: seine Zeile löschen.
- Ohne PHP und Datenbank läuft das Spiel ganz normal, nur ohne Bestenliste.
- `datenschutz.html` beschreibt, was gespeichert wird. `impressum.html`
  enthält die Anbieterangaben.
