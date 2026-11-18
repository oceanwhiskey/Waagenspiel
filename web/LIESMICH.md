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
| `raetsel.json` | 1 600 Rätsel (400 je Stufe) mit Lösungsschritten, erzeugt mit `python webversion.py` |
| `spiel.css` | Aussehen |
| `bestenliste.js`, `bestenliste.php` | Globale Bestenliste (Browser und Server) |
| `sw.js`, `manifest.webmanifest`, `icon*` | Installierbar und offline spielbar; der Service Worker speichert nur die Spieldateien |

Die Rätsel stammen aus dem exakt geprüften Katalog: Jedes hat genau eine
schwerste Figur, und jede Waage wird gebraucht. Im Browser läuft kein Löser,
deshalb sind die Lösungsschritte vorberechnet. Mehr Rätsel je Stufe:
`python webversion.py --je-stufe 800`.

## Bestenliste

Eigene Rekorde und Einstellungen liegen nur im Browser des Geräts
(`localStorage`). Dazu kommt eine **globale Bestenliste** (`bestenliste.php`,
`bestenliste.js`): Je Schwierigkeit und Zeit gibt es einen Rekord, und wer ihn
in einer vollen Partie auf Zeit bricht, darf sich mit einem Namen eintragen.
Übertragen werden nur Kategorie, Punkte und dieser Name.

- Braucht PHP (ab 7.4) und Schreibrechte im Ordner der Seite. Beim ersten
  Aufruf legt `bestenliste.php` den Ordner `bestenliste-daten/` an, sperrt ihn
  per `.htaccess` und erzeugt dort einen geheimen Schlüssel (`geheim.txt`).
  Der Schlüssel steht deshalb in keinem Repository.
- Schutz gegen einfaches Schummeln: Beim Spielstart gibt es eine signierte
  Spielmarke. Der Server nimmt sie erst nach Ablauf der Spielzeit an, nur
  einmal und nur mit glaubwürdigen Punkten (höchstens 60 je Sekunde). Wer es
  darauf anlegt, kann im Browser trotzdem schummeln.
- Zurücksetzen: `bestenliste-daten/daten.json` löschen. Einen einzelnen
  Eintrag entfernen: in dieser Datei den Eintrag der Kategorie löschen.
- Ohne PHP läuft das Spiel ganz normal, nur ohne globale Bestenliste.
